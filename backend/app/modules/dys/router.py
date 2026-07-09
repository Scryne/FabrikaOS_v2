"""DYS uçları (``/api/v1``) — belge + sürümlü içerik (yükle/indir).

Tüm uçlar tenant-kapsamlı + RBAC. Okuma/indirme ``dys:oku``, yazma/yükleme ``dys:yaz``.
İçerik nesne depolamada tutulur; sürümler append-only'dir.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, tenant_cozumle
from app.core.exceptions import DogrulamaHatasi, KaynakBulunamadi
from app.core.gercekzaman import yayinla
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.dys import repository, service
from app.modules.dys.models import Belge, BelgeSurumu
from app.modules.dys.schemas import (
    BelgeCevapDTO,
    BelgeGuncelleDTO,
    BelgeOlusturDTO,
    BelgeSurumuCevapDTO,
    DysOzetDTO,
)

router = APIRouter(tags=["DYS"])

# Yükleme boyut sınırı (16 MiB) — event loop'u ve belleği korur.
_MAKS_BOYUT = 16 * 1024 * 1024


def _belge_cevap(b: Belge) -> dict[str, Any]:
    return BelgeCevapDTO(
        id=b.id,
        kod=b.kod,
        ad=b.ad,
        kategori=b.kategori,
        aciklama=b.aciklama,
        guncel_surum=b.guncel_surum,
        aktif=b.aktif,
        olusturan_kullanici_id=b.olusturan_kullanici_id,
        olusturma_tarihi=b.olusturma_tarihi,
    ).model_dump()


def _surum_cevap(s: BelgeSurumu) -> dict[str, Any]:
    return BelgeSurumuCevapDTO(
        id=s.id,
        belge_id=s.belge_id,
        surum_no=s.surum_no,
        dosya_adi=s.dosya_adi,
        icerik_tipi=s.icerik_tipi,
        boyut=s.boyut,
        yukleyen_kullanici_id=s.yukleyen_kullanici_id,
        aciklama=s.aciklama,
        olusturma_tarihi=s.olusturma_tarihi,
    ).model_dump()


@router.post(
    "/belgeler", response_model=Zarf[BelgeCevapDTO], status_code=201, summary="Belge oluştur"
)
async def belge_olustur(
    govde: BelgeOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("dys:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    belge = Belge(
        kod=service.belge_gecici_kod(),
        ad=govde.ad,
        kategori=govde.kategori,
        aciklama=govde.aciklama,
        olusturan_kullanici_id=kullanici.id,
    )
    await repository.belge_ekle(db, belge)
    belge.kod = service.belge_kalici_kod(belge.id)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="belge", kaynak_id=str(belge.id), kullanici=kullanici
    )
    return basari(_belge_cevap(belge), mesaj="Belge oluşturuldu")


@router.get("/belgeler", response_model=Zarf[list[BelgeCevapDTO]], summary="Belgeleri listele")
async def belge_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("dys:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    kategori: str | None = None,
    aktif: bool | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.belge_listele(
        db,
        sayfa=sayfa,
        adet=adet,
        kategori=kategori,
        aktif=aktif,
        arama=arama,
        siralama=siralama,
        yon=yon,
    )
    return sayfali([_belge_cevap(b) for b in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get("/belgeler/{belge_id}", response_model=Zarf[BelgeCevapDTO], summary="Belge detayı")
async def belge_detay(
    belge_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("dys:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    belge = await repository.belge_getir(db, belge_id)
    if belge is None:
        raise KaynakBulunamadi("Belge bulunamadı")
    return basari(_belge_cevap(belge), mesaj="Belge detayı")


@router.patch("/belgeler/{belge_id}", response_model=Zarf[BelgeCevapDTO], summary="Belge düzenle")
async def belge_guncelle(
    belge_id: int,
    govde: BelgeGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("dys:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    belge = await repository.belge_getir(db, belge_id)
    if belge is None:
        raise KaynakBulunamadi("Belge bulunamadı")
    for alan, deger in govde.model_dump(exclude_unset=True).items():
        if deger is not None:
            setattr(belge, alan, deger)
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="belge", kaynak_id=str(belge.id), kullanici=kullanici
    )
    return basari(_belge_cevap(belge), mesaj="Belge güncellendi")


# --- Sürümler ---
@router.post(
    "/belgeler/{belge_id}/surumler",
    response_model=Zarf[BelgeSurumuCevapDTO],
    status_code=201,
    summary="Belgeye yeni sürüm yükle (multipart)",
)
async def surum_yukle(
    belge_id: int,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("dys:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    dosya: Annotated[UploadFile, File(description="Yüklenecek dosya")],
    aciklama: Annotated[str, Form()] = "",
) -> dict[str, Any]:
    belge = await repository.belge_getir(db, belge_id)
    if belge is None:
        raise KaynakBulunamadi("Belge bulunamadı")
    veri = await dosya.read()
    if len(veri) == 0:
        raise DogrulamaHatasi(
            "Boş dosya yüklenemez", detaylar=[{"alan": "dosya", "mesaj": "içerik gerekli"}]
        )
    if len(veri) > _MAKS_BOYUT:
        raise DogrulamaHatasi(
            "Dosya çok büyük",
            detaylar=[{"alan": "dosya", "mesaj": f"en fazla {_MAKS_BOYUT // (1024 * 1024)} MiB"}],
        )
    surum = await service.surum_ekle(
        db,
        tenant_slug=tenant.slug,
        belge=belge,
        dosya_adi=dosya.filename or "dosya",
        icerik_tipi=dosya.content_type or "application/octet-stream",
        veri=veri,
        yukleyen_kullanici_id=kullanici.id,
        aciklama=aciklama,
    )
    await denetim_yaz(
        db,
        eylem="surum_yukle",
        kaynak="belge",
        kaynak_id=str(belge.id),
        kullanici=kullanici,
        detay={"surum_no": surum.surum_no},
    )
    await yayinla(tenant.slug, {"tur": "dys.belge", "id": belge.id})
    return basari(_surum_cevap(surum), mesaj="Sürüm yüklendi")


@router.get(
    "/belgeler/{belge_id}/surumler",
    response_model=Zarf[list[BelgeSurumuCevapDTO]],
    summary="Belge sürümlerini listele",
)
async def surum_listele(
    belge_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("dys:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    if await repository.belge_getir(db, belge_id) is None:
        raise KaynakBulunamadi("Belge bulunamadı")
    surumler = await repository.surum_listele(db, belge_id)
    return basari([_surum_cevap(s) for s in surumler], mesaj="Sürümler")


@router.get(
    "/belgeler/{belge_id}/surumler/{surum_no}/indir",
    summary="Belge sürümünü indir (ikili içerik)",
)
async def surum_indir(
    belge_id: int,
    surum_no: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("dys:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> Response:
    surum = await repository.surum_getir(db, belge_id, surum_no)
    if surum is None:
        raise KaynakBulunamadi("Sürüm bulunamadı")
    veri = await service.surum_indir(surum)
    dosya = quote(surum.dosya_adi)
    return Response(
        content=veri,
        media_type=surum.icerik_tipi,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{dosya}"},
    )


@router.get("/dys/ozet", response_model=Zarf[DysOzetDTO], summary="DYS (belge) özeti (KPI)")
async def dys_ozet(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("dys:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    ay_basi = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    toplam_belge = await db.scalar(select(func.count()).select_from(Belge)) or 0
    kategori_sayisi = (
        await db.scalar(
            select(func.count(func.distinct(Belge.kategori))).where(Belge.kategori != "")
        )
        or 0
    )
    bu_ay_surum = (
        await db.scalar(
            select(func.count())
            .select_from(BelgeSurumu)
            .where(BelgeSurumu.olusturma_tarihi >= ay_basi)
        )
        or 0
    )
    toplam_boyut = await db.scalar(select(func.coalesce(func.sum(BelgeSurumu.boyut), 0))) or 0

    ozet = DysOzetDTO(
        toplam_belge=int(toplam_belge),
        kategori_sayisi=int(kategori_sayisi),
        bu_ay_surum=int(bu_ay_surum),
        toplam_boyut=int(toplam_boyut),
    )
    return basari(ozet.model_dump(), mesaj="DYS özeti")
