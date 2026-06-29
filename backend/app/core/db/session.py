"""Async veritabanı motoru (engine) ve oturum (session) yönetimi.

Motor/oturum tembel (lazy) oluşturulur; böylece import anında DB bağlantısı kurulmaz
ve testler kendi motorunu enjekte edebilir.

``get_session`` istek-kapsamlı bir oturum verir; istek başarılıysa commit, hata olursa
rollback yapar. Tenant izolasyonu (``search_path``) ``tenancy.py`` içindeki dependency
tarafından bu oturumun işlemi (transaction) içinde ayarlanır.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Süreç-genelinde tekil async motoru döndürür (tembel oluşturulur)."""
    global _engine
    if _engine is None:
        ayar = get_settings()
        _engine = create_async_engine(
            ayar.database_url,
            pool_pre_ping=True,
            future=True,
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Tekil async oturum fabrikasını döndürür."""
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False, autoflush=False)
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: istek-kapsamlı oturum (başarıda commit, hatada rollback)."""
    fabrika = get_sessionmaker()
    async with fabrika() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
