"""S25-B satınalma siparişi → teslim alma → iade iş kuralları (ADR-0024 §3, §4b, §6).

Kilit sırası S25-A ile aynıdır: önce **sipariş** satırı (çağıran ``siparis_kilitli`` ile alır,
aynı siparişe eşzamanlı iki teslim seri hâle gelir), sonra **malzemeler artan id sırasıyla**,
en son bakiye satırları (``stok_hareketi_uygula`` → ``bakiye_kilitle``).

- **Fazla teslim** kümülatif kontrol edilir: kısmi teslimlerin toplamı sipariş miktarı ×
  (1 + tolerans) sınırını aşamaz (422 ``FAZLA_TESLIM``); sınır içindeki aşım işaretlenir.
- **İdempotency:** aynı siparişte aynı irsaliye ikinci kez işlenmez, mevcut kayıt döner.
- **Hızlı mal kabul eşleşmesi (§4b):** aynı malzeme + aynı irsaliye no'lu eşleşmemiş hızlı
  giriş varsa yeni hareket yazılmaz, o hareket kaleme bağlanır (çift sayım yok).
- **Birim (§6):** gövdede birim varsa malzemenin temel birimiyle aynı olmalı (422
  ``BIRIM_UYUSMAZLIGI``); miktar aktarımı tek noktadan geçer
  (``teslim_alma_kalemine_gore_miktar``) — dönüşüm gelince yalnız o fonksiyon değişir.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.kimlik.models import Kullanici
from app.modules.crm.models import Firma
from app.modules.stok import depo_service
from app.modules.stok.models import (
    Malzeme,
    SatinalmaSiparisi,
    SatinalmaSiparisiKalemi,
    SatinalmaTalebi,
    StokHareketi,
    TeslimAlma,
    TeslimAlmaKalemi,
)
from app.modules.stok.service import stok_hareketi_uygula

# Türkiye 2016'dan beri sabit UTC+3 (yaz saati yok); "zamanında" gün bazında yerel saatle ölçülür.
YEREL_SAAT = timezone(timedelta(hours=3))

TESLIM_ALINABILIR = frozenset({"acik", "kismi_teslim"})
DURUMLAR = frozenset({"acik", "kismi_teslim", "tamamlandi", "kapatildi", "iptal"})


@dataclass(frozen=True)
class TeslimSatiri:
    siparis_kalemi_id: int
    miktar: Decimal
    lot_no: str = ""
    birim: str | None = None
    lokasyon_id: int | None = None


@dataclass(frozen=True)
class IadeSatiri:
    teslim_alma_kalemi_id: int
    miktar: Decimal


# ── Saf kurallar (DB'siz, birim testli) ──────────────────────────────────────


def siparis_kalici_kod(siparis_id: int) -> str:
    return f"SS-{datetime.now(UTC).year}-{siparis_id:06d}"


def teslim_alma_kalemine_gore_miktar(kalem: SatinalmaSiparisiKalemi, miktar: Decimal) -> Decimal:
    """PO birimindeki miktarı stok temel birimine çevirir. S25'te dönüşüm yok (ADR-0024 §6):
    tek nokta burasıdır; ``MalzemeBirimDonusum`` gelince yalnız bu fonksiyon değişir."""
    return miktar


def fazla_teslim_kontrol(
    siparis_miktari: Decimal, onceki: Decimal, yeni: Decimal, tolerans_yuzde: Decimal
) -> bool:
    """Kümülatif teslim sınırı. Sınırı aşarsa 422; sipariş miktarını aşıyorsa ``True``."""
    kumulatif = onceki + yeni
    sinir = siparis_miktari * (1 + tolerans_yuzde / 100)
    if kumulatif > sinir:
        raise DogrulamaHatasi(
            "Fazla teslim toleransı aşıldı",
            hata_kodu="FAZLA_TESLIM",
            detaylar=[
                {
                    "alan": "miktar",
                    "mesaj": (
                        f"Sipariş {siparis_miktari}, önceki teslim {onceki}, bu teslim {yeni}; "
                        f"tolerans %{tolerans_yuzde} ile en çok {sinir}"
                    ),
                }
            ],
        )
    return kumulatif > siparis_miktari


def siparis_durumu_hesapla(kalemler: list[SatinalmaSiparisiKalemi]) -> str:
    """Teslim miktarlarından açık/kısmi/tamam durumunu türetir (terminal durumlara dokunmaz)."""
    if kalemler and all(k.teslim_alinan_miktar >= k.miktar for k in kalemler):
        return "tamamlandi"
    if any(k.teslim_alinan_miktar > 0 for k in kalemler):
        return "kismi_teslim"
    return "acik"


def zamaninda_mi(fiili: datetime, beklenen: date | None) -> bool | None:
    if beklenen is None:
        return None
    return fiili.astimezone(YEREL_SAAT).date() <= beklenen


def fiili_tarih_dogrula(fiili: datetime, siparis_tarihi: datetime) -> None:
    """§4b: fiziksel geliş anı gelecekte ve sipariş tarihinden önce olamaz."""
    simdi = datetime.now(UTC)
    if fiili.tzinfo is None:
        raise DogrulamaHatasi(
            "Fiili tarih saat dilimi taşımalı",
            detaylar=[{"alan": "fiili_tarih", "mesaj": "ISO 8601, ör. 2026-11-01T09:30:00+03:00"}],
        )
    if fiili > simdi + timedelta(minutes=5):
        raise DogrulamaHatasi(
            "Fiili tarih gelecekte olamaz",
            detaylar=[{"alan": "fiili_tarih", "mesaj": fiili.isoformat()}],
        )
    if fiili.astimezone(YEREL_SAAT).date() < siparis_tarihi.astimezone(YEREL_SAAT).date():
        raise DogrulamaHatasi(
            "Fiili tarih sipariş tarihinden önce olamaz",
            detaylar=[{"alan": "fiili_tarih", "mesaj": fiili.isoformat()}],
        )


# ── Sipariş ──────────────────────────────────────────────────────────────────


async def siparis_kilitli(db: AsyncSession, siparis_id: int) -> SatinalmaSiparisi:
    siparis = (
        await db.execute(
            select(SatinalmaSiparisi).where(SatinalmaSiparisi.id == siparis_id).with_for_update()
        )
    ).scalar_one_or_none()
    if siparis is None:
        raise KaynakBulunamadi("Sipariş bulunamadı")
    return siparis


async def kalemler(db: AsyncSession, siparis_id: int) -> list[SatinalmaSiparisiKalemi]:
    return list(
        (
            await db.execute(
                select(SatinalmaSiparisiKalemi)
                .where(SatinalmaSiparisiKalemi.siparis_id == siparis_id)
                .order_by(SatinalmaSiparisiKalemi.id)
            )
        ).scalars()
    )


async def siparis_olustur(
    db: AsyncSession,
    talep: SatinalmaTalebi,
    *,
    tedarikci_firma_id: int,
    beklenen_teslim_tarihi: date | None,
    aciklama: str,
    fiyatlar: dict[int, Decimal],
    toleranslar: dict[int, Decimal],
    kullanici: Kullanici,
) -> SatinalmaSiparisi:
    """Onaylanmış talebin kalemlerini siparişe kopyalar (talep onayı = görev ayrımı)."""
    if talep.durum != "onaylandi":
        raise CakismaHatasi("Yalnız onaylanmış talepten sipariş açılır")
    firma = await db.get(Firma, tedarikci_firma_id)
    if firma is None:
        raise KaynakBulunamadi("Tedarikçi firma bulunamadı")
    if firma.tip != "tedarikci":
        raise DogrulamaHatasi(
            "Firma tedarikçi değil",
            detaylar=[{"alan": "tedarikci_firma_id", "mesaj": f"Firma tipi: {firma.tip}"}],
        )
    aktif = (
        await db.execute(
            select(SatinalmaSiparisi.kod).where(
                SatinalmaSiparisi.talep_id == talep.id, SatinalmaSiparisi.durum != "iptal"
            )
        )
    ).scalar_one_or_none()
    if aktif is not None:
        raise CakismaHatasi(f"Bu talebin açık bir siparişi var: {aktif}")
    talep_kalemleri = {k.id for k in talep.kalemler}
    for anahtar in (*fiyatlar, *toleranslar):
        if anahtar not in talep_kalemleri:
            raise DogrulamaHatasi(
                "Talep kalemi bulunamadı",
                detaylar=[{"alan": "kalemler", "mesaj": f"talep_kalemi_id={anahtar}"}],
            )

    siparis = SatinalmaSiparisi(
        kod=f"GECICI-{talep.id}-{datetime.now(UTC).timestamp():.0f}",
        talep_id=talep.id,
        tedarikci_firma_id=firma.id,
        para_birimi=talep.para_birimi,
        beklenen_teslim_tarihi=beklenen_teslim_tarihi,
        aciklama=aciklama,
        olusturan_kullanici_id=kullanici.id,
    )
    for tk in talep.kalemler:
        siparis.kalemler.append(
            SatinalmaSiparisiKalemi(
                talep_kalemi_id=tk.id,
                malzeme_id=tk.malzeme_id,
                miktar=tk.miktar,
                birim_fiyat=fiyatlar.get(tk.id, tk.tahmini_birim_fiyat),
                fazla_teslim_toleransi_yuzde=toleranslar.get(tk.id, Decimal(0)),
            )
        )
    db.add(siparis)
    await db.flush()
    siparis.kod = siparis_kalici_kod(siparis.id)
    await db.flush()
    return siparis


def siparis_gecisi(siparis: SatinalmaSiparisi, hedef: str, *, teslim_var: bool) -> None:
    """Elle geçişler: iptal (hiç teslim yokken) ve kısa kapanış (kısmi teslimde)."""
    if hedef == "iptal":
        if siparis.durum != "acik" or teslim_var:
            raise CakismaHatasi("Yalnız teslim alınmamış açık sipariş iptal edilir")
    elif hedef == "kapatildi":
        if siparis.durum != "kismi_teslim":
            raise CakismaHatasi("Yalnız kısmi teslimli sipariş kapatılır (kalan iptal edilir)")
    else:
        raise DogrulamaHatasi(f"Geçersiz elle geçiş: {hedef}")
    siparis.durum = hedef


async def teslim_var_mi(db: AsyncSession, siparis_id: int) -> bool:
    sayi = (
        await db.execute(
            select(func.count()).select_from(TeslimAlma).where(TeslimAlma.siparis_id == siparis_id)
        )
    ).scalar_one()
    return int(sayi) > 0


# ── Teslim alma ──────────────────────────────────────────────────────────────


async def _malzemeleri_kilitle(db: AsyncSession, malzeme_idleri: set[int]) -> dict[int, Malzeme]:
    kilitli: dict[int, Malzeme] = {}
    for mid in sorted(malzeme_idleri):
        kilitli[mid] = (
            await db.execute(select(Malzeme).where(Malzeme.id == mid).with_for_update())
        ).scalar_one()
    return kilitli


async def _eslesmemis_hizli_kabul(
    db: AsyncSession, malzeme_id: int, irsaliye_no: str
) -> StokHareketi | None:
    bagli = select(TeslimAlmaKalemi.eslesen_hareket_id).where(
        TeslimAlmaKalemi.eslesen_hareket_id.is_not(None)
    )
    return (
        await db.execute(
            select(StokHareketi)
            .where(
                StokHareketi.hizli_kabul.is_(True),
                StokHareketi.malzeme_id == malzeme_id,
                StokHareketi.kaynak == irsaliye_no,
                StokHareketi.id.not_in(bagli),
            )
            .order_by(StokHareketi.id)
            .limit(1)
            .with_for_update()
        )
    ).scalar_one_or_none()


async def teslim_al(
    db: AsyncSession,
    siparis: SatinalmaSiparisi,
    *,
    irsaliye_no: str,
    fiili_tarih: datetime,
    lokasyon_id: int | None,
    satirlar: list[TeslimSatiri],
    aciklama: str,
    kullanici: Kullanici,
) -> tuple[TeslimAlma, bool]:
    """Teslimi işler; ``(kayıt, yeni_mi)``. Aynı irsaliye tekrar gelirse mevcut kayıt döner."""
    mevcut = (
        await db.execute(
            select(TeslimAlma).where(
                TeslimAlma.siparis_id == siparis.id,
                TeslimAlma.irsaliye_no == irsaliye_no,
                TeslimAlma.tur == "teslim",
            )
        )
    ).scalar_one_or_none()
    if mevcut is not None:
        return mevcut, False
    if siparis.durum not in TESLIM_ALINABILIR:
        raise CakismaHatasi(f"'{siparis.durum}' durumundaki siparişe teslim alınamaz")
    if not satirlar:
        raise DogrulamaHatasi("En az bir teslim satırı gerekli")
    kimlikler = [s.siparis_kalemi_id for s in satirlar]
    if len(set(kimlikler)) != len(kimlikler):
        raise DogrulamaHatasi("Bir sipariş kalemi teslimde bir kez yer alır")
    fiili_tarih_dogrula(fiili_tarih, siparis.olusturma_tarihi)

    kalem_map = {k.id: k for k in await kalemler(db, siparis.id)}
    for s in satirlar:
        if s.siparis_kalemi_id not in kalem_map:
            raise DogrulamaHatasi(
                "Kalem bu siparişe ait değil",
                detaylar=[{"alan": "siparis_kalemi_id", "mesaj": str(s.siparis_kalemi_id)}],
            )
        if s.miktar <= 0:
            raise DogrulamaHatasi("Teslim miktarı pozitif olmalı")
    malzemeler = await _malzemeleri_kilitle(
        db, {kalem_map[s.siparis_kalemi_id].malzeme_id for s in satirlar}
    )
    varsayilan_lok = lokasyon_id if lokasyon_id is not None else None

    teslim = TeslimAlma(
        siparis_id=siparis.id,
        tur="teslim",
        irsaliye_no=irsaliye_no,
        fiili_tarih=fiili_tarih,
        zamaninda=zamaninda_mi(fiili_tarih, siparis.beklenen_teslim_tarihi),
        aciklama=aciklama,
        olusturan_kullanici_id=kullanici.id,
    )
    db.add(teslim)
    await db.flush()

    for s in sorted(satirlar, key=lambda x: (kalem_map[x.siparis_kalemi_id].malzeme_id, x.lot_no)):
        kalem = kalem_map[s.siparis_kalemi_id]
        malzeme = malzemeler[kalem.malzeme_id]
        if s.birim is not None and s.birim != malzeme.birim:
            raise DogrulamaHatasi(
                "Birim uyuşmuyor",
                hata_kodu="BIRIM_UYUSMAZLIGI",
                detaylar=[
                    {"alan": "birim", "mesaj": f"Malzeme birimi {malzeme.birim}, gelen {s.birim}"}
                ],
            )
        miktar = teslim_alma_kalemine_gore_miktar(kalem, s.miktar)
        fazla = fazla_teslim_kontrol(
            kalem.miktar, kalem.teslim_alinan_miktar, miktar, kalem.fazla_teslim_toleransi_yuzde
        )

        hizli = await _eslesmemis_hizli_kabul(db, malzeme.id, irsaliye_no)
        if hizli is not None:
            if hizli.miktar != miktar:
                raise DogrulamaHatasi(
                    "Hızlı mal kabul miktarı teslimle uyuşmuyor",
                    hata_kodu="ESLESME_MIKTAR",
                    detaylar=[
                        {
                            "alan": "miktar",
                            "mesaj": (
                                f"İrsaliye {irsaliye_no} için hızlı kabul {hizli.miktar}, "
                                f"teslim {miktar}. Önce hızlı kabulü düzeltin."
                            ),
                        }
                    ],
                )
            satir = TeslimAlmaKalemi(
                teslim_id=teslim.id,
                siparis_kalemi_id=kalem.id,
                miktar=miktar,
                lokasyon_id=hizli.lokasyon_id
                if hizli.lokasyon_id is not None
                else await depo_service.varsayilan_lokasyon_id(db),
                lot_no=hizli.lot_no,
                fazla_teslim=fazla,
                eslesen_hareket_id=hizli.id,
            )
        else:
            hedef_lok = s.lokasyon_id if s.lokasyon_id is not None else varsayilan_lok
            hareket, _ = await stok_hareketi_uygula(
                db,
                malzeme,
                tur="giris",
                miktar=miktar,
                aciklama=f"{siparis.kod} · irsaliye {irsaliye_no}",
                kaynak=siparis.kod,
                kullanici=kullanici,
                idempotency_anahtari=f"teslim-{kalem.id}-{irsaliye_no}"[:64],
                lokasyon_id=hedef_lok,
                lot_no=s.lot_no,
            )
            satir = TeslimAlmaKalemi(
                teslim_id=teslim.id,
                siparis_kalemi_id=kalem.id,
                miktar=miktar,
                lokasyon_id=hareket.lokasyon_id,
                lot_no=s.lot_no,
                fazla_teslim=fazla,
                stok_hareketi_id=hareket.id,
            )
        db.add(satir)
        kalem.teslim_alinan_miktar = kalem.teslim_alinan_miktar + miktar

    siparis.durum = siparis_durumu_hesapla(list(kalem_map.values()))
    await db.flush()
    return teslim, True


async def iade_et(
    db: AsyncSession,
    siparis: SatinalmaSiparisi,
    teslim: TeslimAlma,
    *,
    irsaliye_no: str,
    satirlar: list[IadeSatiri],
    aciklama: str,
    kullanici: Kullanici,
    idempotency_anahtari: str | None,
) -> TeslimAlma:
    """Orijinal teslime bağlı ters kayıt: stoktan çıkış, siparişin teslim miktarını azaltır."""
    if teslim.tur != "teslim" or teslim.siparis_id != siparis.id:
        raise DogrulamaHatasi("Yalnız bu siparişin teslim kaydı iade edilir")
    if siparis.durum == "iptal":
        raise CakismaHatasi("İptal edilmiş siparişte iade yapılmaz")
    if not satirlar:
        raise DogrulamaHatasi("En az bir iade satırı gerekli")
    orijinal = {
        k.id: k
        for k in (
            await db.execute(
                select(TeslimAlmaKalemi).where(TeslimAlmaKalemi.teslim_id == teslim.id)
            )
        ).scalars()
    }
    kalem_map = {k.id: k for k in await kalemler(db, siparis.id)}
    for s in satirlar:
        if s.teslim_alma_kalemi_id not in orijinal:
            raise DogrulamaHatasi(
                "Satır bu teslime ait değil",
                detaylar=[{"alan": "teslim_alma_kalemi_id", "mesaj": str(s.teslim_alma_kalemi_id)}],
            )
    malzemeler = await _malzemeleri_kilitle(
        db,
        {
            kalem_map[orijinal[s.teslim_alma_kalemi_id].siparis_kalemi_id].malzeme_id
            for s in satirlar
        },
    )

    iade = TeslimAlma(
        siparis_id=siparis.id,
        tur="iade",
        irsaliye_no=irsaliye_no,
        iade_edilen_id=teslim.id,
        fiili_tarih=datetime.now(UTC),
        zamaninda=None,
        aciklama=aciklama,
        idempotency_anahtari=idempotency_anahtari,
        olusturan_kullanici_id=kullanici.id,
    )
    db.add(iade)
    await db.flush()

    for s in satirlar:
        ok = orijinal[s.teslim_alma_kalemi_id]
        onceki = (
            await db.execute(
                select(func.coalesce(func.sum(TeslimAlmaKalemi.miktar), 0)).where(
                    TeslimAlmaKalemi.iade_edilen_kalem_id == ok.id
                )
            )
        ).scalar_one()
        if s.miktar <= 0 or Decimal(onceki) + s.miktar > ok.miktar:
            raise DogrulamaHatasi(
                "İade miktarı teslim edileni aşamaz",
                hata_kodu="IADE_FAZLA",
                detaylar=[
                    {
                        "alan": "miktar",
                        "mesaj": f"Teslim {ok.miktar}, önceki iade {onceki}, istenen {s.miktar}",
                    }
                ],
            )
        kalem = kalem_map[ok.siparis_kalemi_id]
        hareket, _ = await stok_hareketi_uygula(
            db,
            malzemeler[kalem.malzeme_id],
            tur="cikis",
            miktar=s.miktar,
            aciklama=f"{siparis.kod} · iade {irsaliye_no}",
            kaynak=siparis.kod,
            kullanici=kullanici,
            idempotency_anahtari=f"iade-{iade.id}-{ok.id}",
            lokasyon_id=ok.lokasyon_id,
            lot_no=ok.lot_no,
        )
        db.add(
            TeslimAlmaKalemi(
                teslim_id=iade.id,
                siparis_kalemi_id=kalem.id,
                iade_edilen_kalem_id=ok.id,
                miktar=s.miktar,
                lokasyon_id=ok.lokasyon_id,
                lot_no=ok.lot_no,
                stok_hareketi_id=hareket.id,
            )
        )
        kalem.teslim_alinan_miktar = kalem.teslim_alinan_miktar - s.miktar

    if siparis.durum in {"acik", "kismi_teslim", "tamamlandi"}:
        siparis.durum = siparis_durumu_hesapla(list(kalem_map.values()))
    await db.flush()
    return iade


async def eslesmemis_hizli_kabuller(db: AsyncSession) -> list[tuple[StokHareketi, Malzeme]]:
    """§4b takip listesi: resmî teslime bağlanmamış hızlı mal kabuller (en eski önce)."""
    bagli = select(TeslimAlmaKalemi.eslesen_hareket_id).where(
        TeslimAlmaKalemi.eslesen_hareket_id.is_not(None)
    )
    rows = (
        await db.execute(
            select(StokHareketi, Malzeme)
            .join(Malzeme, Malzeme.id == StokHareketi.malzeme_id)
            .where(StokHareketi.hizli_kabul.is_(True), StokHareketi.id.not_in(bagli))
            .order_by(StokHareketi.id)
            .limit(500)
        )
    ).all()
    return [(h, m) for h, m in rows]
