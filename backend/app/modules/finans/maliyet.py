"""Üretim malzeme maliyeti (S29, ADR-0048) — kapanan iş emirlerinin reçete tüketimi × birim fiyat.

Tüketim kaynağı gerçek stok hareketidir: iş emri kapanırken BOM patlatma her malzeme için
``kaynak = "bom:<iş emri id>"`` çıkışı yazar (S24). Birim fiyat malzemenin **son satınalma
siparişi** kalemindeki fiyattır; sipariş fiyatı yoksa son talepteki tahmini fiyat. İkisi de yoksa
kalem *fiyatsız* sayılır ve maliyete 0 diye eklenmez: satır ``eksik_fiyat`` ile işaretlenir
(sipariş PDF'indeki "eksik fiyat sessizce 0 sayılmaz" ilkesi).

Kapsam bilerek basit: işçilik, genel üretim gideri ve stok değerleme yöntemi (FIFO/ağırlıklı
ortalama) yok; bunlar tam maliyet muhasebesinin işi (ADR-0048 §Kapsam dışı).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finans.hesap import yuvarla
from app.modules.isemri.models import IsEmri
from app.modules.stok.models import (
    Malzeme,
    SatinalmaSiparisi,
    SatinalmaSiparisiKalemi,
    SatinalmaTalebiKalemi,
    StokHareketi,
)
from app.modules.urun.models import Urun


@dataclass
class MaliyetKalemi:
    malzeme_id: int
    malzeme_kod: str
    malzeme_ad: str
    miktar: Decimal
    birim_fiyat: Decimal | None
    fiyat_kaynagi: str  # siparis | talep | yok
    tutar: Decimal | None


@dataclass
class IsEmriMaliyeti:
    is_emri_id: int
    is_emri_kod: str
    urun_kod: str
    urun_ad: str
    miktar: Decimal | None
    kapanis_tarihi: datetime | None
    malzeme_maliyeti: Decimal = Decimal("0.00")
    birim_maliyet: Decimal | None = None
    eksik_fiyat: int = 0
    kalemler: list[MaliyetKalemi] = field(default_factory=list)


async def _birim_fiyatlar(
    db: AsyncSession, malzeme_idler: set[int]
) -> dict[int, tuple[Decimal, str]]:
    fiyatlar: dict[int, tuple[Decimal, str]] = {}
    if not malzeme_idler:
        return fiyatlar
    siparis = (
        await db.execute(
            select(SatinalmaSiparisiKalemi.malzeme_id, SatinalmaSiparisiKalemi.birim_fiyat)
            .join(SatinalmaSiparisi, SatinalmaSiparisi.id == SatinalmaSiparisiKalemi.siparis_id)
            .where(
                SatinalmaSiparisiKalemi.malzeme_id.in_(malzeme_idler),
                SatinalmaSiparisiKalemi.birim_fiyat.is_not(None),
                SatinalmaSiparisi.durum != "iptal",
            )
            .order_by(SatinalmaSiparisi.olusturma_tarihi.desc(), SatinalmaSiparisiKalemi.id.desc())
        )
    ).all()
    for mid, fiyat in siparis:
        if fiyat is not None:
            fiyatlar.setdefault(mid, (Decimal(fiyat), "siparis"))
    eksik = malzeme_idler - fiyatlar.keys()
    if eksik:
        talep = (
            await db.execute(
                select(SatinalmaTalebiKalemi.malzeme_id, SatinalmaTalebiKalemi.tahmini_birim_fiyat)
                .where(
                    SatinalmaTalebiKalemi.malzeme_id.in_(eksik),
                    SatinalmaTalebiKalemi.tahmini_birim_fiyat.is_not(None),
                )
                .order_by(SatinalmaTalebiKalemi.id.desc())
            )
        ).all()
        for mid, fiyat in talep:
            if fiyat is not None:
                fiyatlar.setdefault(mid, (Decimal(fiyat), "talep"))
    return fiyatlar


async def uretim_maliyeti(
    db: AsyncSession, *, baslangic: datetime, bitis: datetime
) -> list[IsEmriMaliyeti]:
    emirler = (
        await db.execute(
            select(IsEmri, Urun)
            .join(Urun, Urun.id == IsEmri.urun_id)
            .where(
                IsEmri.durum == "kapandi",
                IsEmri.kapanis_tarihi >= baslangic,
                IsEmri.kapanis_tarihi < bitis,
            )
            .order_by(IsEmri.kapanis_tarihi.desc())
        )
    ).all()
    if not emirler:
        return []
    kaynaklar = {f"bom:{e.id}": e.id for e, _ in emirler}
    tuketim = (
        await db.execute(
            select(StokHareketi.kaynak, StokHareketi.malzeme_id, StokHareketi.miktar, Malzeme)
            .join(Malzeme, Malzeme.id == StokHareketi.malzeme_id)
            .where(StokHareketi.kaynak.in_(kaynaklar), StokHareketi.tur == "cikis")
        )
    ).all()
    fiyatlar = await _birim_fiyatlar(db, {mid for _, mid, _, _ in tuketim})

    sonuc = {
        e.id: IsEmriMaliyeti(
            is_emri_id=e.id,
            is_emri_kod=e.kod,
            urun_kod=u.kod,
            urun_ad=u.ad,
            miktar=e.miktar,
            kapanis_tarihi=e.kapanis_tarihi,
        )
        for e, u in emirler
    }
    for kaynak, mid, miktar, malzeme in tuketim:
        kayit = sonuc[kaynaklar[str(kaynak)]]
        fiyat, fiyat_kaynagi = fiyatlar.get(mid, (None, "yok"))
        tutar = yuvarla(Decimal(miktar) * fiyat) if fiyat is not None else None
        kayit.kalemler.append(
            MaliyetKalemi(
                malzeme_id=mid,
                malzeme_kod=malzeme.kod,
                malzeme_ad=malzeme.ad,
                miktar=Decimal(miktar),
                birim_fiyat=fiyat,
                fiyat_kaynagi=fiyat_kaynagi,
                tutar=tutar,
            )
        )
        if tutar is None:
            kayit.eksik_fiyat += 1
        else:
            kayit.malzeme_maliyeti += tutar
    for kayit in sonuc.values():
        if kayit.miktar and kayit.miktar > 0 and not kayit.eksik_fiyat:
            kayit.birim_maliyet = yuvarla(kayit.malzeme_maliyeti / kayit.miktar)
    return list(sonuc.values())
