"""Ürün/BOM iş kuralları — kapanışta BOM patlatma (otomatik stok tüketimi).

``bom_patlat`` iş emri kapanışıyla **aynı transaction'da** çalışır: reçetenin her
kalemi için ``recete.miktar × is_emri.miktar`` kadar stok çıkışı üretir (S9
``stok_hareketi_uygula`` yeniden kullanımı — kritik eşik kenar-tetiği dahil).

İdempotency iki katmanlı: durum makinesi terminalden çıkışı zaten engeller (çift
kapanış imkânsız); ek olarak hareket ``bom-{is_emri_id}-{malzeme_id}`` idempotency
anahtarı taşır — aynı anahtar varsa kalem atlanır (yarış/yeniden deneme koruması).
Yetersiz stok kapanışı 422 ile durdurur (negatif bakiye yazılamaz; kullanıcı önce
stok düzeltir) — transaction bütünüyle geri alınır, iş emri açık kalır.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import DogrulamaHatasi
from app.kimlik.models import Kullanici
from app.modules.isemri.models import IsEmri
from app.modules.stok.models import Malzeme, StokHareketi
from app.modules.stok.service import stok_hareketi_uygula
from app.modules.urun.models import Recete


async def recete_getir(db: AsyncSession, urun_id: int) -> Recete | None:
    """Reçeteyi kalemleriyle **eager** yükler (async oturumda lazy erişim yasak)."""
    return (
        await db.execute(
            select(Recete).options(selectinload(Recete.kalemler)).where(Recete.urun_id == urun_id)
        )
    ).scalar_one_or_none()


async def bom_patlat(db: AsyncSession, is_emri: IsEmri, *, kullanici: Kullanici) -> int:
    """İş emri kapanışında reçete kalemlerini stok çıkışına dönüştürür; hareket sayısını döner.

    Ürünsüz/miktarsız iş emri veya reçetesiz/pasif reçeteli ürün sessizce atlanır
    (BOM patlatma opt-in'dir: ürün + miktar bağlanmış iş emrine uygulanır).
    """
    if is_emri.urun_id is None or is_emri.miktar is None or is_emri.miktar <= 0:
        return 0
    recete = await recete_getir(db, is_emri.urun_id)
    if recete is None or not recete.aktif or not recete.kalemler:
        return 0

    uretilen = 0
    for kalem in recete.kalemler:
        anahtar = f"bom-{is_emri.id}-{kalem.malzeme_id}"
        mevcut = (
            await db.execute(
                select(StokHareketi.id).where(StokHareketi.idempotency_anahtari == anahtar)
            )
        ).scalar_one_or_none()
        if mevcut is not None:
            continue  # bu kalem zaten tüketilmiş (idempotent)
        malzeme = (
            await db.execute(
                select(Malzeme).where(Malzeme.id == kalem.malzeme_id).with_for_update()
            )
        ).scalar_one_or_none()
        if malzeme is None:
            raise DogrulamaHatasi(
                "Reçete malzemesi bulunamadı",
                detaylar=[{"alan": "malzeme_id", "mesaj": f"#{kalem.malzeme_id}"}],
            )
        tuketim = Decimal(kalem.miktar) * Decimal(is_emri.miktar)
        await stok_hareketi_uygula(
            db,
            malzeme,
            tur="cikis",
            miktar=tuketim,
            aciklama=f"BOM tüketimi — {is_emri.kod}",
            kaynak=f"bom:{is_emri.id}",
            kullanici=kullanici,
            idempotency_anahtari=anahtar,
        )
        uretilen += 1
    return uretilen
