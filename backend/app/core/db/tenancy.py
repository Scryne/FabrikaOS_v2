"""Çok kiracılılık çekirdeği: ``search_path`` izolasyonu (EN KRİTİK modül).

Tenant izolasyonu tek savunma hattıdır (RLS bilinçli olarak kapsam dışı — bkz. ADR-0003).
Bu yüzden ``search_path`` disiplini burada TEK NOKTADA çözülür:

- ``set_config('search_path', '<sema>, public', true)`` kullanılır. Üçüncü argüman
  ``true`` (is_local) → ayar **işleme (transaction) özeldir**; commit/rollback'te otomatik
  sıfırlanır. Böylece bağlantı havuza dönerken ``search_path`` sızmaz (R3 riski kapatılır).
- Slug katı bir biçimde doğrulanır (yalnızca ``[a-z0-9-]``); şema adı asla doğrudan
  string birleştirmeyle güvenilmez girdiden üretilmez.
"""

from __future__ import annotations

import re

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant

# DNS-label uyumlu slug (subdomain olarak da kullanılır): küçük harf/rakam/tire, 1–63.
SLUG_DESENI = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def slug_gecerli_mi(slug: str) -> bool:
    """Slug DNS-label biçimine uyuyor mu (şema adı/subdomain için güvenli mi)?"""
    return bool(SLUG_DESENI.fullmatch(slug))


def sema_adi(slug: str) -> str:
    """``slug`` → ``tenant_<slug>`` şema adı. Geçersiz slug'da ``ValueError``."""
    if not slug_gecerli_mi(slug):
        raise ValueError(f"Geçersiz tenant slug: {slug!r}")
    return f"tenant_{slug}"


async def search_path_ayarla(session: AsyncSession, slug: str) -> None:
    """Aktif işlem için ``search_path``'i ``tenant_<slug>, public`` yapar (işlem-yerel)."""
    sema = sema_adi(slug)
    await session.execute(
        text("SELECT set_config('search_path', :sp, true)"),
        {"sp": f"{sema}, public"},
    )


async def search_path_sifirla(session: AsyncSession) -> None:
    """``search_path``'i yalnızca ``public`` yapar (işlem-yerel) — control-plane sorguları için."""
    await session.execute(text("SELECT set_config('search_path', 'public', true)"))


async def tenant_bul(session: AsyncSession, slug: str) -> Tenant | None:
    """``public.tenant``'tan slug ile tenant'ı bulur (abonelikler eager yüklenir)."""
    if not slug_gecerli_mi(slug):
        return None
    sonuc = await session.execute(select(Tenant).where(Tenant.slug == slug))
    return sonuc.scalar_one_or_none()
