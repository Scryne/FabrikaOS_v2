"""Tenant provizyonlama servisi (idempotent).

Sıra sabittir ve tekrar çalıştırıldığında veriyi bozmaz (alembic-fan-out skill'i):
1. **public kayıt** → ``public.tenant`` + ``public.abonelik`` (varsa atlanır).
2. **şema** → ``CREATE SCHEMA IF NOT EXISTS tenant_<slug>``.
3. **migrate** → tenant migration ağacı yalnızca bu şemaya uygulanır (fan-out tek şema).
4. **tohum** → izin kataloğu + varsayılan roller + admin kullanıcı (varsa atlanır/eşitlenir).

Async bağlamdan çağrılır; migration adımı ``asyncio.to_thread`` ile ayrı iş parçacığında
(Alembic kendi event loop'unu kurar) çalıştırılır.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.control_plane.models import Abonelik, Plan, Tenant
from app.control_plane.moduller import PLAN_KATALOGU
from app.control_plane.uzlastirma import izin_rol_uzlastir
from app.core.config import get_settings
from app.core.db import fanout
from app.core.db.tenancy import sema_adi, slug_gecerli_mi, tenant_bul
from app.core.security.parola import parola_ozetle
from app.kimlik.models import Kullanici, Rol

type _SM = async_sessionmaker[AsyncSession]


async def _plan_tohumla(sm: _SM) -> None:
    """``PLAN_KATALOGU``'nu ``planlar`` tablosuyla eşitler (idempotent upsert).

    Migration ilk seed'i yapar; katalog kod tarafında evrildiğinde (yeni modül/plan)
    her provizyon koşusu tabloyu günceller — yeni migration gerekmez (ADR-0018).
    """
    async with sm() as s, s.begin():
        mevcut = {p.kod: p for p in (await s.execute(select(Plan))).scalars()}
        for tanim in PLAN_KATALOGU.values():
            plan = mevcut.get(tanim.kod)
            if plan is None:
                plan = Plan(kod=tanim.kod, ad=tanim.ad, aktif=True)
                s.add(plan)
            plan.ad = tanim.ad
            plan.koltuk_limiti = tanim.koltuk_limiti
            plan.moduller = sorted(tanim.moduller)
            plan.ozellikler = sorted(tanim.ozellikler)


async def _public_kayit(sm: _SM, slug: str, ad: str, plan_kodu: str) -> int:
    async with sm() as s, s.begin():
        tenant = await tenant_bul(s, slug)
        if tenant is None:
            tenant = Tenant(slug=slug, ad=ad, aktif=True)
            s.add(tenant)
            await s.flush()
            s.add(
                Abonelik(
                    tenant_id=tenant.id,
                    plan_kodu=plan_kodu,
                    durum="deneme",
                    baslangic_tarihi=datetime.now(UTC),
                )
            )
        return tenant.id


async def _sema_olustur(engine: AsyncEngine, slug: str) -> None:
    async with engine.connect() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{sema_adi(slug)}"'))
        await conn.commit()


async def _tohumla(sm: _SM, slug: str, admin_eposta: str, admin_parola: str) -> None:
    async with sm() as s, s.begin():
        # 1+2) izin/rol kataloğu — provizyon ve uzlaştırma AYNI kodu kullanır (tek
        # doğruluk kaynağı; ikisi ayrışırsa yeni tenant ile eskiler arasında fark oluşur).
        await izin_rol_uzlastir(s, slug)
        rol_haritasi = {r.ad: r for r in (await s.execute(select(Rol))).scalars()}

        # 3) admin kullanıcı (varsa atla) + admin rolü
        admin = (
            await s.execute(select(Kullanici).where(Kullanici.eposta == admin_eposta))
        ).scalar_one_or_none()
        if admin is None:
            admin = Kullanici(
                eposta=admin_eposta,
                parola_ozet=parola_ozetle(admin_parola),
                ad_soyad="Tenant Yöneticisi",
                aktif=True,
            )
            s.add(admin)
        if rol_haritasi["admin"] not in admin.roller:
            admin.roller.append(rol_haritasi["admin"])


async def tenant_provizyonla(
    *,
    slug: str,
    ad: str,
    admin_eposta: str,
    admin_parola: str,
    plan_kodu: str = "deneme",
    db_url: str | None = None,
) -> int:
    """Yeni (veya var olan) tenant'ı uçtan uca provizyonlar; tenant id döner."""
    if not slug_gecerli_mi(slug):
        raise ValueError(f"Geçersiz tenant slug: {slug!r}")
    if plan_kodu not in PLAN_KATALOGU:
        raise ValueError(f"Katalogda olmayan plan: {plan_kodu!r}")

    db_url = db_url or get_settings().database_url
    engine = create_async_engine(db_url, poolclass=NullPool)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    try:
        await _plan_tohumla(sm)
        tenant_id = await _public_kayit(sm, slug, ad, plan_kodu)
        await _sema_olustur(engine, slug)
        await asyncio.to_thread(fanout.tenant_yukselt_tek, slug, db_url=db_url)
        await _tohumla(sm, slug, admin_eposta, admin_parola)
        return tenant_id
    finally:
        await engine.dispose()
