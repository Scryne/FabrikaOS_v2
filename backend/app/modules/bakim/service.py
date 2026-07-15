"""Bakım iş kuralları (S24) — vadesi gelen plandan otomatik iş emri üretimi.

``vade_tara`` kenar-tetiklidir ve **bir-kez** garantilidir (iki katman):

1. Plan başına terminal-olmayan (açık) otomatik iş emri varsa yenisi üretilmez
   (``is_emirleri.bakim_plani_id`` bağlantısı dedup anahtarıdır).
2. Üretim sonrası planın vadesi periyot kadar ileri atılır (``periyot_gun`` doluysa;
   yoksa vade temizlenir — tek seferlik plan). İkinci tarama aynı planı yeniden üretmez.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.kimlik.models import Kullanici
from app.modules.bakim.models import BakimPlani
from app.modules.isemri import service as isemri_service
from app.modules.isemri.durum import ILK_DURUM, TERMINAL_DURUMLAR
from app.modules.isemri.models import IsEmri


async def _acik_otomatik_is_emri_var_mi(db: AsyncSession, plan_id: int) -> bool:
    kayit = (
        await db.execute(
            select(IsEmri.id).where(
                IsEmri.bakim_plani_id == plan_id, IsEmri.durum.notin_(TERMINAL_DURUMLAR)
            )
        )
    ).scalar_one_or_none()
    return kayit is not None


async def vade_tara(
    db: AsyncSession, *, kullanici: Kullanici, simdi: datetime | None = None
) -> int:
    """Vadesi gelen aktif planlardan otomatik bakım iş emri üretir; üretilen sayıyı döner."""
    simdi = simdi or datetime.now(UTC)
    planlar = (
        (
            await db.execute(
                select(BakimPlani).where(
                    BakimPlani.aktif.is_(True),
                    BakimPlani.sonraki_bakim_tarihi.isnot(None),
                    BakimPlani.sonraki_bakim_tarihi <= simdi,
                )
            )
        )
        .scalars()
        .all()
    )
    uretilen = 0
    for plan in planlar:
        if await _acik_otomatik_is_emri_var_mi(db, plan.id):
            continue
        is_emri = IsEmri(
            kod=isemri_service.gecici_kod(),
            baslik=f"Bakım — {plan.ad}",
            aciklama=plan.aciklama,
            makine_id=plan.makine_id,
            durum=ILK_DURUM,
            oncelik="yuksek" if plan.tip == "kestirimci" else "orta",
            bakim_plani_id=plan.id,
        )
        db.add(is_emri)
        await db.flush()
        is_emri.kod = isemri_service.kalici_kod(is_emri.id)
        # Vade ileri atılır: periyotlu plan bir sonraki döngüye, periyotsuz plan tek seferlik.
        if plan.periyot_gun:
            plan.sonraki_bakim_tarihi = simdi + timedelta(days=plan.periyot_gun)
        else:
            plan.sonraki_bakim_tarihi = None
        uretilen += 1
    await db.flush()
    return uretilen
