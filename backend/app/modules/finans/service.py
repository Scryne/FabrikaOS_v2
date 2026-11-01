"""Finans iş kuralları (S29, ADR-0048).

Eşzamanlılık sözleşmesi: cari bakiye yalnız ``_cari_kilitle`` ile alınan ``FOR UPDATE`` satır
kilidi altında değişir; fatura ödeme tutarı da fatura satırı kilitliyken. Çift sayım iki katmanla
engellenir: ``CariHareket.kaynak`` tekil (aynı fatura/ödeme bakiyeye ikinci kez girmez) ve
``Odeme.idempotency_anahtari`` tekil (istemci yeniden denemesi ikinci ödeme açmaz).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AppError,
    CakismaHatasi,
    DogrulamaHatasi,
    KaynakBulunamadi,
    YetkiHatasi,
)
from app.core.olaylar import olay_yayinla
from app.core.zaman import is_gunu
from app.kimlik.models import Kullanici
from app.modules.crm.models import Firma
from app.modules.finans import durum, hesap
from app.modules.finans.models import CariHareket, CariHesap, Fatura, FaturaKalemi, Odeme

OLAY_FATURA_KESILDI = "fatura.kesildi"
OLAY_ODEME_ALINDI = "odeme.alindi"
OLAY_ODEME_YAPILDI = "odeme.yapildi"


@dataclass(frozen=True)
class KalemGirdisi:
    aciklama: str
    miktar: Decimal
    birim: str
    birim_fiyat: Decimal
    kdv_orani: int
    malzeme_id: int | None = None


def _gecici_kod() -> str:
    return f"GECICI-{uuid.uuid4().hex}"


def fatura_kalici_kod(f: Fatura) -> str:
    return f"FT-{f.fatura_tarihi.year}-{f.id:06d}"


def odeme_kalici_kod(o: Odeme) -> str:
    on = "TH" if o.tur == "tahsilat" else "OD"
    return f"{on}-{o.tarih.year}-{o.id:06d}"


# ── Cari ─────────────────────────────────────────────────────────────────────


async def _cari_kilitle(db: AsyncSession, firma_id: int) -> CariHesap:
    """Firmanın cari hesabını kilitli döndürür; yoksa açar (eşzamanlı açılışta tek satır)."""
    await db.execute(
        insert(CariHesap)
        .values(firma_id=firma_id)
        .on_conflict_do_nothing(index_elements=["firma_id"])
    )
    cari = await db.scalar(
        select(CariHesap).where(CariHesap.firma_id == firma_id).with_for_update()
    )
    assert cari is not None
    return cari


async def cari_uygula(
    db: AsyncSession,
    *,
    firma_id: int,
    tur: str,
    tutar: Decimal,
    tarih: date,
    kaynak: str,
    aciklama: str,
    kullanici: Kullanici | None,
) -> CariHareket:
    """Bakiyeye ``tutar`` (işaretli) ekler; aynı ``kaynak`` daha önce işlendiyse dokunmaz."""
    cari = await _cari_kilitle(db, firma_id)
    onceki = await db.scalar(select(CariHareket).where(CariHareket.kaynak == kaynak))
    if onceki is not None:
        return onceki
    cari.bakiye = hesap.yuvarla(cari.bakiye + tutar)
    hareket = CariHareket(
        cari_id=cari.id,
        tur=tur,
        tutar=tutar,
        bakiye_sonrasi=cari.bakiye,
        tarih=tarih,
        kaynak=kaynak,
        aciklama=aciklama[:500],
        kullanici_id=kullanici.id if kullanici else None,
    )
    db.add(hareket)
    await db.flush()
    return hareket


# ── Fatura ───────────────────────────────────────────────────────────────────


async def _firma_dogrula(db: AsyncSession, firma_id: int) -> Firma:
    firma = await db.get(Firma, firma_id)
    if firma is None:
        raise DogrulamaHatasi(
            "Firma bulunamadı", detaylar=[{"alan": "firma_id", "mesaj": "Kayıtlı bir firma seçin"}]
        )
    return firma


def _kalemleri_kur(fatura: Fatura, kalemler: list[KalemGirdisi]) -> None:
    if not kalemler:
        raise DogrulamaHatasi(
            "Fatura en az bir kalem içermeli", detaylar=[{"alan": "kalemler", "mesaj": "Boş"}]
        )
    hesaplanan: list[hesap.KalemTutari] = []
    yeni: list[FaturaKalemi] = []
    for i, k in enumerate(kalemler, start=1):
        try:
            t = hesap.kalem_hesapla(k.miktar, k.birim_fiyat, k.kdv_orani)
        except ValueError as exc:
            raise DogrulamaHatasi(
                "Geçersiz fatura kalemi",
                detaylar=[{"alan": f"kalemler.{i - 1}", "mesaj": str(exc)}],
            ) from exc
        hesaplanan.append(t)
        yeni.append(
            FaturaKalemi(
                sira=i,
                aciklama=k.aciklama,
                malzeme_id=k.malzeme_id,
                miktar=k.miktar,
                birim=k.birim,
                birim_fiyat=k.birim_fiyat,
                kdv_orani=k.kdv_orani,
                satir_tutari=t.satir_tutari,
                kdv_tutari=t.kdv_tutari,
            )
        )
    toplam = hesap.fatura_toplami(hesaplanan)
    fatura.kalemler = yeni
    fatura.ara_toplam = toplam.ara_toplam
    fatura.kdv_toplam = toplam.kdv_toplam
    fatura.genel_toplam = toplam.genel_toplam


async def fatura_olustur(
    db: AsyncSession,
    *,
    tur: str,
    firma_id: int,
    fatura_tarihi: date,
    vade_gun: int,
    kalemler: list[KalemGirdisi],
    aciklama: str,
    senaryo: str,
    satinalma_siparisi_id: int | None,
    kullanici: Kullanici,
) -> Fatura:
    if tur not in hesap.FATURA_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz fatura türü", detaylar=[{"alan": "tur", "mesaj": "satis | alis"}]
        )
    await _firma_dogrula(db, firma_id)
    fatura = Fatura(
        kod=_gecici_kod(),
        tur=tur,
        firma_id=firma_id,
        fatura_tarihi=fatura_tarihi,
        vade_tarihi=fatura_tarihi + timedelta(days=vade_gun),
        aciklama=aciklama,
        senaryo=senaryo,
        satinalma_siparisi_id=satinalma_siparisi_id,
        olusturan_kullanici_id=kullanici.id,
    )
    _kalemleri_kur(fatura, kalemler)
    db.add(fatura)
    await db.flush()
    fatura.kod = fatura_kalici_kod(fatura)
    await db.flush()
    return fatura


async def fatura_kilitle(db: AsyncSession, fatura_id: int) -> Fatura:
    f = await db.scalar(select(Fatura).where(Fatura.id == fatura_id).with_for_update())
    if f is None:
        raise KaynakBulunamadi("Fatura bulunamadı")
    return f


async def fatura_guncelle(
    db: AsyncSession,
    fatura: Fatura,
    *,
    firma_id: int | None,
    fatura_tarihi: date | None,
    vade_gun: int | None,
    kalemler: list[KalemGirdisi] | None,
    aciklama: str | None,
) -> Fatura:
    if fatura.durum != "taslak":
        raise CakismaHatasi("Yalnız taslak fatura düzenlenebilir")
    if firma_id is not None:
        await _firma_dogrula(db, firma_id)
        fatura.firma_id = firma_id
    if fatura_tarihi is not None:
        vade = (fatura.vade_tarihi - fatura.fatura_tarihi).days
        fatura.fatura_tarihi = fatura_tarihi
        fatura.vade_tarihi = fatura_tarihi + timedelta(days=vade)
    if vade_gun is not None:
        fatura.vade_tarihi = fatura.fatura_tarihi + timedelta(days=vade_gun)
    if aciklama is not None:
        fatura.aciklama = aciklama
    if kalemler is not None:
        _kalemleri_kur(fatura, kalemler)
    fatura.iade_nedeni = ""
    await db.flush()
    return fatura


def _gecis_dogrula(fatura: Fatura, hedef: str) -> None:
    if hedef not in durum.DURUMLAR or hedef in durum.OTOMATIK_HEDEFLER:
        raise DogrulamaHatasi("Geçersiz hedef durum", detaylar=[{"alan": "durum", "mesaj": hedef}])
    if not durum.gecis_gecerli_mi(fatura.durum, hedef):
        raise CakismaHatasi(f"Geçersiz durum geçişi: {fatura.durum} → {hedef}")


async def fatura_gonder(db: AsyncSession, fatura: Fatura) -> Fatura:
    _gecis_dogrula(fatura, "onay_bekliyor")
    if fatura.genel_toplam <= 0:
        raise DogrulamaHatasi(
            "Tutarı sıfır olan fatura onaya gönderilemez",
            detaylar=[{"alan": "kalemler", "mesaj": "Genel toplam 0"}],
        )
    fatura.durum = "onay_bekliyor"
    await db.flush()
    return fatura


async def fatura_iade(db: AsyncSession, fatura: Fatura, *, neden: str) -> Fatura:
    _gecis_dogrula(fatura, "taslak")
    if not neden.strip():
        raise DogrulamaHatasi("İade nedeni gerekli", detaylar=[{"alan": "neden", "mesaj": "Boş"}])
    fatura.durum = "taslak"
    fatura.iade_nedeni = neden.strip()[:500]
    await db.flush()
    return fatura


async def fatura_kes(db: AsyncSession, fatura: Fatura, *, kesen: Kullanici) -> Fatura:
    """Faturayı keser: cari hesaba işler ve ``fatura.kesildi`` olayını yazar (aynı işlemde)."""
    _gecis_dogrula(fatura, "kesildi")
    if fatura.olusturan_kullanici_id == kesen.id:
        raise YetkiHatasi("Faturayı hazırlayan kullanıcı kesemez (görev ayrımı)")
    fatura.durum = "kesildi"
    fatura.kesen_kullanici_id = kesen.id
    fatura.kesim_tarihi = datetime.now(UTC)
    await cari_uygula(
        db,
        firma_id=fatura.firma_id,
        tur=f"fatura_{fatura.tur}",
        tutar=hesap.fatura_cari_etkisi(fatura.tur, fatura.genel_toplam),
        tarih=fatura.fatura_tarihi,
        kaynak=f"fatura:{fatura.id}",
        aciklama=f"{fatura.kod} {'satış' if fatura.tur == 'satis' else 'alış'} faturası",
        kullanici=kesen,
    )
    await olay_yayinla(
        db,
        olay_turu=OLAY_FATURA_KESILDI,
        govde={
            "kaynak_id": fatura.id,
            "kod": fatura.kod,
            "tur": fatura.tur,
            "firma_id": fatura.firma_id,
            "genel_toplam": str(fatura.genel_toplam),
            "para_birimi": fatura.para_birimi,
            "vade_tarihi": fatura.vade_tarihi.isoformat(),
            "ettn": str(fatura.ettn),
        },
    )
    await db.flush()
    return fatura


async def fatura_iptal(
    db: AsyncSession, fatura: Fatura, *, neden: str, kullanici: Kullanici
) -> Fatura:
    _gecis_dogrula(fatura, "iptal")
    kesilmisti = fatura.durum == "kesildi"
    if kesilmisti:
        if fatura.odenen_tutar > 0:
            raise CakismaHatasi(
                "Ödemesi/tahsilatı olan fatura iptal edilemez; önce ödeme kayıtlarını düzeltin"
            )
        if not neden.strip():
            raise DogrulamaHatasi(
                "Kesilmiş faturanın iptali için neden gerekli",
                detaylar=[{"alan": "neden", "mesaj": "Boş"}],
            )
    fatura.durum = "iptal"
    fatura.iptal_nedeni = neden.strip()[:500]
    if kesilmisti:
        await cari_uygula(
            db,
            firma_id=fatura.firma_id,
            tur="fatura_iptal",
            tutar=-hesap.fatura_cari_etkisi(fatura.tur, fatura.genel_toplam),
            tarih=is_gunu(),
            kaynak=f"fatura-iptal:{fatura.id}",
            aciklama=f"{fatura.kod} iptali",
            kullanici=kullanici,
        )
    await db.flush()
    return fatura


# ── Tahsilat / ödeme ─────────────────────────────────────────────────────────


class OdemeFazla(AppError):
    durum_kodu = 422
    hata_kodu = "ODEME_FAZLA"


async def odeme_kaydet(
    db: AsyncSession,
    *,
    tur: str,
    firma_id: int,
    tutar: Decimal,
    tarih: date,
    yontem: str,
    fatura_id: int | None,
    aciklama: str,
    idempotency_anahtari: str | None,
    kullanici: Kullanici,
) -> tuple[Odeme, bool]:
    """Tahsilat ya da ödemeyi kaydeder; ``(odeme, yeni_mi)`` döner (tekrar istekte ``False``)."""
    if idempotency_anahtari:
        var = await db.scalar(
            select(Odeme).where(Odeme.idempotency_anahtari == idempotency_anahtari)
        )
        if var is not None:
            return var, False
    if tur not in hesap.ODEME_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz tür", detaylar=[{"alan": "tur", "mesaj": "tahsilat | odeme"}]
        )
    if yontem not in hesap.ODEME_YONTEMLERI:
        raise DogrulamaHatasi(
            "Geçersiz ödeme yöntemi",
            detaylar=[{"alan": "yontem", "mesaj": ", ".join(sorted(hesap.ODEME_YONTEMLERI))}],
        )
    tutar = hesap.yuvarla(tutar)
    if tutar <= 0:
        raise DogrulamaHatasi("Tutar pozitif olmalı", detaylar=[{"alan": "tutar", "mesaj": "> 0"}])
    await _firma_dogrula(db, firma_id)

    fatura: Fatura | None = None
    if fatura_id is not None:
        fatura = await fatura_kilitle(db, fatura_id)
        if fatura.firma_id != firma_id:
            raise DogrulamaHatasi(
                "Fatura bu firmaya ait değil",
                detaylar=[{"alan": "fatura_id", "mesaj": "Firma farklı"}],
            )
        if not hesap.odeme_faturaya_uyar_mi(tur, fatura.tur):
            raise DogrulamaHatasi(
                "Tahsilat satış, ödeme alış faturasına bağlanır",
                detaylar=[{"alan": "fatura_id", "mesaj": f"{tur} → {fatura.tur}"}],
            )
        if fatura.durum != "kesildi":
            raise CakismaHatasi(f"Yalnız kesilmiş ve açık faturaya ödeme bağlanır ({fatura.durum})")
        acik = hesap.acik_tutar(fatura.genel_toplam, fatura.odenen_tutar)
        if tutar > acik:
            raise OdemeFazla(
                f"Tutar faturanın açık tutarını aşıyor (açık: {acik} {fatura.para_birimi})",
                detaylar=[{"alan": "tutar", "mesaj": f"En çok {acik}"}],
            )

    odeme = Odeme(
        kod=_gecici_kod(),
        tur=tur,
        firma_id=firma_id,
        fatura_id=fatura_id,
        tarih=tarih,
        tutar=tutar,
        yontem=yontem,
        aciklama=aciklama,
        idempotency_anahtari=idempotency_anahtari,
        kullanici_id=kullanici.id,
    )
    db.add(odeme)
    await db.flush()
    odeme.kod = odeme_kalici_kod(odeme)
    if fatura is not None:
        fatura.odenen_tutar = fatura.odenen_tutar + tutar
        if fatura.odenen_tutar >= fatura.genel_toplam:
            fatura.durum = "kapandi"
    await cari_uygula(
        db,
        firma_id=firma_id,
        tur=tur,
        tutar=hesap.odeme_cari_etkisi(tur, tutar),
        tarih=tarih,
        kaynak=f"odeme:{odeme.id}",
        aciklama=f"{odeme.kod}{f' · {fatura.kod}' if fatura else ''}",
        kullanici=kullanici,
    )
    await olay_yayinla(
        db,
        olay_turu=OLAY_ODEME_ALINDI if tur == "tahsilat" else OLAY_ODEME_YAPILDI,
        govde={
            "kaynak_id": odeme.id,
            "kod": odeme.kod,
            "firma_id": firma_id,
            "fatura_id": fatura_id,
            "tutar": str(tutar),
            "tarih": tarih.isoformat(),
        },
    )
    await db.flush()
    return odeme, True


# ── Raporlar ─────────────────────────────────────────────────────────────────


async def yaslandirma(db: AsyncSession, bugun: date) -> dict[str, Any]:
    """Açık (kesilmiş) faturaların vade yaşına göre dağılımı; alacak ve borç ayrı."""
    satirlar = (
        await db.execute(
            select(Fatura, Firma.ad)
            .join(Firma, Firma.id == Fatura.firma_id)
            .where(Fatura.durum == "kesildi")
        )
    ).all()
    sonuc: dict[str, Any] = {}
    for yon, ftur in (("alacak", "satis"), ("borc", "alis")):
        kovalar = {k: Decimal("0.00") for k in hesap.YASLANDIRMA_KOVALARI}
        firmalar: dict[int, dict[str, Any]] = {}
        for f, firma_ad in satirlar:
            if f.tur != ftur:
                continue
            acik = hesap.acik_tutar(f.genel_toplam, f.odenen_tutar)
            kova = hesap.yaslandirma_kovasi(f.vade_tarihi, bugun)
            kovalar[kova] += acik
            kayit = firmalar.setdefault(
                f.firma_id,
                {"firma_id": f.firma_id, "firma_ad": firma_ad, "toplam": Decimal("0.00")}
                | {k: Decimal("0.00") for k in hesap.YASLANDIRMA_KOVALARI},
            )
            kayit[kova] += acik
            kayit["toplam"] += acik
        sonuc[yon] = {
            "kovalar": kovalar,
            "toplam": sum(kovalar.values(), Decimal("0.00")),
            "firmalar": sorted(firmalar.values(), key=lambda x: x["toplam"], reverse=True),
        }
    return sonuc


async def ozet(db: AsyncSession, bugun: date) -> dict[str, Decimal | int]:
    ay_basi = bugun.replace(day=1)

    async def toplam(*kosul: Any, alan: Any = Fatura.genel_toplam) -> Decimal:
        deger = await db.scalar(select(func.coalesce(func.sum(alan), 0)).where(*kosul))
        return Decimal(deger or 0)

    acik = Fatura.genel_toplam - Fatura.odenen_tutar
    return {
        "acik_alacak": await toplam(Fatura.durum == "kesildi", Fatura.tur == "satis", alan=acik),
        "acik_borc": await toplam(Fatura.durum == "kesildi", Fatura.tur == "alis", alan=acik),
        "vadesi_gecen_alacak": await toplam(
            Fatura.durum == "kesildi",
            Fatura.tur == "satis",
            Fatura.vade_tarihi < bugun,
            alan=acik,
        ),
        "bu_ay_satis": await toplam(
            Fatura.tur == "satis",
            Fatura.durum.in_(("kesildi", "kapandi")),
            Fatura.fatura_tarihi >= ay_basi,
        ),
        "bu_ay_tahsilat": Decimal(
            await db.scalar(
                select(func.coalesce(func.sum(Odeme.tutar), 0)).where(
                    Odeme.tur == "tahsilat", Odeme.tarih >= ay_basi
                )
            )
            or 0
        ),
        "onay_bekleyen": int(
            await db.scalar(
                select(func.count()).select_from(Fatura).where(Fatura.durum == "onay_bekliyor")
            )
            or 0
        ),
    }
