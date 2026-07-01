"""Kalite uçları (``/api/v1``) — denetim + Tam CAPA.

Tüm uçlar tenant-kapsamlı + RBAC (``kalite:oku``/``kalite:yaz``); yazma işlemleri audit'lenir.
Uygunsuzluk + CAPA uçları sonraki task'ta eklenir.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, tenant_cozumle
from app.core.exceptions import DogrulamaHatasi, KaynakBulunamadi
from app.core.gercekzaman import yayinla
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.kalite import repository, service
from app.modules.kalite.birimler import KONTROL_SONUCLARI, KONTROL_TURLERI
from app.modules.kalite.models import KaliteKontrol
from app.modules.kalite.schemas import KaliteKontrolCevapDTO, KaliteKontrolOlusturDTO

router = APIRouter(tags=["Kalite"])


def _kontrol_cevap(k: KaliteKontrol) -> dict[str, Any]:
    return KaliteKontrolCevapDTO(
        id=k.id,
        kod=k.kod,
        makine_id=k.makine_id,
        is_emri_id=k.is_emri_id,
        kontrol_turu=k.kontrol_turu,
        sonuc=k.sonuc,
        olculen_deger=float(k.olculen_deger) if k.olculen_deger is not None else None,
        alt_limit=float(k.alt_limit) if k.alt_limit is not None else None,
        ust_limit=float(k.ust_limit) if k.ust_limit is not None else None,
        numune_adedi=k.numune_adedi,
        uygunsuz_adet=k.uygunsuz_adet,
        aciklama=k.aciklama,
        kontrol_eden_kullanici_id=k.kontrol_eden_kullanici_id,
        zaman=k.zaman,
    ).model_dump()


def _kontrol_dogrula(govde: KaliteKontrolOlusturDTO) -> None:
    if govde.sonuc not in KONTROL_SONUCLARI:
        raise DogrulamaHatasi(
            "Geçersiz sonuç",
            detaylar=[
                {"alan": "sonuc", "mesaj": f"Geçerli: {', '.join(sorted(KONTROL_SONUCLARI))}"}
            ],
        )
    if govde.kontrol_turu not in KONTROL_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz kontrol türü",
            detaylar=[
                {
                    "alan": "kontrol_turu",
                    "mesaj": f"Geçerli: {', '.join(sorted(KONTROL_TURLERI))}",
                }
            ],
        )
    if govde.uygunsuz_adet > govde.numune_adedi:
        raise DogrulamaHatasi(
            "Uygunsuz adet numune adedini aşamaz",
            detaylar=[
                {"alan": "uygunsuz_adet", "mesaj": f"<= numune_adedi ({govde.numune_adedi})"}
            ],
        )
    if (
        govde.alt_limit is not None
        and govde.ust_limit is not None
        and govde.alt_limit > govde.ust_limit
    ):
        raise DogrulamaHatasi(
            "alt_limit ust_limit'ten büyük olamaz",
            detaylar=[{"alan": "alt_limit", "mesaj": "<= ust_limit"}],
        )


@router.post(
    "/kalite-kontrolleri",
    response_model=Zarf[KaliteKontrolCevapDTO],
    status_code=201,
    summary="Kalite kontrol kaydı oluştur",
)
async def kontrol_olustur(
    govde: KaliteKontrolOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    _kontrol_dogrula(govde)
    kontrol = KaliteKontrol(
        kod=service.kalite_kontrol_gecici_kod(),
        makine_id=govde.makine_id,
        is_emri_id=govde.is_emri_id,
        kontrol_turu=govde.kontrol_turu,
        sonuc=govde.sonuc,
        olculen_deger=govde.olculen_deger,
        alt_limit=govde.alt_limit,
        ust_limit=govde.ust_limit,
        numune_adedi=govde.numune_adedi,
        uygunsuz_adet=govde.uygunsuz_adet,
        aciklama=govde.aciklama,
        kontrol_eden_kullanici_id=kullanici.id,
        **({"zaman": govde.zaman} if govde.zaman is not None else {}),
    )
    await repository.kontrol_ekle(db, kontrol)
    kontrol.kod = service.kalite_kontrol_kalici_kod(kontrol.id)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="kalite_kontrol", kaynak_id=str(kontrol.id), kullanici=kullanici
    )
    await yayinla(tenant.slug, {"tur": "kalite.kontrol", "id": kontrol.id})
    return basari(_kontrol_cevap(kontrol), mesaj="Kalite kontrol oluşturuldu")


@router.get(
    "/kalite-kontrolleri",
    response_model=Zarf[list[KaliteKontrolCevapDTO]],
    summary="Kalite kontrolleri listele",
)
async def kontrol_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    makine_id: int | None = None,
    sonuc: str | None = None,
    arama: str | None = None,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.kontrol_listele(
        db,
        sayfa=sayfa,
        adet=adet,
        makine_id=makine_id,
        sonuc=sonuc,
        arama=arama,
        baslangic=baslangic,
        bitis=bitis,
        siralama=siralama,
        yon=yon,
    )
    return sayfali([_kontrol_cevap(k) for k in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/kalite-kontrolleri/{kontrol_id}",
    response_model=Zarf[KaliteKontrolCevapDTO],
    summary="Kalite kontrol detayı",
)
async def kontrol_detay(
    kontrol_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    kontrol = await repository.kontrol_getir(db, kontrol_id)
    if kontrol is None:
        raise KaynakBulunamadi("Kalite kontrol bulunamadı")
    return basari(_kontrol_cevap(kontrol), mesaj="Kalite kontrol detayı")
