"""Sözleşme iş kuralları — oto kod + durum geçişi + yaklaşan-bitiş taraması (outbox).

``yaklasan_tara`` **kenar-tetiklidir**: bitişine ``esik_gun`` veya daha az kalan aktif
sözleşmeler için ``sozlesme.yaklasiyor`` domain olayını **sözleşme başına yalnız bir kez**
yazar (``yaklasim_bildirildi`` bayrağı). S9 ``stok.kritik`` deseniyle aynı; teslimat (webhook
relay) S18'e bırakıldı (olay outbox'ta ``durum='beklemede'`` kalır).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CakismaHatasi, DogrulamaHatasi
from app.core.gercekzaman import yayinla
from app.core.olaylar import olay_yayinla
from app.modules.sozlesme import durum as sdurum
from app.modules.sozlesme import repository
from app.modules.sozlesme.hesap import kalan_gun
from app.modules.sozlesme.models import Sozlesme


def sozlesme_gecici_kod() -> str:
    return f"GECICI-{uuid.uuid4().hex}"


def sozlesme_kalici_kod(sozlesme_id: int) -> str:
    """İnsan-okur sözleşme numarası: ``SZ-{yıl}-{id:06d}``."""
    return f"SZ-{datetime.now(UTC).year}-{sozlesme_id:06d}"


async def sozlesme_durum_gecisi(db: AsyncSession, sozlesme: Sozlesme, *, hedef: str) -> Sozlesme:
    """Sözleşmeyi ``hedef`` duruma geçirir (tanımsız → 422; makineye aykırı → 409)."""
    if hedef not in sdurum.DURUMLAR:
        raise DogrulamaHatasi(
            "Geçersiz durum",
            detaylar=[{"alan": "durum", "mesaj": f"Geçerli: {', '.join(sorted(sdurum.DURUMLAR))}"}],
        )
    if not sdurum.gecis_gecerli_mi(sozlesme.durum, hedef):
        raise CakismaHatasi(f"Geçersiz durum geçişi: {sozlesme.durum} → {hedef}")
    sozlesme.durum = hedef
    await db.flush()
    return sozlesme


async def yaklasan_tara(
    db: AsyncSession, *, tenant_slug: str, esik_gun: int = 30, bugun: date | None = None
) -> int:
    """Yaklaşan-bitiş sözleşmeleri için kenar-tetikli ``sozlesme.yaklasiyor`` olayı yazar.

    Aktif + bitişine ``esik_gun`` içinde (kalan ≥ 0) + henüz bildirilmemiş sözleşmeler
    işlenir. Her biri için bir outbox olayı + best-effort gerçek-zaman sinyali; bayrak
    işaretlenir (bir daha üretilmez). İşlenen sözleşme sayısını döner.
    """
    bugun = bugun or datetime.now(UTC).date()
    sinir = bugun + timedelta(days=esik_gun)
    adaylar = await repository.yaklasan_bildirilmemis(db, bugun=bugun, sinir=sinir)
    for s in adaylar:
        await olay_yayinla(
            db,
            olay_turu="sozlesme.yaklasiyor",
            govde={
                "sozlesme_id": s.id,
                "kod": s.kod,
                "firma_id": s.firma_id,
                "baslik": s.baslik,
                "bitis_tarihi": s.bitis_tarihi.isoformat(),
                "kalan_gun": kalan_gun(s.bitis_tarihi, bugun),
            },
        )
        s.yaklasim_bildirildi = True
        await yayinla(tenant_slug, {"tur": "sozlesme.yaklasiyor", "id": s.id})
    await db.flush()
    return len(adaylar)
