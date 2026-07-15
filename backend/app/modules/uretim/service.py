"""Üretim modülü iş kuralları — OEE toplulaştırma + düşük-OEE taraması (S18).

Toplulaştırılmış girdiler (``OeeToplam``) saf ``oee_hesapla`` fonksiyonuna bağlanır:
toplam ideal süreden "efektif çevrim süresi" türetilerek tek doğruluk kaynağı korunur.

S24: kayıtlı duruşlar (``durus_kayitlari``) pencere içi kesişim dakikalarıyla
``durus_sure_dk`` toplamına **eklenir** — üretim verisindeki manuel duruş alanına ek
bağımsız kaynak (kullanılabilirlik gerçek duruşlardan düşer). Vardiya kırılımı
``?vardiya=`` filtresiyle (kayıtlı duruşlar vardiyaya bağlanmaz; vardiya filtreli
sorguda yalnız üretim verisi duruşu sayılır — belgelenmiş sınır).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.gercekzaman import yayinla
from app.core.olaylar import GidenOlay, olay_yayinla
from app.modules.durus import repository as durus_repository
from app.modules.uretim import repository
from app.modules.uretim.models import Makine
from app.modules.uretim.oee import OeeSonuc, oee_hesapla
from app.modules.uretim.repository import OeeToplam


def oee_toplamdan(t: OeeToplam) -> OeeSonuc:
    """Toplulaştırılmış girdilerden OEE hesaplar (saf fonksiyonu yeniden kullanır)."""
    # ideal_sure_dk = efektif_cevrim_sn * toplam_adet / 60  →  efektif_cevrim_sn'i geri çöz.
    efektif_cevrim_sn = t.ideal_sure_dk * 60.0 / t.toplam_adet if t.toplam_adet > 0 else 0.0
    return oee_hesapla(
        planlanan_sure_dk=t.planlanan_sure_dk,
        durus_sure_dk=t.durus_sure_dk,
        toplam_adet=t.toplam_adet,
        saglam_adet=t.saglam_adet,
        ideal_cevrim_sn=efektif_cevrim_sn,
    )


def _duruslu(t: OeeToplam, ek_durus_dk: float) -> OeeToplam:
    """Toplama kayıtlı duruş dakikalarını ekler (saf; girdiyi değiştirmez)."""
    if ek_durus_dk <= 0:
        return t
    return OeeToplam(
        planlanan_sure_dk=t.planlanan_sure_dk,
        durus_sure_dk=t.durus_sure_dk + ek_durus_dk,
        toplam_adet=t.toplam_adet,
        saglam_adet=t.saglam_adet,
        ideal_sure_dk=t.ideal_sure_dk,
        kayit_sayisi=t.kayit_sayisi,
    )


async def makine_oee(
    db: AsyncSession,
    makine_id: int,
    *,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    vardiya: str | None = None,
) -> tuple[OeeSonuc, int]:
    toplam = await repository.oee_toplam(
        db, makine_id, baslangic=baslangic, bitis=bitis, vardiya=vardiya
    )
    if vardiya is None:
        duruslar = await durus_repository.pencere_durus_dakikalari(
            db, baslangic=baslangic, bitis=bitis, makine_id=makine_id
        )
        toplam = _duruslu(toplam, duruslar.get(makine_id, 0.0))
    return oee_toplamdan(toplam), toplam.kayit_sayisi


async def oee_ozet(
    db: AsyncSession,
    *,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    vardiya: str | None = None,
) -> list[tuple[int, str, OeeSonuc, int]]:
    satirlar = await repository.oee_ozet(db, baslangic=baslangic, bitis=bitis, vardiya=vardiya)
    duruslar: dict[int, float] = {}
    if vardiya is None:
        duruslar = await durus_repository.pencere_durus_dakikalari(
            db, baslangic=baslangic, bitis=bitis
        )
    return [
        (mid, kod, oee_toplamdan(_duruslu(t, duruslar.get(mid, 0.0))), t.kayit_sayisi)
        for mid, kod, t in satirlar
    ]


async def _oee_dustu_bildirildi_mi(db: AsyncSession, makine_id: int, tarih: date) -> bool:
    """Aynı makine+gün için daha önce ``oee.dustu`` olayı üretildi mi (dedup)?"""
    sayi = (
        await db.execute(
            select(func.count())
            .select_from(GidenOlay)
            .where(
                GidenOlay.olay_turu == "oee.dustu",
                GidenOlay.govde["makine_id"].astext == str(makine_id),
                GidenOlay.govde["tarih"].astext == tarih.isoformat(),
            )
        )
    ).scalar_one()
    return int(sayi) > 0


async def dusuk_oee_tara(
    db: AsyncSession, *, tenant_slug: str, esik: float = 0.6, bugun: date | None = None
) -> int:
    """Bugünkü OEE'si eşiğin altındaki makineler için kenar-tetikli ``oee.dustu`` yazar.

    Eşik makine başına ``makine.oee_hedefi``'dir (doluysa); yoksa ``esik`` parametresi.
    Aynı makine+gün için olay **bir kez** üretilir (outbox dedup — S12 ``yaklasan-tara``
    deseninin durumsuz eşdeğeri). Üretim verisi olmayan makineler atlanır (OEE'si 0
    görünür ama "veri yok" ≠ "düştü"). İşlenen makine sayısını döner.
    """
    bugun = bugun or datetime.now(UTC).date()
    baslangic = datetime(bugun.year, bugun.month, bugun.day, tzinfo=UTC)
    satirlar = await oee_ozet(db, baslangic=baslangic, bitis=baslangic + timedelta(days=1))
    hedefler = {
        m.id: m.oee_hedefi
        for m in (await db.execute(select(Makine))).scalars()
        if m.oee_hedefi is not None
    }
    islenen = 0
    for makine_id, kod, sonuc, kayit_sayisi in satirlar:
        if kayit_sayisi == 0:
            continue
        hedef = hedefler.get(makine_id, esik)
        if sonuc.oee >= hedef:
            continue
        if await _oee_dustu_bildirildi_mi(db, makine_id, bugun):
            continue
        await olay_yayinla(
            db,
            olay_turu="oee.dustu",
            govde={
                "makine_id": makine_id,
                "makine_kod": kod,
                "tarih": bugun.isoformat(),
                "oee": round(sonuc.oee, 4),
                "esik": round(hedef, 4),
            },
        )
        await yayinla(tenant_slug, {"tur": "oee.dustu", "makine_id": makine_id})
        islenen += 1
    await db.flush()
    return islenen
