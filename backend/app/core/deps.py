"""FastAPI bağımlılıkları (dependencies) — tenant çözümleme, kimlik, RBAC.

Altın kural (tenant-rbac-conventions): tenant-kapsamlı her uç **iki** dependency'den geçer:
``tenant_cozumle`` (tenant'ı belirler + ``search_path``'i ayarlar) ve
``izin_gerekli("modul:islem")`` (RBAC). Bu iki dependency olmadan tenant-kapsamlı uç yazılmaz.

``get_session`` FastAPI tarafından istek başına önbelleğe alınır; bu yüzden ``tenant_cozumle``,
``mevcut_kullanici`` ve uç gövdesi **aynı** oturumu (ve aynı ``search_path``'i) paylaşır.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane import entitlement_service
from app.control_plane.models import Tenant
from app.core.config import get_settings
from app.core.context import cozulmus_tenant_ctx
from app.core.db.session import get_session
from app.core.db.tenancy import search_path_ayarla, slug_gecerli_mi, tenant_bul
from app.core.exceptions import KaynakBulunamadi, KimlikHatasi, YetkiHatasi
from app.core.security import jwt as jwtmod
from app.core.security.politika import guvenlik_ayari, ip_izinli_mi
from app.kimlik.models import Kullanici

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{get_settings().api_v1_prefix}/kimlik/token", auto_error=False
)


def istek_tenant_slug(request: Request) -> str | None:
    """İstekten tenant slug'ını çözer: önce ``X-Tenant`` başlığı, sonra subdomain."""
    x_tenant = request.headers.get("x-tenant")
    if x_tenant:
        return x_tenant.strip().lower()
    host = (request.headers.get("host") or "").split(":")[0]
    parcalar = host.split(".")
    # ör: fabrika-a.fabrikaos.localhost -> "fabrika-a"
    if len(parcalar) >= 3:
        return parcalar[0].lower()
    return None


async def tenant_cozumle(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> Tenant:
    """Tenant'ı belirler, geçerliliğini doğrular ve ``search_path``'i ayarlar."""
    slug = istek_tenant_slug(request)
    if slug is None or not slug_gecerli_mi(slug):
        raise KaynakBulunamadi("Tenant belirlenemedi")
    tenant = await tenant_bul(db, slug)
    if tenant is None or not tenant.aktif or not tenant.abonelik_gecerli:
        # Görünmez kalsın: var olmayan ve erişilemeyen tenant aynı yanıtı verir.
        raise KaynakBulunamadi("Tenant bulunamadı veya erişilemez")
    # Tenant IP izin listesi (S23): liste doluysa istemci IP'si listede olmalı.
    izin_listesi = guvenlik_ayari(tenant.guvenlik_ayarlari, "ip_izin_listesi")
    if izin_listesi:
        istemci_ip = request.client.host if request.client else None
        if not ip_izinli_mi(istemci_ip, izin_listesi):
            raise YetkiHatasi("Bu ağdan erişime izin verilmiyor", hata_kodu="IP_KISITLI")
    await search_path_ayarla(db, slug)
    request.state.tenant_slug = slug
    # Doğrulanmış slug: commit sonrası search_path'i geri kuran yapısal koruma bunu
    # okur (bkz. core/db/tenancy.py::_search_path_otomatik_kur).
    cozulmus_tenant_ctx.set(slug)
    return tenant


async def mevcut_kullanici(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> Kullanici:
    """Access token'ı doğrular, cross-tenant kontrolü yapar ve kullanıcıyı döndürür."""
    if not token:
        raise KimlikHatasi("Kimlik doğrulaması gerekli")
    try:
        icerik = jwtmod.coz(token, "access")
    except jwtmod.TokenGecersiz as exc:
        raise KimlikHatasi("Geçersiz veya süresi dolmuş token") from exc

    # Cross-tenant koruması: token'daki tenant ile istek tenant'ı eşleşmek zorunda.
    if icerik.tenant_slug != tenant.slug:
        raise YetkiHatasi("Token tenant'ı ile istek tenant'ı uyuşmuyor")

    # search_path tenant_cozumle'de ayarlandı → kullanıcı tenant şemasından gelir.
    sonuc = await db.execute(select(Kullanici).where(Kullanici.id == icerik.kullanici_id))
    kullanici = sonuc.scalar_one_or_none()
    if kullanici is None or not kullanici.aktif:
        raise KimlikHatasi("Kullanıcı bulunamadı veya aktif değil")
    return kullanici


def izin_gerekli(izin_kodu: str) -> Callable[..., Awaitable[Kullanici]]:
    """``izin_kodu`` iznini şart koşan bir dependency üretir (yoksa 403)."""

    async def kontrol(
        kullanici: Annotated[Kullanici, Depends(mevcut_kullanici)],
    ) -> Kullanici:
        if not kullanici.izin_var(izin_kodu):
            raise YetkiHatasi(f"Gerekli izin yok: {izin_kodu}")
        return kullanici

    return kontrol


def modul_gerekli(modul_kodu: str) -> Callable[..., Awaitable[None]]:
    """Modülün tenant aboneliğinde açık olmasını şart koşar (S16 / ADR-0018).

    RBAC'den bağımsızdır: modül kapalıysa **admin dahil** herkes 403 ``MODUL_KAPALI``
    alır (entitlement = ne satın alındığı; izin = kimin ne yapabildiği). Router
    seviyesinde ``dependencies=[Depends(modul_gerekli("stok"))]`` olarak bağlanır.
    """

    async def kontrol(
        tenant: Annotated[Tenant, Depends(tenant_cozumle)],
        db: Annotated[AsyncSession, Depends(get_session)],
    ) -> None:
        if not await entitlement_service.tenant_modul_acik_mi(db, tenant, modul_kodu):
            raise YetkiHatasi(
                f"Bu modül aboneliğinizde kapalı: {modul_kodu}", hata_kodu="MODUL_KAPALI"
            )

    return kontrol


def modul_veya_ozellik_gerekli(
    modul_kodu: str, ozellik_kodu: str
) -> Callable[..., Awaitable[None]]:
    """Modül entitlement'ı VEYA özellik bayrağı açıksa geçirir (S18 / ADR-0020).

    ``webhook-onizleme`` tüketimi: ``entegrasyon`` modülünü satın almamış bir tenant'a
    platform admin bayrak override'ıyla (S17 PUT ozellik-bayraklari) ön izleme verebilir.
    İkisi de kapalıysa ``modul_gerekli`` ile aynı sözleşme: 403 ``MODUL_KAPALI``.
    """

    async def kontrol(
        tenant: Annotated[Tenant, Depends(tenant_cozumle)],
        db: Annotated[AsyncSession, Depends(get_session)],
    ) -> None:
        if await entitlement_service.tenant_modul_acik_mi(db, tenant, modul_kodu):
            return
        ozellikler = await entitlement_service.tenant_etkin_ozellikler(db, tenant)
        if ozellikler.get(ozellik_kodu, False):
            return
        raise YetkiHatasi(f"Bu modül aboneliğinizde kapalı: {modul_kodu}", hata_kodu="MODUL_KAPALI")

    return kontrol
