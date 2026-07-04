"""İK iş kuralları — oto kod (izin talebi) + KVKK maskeleme + izin gün hesabı.

``tc_maskele`` KVKK veri minimizasyonu gereği TC kimlik numarasını yanıtta gizler
(yalnız son 2 hane görünür). ``izin_gun_sayisi`` başlangıç/bitiş dâhil gün sayısını hesaplar.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CakismaHatasi, DogrulamaHatasi
from app.kimlik.models import Kullanici
from app.modules.ik import izin_durum
from app.modules.ik.models import IzinTalebi


def izin_gecici_kod() -> str:
    return f"GECICI-{uuid.uuid4().hex}"


def izin_kalici_kod(izin_id: int) -> str:
    """İnsan-okur izin talebi numarası: ``IZ-{yıl}-{id:06d}``."""
    return f"IZ-{datetime.now(UTC).year}-{izin_id:06d}"


def tc_maskele(tc: str) -> str:
    """KVKK: TC kimlik numarasını maskeler; yalnız son 2 hane görünür (boşsa boş döner)."""
    if not tc:
        return ""
    if len(tc) <= 2:
        return "*" * len(tc)
    return "*" * (len(tc) - 2) + tc[-2:]


def izin_gun_sayisi(baslangic: date, bitis: date) -> int:
    """İzin gün sayısı (başlangıç ve bitiş dâhil); bitiş başlangıçtan önceyse 0."""
    fark = (bitis - baslangic).days + 1
    return max(fark, 0)


async def izin_durum_gecisi(
    db: AsyncSession,
    izin: IzinTalebi,
    *,
    hedef: str,
    onaylayan: Kullanici | None = None,
    red_nedeni: str | None = None,
) -> IzinTalebi:
    """İzin talebini ``hedef`` duruma geçirir; durum makinesi + onay/red alanlarını uygular.

    - Tanımsız hedef → 422; makineye aykırı geçiş → 409.
    - ``reddedildi`` ``red_nedeni`` gerektirir → 422.
    - ``onaylandi``/``reddedildi`` onaylayan + onay tarihini yazar (``ik:onay`` router'da).
    """
    if hedef not in izin_durum.DURUMLAR:
        raise DogrulamaHatasi(
            "Geçersiz durum",
            detaylar=[
                {"alan": "durum", "mesaj": f"Geçerli: {', '.join(sorted(izin_durum.DURUMLAR))}"}
            ],
        )
    if not izin_durum.gecis_gecerli_mi(izin.durum, hedef):
        raise CakismaHatasi(f"Geçersiz durum geçişi: {izin.durum} → {hedef}")

    if hedef == "reddedildi" and not (red_nedeni and red_nedeni.strip()):
        raise DogrulamaHatasi(
            "Red nedeni gerekli",
            detaylar=[{"alan": "red_nedeni", "mesaj": "'reddedildi' için zorunlu"}],
        )

    izin.durum = hedef
    if hedef in ("onaylandi", "reddedildi"):
        izin.onaylayan_kullanici_id = onaylayan.id if onaylayan is not None else None
        izin.onay_tarihi = datetime.now(UTC)
    if hedef == "reddedildi" and red_nedeni is not None:
        izin.red_nedeni = red_nedeni
    await db.flush()
    return izin
