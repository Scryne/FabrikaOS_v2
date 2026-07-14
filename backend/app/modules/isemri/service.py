"""İş emri modülü iş kuralları — durum geçişi, atama, otomatik kod, domain olayı.

Durum geçiş tablosu saf ``durum.py``'dedir; bu katman onu DB ve outbox ile birleştirir.
``kapandi``'ya geçişte, iş emrini kapatan iş ile **aynı transaction'da** bir
``is_emri.kapandi`` olayı outbox'a yazılır (transactional outbox / ADR-0007).

``sla_tara`` (S-VB) kenar-tetiklidir: hedef tarihi geçmiş **açık** iş emirleri için
``sla.asildi`` olayını kaynak başına yalnız bir kez yazar (dedup outbox sorgusuyla —
S12 ``sozlesme.yaklasiyor`` deseni).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.olaylar import olay_yayinla
from app.core.sla import SlaAdayi, sla_asildi_yayinla
from app.modules.isemri import repository
from app.modules.isemri.durum import DURUMLAR, TERMINAL_DURUMLAR, gecis_gecerli_mi
from app.modules.isemri.models import IsEmri

OLAY_KAPANDI = "is_emri.kapandi"


def gecici_kod() -> str:
    """Kalıcı kod üretilene dek (id bilinene dek) kullanılan geçici tekil değer."""
    return f"GECICI-{uuid.uuid4().hex}"


def kalici_kod(is_emri_id: int) -> str:
    """İnsan-okur iş emri numarası: ``IE-{yıl}-{id:06d}``."""
    return f"IE-{datetime.now(UTC).year}-{is_emri_id:06d}"


async def dogrula_atanan(db: AsyncSession, atanan_kullanici_id: int) -> None:
    """Atanan kullanıcının bu tenant'ta var olduğunu doğrular (yoksa 404)."""
    if not await repository.kullanici_var_mi(db, atanan_kullanici_id):
        raise KaynakBulunamadi("Atanan kullanıcı bulunamadı")


async def durum_gecisi(
    db: AsyncSession,
    is_emri: IsEmri,
    *,
    hedef: str,
    atanan_kullanici_id: int | None,
) -> IsEmri:
    """İş emrini ``hedef`` duruma geçirir; kuralları uygular ve gerekli olayı yayınlar.

    - Tanımsız hedef durum → 422.
    - Durum makinesine aykırı geçiş → 409.
    - ``atandi`` hedefi ``atanan_kullanici_id`` gerektirir (gövdede veya kayıtta) → 422.
    - ``kapandi`` hedefinde ``kapanis_tarihi`` set edilir + ``is_emri.kapandi`` olayı yazılır.
    """
    if hedef not in DURUMLAR:
        raise DogrulamaHatasi(
            "Geçersiz durum",
            detaylar=[{"alan": "durum", "mesaj": f"Geçerli: {', '.join(sorted(DURUMLAR))}"}],
        )
    if not gecis_gecerli_mi(is_emri.durum, hedef):
        raise CakismaHatasi(f"Geçersiz durum geçişi: {is_emri.durum} → {hedef}")

    if atanan_kullanici_id is not None:
        await dogrula_atanan(db, atanan_kullanici_id)
        is_emri.atanan_kullanici_id = atanan_kullanici_id

    if hedef == "atandi" and is_emri.atanan_kullanici_id is None:
        raise DogrulamaHatasi(
            "Atama için atanan kullanıcı gerekli",
            detaylar=[{"alan": "atanan_kullanici_id", "mesaj": "'atandi' için zorunlu"}],
        )

    is_emri.durum = hedef
    if hedef == "kapandi":
        is_emri.kapanis_tarihi = datetime.now(UTC)
        await olay_yayinla(
            db,
            olay_turu=OLAY_KAPANDI,
            govde={
                "is_emri_id": is_emri.id,
                "kod": is_emri.kod,
                "makine_id": is_emri.makine_id,
                "atanan_kullanici_id": is_emri.atanan_kullanici_id,
                "kapanis_tarihi": is_emri.kapanis_tarihi.isoformat(),
            },
        )
    await db.flush()
    return is_emri


async def sla_tara(db: AsyncSession, *, tenant_slug: str, simdi: datetime | None = None) -> int:
    """Hedef tarihi geçmiş **açık** iş emirleri için ``sla.asildi`` yazar (bir-kez).

    Terminal (kapandi/iptal) kayıtlar olay üretmez; dedup ``core.sla`` outbox
    sorgusuyla sağlanır. İşlenen kayıt sayısını döner.
    """
    simdi = simdi or datetime.now(UTC)
    adaylar = (
        (
            await db.execute(
                select(IsEmri).where(
                    IsEmri.durum.notin_(TERMINAL_DURUMLAR),
                    IsEmri.hedef_tarih.isnot(None),
                    IsEmri.hedef_tarih < simdi,
                )
            )
        )
        .scalars()
        .all()
    )
    return await sla_asildi_yayinla(
        db,
        tenant_slug=tenant_slug,
        kaynak_tur="is_emri",
        adaylar=[
            SlaAdayi(
                kaynak_id=ie.id,
                kod=ie.kod,
                hedef_tarih=ie.hedef_tarih,  # type: ignore[arg-type]
                sorumlu_kullanici_id=ie.atanan_kullanici_id,
            )
            for ie in adaylar
        ],
    )
