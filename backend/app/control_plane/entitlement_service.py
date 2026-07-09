"""Tenant'ın etkin entitlement'ını hesaplayan/yöneten servis (S16 / ADR-0018).

Plan + override'lar her istekte **taze sorgulanır** (önbellek YOK): entitlement
değişimi bir sonraki istekte anında etkilidir. Redis önbelleği bilinçli olarak
ertelendi (ADR-0018) — sorgular indeksli ve ucuzdur.

Plan kaydı bulunamazsa (geçerli abonelik yok / plan silinmiş) sonuç **fail-closed**:
tüm modüller kapalı, koltuk limiti 0.
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane import entitlement
from app.control_plane.models import ModulHakki, OzellikBayragi, Plan, Tenant
from app.control_plane.moduller import MODUL_KATALOGU, OZELLIK_KATALOGU


async def plan_getir(db: AsyncSession, tenant: Tenant) -> Plan | None:
    """Tenant'ın geçerli aboneliğinin (aktif) plan kaydını döndürür; yoksa ``None``."""
    ab = tenant.gecerli_abonelik
    if ab is None:
        return None
    sonuc = await db.execute(select(Plan).where(Plan.kod == ab.plan_kodu, Plan.aktif))
    return sonuc.scalar_one_or_none()


async def hak_haritasi_getir(db: AsyncSession, tenant_id: int) -> dict[str, bool]:
    """Tenant'ın modül override'ları: kod -> açık/kapalı."""
    sonuc = await db.execute(select(ModulHakki).where(ModulHakki.tenant_id == tenant_id))
    return {h.modul_kodu: h.acik for h in sonuc.scalars()}


async def bayrak_haritasi_getir(db: AsyncSession, tenant_id: int) -> dict[str, bool]:
    """Tenant'ın özellik bayrağı override'ları: kod -> açık/kapalı."""
    sonuc = await db.execute(select(OzellikBayragi).where(OzellikBayragi.tenant_id == tenant_id))
    return {b.kod: b.acik for b in sonuc.scalars()}


async def tenant_etkin_moduller(db: AsyncSession, tenant: Tenant) -> dict[str, bool]:
    """Katalogdaki tüm modüller için kod -> açık/kapalı (plan + override birleşimi)."""
    plan = await plan_getir(db, tenant)
    plan_moduller: list[str] = list(plan.moduller) if plan is not None else []
    return entitlement.etkin_moduller(plan_moduller, await hak_haritasi_getir(db, tenant.id))


async def tenant_modul_acik_mi(db: AsyncSession, tenant: Tenant, modul_kodu: str) -> bool:
    """Tek modül için etkin entitlement (``modul_gerekli`` dependency'sinin çekirdeği)."""
    plan = await plan_getir(db, tenant)
    plan_moduller = list(plan.moduller) if plan is not None else []
    return entitlement.modul_acik_mi(
        modul_kodu, plan_moduller, await hak_haritasi_getir(db, tenant.id)
    )


async def tenant_etkin_ozellikler(db: AsyncSession, tenant: Tenant) -> dict[str, bool]:
    """Katalogdaki tüm özellik bayrakları için kod -> açık/kapalı."""
    plan = await plan_getir(db, tenant)
    plan_ozellikler: list[str] = list(plan.ozellikler) if plan is not None else []
    return entitlement.etkin_ozellikler(plan_ozellikler, await bayrak_haritasi_getir(db, tenant.id))


async def koltuk_limiti_getir(db: AsyncSession, tenant: Tenant) -> int | None:
    """Etkin koltuk limiti: ``None`` = sınırsız; plan yoksa 0 (fail-closed)."""
    plan = await plan_getir(db, tenant)
    if plan is None:
        return 0
    return plan.koltuk_limiti


async def modul_hakki_ayarla(
    db: AsyncSession, tenant_id: int, modul_kodu: str, acik: bool | None
) -> None:
    """Modül override'ı yazar/günceller; ``acik=None`` override'ı kaldırır (plana döner).

    Katalog dışı kod reddedilir — yazım hatası sessizce ölü kayıt üretmesin.
    """
    if modul_kodu not in MODUL_KATALOGU:
        raise ValueError(f"Katalogda olmayan modül: {modul_kodu!r}")
    if acik is None:
        await db.execute(
            delete(ModulHakki).where(
                ModulHakki.tenant_id == tenant_id, ModulHakki.modul_kodu == modul_kodu
            )
        )
        return
    mevcut = (
        await db.execute(
            select(ModulHakki).where(
                ModulHakki.tenant_id == tenant_id, ModulHakki.modul_kodu == modul_kodu
            )
        )
    ).scalar_one_or_none()
    if mevcut is None:
        db.add(ModulHakki(tenant_id=tenant_id, modul_kodu=modul_kodu, acik=acik))
    else:
        mevcut.acik = acik


async def ozellik_bayragi_ayarla(
    db: AsyncSession, tenant_id: int, kod: str, acik: bool | None
) -> None:
    """Özellik bayrağı override'ı yazar/günceller; ``acik=None`` kaldırır."""
    if kod not in OZELLIK_KATALOGU:
        raise ValueError(f"Katalogda olmayan özellik: {kod!r}")
    if acik is None:
        await db.execute(
            delete(OzellikBayragi).where(
                OzellikBayragi.tenant_id == tenant_id, OzellikBayragi.kod == kod
            )
        )
        return
    mevcut = (
        await db.execute(
            select(OzellikBayragi).where(
                OzellikBayragi.tenant_id == tenant_id, OzellikBayragi.kod == kod
            )
        )
    ).scalar_one_or_none()
    if mevcut is None:
        db.add(OzellikBayragi(tenant_id=tenant_id, kod=kod, acik=acik))
    else:
        mevcut.acik = acik
