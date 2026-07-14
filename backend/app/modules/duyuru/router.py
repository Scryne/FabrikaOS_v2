"""Duyuru uçları (``/api/v1``) — CRUD + yayınla/kaldır (gerçek-zaman ``duyuru.yeni``).

Tüm uçlar tenant-kapsamlı + RBAC. Okuma ``duyuru:oku``, yazma/yayınlama ``duyuru:yaz``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.exceptions import DogrulamaHatasi, KaynakBulunamadi
from app.core.gercekzaman import yayinla
from app.core.olaylar import olay_yayinla
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.duyuru import repository, service
from app.modules.duyuru.birimler import ONEM_DUZEYLERI
from app.modules.duyuru.models import Duyuru
from app.modules.duyuru.schemas import DuyuruCevapDTO, DuyuruGuncelleDTO, DuyuruOlusturDTO

router = APIRouter(tags=["Duyuru"], dependencies=[Depends(modul_gerekli("duyuru"))])


def _cevap(d: Duyuru) -> dict[str, Any]:
    return DuyuruCevapDTO(
        id=d.id,
        kod=d.kod,
        baslik=d.baslik,
        icerik=d.icerik,
        onem=d.onem,
        yayinda=d.yayinda,
        yayin_tarihi=d.yayin_tarihi,
        bitis_tarihi=d.bitis_tarihi,
        hedef_departman=d.hedef_departman,
        olusturan_kullanici_id=d.olusturan_kullanici_id,
        olusturma_tarihi=d.olusturma_tarihi,
    ).model_dump()


def _onem_dogrula(onem: str) -> None:
    if onem not in ONEM_DUZEYLERI:
        raise DogrulamaHatasi(
            "Geçersiz önem düzeyi",
            detaylar=[{"alan": "onem", "mesaj": f"Geçerli: {', '.join(sorted(ONEM_DUZEYLERI))}"}],
        )


@router.post(
    "/duyurular", response_model=Zarf[DuyuruCevapDTO], status_code=201, summary="Duyuru oluştur"
)
async def duyuru_olustur(
    govde: DuyuruOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("duyuru:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    _onem_dogrula(govde.onem)
    duyuru = Duyuru(
        kod=service.duyuru_gecici_kod(),
        baslik=govde.baslik,
        icerik=govde.icerik,
        onem=govde.onem,
        hedef_departman=govde.hedef_departman,
        bitis_tarihi=govde.bitis_tarihi,
        olusturan_kullanici_id=kullanici.id,
    )
    await repository.ekle(db, duyuru)
    duyuru.kod = service.duyuru_kalici_kod(duyuru.id)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="duyuru", kaynak_id=str(duyuru.id), kullanici=kullanici
    )
    return basari(_cevap(duyuru), mesaj="Duyuru oluşturuldu")


@router.get("/duyurular", response_model=Zarf[list[DuyuruCevapDTO]], summary="Duyuruları listele")
async def duyuru_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("duyuru:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    onem: str | None = None,
    yayinda: bool | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.listele(
        db, sayfa=sayfa, adet=adet, onem=onem, yayinda=yayinda
    )
    return sayfali([_cevap(d) for d in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get("/duyurular/{duyuru_id}", response_model=Zarf[DuyuruCevapDTO], summary="Duyuru detayı")
async def duyuru_detay(
    duyuru_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("duyuru:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    duyuru = await repository.getir(db, duyuru_id)
    if duyuru is None:
        raise KaynakBulunamadi("Duyuru bulunamadı")
    return basari(_cevap(duyuru), mesaj="Duyuru detayı")


@router.patch(
    "/duyurular/{duyuru_id}", response_model=Zarf[DuyuruCevapDTO], summary="Duyuru düzenle"
)
async def duyuru_guncelle(
    duyuru_id: int,
    govde: DuyuruGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("duyuru:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    duyuru = await repository.getir(db, duyuru_id)
    if duyuru is None:
        raise KaynakBulunamadi("Duyuru bulunamadı")
    if govde.onem is not None:
        _onem_dogrula(govde.onem)
    for alan, deger in govde.model_dump(exclude_unset=True).items():
        if deger is not None:
            setattr(duyuru, alan, deger)
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="duyuru", kaynak_id=str(duyuru.id), kullanici=kullanici
    )
    return basari(_cevap(duyuru), mesaj="Duyuru güncellendi")


@router.post(
    "/duyurular/{duyuru_id}/yayinla",
    response_model=Zarf[DuyuruCevapDTO],
    summary="Duyuruyu yayınla (duyuru.yeni olayı)",
)
async def duyuru_yayinla(
    duyuru_id: int,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("duyuru:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    duyuru = await repository.getir(db, duyuru_id)
    if duyuru is None:
        raise KaynakBulunamadi("Duyuru bulunamadı")
    duyuru.yayinda = True
    duyuru.yayin_tarihi = datetime.now(UTC)
    await db.flush()
    # Bildirim üretici (S-VB) outbox'tan beslenir: duyuru yayını dayanıklı olay olarak
    # da yazılır (gerçek-zaman sinyali best-effort kalır; outbox otoritedir).
    await olay_yayinla(
        db,
        olay_turu="duyuru.yeni",
        govde={"kaynak_tur": "duyuru", "kaynak_id": duyuru.id, "baslik": duyuru.baslik},
    )
    await denetim_yaz(
        db, eylem="yayinla", kaynak="duyuru", kaynak_id=str(duyuru.id), kullanici=kullanici
    )
    await yayinla(tenant.slug, {"tur": "duyuru.yeni", "id": duyuru.id, "onem": duyuru.onem})
    return basari(_cevap(duyuru), mesaj="Duyuru yayınlandı")


@router.post(
    "/duyurular/{duyuru_id}/kaldir",
    response_model=Zarf[DuyuruCevapDTO],
    summary="Duyuruyu yayından kaldır",
)
async def duyuru_kaldir(
    duyuru_id: int,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("duyuru:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    duyuru = await repository.getir(db, duyuru_id)
    if duyuru is None:
        raise KaynakBulunamadi("Duyuru bulunamadı")
    duyuru.yayinda = False
    await db.flush()
    await denetim_yaz(
        db, eylem="kaldir", kaynak="duyuru", kaynak_id=str(duyuru.id), kullanici=kullanici
    )
    return basari(_cevap(duyuru), mesaj="Duyuru yayından kaldırıldı")
