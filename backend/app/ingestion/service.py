"""Ingestion iş kuralı — ölçüm paketlerini tenant şemasına idempotent yazar.

Çağıran ``search_path``'i tenant şemasına ayarlamış olmalıdır (REST'te ``tenant_cozumle``,
worker'da ``search_path_ayarla``). Gerçek-zaman yayını burada yapılmaz; çağıran
``etkilenen_makineler`` üzerinden ``yayinla`` eder (test edilebilirlik + ayrışma).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.saha import repository
from app.modules.saha.schemas import OlcumPaketi
from app.modules.uretim.models import UretimVerisi


@dataclass(frozen=True, slots=True)
class IngestSonuc:
    yazilan: int
    atlanan: int
    hatali: int
    etkilenen_makineler: tuple[int, ...]
    hatalar: tuple[str, ...]


async def olcum_yaz_toplu(
    session: AsyncSession, *, cihaz_kod: str, paketler: Sequence[OlcumPaketi]
) -> IngestSonuc:
    """Bir gateway'in ölçüm paketlerini yazar. Cihaz/makine doğrular, idempotent."""
    cihaz = await repository.cihaz_kod_ile(session, cihaz_kod)
    if cihaz is None or not cihaz.aktif:
        return IngestSonuc(0, 0, len(paketler), (), (f"Cihaz bulunamadı/pasif: {cihaz_kod}",))

    yazilan = atlanan = 0
    hatalar: list[str] = []
    etkilenen: set[int] = set()

    for p in paketler:
        makine_id = await repository.makine_id_kod_ile(session, p.makine_kod)
        if makine_id is None:
            hatalar.append(f"Makine bulunamadı: {p.makine_kod}")
            continue
        if not await repository.olcum_isaretle(session, p.olcum_id, makine_id):
            atlanan += 1
            continue
        session.add(
            UretimVerisi(
                makine_id=makine_id,
                zaman=p.zaman,
                vardiya=p.vardiya,
                planlanan_sure_dk=p.planlanan_sure_dk,
                durus_sure_dk=p.durus_sure_dk,
                toplam_adet=p.toplam_adet,
                saglam_adet=p.saglam_adet,
                ideal_cevrim_sn=p.ideal_cevrim_sn,
            )
        )
        etkilenen.add(makine_id)
        yazilan += 1

    cihaz.son_gorulme = datetime.now(UTC)
    await session.flush()
    return IngestSonuc(
        yazilan=yazilan,
        atlanan=atlanan,
        hatali=len(hatalar),
        etkilenen_makineler=tuple(sorted(etkilenen)),
        hatalar=tuple(hatalar),
    )
