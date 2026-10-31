"""S26-A servis: ölçüm cihazı + kalibrasyon, kontrol planı + SPC ölçümü (ADR-0025).

**Kalibrasyonu geçmiş cihazla ölçüm girilmez.** ISO 9001 7.1.5: geçerliliği doğrulanmamış
ekipmanla yapılan ölçüm kalite kanıtı değildir; kabul edilseydi kart "kararlı" görünür ama
dayanaksız olurdu. Hata 422 ``KALIBRASYON_GECERSIZ``.

**Kural ihlali yalnız yeni noktada olay üretir.** Her ölçümde kart yeniden çizilir ama
``kalite.spc_ihlal`` yalnız yeni alt grubun *tamamladığı* ihlaller için yayınlanır (kenar
tetikli); eski bir ihlal her yeni ölçümde tekrar bildirim üretmez.

**Limitler:** sabitlenmişse (faz-I) onlar, değilse o ana kadarki tüm alt gruplardan hesaplanır.
Sabitlenmemiş kartta ihlal bilgisi geçicidir; ekran bunu söyler.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.gercekzaman import yayinla
from app.core.olaylar import olay_yayinla
from app.kimlik.models import Kullanici
from app.modules.kalite import spc
from app.modules.kalite.models import (
    KalibrasyonKaydi,
    KontrolKarakteristigi,
    KontrolPlani,
    OlcumCihazi,
    SpcAltGrup,
)

OLAY_SPC_IHLAL = "kalite.spc_ihlal"
OLAY_KALIBRASYON = "kalibrasyon.yaklasiyor"


# ── Ölçüm cihazı ─────────────────────────────────────────────────────────────


def cihaz_gecerli_mi(cihaz: OlcumCihazi, bugun: date) -> bool:
    return (
        cihaz.durum == "aktif"
        and cihaz.sonraki_kalibrasyon_tarihi is not None
        and cihaz.sonraki_kalibrasyon_tarihi >= bugun
    )


def cihaz_durum_etiketi(cihaz: OlcumCihazi, bugun: date, esik_gun: int = 30) -> str:
    """Ekranın tek bakışta okuduğu durum: gecerli / yaklasiyor / gecmis / kalibrasyonsuz / ..."""
    if cihaz.durum != "aktif":
        return cihaz.durum
    if cihaz.sonraki_kalibrasyon_tarihi is None:
        return "kalibrasyonsuz"
    if cihaz.sonraki_kalibrasyon_tarihi < bugun:
        return "gecmis"
    if cihaz.sonraki_kalibrasyon_tarihi <= bugun + timedelta(days=esik_gun):
        return "yaklasiyor"
    return "gecerli"


async def kalibrasyon_ekle(
    db: AsyncSession,
    cihaz: OlcumCihazi,
    *,
    tarih: date,
    sonuc: str,
    sertifika_no: str,
    kurum: str,
    aciklama: str,
    belge_id: int | None,
    kullanici: Kullanici,
) -> KalibrasyonKaydi:
    if tarih > datetime.now(UTC).date():
        raise DogrulamaHatasi(
            "Kalibrasyon tarihi gelecekte olamaz",
            detaylar=[{"alan": "tarih", "mesaj": tarih.isoformat()}],
        )
    if cihaz.son_kalibrasyon_tarihi is not None and tarih < cihaz.son_kalibrasyon_tarihi:
        raise DogrulamaHatasi(
            "Kayıtlı son kalibrasyondan eski tarih",
            detaylar=[
                {"alan": "tarih", "mesaj": f"Son kalibrasyon {cihaz.son_kalibrasyon_tarihi}"}
            ],
        )
    kayit = KalibrasyonKaydi(
        cihaz_id=cihaz.id,
        tarih=tarih,
        sonuc=sonuc,
        sertifika_no=sertifika_no,
        kurum=kurum,
        aciklama=aciklama,
        belge_id=belge_id,
        kaydeden_kullanici_id=kullanici.id,
    )
    db.add(kayit)
    cihaz.son_kalibrasyon_tarihi = tarih
    if sonuc == "uygunsuz":
        # Uygunsuz kalibrasyon: cihaz ayarlanıp yeniden kalibre edilene kadar ölçümde kullanılmaz.
        cihaz.durum = "kullanim_disi"
    else:
        cihaz.durum = "aktif"
        cihaz.sonraki_kalibrasyon_tarihi = tarih + timedelta(days=cihaz.kalibrasyon_periyodu_gun)
        cihaz.yaklasim_bildirildi = False  # yeni dönem: hatırlatma yeniden kurulur
    await db.flush()
    return kayit


async def kalibrasyon_tara(
    db: AsyncSession, *, tenant_slug: str, esik_gun: int = 30, bugun: date | None = None
) -> int:
    """Kalibrasyonu ``esik_gun`` içinde dolacak (ya da dolmuş) aktif cihazlar için bir kez olay."""
    bugun = bugun or datetime.now(UTC).date()
    adaylar = (
        (
            await db.execute(
                select(OlcumCihazi).where(
                    OlcumCihazi.durum == "aktif",
                    OlcumCihazi.yaklasim_bildirildi.is_(False),
                    OlcumCihazi.sonraki_kalibrasyon_tarihi.is_not(None),
                    OlcumCihazi.sonraki_kalibrasyon_tarihi <= bugun + timedelta(days=esik_gun),
                )
            )
        )
        .scalars()
        .all()
    )
    for c in adaylar:
        assert c.sonraki_kalibrasyon_tarihi is not None
        await olay_yayinla(
            db,
            olay_turu=OLAY_KALIBRASYON,
            govde={
                "kaynak_id": c.id,
                "cihaz_id": c.id,
                "kod": c.kod,
                "ad": c.ad,
                "sonraki_kalibrasyon_tarihi": c.sonraki_kalibrasyon_tarihi.isoformat(),
                "kalan_gun": (c.sonraki_kalibrasyon_tarihi - bugun).days,
                "sorumlu_kullanici_id": c.sorumlu_kullanici_id,
            },
        )
        c.yaklasim_bildirildi = True
        await yayinla(tenant_slug, {"tur": OLAY_KALIBRASYON, "id": c.id})
    await db.flush()
    return len(adaylar)


# ── Kontrol planı ────────────────────────────────────────────────────────────


def plan_kodu(plan_id: int) -> str:
    return f"KP-{datetime.now(UTC).year}-{plan_id:05d}"


async def plan_getir(db: AsyncSession, plan_id: int) -> KontrolPlani:
    plan = (
        await db.execute(
            select(KontrolPlani)
            .where(KontrolPlani.id == plan_id)
            .options(selectinload(KontrolPlani.karakteristikler))
        )
    ).scalar_one_or_none()
    if plan is None:
        raise KaynakBulunamadi("Kontrol planı bulunamadı")
    return plan


def karakteristik_dogrula(alt: Any, ust: Any, n: int) -> None:
    if n not in spc.SABITLER:
        raise DogrulamaHatasi(
            "Alt grup boyutu 2 ile 10 arasında olmalı (X̄-R kartı)",
            detaylar=[{"alan": "alt_grup_boyutu", "mesaj": str(n)}],
        )
    if alt is not None and ust is not None and alt >= ust:
        raise DogrulamaHatasi(
            "Alt tolerans üst toleranstan küçük olmalı",
            detaylar=[{"alan": "alt_tolerans", "mesaj": ""}],
        )


# ── SPC kartı ────────────────────────────────────────────────────────────────


def _limitler_sozlukten(d: dict[str, Any]) -> spc.Limitler:
    return spc.Limitler(**{k: d[k] for k in spc.Limitler.__dataclass_fields__})


async def _alt_gruplar(db: AsyncSession, karakteristik_id: int) -> list[SpcAltGrup]:
    return list(
        (
            await db.execute(
                select(SpcAltGrup)
                .where(SpcAltGrup.karakteristik_id == karakteristik_id)
                .order_by(SpcAltGrup.sira)
            )
        )
        .scalars()
        .all()
    )


def kart_hesapla(k: KontrolKarakteristigi, gruplar: list[SpcAltGrup]) -> dict[str, Any]:
    degerler = [[float(v) for v in g.degerler] for g in gruplar]
    noktalar = [
        {
            "sira": g.sira,
            "zaman": g.zaman,
            "xbar": spc.ortalama(d),
            "r": spc.aralik(d),
            "kayitli_ihlaller": g.ihlaller,
        }
        for g, d in zip(gruplar, degerler, strict=True)
    ]
    uyarilar: list[str] = []
    limitler: spc.Limitler | None = None
    if k.sabit_limitler:
        limitler = _limitler_sozlukten(k.sabit_limitler)
    elif len(degerler) >= spc.EN_AZ_ALT_GRUP:
        limitler = spc.xbar_r_limitleri(degerler)
        uyarilar.append("Limitler sabitlenmedi; her yeni ölçümle yeniden hesaplanıyor.")
    if limitler is not None and limitler.alt_grup_sayisi < spc.ONERILEN_ALT_GRUP:
        uyarilar.append(
            f"Limitler {limitler.alt_grup_sayisi} alt gruptan; güvenilir faz-I için en az "
            f"{spc.ONERILEN_ALT_GRUP} önerilir."
        )
    ihlaller: list[spc.Ihlal] = []
    yetenek: spc.Yetenek | None = None
    if limitler is not None:
        xbarlar = [spc.ortalama(d) for d in degerler]
        rler = [spc.aralik(d) for d in degerler]
        ihlaller = spc.western_electric(
            xbarlar, limitler.xbar_cl, limitler.sigma_xbar
        ) + spc.r_karti_ihlalleri(rler, limitler)
        yetenek = spc.yetenek(limitler, alt_tolerans=k.alt_tolerans, ust_tolerans=k.ust_tolerans)
    return {
        "karakteristik_id": k.id,
        "plan_id": k.plan_id,
        "ad": k.ad,
        "birim": k.birim,
        "nominal": float(k.nominal) if k.nominal is not None else None,
        "alt_tolerans": float(k.alt_tolerans) if k.alt_tolerans is not None else None,
        "ust_tolerans": float(k.ust_tolerans) if k.ust_tolerans is not None else None,
        "cihaz_id": k.cihaz_id,
        "alt_grup_boyutu": k.alt_grup_boyutu,
        "limitler_sabit": bool(k.sabit_limitler),
        "limitler": asdict(limitler) if limitler else None,
        "noktalar": noktalar,
        "ihlaller": [asdict(i) for i in ihlaller],
        "yetenek": asdict(yetenek) if yetenek else None,
        "uyarilar": uyarilar,
    }


async def kart(db: AsyncSession, k: KontrolKarakteristigi) -> dict[str, Any]:
    return kart_hesapla(k, await _alt_gruplar(db, k.id))


async def karakteristik_kilitli(db: AsyncSession, karakteristik_id: int) -> KontrolKarakteristigi:
    k = (
        await db.execute(
            select(KontrolKarakteristigi)
            .where(KontrolKarakteristigi.id == karakteristik_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if k is None:
        raise KaynakBulunamadi("Karakteristik bulunamadı")
    return k


async def olcum_ekle(
    db: AsyncSession,
    karakteristik_id: int,
    *,
    degerler: list[float],
    cihaz_id: int | None,
    aciklama: str,
    kullanici: Kullanici,
    tenant_slug: str,
) -> tuple[SpcAltGrup, list[spc.Ihlal]]:
    # Satır kilidi: eşzamanlı iki ölçüm aynı sıra numarasını almasın.
    k = await karakteristik_kilitli(db, karakteristik_id)
    if len(degerler) != k.alt_grup_boyutu:
        raise DogrulamaHatasi(
            f"Bu karakteristikte alt grup {k.alt_grup_boyutu} ölçümden oluşur",
            detaylar=[{"alan": "degerler", "mesaj": f"{len(degerler)} değer geldi"}],
        )
    cihaz_id = cihaz_id or k.cihaz_id
    if cihaz_id is not None:
        cihaz = await db.get(OlcumCihazi, cihaz_id)
        if cihaz is None:
            raise KaynakBulunamadi("Ölçüm cihazı bulunamadı")
        if not cihaz_gecerli_mi(cihaz, datetime.now(UTC).date()):
            raise DogrulamaHatasi(
                f"{cihaz.kod} cihazının kalibrasyonu geçerli değil; ölçüm kalite kanıtı sayılmaz",
                hata_kodu="KALIBRASYON_GECERSIZ",
                detaylar=[
                    {
                        "alan": "cihaz_id",
                        "mesaj": (
                            f"durum={cihaz.durum}, geçerlilik={cihaz.sonraki_kalibrasyon_tarihi}"
                        ),
                    }
                ],
            )
    sira = (
        await db.scalar(
            select(func.coalesce(func.max(SpcAltGrup.sira), 0)).where(
                SpcAltGrup.karakteristik_id == k.id
            )
        )
        or 0
    ) + 1
    grup = SpcAltGrup(
        karakteristik_id=k.id,
        sira=sira,
        degerler=[float(v) for v in degerler],
        cihaz_id=cihaz_id,
        olcen_kullanici_id=kullanici.id,
        aciklama=aciklama,
        ihlaller=[],
    )
    db.add(grup)
    await db.flush()

    hesap = kart_hesapla(k, await _alt_gruplar(db, k.id))
    son = len(hesap["noktalar"]) - 1
    yeni = [spc.Ihlal(**i) for i in hesap["ihlaller"] if i["indeks"] == son]
    grup.ihlaller = [{"kart": i.kart, "kural": i.kural, "aciklama": i.aciklama} for i in yeni]
    if yeni:
        await olay_yayinla(
            db,
            olay_turu=OLAY_SPC_IHLAL,
            govde={
                "kaynak_id": k.id,
                "karakteristik_id": k.id,
                "plan_id": k.plan_id,
                "kod": f"{k.ad} #{sira}",
                "alt_grup_sira": sira,
                "kurallar": sorted({i.kural for i in yeni}),
                "limitler_sabit": hesap["limitler_sabit"],
            },
        )
        await yayinla(tenant_slug, {"tur": OLAY_SPC_IHLAL, "id": k.id})
    await db.flush()
    return grup, yeni


async def limitleri_sabitle(
    db: AsyncSession, karakteristik_id: int, *, ilk: int | None, kullanici: Kullanici
) -> KontrolKarakteristigi:
    """Faz-I: ilk ``ilk`` alt gruptan (varsayılan hepsi) limitleri hesaplar ve sabitler."""
    k = await karakteristik_kilitli(db, karakteristik_id)
    gruplar = await _alt_gruplar(db, k.id)
    if ilk is not None:
        gruplar = gruplar[:ilk]
    try:
        lim = spc.xbar_r_limitleri([[float(v) for v in g.degerler] for g in gruplar])
    except spc.SpcHatasi as exc:
        raise CakismaHatasi(str(exc), hata_kodu="SPC_YETERSIZ_VERI") from exc
    k.sabit_limitler = {
        **asdict(lim),
        "sabitlenme": datetime.now(UTC).isoformat(),
        "sabitleyen_kullanici_id": kullanici.id,
        "son_sira": gruplar[-1].sira,
    }
    await db.flush()
    return k
