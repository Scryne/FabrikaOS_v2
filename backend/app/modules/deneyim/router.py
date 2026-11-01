"""S27-A uçları: ``GET /onaylarim`` (birleşik onay kutusu) ve ``GET /ara`` (içerik araması).

İkisi de modül-bağımsızdır (router seviyesinde ``modul_gerekli`` yok); her kaynak kendi okuma/onay
iznini ve modül aboneliğini ``service`` içinde ayrı ayrı denetler (ADR-0045).
"""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.db.session import get_session
from app.core.deps import mevcut_kullanici, tenant_cozumle
from app.core.responses import Zarf, basari
from app.kimlik.models import Kullanici
from app.modules.deneyim import service

router = APIRouter(tags=["Platform deneyimi"])

Kullanicim = Annotated[Kullanici, Depends(mevcut_kullanici)]
Db = Annotated[AsyncSession, Depends(get_session)]
TenantDep = Annotated[Tenant, Depends(tenant_cozumle)]


class OnayKalemiDTO(BaseModel):
    tur: str
    id: int
    kod: str
    baslik: str
    ozet: str
    talep_eden: str | None
    tarih: datetime
    onay_yolu: str
    red_yolu: str | None
    red_gerekce_zorunlu: bool
    detay_yolu: str


class OnayKutusuDTO(BaseModel):
    kalemler: list[OnayKalemiDTO]
    kendi_kayitlarim: int


class AramaKaydiDTO(BaseModel):
    id: int
    baslik: str
    alt: str
    yol: str


class AramaGrubuDTO(BaseModel):
    tur: str
    kayitlar: list[AramaKaydiDTO]


@router.get("/onaylarim", response_model=Zarf[OnayKutusuDTO], summary="Onay bekleyen işlerim")
async def onaylarim(k: Kullanicim, db: Db, tenant: TenantDep) -> dict[str, Any]:
    kutu = await service.onay_kutusu(db, tenant, k)
    return basari(
        OnayKutusuDTO(
            kalemler=[OnayKalemiDTO(**vars(x)) for x in kutu.kalemler],
            kendi_kayitlarim=kutu.kendi_kayitlarim,
        ).model_dump(),
        mesaj="Onay kutusu",
    )


@router.get("/ara", response_model=Zarf[list[AramaGrubuDTO]], summary="İçerik araması")
async def ara(
    k: Kullanicim,
    db: Db,
    tenant: TenantDep,
    q: Annotated[str, Query(min_length=2, max_length=100)],
    limit: Annotated[int, Query(ge=1, le=10)] = 5,
) -> dict[str, Any]:
    return basari(await service.ara(db, tenant, k, q.strip(), limit), mesaj="Arama")
