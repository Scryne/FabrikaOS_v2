"""Alembic fan-out runner — programatik migration uygulama.

İki ağaç vardır (bkz. ``alembic.ini``):
- ``public`` → control-plane şeması (bir kez).
- ``tenant`` → ``tenant_<slug>`` şemaları (tek veya tüm aktif tenant'lara fan-out).

Bu fonksiyonlar SENKRONDUR (Alembic ``command`` API senkrondur; env.py içinde kendi
``asyncio.run``'ını çalıştırır). Async bir bağlamdan çağırırken
``await asyncio.to_thread(...)`` ile ayrı bir iş parçacığında çalıştırın — aksi halde
"event loop zaten çalışıyor" hatası alırsınız.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import get_settings

# backend/app/core/db/fanout.py -> repo kökü
_KOK = Path(__file__).resolve().parents[4]
_INI = _KOK / "alembic.ini"


def _cfg(agac: str, *, db_url: str | None, schemas: list[str] | None) -> Config:
    cfg = Config(str(_INI), ini_section=agac)
    cfg.attributes["db_url"] = db_url or get_settings().database_url
    if schemas is not None:
        cfg.attributes["schemas"] = schemas
    return cfg


def public_yukselt(rev: str = "head", *, db_url: str | None = None) -> None:
    """Public (control-plane) ağacını yükseltir."""
    command.upgrade(_cfg("public", db_url=db_url, schemas=None), rev)


def public_indir(rev: str = "base", *, db_url: str | None = None) -> None:
    """Public ağacını geri alır (downgrade)."""
    command.downgrade(_cfg("public", db_url=db_url, schemas=None), rev)


def tenant_yukselt_tek(slug: str, rev: str = "head", *, db_url: str | None = None) -> None:
    """Tek bir ``tenant_<slug>`` şemasını yükseltir (provizyonlamada kullanılır)."""
    command.upgrade(_cfg("tenant", db_url=db_url, schemas=[f"tenant_{slug}"]), rev)


def tenant_indir_tek(slug: str, rev: str = "base", *, db_url: str | None = None) -> None:
    """Tek bir ``tenant_<slug>`` şemasını geri alır."""
    command.downgrade(_cfg("tenant", db_url=db_url, schemas=[f"tenant_{slug}"]), rev)


def tenant_yukselt_tum(rev: str = "head", *, db_url: str | None = None) -> None:
    """Tüm aktif tenant şemalarına fan-out yükseltme (env.py public.tenant'tan okur)."""
    command.upgrade(_cfg("tenant", db_url=db_url, schemas=None), rev)
