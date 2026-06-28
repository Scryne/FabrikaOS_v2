"""/api/v1 router toplayıcısı.

Modül router'ları (uretim, isemri, stok, ...) S3+ sprintlerinde buraya include edilir:
    from app.modules.uretim.router import router as uretim_router
    api_router.include_router(uretim_router)
"""

from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter()
