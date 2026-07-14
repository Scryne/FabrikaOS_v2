"""SLA aşım taraması çekirdeği (S-VB / ADR-0021) — kenar-tetikli, bir-kez garantili.

İş emri ve talep modülleri aynı deseni paylaşır: hedef tarihi geçmiş **açık** kayıtlar
için ``sla.asildi`` outbox olayı yazılır. Dedup, outbox'un kendisinden sorgulanır
(``olay_turu='sla.asildi' ∧ govde->>'kaynak_tur' ∧ govde->>'kaynak_id'``) — kaynak
tabloya bayrak kolonu eklemek yerine olay geçmişi tek doğruluk kaynağıdır; ikinci
tarama aynı kaynak için ikinci olay üretmez (S12 ``sozlesme.yaklasiyor`` deseninin
genelleştirilmiş hali).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.gercekzaman import yayinla
from app.core.olaylar import GidenOlay, olay_yayinla

OLAY_SLA_ASILDI = "sla.asildi"


@dataclass(frozen=True)
class SlaAdayi:
    """Hedef tarihi geçmiş açık kaydın olaya taşınacak özeti."""

    kaynak_id: int
    kod: str
    hedef_tarih: datetime
    sorumlu_kullanici_id: int | None = None


async def bildirilmis_kaynak_idler(db: AsyncSession, *, kaynak_tur: str) -> set[int]:
    """Bu kaynak türü için daha önce ``sla.asildi`` üretilmiş kaynak id kümesi."""
    sorgu = select(GidenOlay.govde["kaynak_id"].astext).where(
        GidenOlay.olay_turu == OLAY_SLA_ASILDI,
        GidenOlay.govde["kaynak_tur"].astext == kaynak_tur,
    )
    return {int(v) for (v,) in (await db.execute(sorgu)).all() if v is not None}


async def sla_asildi_yayinla(
    db: AsyncSession,
    *,
    tenant_slug: str,
    kaynak_tur: str,
    adaylar: list[SlaAdayi],
) -> int:
    """Bildirilmemiş adaylar için ``sla.asildi`` olayı yazar; işlenen sayıyı döner.

    Çağıran adayları (açık + hedef tarihi geçmiş) seçmiş olmalıdır; bu fonksiyon
    yalnız dedup + outbox + best-effort gerçek-zaman sinyalinden sorumludur.
    """
    if not adaylar:
        return 0
    bildirilmis = await bildirilmis_kaynak_idler(db, kaynak_tur=kaynak_tur)
    islenen = 0
    for aday in adaylar:
        if aday.kaynak_id in bildirilmis:
            continue
        govde: dict[str, object] = {
            "kaynak_tur": kaynak_tur,
            "kaynak_id": aday.kaynak_id,
            "kod": aday.kod,
            "hedef_tarih": aday.hedef_tarih.isoformat(),
        }
        if aday.sorumlu_kullanici_id is not None:
            govde["sorumlu_kullanici_id"] = aday.sorumlu_kullanici_id
        await olay_yayinla(db, olay_turu=OLAY_SLA_ASILDI, govde=govde)
        await yayinla(
            tenant_slug,
            {"tur": OLAY_SLA_ASILDI, "kaynak_tur": kaynak_tur, "kaynak_id": aday.kaynak_id},
        )
        islenen += 1
    await db.flush()
    return islenen
