"""Sağlık (health) uçları — kimlik/tenant gerektirmez."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app import __version__
from app.core.config import get_settings
from app.core.responses import Zarf, basari

router = APIRouter(tags=["Sağlık"])


@router.get("/saglik", response_model=Zarf[dict[str, Any]], summary="Canlılık (liveness)")
async def saglik() -> dict[str, Any]:
    ayar = get_settings()
    return basari(
        {
            "durum": "ayakta",
            "uygulama": ayar.app_name,
            "surum": __version__,
            "ortam": ayar.app_env,
        },
        mesaj="Servis ayakta",
    )


@router.get("/saglik/hazir", response_model=Zarf[dict[str, Any]], summary="Hazırlık (readiness)")
async def hazir() -> dict[str, Any]:
    # S2+: DB ve Redis bağlantı kontrolleri burada yapılacak.
    return basari({"hazir": True}, mesaj="Servis hazır")
