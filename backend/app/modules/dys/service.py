"""DYS iş kuralları — oto kod + sürüm yükleme/indirme (nesne depolama orkestrasyonu).

Sürüm ekleme **append-only**'dir: ``guncel_surum+1`` numaralı yeni bir ``BelgeSurumu`` üretir,
dosya içeriğini tenant-izole anahtarla nesne deposuna yazar ve belgenin ``guncel_surum``
alanını günceller. Senkron depo çağrıları ``asyncio.to_thread`` ile sarılır (event loop'u
bloklamamak için; provizyon deseni).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dys.depolama import belge_nesne_anahtari, nesne_depo_al
from app.modules.dys.models import Belge, BelgeSurumu


def belge_gecici_kod() -> str:
    return f"GECICI-{uuid.uuid4().hex}"


def belge_kalici_kod(belge_id: int) -> str:
    """İnsan-okur belge numarası: ``BLG-{yıl}-{id:06d}``."""
    return f"BLG-{datetime.now(UTC).year}-{belge_id:06d}"


async def surum_ekle(
    db: AsyncSession,
    *,
    tenant_slug: str,
    belge: Belge,
    dosya_adi: str,
    icerik_tipi: str,
    veri: bytes,
    yukleyen_kullanici_id: int | None,
    aciklama: str = "",
) -> BelgeSurumu:
    """Belgeye yeni bir sürüm ekler (içeriği nesne deposuna yazar, ``guncel_surum``'u artırır)."""
    yeni_no = belge.guncel_surum + 1
    anahtar = belge_nesne_anahtari(tenant_slug, belge.id, yeni_no, dosya_adi)
    depo = nesne_depo_al()
    await asyncio.to_thread(depo.yukle, anahtar, veri, icerik_tipi)
    surum = BelgeSurumu(
        belge_id=belge.id,
        surum_no=yeni_no,
        dosya_adi=dosya_adi,
        icerik_tipi=icerik_tipi or "application/octet-stream",
        boyut=len(veri),
        nesne_anahtari=anahtar,
        yukleyen_kullanici_id=yukleyen_kullanici_id,
        aciklama=aciklama,
    )
    db.add(surum)
    belge.guncel_surum = yeni_no
    await db.flush()
    return surum


async def surum_indir(surum: BelgeSurumu) -> bytes:
    """Sürümün içeriğini nesne deposundan okur."""
    depo = nesne_depo_al()
    return await asyncio.to_thread(depo.indir, surum.nesne_anahtari)
