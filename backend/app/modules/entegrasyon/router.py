"""Webhook yönetim uçları (``/api/v1/webhooklar``) — S18 / ADR-0020.

Erişim kapısı ``modul_veya_ozellik_gerekli("entegrasyon", "webhook-onizleme")``:
modülü satın almamış tenant'a platform admin bayrakla ön izleme verebilir (S16
tüketimi). RBAC: okuma ``entegrasyon:oku``, yazma ``entegrasyon:yaz``.

``gizli_anahtar`` yalnız oluşturma ve anahtar-yenile yanıtlarında TAM döner (bir kez);
liste/detay her zaman maskelidir. Sabit yollar (``olay-turleri``, ``teslimatlar``)
``/{webhook_id}``'den ÖNCE tanımlıdır (rota eşleşme önceliği).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_veya_ozellik_gerekli, tenant_cozumle
from app.core.exceptions import KaynakBulunamadi
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.entegrasyon import repository, service
from app.modules.entegrasyon.birimler import OLAY_TURU_KATALOGU
from app.modules.entegrasyon.imza import gizli_anahtar_uret
from app.modules.entegrasyon.models import WebhookAboneligi, WebhookTeslimati
from app.modules.entegrasyon.schemas import (
    OlayTuruCevapDTO,
    TeslimatCevapDTO,
    WebhookCevapDTO,
    WebhookGuncelleDTO,
    WebhookOlusturDTO,
)

router = APIRouter(
    tags=["Entegrasyon"],
    dependencies=[Depends(modul_veya_ozellik_gerekli("entegrasyon", "webhook-onizleme"))],
)


def _cevap(a: WebhookAboneligi, *, tam_anahtar: bool = False) -> dict[str, Any]:
    return WebhookCevapDTO(
        id=a.id,
        ad=a.ad,
        url=a.url,
        gizli_anahtar=a.gizli_anahtar if tam_anahtar else service.anahtar_maskele(a.gizli_anahtar),
        olay_turleri=list(a.olay_turleri),
        aktif=a.aktif,
        olusturma_tarihi=a.olusturma_tarihi,
    ).model_dump()


def _teslimat_cevap(t: WebhookTeslimati) -> dict[str, Any]:
    return TeslimatCevapDTO(
        id=t.id,
        dis_anahtar=t.dis_anahtar,
        abonelik_id=t.abonelik_id,
        olay_turu=t.olay_turu,
        durum=t.durum,
        deneme_sayisi=t.deneme_sayisi,
        sonraki_deneme_tarihi=t.sonraki_deneme_tarihi,
        son_deneme_tarihi=t.son_deneme_tarihi,
        yanit_kodu=t.yanit_kodu,
        yanit_ozeti=t.yanit_ozeti,
        govde=dict(t.govde),
        olusturma_tarihi=t.olusturma_tarihi,
    ).model_dump()


@router.get(
    "/webhooklar/olay-turleri",
    response_model=Zarf[list[OlayTuruCevapDTO]],
    summary="Webhook olay türü kataloğu",
)
async def olay_turleri(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("entegrasyon:oku"))],
) -> dict[str, Any]:
    veri = [{"kod": k, "aciklama": a} for k, a in OLAY_TURU_KATALOGU.items()]
    return basari(veri, mesaj="Olay türü kataloğu")


@router.get(
    "/webhooklar/teslimatlar",
    response_model=Zarf[list[TeslimatCevapDTO]],
    summary="Webhook teslimat günlüğü",
)
async def teslimat_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("entegrasyon:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    abonelik_id: int | None = None,
    durum: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.teslimat_listele(
        db, sayfa=sayfa, adet=adet, abonelik_id=abonelik_id, durum=durum
    )
    return sayfali([_teslimat_cevap(t) for t in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.post(
    "/webhooklar/teslimatlar/{teslimat_id}/yeniden-dene",
    response_model=Zarf[TeslimatCevapDTO],
    summary="Teslimatı yeniden kuyruğa al",
)
async def teslimat_yeniden_dene(
    teslimat_id: int,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("entegrasyon:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    teslimat = await repository.teslimat_getir(db, teslimat_id)
    if teslimat is None:
        raise KaynakBulunamadi("Teslimat bulunamadı")
    # Terminal `basarisiz` dahil: bir sonraki relay turunda bir deneme daha yapılır
    # (deneme sayacı korunur — manuel yeniden-dene son şans semantiğidir).
    teslimat.durum = "beklemede"
    teslimat.sonraki_deneme_tarihi = datetime.now(UTC)
    await db.flush()
    await denetim_yaz(
        db,
        eylem="yeniden_dene",
        kaynak="webhook_teslimat",
        kaynak_id=str(teslimat.id),
        kullanici=kullanici,
    )
    return basari(_teslimat_cevap(teslimat), mesaj="Teslimat yeniden kuyruğa alındı")


@router.post(
    "/webhooklar",
    response_model=Zarf[WebhookCevapDTO],
    status_code=201,
    summary="Webhook aboneliği oluştur (gizli anahtar bir kez döner)",
)
async def webhook_olustur(
    govde: WebhookOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("entegrasyon:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    service.url_dogrula(govde.url)
    service.olay_turleri_dogrula(govde.olay_turleri)
    abonelik = WebhookAboneligi(
        ad=govde.ad,
        url=govde.url,
        gizli_anahtar=gizli_anahtar_uret(),
        olay_turleri=govde.olay_turleri,
        aktif=govde.aktif,
    )
    await repository.abonelik_ekle(db, abonelik)
    await denetim_yaz(
        db, eylem="olustur", kaynak="webhook", kaynak_id=str(abonelik.id), kullanici=kullanici
    )
    return basari(
        _cevap(abonelik, tam_anahtar=True),
        mesaj="Webhook aboneliği oluşturuldu — gizli anahtarı şimdi kaydedin, bir daha gösterilmez",
    )


@router.get(
    "/webhooklar",
    response_model=Zarf[list[WebhookCevapDTO]],
    summary="Webhook aboneliklerini listele (anahtar maskeli)",
)
async def webhook_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("entegrasyon:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.abonelik_listele(db, sayfa=sayfa, adet=adet)
    return sayfali([_cevap(a) for a in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/webhooklar/{webhook_id}",
    response_model=Zarf[WebhookCevapDTO],
    summary="Webhook aboneliği detayı (anahtar maskeli)",
)
async def webhook_detay(
    webhook_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("entegrasyon:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    abonelik = await repository.abonelik_getir(db, webhook_id)
    if abonelik is None:
        raise KaynakBulunamadi("Webhook aboneliği bulunamadı")
    return basari(_cevap(abonelik), mesaj="Webhook aboneliği detayı")


@router.patch(
    "/webhooklar/{webhook_id}",
    response_model=Zarf[WebhookCevapDTO],
    summary="Webhook aboneliğini güncelle",
)
async def webhook_guncelle(
    webhook_id: int,
    govde: WebhookGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("entegrasyon:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    abonelik = await repository.abonelik_getir(db, webhook_id)
    if abonelik is None:
        raise KaynakBulunamadi("Webhook aboneliği bulunamadı")
    if govde.url is not None:
        service.url_dogrula(govde.url)
    if govde.olay_turleri is not None:
        service.olay_turleri_dogrula(govde.olay_turleri)
    for alan, deger in govde.model_dump(exclude_unset=True).items():
        if deger is not None:
            setattr(abonelik, alan, deger)
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="webhook", kaynak_id=str(abonelik.id), kullanici=kullanici
    )
    return basari(_cevap(abonelik), mesaj="Webhook aboneliği güncellendi")


@router.delete(
    "/webhooklar/{webhook_id}",
    response_model=Zarf[None],
    summary="Webhook aboneliğini sil",
)
async def webhook_sil(
    webhook_id: int,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("entegrasyon:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    abonelik = await repository.abonelik_getir(db, webhook_id)
    if abonelik is None:
        raise KaynakBulunamadi("Webhook aboneliği bulunamadı")
    await repository.abonelik_sil(db, abonelik)
    await denetim_yaz(
        db, eylem="sil", kaynak="webhook", kaynak_id=str(webhook_id), kullanici=kullanici
    )
    return basari(None, mesaj="Webhook aboneliği silindi")


@router.post(
    "/webhooklar/{webhook_id}/anahtar-yenile",
    response_model=Zarf[WebhookCevapDTO],
    summary="Gizli anahtarı yenile (yeni anahtar bir kez döner)",
)
async def webhook_anahtar_yenile(
    webhook_id: int,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("entegrasyon:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    abonelik = await repository.abonelik_getir(db, webhook_id)
    if abonelik is None:
        raise KaynakBulunamadi("Webhook aboneliği bulunamadı")
    abonelik.gizli_anahtar = gizli_anahtar_uret()
    await db.flush()
    await denetim_yaz(
        db,
        eylem="anahtar_yenile",
        kaynak="webhook",
        kaynak_id=str(abonelik.id),
        kullanici=kullanici,
    )
    return basari(
        _cevap(abonelik, tam_anahtar=True),
        mesaj="Gizli anahtar yenilendi — yeni anahtarı şimdi kaydedin, bir daha gösterilmez",
    )
