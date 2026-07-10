"""API anahtarı yönetim uçları (``/api/v1/api-anahtarlari``) — S18 / ADR-0020.

Sıkı modül kapısı ``modul_gerekli("entegrasyon")`` (webhook'un aksine bayrak GEÇMEZ).
RBAC: okuma ``entegrasyon:oku``, yazma ``entegrasyon:yaz``. Düz anahtar yalnız
oluşturma yanıtında döner (bir kez); DB'de SHA-256 özet saklanır, listede yalnız
``onek`` görünür.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.exceptions import KaynakBulunamadi
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.entegrasyon import service
from app.modules.entegrasyon.models import ApiAnahtari
from app.modules.entegrasyon.schemas import (
    ApiAnahtariCevapDTO,
    ApiAnahtariGuncelleDTO,
    ApiAnahtariOlusturDTO,
)

router = APIRouter(
    prefix="/api-anahtarlari",
    tags=["Entegrasyon"],
    dependencies=[Depends(modul_gerekli("entegrasyon"))],
)


def _cevap(a: ApiAnahtari, *, anahtar: str | None = None) -> dict[str, Any]:
    return ApiAnahtariCevapDTO(
        id=a.id,
        ad=a.ad,
        onek=a.onek,
        izinler=list(a.izinler),
        aktif=a.aktif,
        gecerlilik_tarihi=a.gecerlilik_tarihi,
        son_kullanim_tarihi=a.son_kullanim_tarihi,
        olusturma_tarihi=a.olusturma_tarihi,
        anahtar=anahtar,
    ).model_dump()


async def _getir(db: AsyncSession, anahtar_id: int) -> ApiAnahtari:
    sonuc = await db.execute(select(ApiAnahtari).where(ApiAnahtari.id == anahtar_id))
    anahtar = sonuc.scalar_one_or_none()
    if anahtar is None:
        raise KaynakBulunamadi("API anahtarı bulunamadı")
    return anahtar


@router.post(
    "",
    response_model=Zarf[ApiAnahtariCevapDTO],
    status_code=201,
    summary="API anahtarı oluştur (düz anahtar bir kez döner)",
)
async def anahtar_olustur(
    govde: ApiAnahtariOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("entegrasyon:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    service.kapsamlar_dogrula(govde.izinler)
    duz = service.api_anahtar_uret()
    anahtar = ApiAnahtari(
        ad=govde.ad,
        onek=duz[: service.ONEK_UZUNLUGU],
        anahtar_ozet=service.anahtar_ozetle(duz),
        izinler=govde.izinler,
        gecerlilik_tarihi=govde.gecerlilik_tarihi,
        olusturan_kullanici_id=kullanici.id,
    )
    db.add(anahtar)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="api_anahtar", kaynak_id=str(anahtar.id), kullanici=kullanici
    )
    return basari(
        _cevap(anahtar, anahtar=duz),
        mesaj="API anahtarı oluşturuldu — anahtarı şimdi kaydedin, bir daha gösterilmez",
    )


@router.get(
    "",
    response_model=Zarf[list[ApiAnahtariCevapDTO]],
    summary="API anahtarlarını listele (yalnız önek görünür)",
)
async def anahtar_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("entegrasyon:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    toplam = (await db.execute(select(func.count()).select_from(ApiAnahtari))).scalar_one()
    sonuc = await db.execute(
        select(ApiAnahtari).order_by(ApiAnahtari.id.desc()).offset((sayfa - 1) * adet).limit(adet)
    )
    return sayfali([_cevap(a) for a in sonuc.scalars()], sayfa=sayfa, adet=adet, toplam=int(toplam))


@router.patch(
    "/{anahtar_id}",
    response_model=Zarf[ApiAnahtariCevapDTO],
    summary="API anahtarını güncelle (ad/aktif)",
)
async def anahtar_guncelle(
    anahtar_id: int,
    govde: ApiAnahtariGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("entegrasyon:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    anahtar = await _getir(db, anahtar_id)
    for alan, deger in govde.model_dump(exclude_unset=True).items():
        if deger is not None:
            setattr(anahtar, alan, deger)
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="api_anahtar", kaynak_id=str(anahtar.id), kullanici=kullanici
    )
    return basari(_cevap(anahtar), mesaj="API anahtarı güncellendi")


@router.delete(
    "/{anahtar_id}",
    response_model=Zarf[None],
    summary="API anahtarını sil (kalıcı iptal)",
)
async def anahtar_sil(
    anahtar_id: int,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("entegrasyon:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    anahtar = await _getir(db, anahtar_id)
    await db.delete(anahtar)
    await db.flush()
    await denetim_yaz(
        db, eylem="sil", kaynak="api_anahtar", kaynak_id=str(anahtar_id), kullanici=kullanici
    )
    return basari(None, mesaj="API anahtarı silindi")
