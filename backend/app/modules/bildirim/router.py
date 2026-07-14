"""Bildirim uçları (``/api/v1``) — kişisel yüzey; oturum yeterli, modül kapısı yok.

Bildirim çapraz-kesen özelliktir (S-VB / ADR-0021): ``modul_gerekli`` almaz ve izin
gerektirmez — kullanıcı **yalnız kendi** bildirimlerini görür/yönetir. Kişisel süzgeç
repository sorgusuna ``kullanici_id`` olarak zorlanır (controller'a bırakılmaz);
başkasının bildirimi 404 (görünmez).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.session import get_session
from app.core.deps import mevcut_kullanici, tenant_cozumle
from app.core.exceptions import DogrulamaHatasi, KaynakBulunamadi
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.bildirim import repository
from app.modules.bildirim.hedefleme import BILDIRIM_OLAYLARI
from app.modules.bildirim.models import Bildirim
from app.modules.bildirim.schemas import (
    BildirimCevapDTO,
    BildirimOzetDTO,
    BildirimTercihDTO,
    BildirimTercihGuncelleDTO,
    OkunduSayisiDTO,
)

router = APIRouter(tags=["Bildirim"])


def _cevap(b: Bildirim) -> dict[str, Any]:
    return BildirimCevapDTO(
        id=b.id,
        olay_turu=b.olay_turu,
        baslik=b.baslik,
        govde=b.govde,
        veri=b.veri,
        onem=b.onem,
        okundu=b.okundu,
        okundu_tarihi=b.okundu_tarihi,
        olusturma_tarihi=b.olusturma_tarihi,
    ).model_dump()


@router.get(
    "/bildirimler", response_model=Zarf[list[BildirimCevapDTO]], summary="Bildirimlerim (sayfalı)"
)
async def bildirim_listele(
    kullanici: Annotated[Kullanici, Depends(mevcut_kullanici)],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    okundu: bool | None = None,
    olay_turu: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.listele(
        db, kullanici_id=kullanici.id, sayfa=sayfa, adet=adet, okundu=okundu, olay_turu=olay_turu
    )
    return sayfali([_cevap(b) for b in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get("/bildirimler/ozet", response_model=Zarf[BildirimOzetDTO], summary="Zil rozeti özeti")
async def bildirim_ozet(
    kullanici: Annotated[Kullanici, Depends(mevcut_kullanici)],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    okunmamis, toplam, son = await repository.ozet(db, kullanici_id=kullanici.id)
    return basari(
        BildirimOzetDTO(
            okunmamis=okunmamis, toplam=toplam, son=[BildirimCevapDTO(**_cevap(b)) for b in son]
        ).model_dump(),
        mesaj="Bildirim özeti",
    )


@router.post(
    "/bildirimler/{bildirim_id}/okundu",
    response_model=Zarf[BildirimCevapDTO],
    summary="Bildirimi okundu işaretle",
)
async def bildirim_okundu(
    bildirim_id: int,
    kullanici: Annotated[Kullanici, Depends(mevcut_kullanici)],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    bildirim = await repository.getir(db, bildirim_id, kullanici_id=kullanici.id)
    if bildirim is None:
        raise KaynakBulunamadi("Bildirim bulunamadı")
    if not bildirim.okundu:
        bildirim.okundu = True
        bildirim.okundu_tarihi = datetime.now(UTC)
        await db.flush()
    return basari(_cevap(bildirim), mesaj="Bildirim okundu")


@router.post(
    "/bildirimler/tumunu-okundu",
    response_model=Zarf[OkunduSayisiDTO],
    summary="Tüm bildirimlerimi okundu say",
)
async def bildirim_tumunu_okundu(
    kullanici: Annotated[Kullanici, Depends(mevcut_kullanici)],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    guncellenen = await repository.tumunu_okundu_yap(db, kullanici_id=kullanici.id)
    return basari(OkunduSayisiDTO(guncellenen=guncellenen).model_dump(), mesaj="Tümü okundu")


@router.get(
    "/bildirim-tercihleri",
    response_model=Zarf[list[BildirimTercihDTO]],
    summary="Bildirim tercihlerim (katalog + override)",
)
async def tercihleri_getir(
    kullanici: Annotated[Kullanici, Depends(mevcut_kullanici)],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    kayitli = {
        t.olay_turu: t for t in await repository.tercihleri_getir(db, kullanici_id=kullanici.id)
    }
    tercihler = [
        BildirimTercihDTO(
            olay_turu=olay_turu,
            uygulama_ici=kayitli[olay_turu].uygulama_ici if olay_turu in kayitli else True,
            eposta=kayitli[olay_turu].eposta if olay_turu in kayitli else False,
        ).model_dump()
        for olay_turu in sorted(BILDIRIM_OLAYLARI)
    ]
    return basari(tercihler, mesaj="Bildirim tercihleri")


@router.put(
    "/bildirim-tercihleri",
    response_model=Zarf[list[BildirimTercihDTO]],
    summary="Bildirim tercihlerimi güncelle",
)
async def tercihleri_guncelle(
    govde: BildirimTercihGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(mevcut_kullanici)],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    gecersiz = [t.olay_turu for t in govde.tercihler if t.olay_turu not in BILDIRIM_OLAYLARI]
    if gecersiz:
        raise DogrulamaHatasi(
            "Katalog dışı olay türü",
            detaylar=[
                {"alan": "olay_turu", "mesaj": f"Geçersiz: {', '.join(sorted(set(gecersiz)))}"}
            ],
        )
    guncel: list[dict[str, Any]] = []
    for tercih in govde.tercihler:
        kayit = await repository.tercih_upsert(
            db,
            kullanici_id=kullanici.id,
            olay_turu=tercih.olay_turu,
            uygulama_ici=tercih.uygulama_ici,
            eposta=tercih.eposta,
        )
        guncel.append(
            BildirimTercihDTO(
                olay_turu=kayit.olay_turu, uygulama_ici=kayit.uygulama_ici, eposta=kayit.eposta
            ).model_dump()
        )
    return basari(guncel, mesaj="Bildirim tercihleri güncellendi")
