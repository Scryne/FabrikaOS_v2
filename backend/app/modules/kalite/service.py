"""Kalite iş kuralları — oto kod üretimi + CAPA durum geçişi (durum geçişi Task 4'te eklenir)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CakismaHatasi, DogrulamaHatasi
from app.modules.kalite import durum
from app.modules.kalite.models import Uygunsuzluk


def kalite_kontrol_gecici_kod() -> str:
    return f"GECICI-{uuid.uuid4().hex}"


def kalite_kontrol_kalici_kod(kontrol_id: int) -> str:
    """İnsan-okur kalite kontrol numarası: ``KK-{yıl}-{id:06d}``."""
    return f"KK-{datetime.now(UTC).year}-{kontrol_id:06d}"


def uygunsuzluk_gecici_kod() -> str:
    return f"GECICI-{uuid.uuid4().hex}"


def uygunsuzluk_kalici_kod(uygunsuzluk_id: int) -> str:
    """İnsan-okur uygunsuzluk numarası: ``UY-{yıl}-{id:06d}``."""
    return f"UY-{datetime.now(UTC).year}-{uygunsuzluk_id:06d}"


async def capa_durum_gecisi(
    db: AsyncSession,
    uygunsuzluk: Uygunsuzluk,
    *,
    hedef: str,
    kok_neden: str | None = None,
    dogrulama_notu: str | None = None,
) -> Uygunsuzluk:
    """Uygunsuzluğu ``hedef`` duruma geçirir (saf makine + alan yan etkileri).

    - Tanımsız hedef → 422; makineye aykırı geçiş → 409.
    - ``kok_neden`` durumuna geçişte kök-neden yazılabilir.
    - ``kapandi``: kapanış tarihi + doğrulama notu.
    """
    if hedef not in durum.DURUMLAR:
        raise DogrulamaHatasi(
            "Geçersiz durum",
            detaylar=[{"alan": "hedef", "mesaj": f"Geçerli: {', '.join(sorted(durum.DURUMLAR))}"}],
        )
    if not durum.gecis_gecerli_mi(uygunsuzluk.durum, hedef):
        raise CakismaHatasi(f"Geçersiz durum geçişi: {uygunsuzluk.durum} → {hedef}")

    uygunsuzluk.durum = hedef
    if hedef == "kok_neden" and kok_neden is not None:
        uygunsuzluk.kok_neden = kok_neden
    if hedef == "kapandi":
        uygunsuzluk.kapanis_tarihi = datetime.now(UTC)
        if dogrulama_notu is not None:
            uygunsuzluk.dogrulama_notu = dogrulama_notu
    await db.flush()
    return uygunsuzluk
