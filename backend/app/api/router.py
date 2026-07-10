"""/api/v1 router toplayıcısı.

Modül router'ları (uretim, isemri, stok, ...) S3+ sprintlerinde buraya include edilir:
    from app.modules.uretim.router import router as uretim_router
    api_router.include_router(uretim_router)
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.ws import router as ws_router
from app.kimlik.kullanici_router import rol_router
from app.kimlik.kullanici_router import router as kullanici_router
from app.kimlik.router import router as kimlik_router
from app.modules.abonelik.router import router as abonelik_router
from app.modules.ai.router import router as ai_router
from app.modules.analitik.router import router as analitik_router
from app.modules.bakim.router import router as bakim_router
from app.modules.crm.router import router as crm_router
from app.modules.duyuru.router import router as duyuru_router
from app.modules.dys.router import router as dys_router
from app.modules.enerji.router import router as enerji_router
from app.modules.ik.router import router as ik_router
from app.modules.ikiz.router import router as ikiz_router
from app.modules.isemri.router import router as isemri_router
from app.modules.isg.router import router as isg_router
from app.modules.kalite.router import router as kalite_router
from app.modules.rapor.router import router as rapor_router
from app.modules.saha.router import router as saha_router
from app.modules.sozlesme.router import router as sozlesme_router
from app.modules.stok.router import router as stok_router
from app.modules.talep.router import router as talep_router
from app.modules.ticari.router import router as ticari_router
from app.modules.uretim.router import router as uretim_router
from app.platform.kimlik_router import router as platform_kimlik_router
from app.platform.router import router as platform_router

api_router = APIRouter()
api_router.include_router(kimlik_router)
api_router.include_router(platform_kimlik_router)
api_router.include_router(platform_router)
api_router.include_router(kullanici_router)
api_router.include_router(rol_router)
api_router.include_router(abonelik_router)
api_router.include_router(uretim_router)
api_router.include_router(ikiz_router)
api_router.include_router(saha_router)
api_router.include_router(isemri_router)
api_router.include_router(bakim_router)
api_router.include_router(stok_router)
api_router.include_router(kalite_router)
api_router.include_router(enerji_router)
api_router.include_router(isg_router)
api_router.include_router(ik_router)
api_router.include_router(crm_router)
api_router.include_router(sozlesme_router)
api_router.include_router(talep_router)
api_router.include_router(dys_router)
api_router.include_router(duyuru_router)
api_router.include_router(ticari_router)
api_router.include_router(ai_router)
api_router.include_router(analitik_router)
api_router.include_router(rapor_router)
api_router.include_router(ws_router)
