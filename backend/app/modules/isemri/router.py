"""İş emri modülü uçları (``/api/v1``).

Tüm uçlar tenant-kapsamlı ve RBAC korumalı (``isemri:oku`` / ``isemri:yaz``).
Yazma işlemleri denetim izine kaydedilir (tenant-rbac-conventions).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli
from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.isemri import repository, service
from app.modules.isemri.durum import ILK_DURUM
from app.modules.isemri.models import ONCELIKLER, IsEmri, IsEmriYorum
from app.modules.isemri.schemas import (
    DurumGuncelleDTO,
    IsEmriCevapDTO,
    IsEmriDetayDTO,
    IsEmriOlusturDTO,
    IsEmriYorumCevapDTO,
    YorumOlusturDTO,
)
from app.modules.uretim import repository as uretim_repository

router = APIRouter(tags=["İş Emirleri"])


def _yorum_cevap(y: IsEmriYorum) -> dict[str, Any]:
    return IsEmriYorumCevapDTO(
        id=y.id,
        metin=y.metin,
        yazan_kullanici_id=y.yazan_kullanici_id,
        yazan_eposta=y.yazan_eposta,
        olusturma_tarihi=y.olusturma_tarihi,
    ).model_dump()


def _cevap(e: IsEmri) -> dict[str, Any]:
    return IsEmriCevapDTO(
        id=e.id,
        kod=e.kod,
        baslik=e.baslik,
        aciklama=e.aciklama,
        makine_id=e.makine_id,
        atanan_kullanici_id=e.atanan_kullanici_id,
        durum=e.durum,
        oncelik=e.oncelik,
        kapanis_tarihi=e.kapanis_tarihi,
        olusturma_tarihi=e.olusturma_tarihi,
    ).model_dump()


def _detay_cevap(e: IsEmri) -> dict[str, Any]:
    return IsEmriDetayDTO(
        id=e.id,
        kod=e.kod,
        baslik=e.baslik,
        aciklama=e.aciklama,
        makine_id=e.makine_id,
        atanan_kullanici_id=e.atanan_kullanici_id,
        durum=e.durum,
        oncelik=e.oncelik,
        kapanis_tarihi=e.kapanis_tarihi,
        olusturma_tarihi=e.olusturma_tarihi,
        yorumlar=[
            IsEmriYorumCevapDTO(
                id=y.id,
                metin=y.metin,
                yazan_kullanici_id=y.yazan_kullanici_id,
                yazan_eposta=y.yazan_eposta,
                olusturma_tarihi=y.olusturma_tarihi,
            )
            for y in e.yorumlar
        ],
    ).model_dump()


@router.post(
    "/is-emirleri",
    response_model=Zarf[IsEmriCevapDTO],
    status_code=201,
    summary="İş emri oluştur",
)
async def is_emri_olustur(
    govde: IsEmriOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("isemri:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    if govde.oncelik not in ONCELIKLER:
        raise DogrulamaHatasi(
            "Geçersiz öncelik",
            detaylar=[{"alan": "oncelik", "mesaj": f"Geçerli: {', '.join(sorted(ONCELIKLER))}"}],
        )
    if await uretim_repository.makine_getir(db, govde.makine_id) is None:
        raise KaynakBulunamadi("Makine bulunamadı")
    if govde.kod is not None and await repository.kod_var_mi(db, govde.kod):
        raise CakismaHatasi("Bu kod ile iş emri zaten var")
    if govde.atanan_kullanici_id is not None:
        await service.dogrula_atanan(db, govde.atanan_kullanici_id)

    is_emri = IsEmri(
        kod=govde.kod or service.gecici_kod(),
        baslik=govde.baslik,
        aciklama=govde.aciklama,
        makine_id=govde.makine_id,
        atanan_kullanici_id=govde.atanan_kullanici_id,
        durum=ILK_DURUM,
        oncelik=govde.oncelik,
    )
    await repository.ekle(db, is_emri)
    if govde.kod is None:
        # id artık biliniyor → kalıcı insan-okur kod üret.
        is_emri.kod = service.kalici_kod(is_emri.id)
        await db.flush()

    await denetim_yaz(
        db, eylem="olustur", kaynak="is_emri", kaynak_id=str(is_emri.id), kullanici=kullanici
    )
    return basari(_cevap(is_emri), mesaj="İş emri oluşturuldu")


@router.get(
    "/is-emirleri", response_model=Zarf[list[IsEmriCevapDTO]], summary="İş emirlerini listele"
)
async def is_emri_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("isemri:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    sayfa: int = 1,
    adet: int = 20,
    durum: str | None = None,
    makine_id: int | None = None,
    atanan_kullanici_id: int | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.listele(
        db,
        sayfa=sayfa,
        adet=adet,
        durum=durum,
        makine_id=makine_id,
        atanan_kullanici_id=atanan_kullanici_id,
        arama=arama,
        siralama=siralama,
        yon=yon,
    )
    return sayfali([_cevap(e) for e in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/is-emirleri/{is_emri_id}",
    response_model=Zarf[IsEmriDetayDTO],
    summary="İş emri detayı (yorumlarla)",
)
async def is_emri_detay(
    is_emri_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("isemri:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    is_emri = await repository.getir_yorumlu(db, is_emri_id)
    if is_emri is None:
        raise KaynakBulunamadi("İş emri bulunamadı")
    return basari(_detay_cevap(is_emri), mesaj="İş emri detayı")


@router.patch(
    "/is-emirleri/{is_emri_id}/durum",
    response_model=Zarf[IsEmriCevapDTO],
    summary="İş emri durumunu değiştir (atama/ilerlet/kapat/iptal)",
)
async def is_emri_durum(
    is_emri_id: int,
    govde: DurumGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("isemri:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    is_emri = await repository.getir_kilitli(db, is_emri_id)
    if is_emri is None:
        raise KaynakBulunamadi("İş emri bulunamadı")
    await service.durum_gecisi(
        db, is_emri, hedef=govde.durum, atanan_kullanici_id=govde.atanan_kullanici_id
    )
    await denetim_yaz(
        db,
        eylem="durum_guncelle",
        kaynak="is_emri",
        kaynak_id=str(is_emri.id),
        kullanici=kullanici,
        detay={"durum": is_emri.durum},
    )
    return basari(_cevap(is_emri), mesaj="Durum güncellendi")


@router.post(
    "/is-emirleri/{is_emri_id}/yorum",
    response_model=Zarf[IsEmriYorumCevapDTO],
    status_code=201,
    summary="İş emrine yorum ekle",
)
async def is_emri_yorum(
    is_emri_id: int,
    govde: YorumOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("isemri:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    if await repository.getir(db, is_emri_id) is None:
        raise KaynakBulunamadi("İş emri bulunamadı")
    yorum = IsEmriYorum(
        is_emri_id=is_emri_id,
        yazan_kullanici_id=kullanici.id,
        yazan_eposta=kullanici.eposta,
        metin=govde.metin,
    )
    await repository.yorum_ekle(db, yorum)
    await denetim_yaz(
        db,
        eylem="yorum_ekle",
        kaynak="is_emri",
        kaynak_id=str(is_emri_id),
        kullanici=kullanici,
    )
    return basari(_yorum_cevap(yorum), mesaj="Yorum eklendi")
