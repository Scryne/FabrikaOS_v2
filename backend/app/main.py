"""FastAPI uygulama fabrikası (app factory)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.router import api_router
from app.api.saglik import router as saglik_router
from app.core.config import get_settings
from app.core.exceptions import hata_handlerlari_kaydet
from app.core.logging import yapilandir_loglama
from app.core.middleware import BeklenmeyenHataMiddleware, RequestContextMiddleware

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    ayar = get_settings()
    yapilandir_loglama(ayar.log_level)
    logger.info("FabrikaOS başlatılıyor (ortam=%s, surum=%s)", ayar.app_env, __version__)
    yield
    logger.info("FabrikaOS kapatılıyor")


def create_app() -> FastAPI:
    ayar = get_settings()

    app = FastAPI(
        title="FabrikaOS API",
        version=__version__,
        description="Çok kiracılı (multi-tenant) MES + ERP SaaS platformu",
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Dıştan içe: CORS → istek bağlamı → beklenmeyen hata. (Starlette son eklenen middleware'i
    # en dışta uygular.) Hata katmanı en içte ki 500 yanıtı da CORS + x-request-id taşısın.
    app.add_middleware(BeklenmeyenHataMiddleware)
    app.add_middleware(RequestContextMiddleware)
    if ayar.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=ayar.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    hata_handlerlari_kaydet(app)

    app.include_router(saglik_router)
    app.include_router(api_router, prefix=ayar.api_v1_prefix)

    return app


app = create_app()
