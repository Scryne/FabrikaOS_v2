"""/api/v1 router toplayıcısı.

Modül router'ları (uretim, isemri, stok, ...) S3+ sprintlerinde buraya include edilir:
    from app.modules.uretim.router import router as uretim_router
    api_router.include_router(uretim_router)
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.ws import router as ws_router
from app.kimlik.kullanici_router import router as kullanici_router
from app.kimlik.router import router as kimlik_router
from app.modules.bakim.router import router as bakim_router
from app.modules.enerji.router import router as enerji_router
from app.modules.isemri.router import router as isemri_router
from app.modules.isg.router import router as isg_router
from app.modules.kalite.router import router as kalite_router
from app.modules.saha.router import router as saha_router
from app.modules.stok.router import router as stok_router
from app.modules.uretim.router import router as uretim_router

api_router = APIRouter()
api_router.include_router(kimlik_router)
api_router.include_router(kullanici_router)
api_router.include_router(uretim_router)
api_router.include_router(saha_router)
api_router.include_router(isemri_router)
api_router.include_router(bakim_router)
api_router.include_router(stok_router)
api_router.include_router(kalite_router)
api_router.include_router(enerji_router)
api_router.include_router(isg_router)
api_router.include_router(ws_router)
