"""Platform tenant yönetim servisi — control-plane okuma/yazma iş kuralları.

Sorgular ``PublicBase`` modelleri üzerinden çalışır (şema sabit ``public``);
tenant şemasına yalnız kontrollü noktalarda (koltuk sayımı, ihraç, silme) ve
``sema_adi()`` doğrulamasından geçmiş adlarla dokunulur — bu, provizyondaki
``CREATE SCHEMA`` istisnasının aynısıdır (control-plane çapraz-şema operasyonu).
"""

from __future__ import annotations

import asyncio

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.control_plane import entitlement_service
from app.control_plane.models import Abonelik, Plan, PlatformYonetici, Tenant
from app.control_plane.moduller import MODUL_KATALOGU, OZELLIK_KATALOGU, PLAN_KATALOGU
from app.control_plane.provizyon import tenant_provizyonla
from app.core.config import get_settings
from app.core.db.tenancy import sema_adi, slug_gecerli_mi, tenant_bul
from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.security.redis_istemci import get_redis
from app.modules.dys.depolama import nesne_depo_al
from app.platform.denetim import platform_denetim_yaz
from app.platform.schemas import (
    ModulDurumDTO,
    OzellikDurumDTO,
    PlatformSaglikDTO,
    SondaDTO,
    TenantDetayDTO,
    TenantGuncelleDTO,
    TenantOzetDTO,
    TenantProvizyonDTO,
)

# Testlerin provizyon/ihraç hedef veritabanını enjekte etmesi için (rapor
# ``oturum_fabrikasi_ayarla`` deseni). ``None`` → ayarlardaki ``database_url``.
_db_url: str | None = None


def db_url_ayarla(url: str | None) -> None:
    """Provizyon/ihraç işlerinin hedef DB URL'ini enjekte eder (testler için)."""
    global _db_url
    _db_url = url


def db_url_al() -> str:
    return _db_url if _db_url is not None else get_settings().database_url


async def tenant_getir(db: AsyncSession, tenant_id: int) -> Tenant:
    """Tenant'ı id ile bulur; yoksa 404."""
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise KaynakBulunamadi("Tenant bulunamadı")
    return tenant


def _son_abonelik(tenant: Tenant) -> Abonelik | None:
    """Geçerli abonelik; yoksa en son açılan kayıt (askıdaki tenant'ın planı görünür kalsın)."""
    gecerli = tenant.gecerli_abonelik
    if gecerli is not None:
        return gecerli
    if tenant.abonelikler:
        return max(tenant.abonelikler, key=lambda a: a.id)
    return None


async def koltuk_kullanilan_say(db: AsyncSession, slug: str) -> int | None:
    """Tenant şemasındaki aktif kullanıcı sayısı; şema/tablo yoksa ``None``.

    ``to_regclass`` koruması: provizyonu yarım kalmış ya da silinmekte olan tenant
    listeyi düşürmesin. Şema adı ``sema_adi()`` doğrulamasından geçer.
    """
    sema = sema_adi(slug)
    var = await db.scalar(
        text("SELECT to_regclass(:tablo) IS NOT NULL"), {"tablo": f"{sema}.kullanici"}
    )
    if not var:
        return None
    sayi = await db.scalar(text(f'SELECT count(*) FROM "{sema}".kullanici WHERE aktif'))
    return int(sayi or 0)


async def plan_haritasi(db: AsyncSession) -> dict[str, Plan]:
    return {p.kod: p for p in (await db.execute(select(Plan))).scalars()}


async def tenant_ozeti(db: AsyncSession, tenant: Tenant, planlar: dict[str, Plan]) -> TenantOzetDTO:
    ab = _son_abonelik(tenant)
    plan = planlar.get(ab.plan_kodu) if ab is not None else None
    return TenantOzetDTO(
        id=tenant.id,
        slug=tenant.slug,
        ad=tenant.ad,
        aktif=tenant.aktif,
        plan_kodu=ab.plan_kodu if ab is not None else None,
        abonelik_durum=ab.durum if ab is not None else None,
        koltuk_limiti=plan.koltuk_limiti if plan is not None else None,
        koltuk_kullanilan=await koltuk_kullanilan_say(db, tenant.slug),
        olusturma_tarihi=tenant.olusturma_tarihi,
    )


async def tenant_listele(
    db: AsyncSession, *, sayfa: int, adet: int, arama: str | None
) -> tuple[list[TenantOzetDTO], int]:
    sorgu = select(Tenant)
    if arama:
        desen = f"%{arama}%"
        sorgu = sorgu.where(or_(Tenant.slug.ilike(desen), Tenant.ad.ilike(desen)))
    toplam = await db.scalar(select(func.count()).select_from(sorgu.subquery())) or 0
    sonuc = await db.execute(sorgu.order_by(Tenant.id).offset((sayfa - 1) * adet).limit(adet))
    planlar = await plan_haritasi(db)
    kayitlar = [await tenant_ozeti(db, t, planlar) for t in sonuc.scalars()]
    return kayitlar, int(toplam)


async def _modul_durumlari(db: AsyncSession, tenant: Tenant) -> list[ModulDurumDTO]:
    etkin = await entitlement_service.tenant_etkin_moduller(db, tenant)
    haklar = await entitlement_service.hak_haritasi_getir(db, tenant.id)
    return [
        ModulDurumDTO(
            kod=kod,
            ad=MODUL_KATALOGU[kod],
            acik=acik,
            kaynak="hak" if kod in haklar else "plan",
        )
        for kod, acik in etkin.items()
    ]


async def _ozellik_durumlari(db: AsyncSession, tenant: Tenant) -> list[OzellikDurumDTO]:
    etkin = await entitlement_service.tenant_etkin_ozellikler(db, tenant)
    bayraklar = await entitlement_service.bayrak_haritasi_getir(db, tenant.id)
    return [
        OzellikDurumDTO(
            kod=kod,
            ad=OZELLIK_KATALOGU[kod].ad,
            acik=acik,
            deneysel=OZELLIK_KATALOGU[kod].deneysel,
            kaynak="bayrak" if kod in bayraklar else "plan",
        )
        for kod, acik in etkin.items()
    ]


async def tenant_detayi(db: AsyncSession, tenant: Tenant) -> TenantDetayDTO:
    ab = _son_abonelik(tenant)
    planlar = await plan_haritasi(db)
    plan = planlar.get(ab.plan_kodu) if ab is not None else None
    return TenantDetayDTO(
        id=tenant.id,
        slug=tenant.slug,
        ad=tenant.ad,
        aktif=tenant.aktif,
        plan_kodu=ab.plan_kodu if ab is not None else None,
        abonelik_durum=ab.durum if ab is not None else None,
        abonelik_baslangic=ab.baslangic_tarihi if ab is not None else None,
        abonelik_bitis=ab.bitis_tarihi if ab is not None else None,
        koltuk_limiti=plan.koltuk_limiti if plan is not None else None,
        koltuk_kullanilan=await koltuk_kullanilan_say(db, tenant.slug),
        moduller=await _modul_durumlari(db, tenant),
        ozellikler=await _ozellik_durumlari(db, tenant),
        olusturma_tarihi=tenant.olusturma_tarihi,
    )


# --- Tenant yaşam döngüsü (yazma) ---


async def tenant_provizyon(
    db: AsyncSession, yonetici: PlatformYonetici, govde: TenantProvizyonDTO
) -> Tenant:
    """Yeni tenant'ı uçtan uca provizyonlar (public kayıt + şema + migrate + tohum).

    Senkron beklenir: provizyon idempotenttir ve saniyeler sürer; 202'ye yükseltme
    yolu ADR-0019'da not edilmiştir.
    """
    if not slug_gecerli_mi(govde.slug):
        raise DogrulamaHatasi(
            "Geçersiz tenant slug",
            detaylar=[{"alan": "slug", "mesaj": "küçük harf/rakam/tire (DNS-label) olmalı"}],
        )
    if govde.plan_kodu not in PLAN_KATALOGU:
        raise DogrulamaHatasi(
            "Katalogda olmayan plan",
            detaylar=[{"alan": "plan_kodu", "mesaj": f"şunlardan biri: {sorted(PLAN_KATALOGU)}"}],
        )
    if await tenant_bul(db, govde.slug) is not None:
        raise CakismaHatasi("Bu slug ile tenant zaten var")

    tenant_id = await tenant_provizyonla(
        slug=govde.slug,
        ad=govde.ad,
        admin_eposta=govde.admin_eposta,
        admin_parola=govde.admin_parola,
        plan_kodu=govde.plan_kodu,
        db_url=db_url_al(),
    )
    await platform_denetim_yaz(
        db,
        eylem="provizyon",
        kaynak="tenant",
        kaynak_id=str(tenant_id),
        yonetici=yonetici,
        detay={"slug": govde.slug, "plan_kodu": govde.plan_kodu},
    )
    return await tenant_getir(db, tenant_id)


async def tenant_guncelle(
    db: AsyncSession, yonetici: PlatformYonetici, tenant_id: int, govde: TenantGuncelleDTO
) -> Tenant:
    """Tenant adını ve/veya planını değiştirir (plan değişimi ANINDA etkili — S16)."""
    tenant = await tenant_getir(db, tenant_id)
    detay: dict[str, str] = {}
    if govde.ad is not None:
        tenant.ad = govde.ad
        detay["ad"] = govde.ad
    if govde.plan_kodu is not None:
        if govde.plan_kodu not in PLAN_KATALOGU:
            raise DogrulamaHatasi(
                "Katalogda olmayan plan",
                detaylar=[
                    {"alan": "plan_kodu", "mesaj": f"şunlardan biri: {sorted(PLAN_KATALOGU)}"}
                ],
            )
        ab = _son_abonelik(tenant)
        if ab is None:
            raise CakismaHatasi("Tenant'ın abonelik kaydı yok")
        ab.plan_kodu = govde.plan_kodu
        detay["plan_kodu"] = govde.plan_kodu
    await platform_denetim_yaz(
        db,
        eylem="guncelle",
        kaynak="tenant",
        kaynak_id=str(tenant.id),
        yonetici=yonetici,
        detay=detay,
    )
    return tenant


async def tenant_aktiflik_ayarla(
    db: AsyncSession, yonetici: PlatformYonetici, tenant_id: int, aktif: bool
) -> Tenant:
    """Askıya alır / yeniden aktifleştirir — ``tenant_cozumle`` aktif olmayanı
    404'lediği için erişim bir sonraki istekte kesilir/açılır (önbellek yok)."""
    tenant = await tenant_getir(db, tenant_id)
    tenant.aktif = aktif
    await platform_denetim_yaz(
        db,
        eylem="aktiflestir" if aktif else "askiya_al",
        kaynak="tenant",
        kaynak_id=str(tenant.id),
        yonetici=yonetici,
        detay={"slug": tenant.slug},
    )
    return tenant


async def tenant_sil(
    db: AsyncSession, yonetici: PlatformYonetici, tenant_id: int, onay: str
) -> None:
    """Tenant'ı GERİ DÖNÜŞSÜZ siler: şema DROP CASCADE + public kayıtlar (FK CASCADE).

    ``onay`` slug ile birebir eşleşmek zorundadır (GitHub deseni) — panel bunun
    üstüne ad-yazarak-onayla modalı koyar. Denetim kaydı silmeden ÖNCE yazılır.
    """
    tenant = await tenant_getir(db, tenant_id)
    if onay != tenant.slug:
        raise DogrulamaHatasi(
            "Onay metni tenant slug'ı ile eşleşmiyor",
            detaylar=[{"alan": "onay", "mesaj": f"silmek için {tenant.slug!r} yazın"}],
        )
    await platform_denetim_yaz(
        db,
        eylem="sil",
        kaynak="tenant",
        kaynak_id=str(tenant.id),
        yonetici=yonetici,
        detay={"slug": tenant.slug, "ad": tenant.ad},
    )
    sema = sema_adi(tenant.slug)
    await db.execute(text(f'DROP SCHEMA IF EXISTS "{sema}" CASCADE'))
    await db.delete(tenant)
    await db.flush()


async def _veritabani_sondasi(db: AsyncSession) -> SondaDTO:
    try:
        await db.execute(text("SELECT 1"))
        return SondaDTO(durum="saglikli")
    except Exception as exc:  # noqa: BLE001 — sonda hatası panoyu düşürmez
        return SondaDTO(durum="hata", detay=str(exc)[:200])


async def _redis_sondasi() -> SondaDTO:
    try:
        await get_redis().ping()
        return SondaDTO(durum="saglikli")
    except Exception as exc:  # noqa: BLE001
        return SondaDTO(durum="hata", detay=str(exc)[:200])


async def _nesne_depo_sondasi() -> SondaDTO:
    try:
        depo = nesne_depo_al()
        await asyncio.to_thread(depo.var_mi, "platform/saglik-probu")
        return SondaDTO(durum="saglikli")
    except Exception as exc:  # noqa: BLE001
        return SondaDTO(durum="hata", detay=str(exc)[:200])


async def saglik_durumu(db: AsyncSession) -> PlatformSaglikDTO:
    """Servis sondaları + tenant sayıları — kısmi arıza panoyu düşürmez."""
    toplam = await db.scalar(select(func.count()).select_from(Tenant)) or 0
    aktif = (
        await db.scalar(select(func.count()).select_from(Tenant).where(Tenant.aktif.is_(True))) or 0
    )
    return PlatformSaglikDTO(
        surum=__version__,
        ortam=get_settings().app_env,
        veritabani=await _veritabani_sondasi(db),
        redis=await _redis_sondasi(),
        nesne_depo=await _nesne_depo_sondasi(),
        tenant_toplam=int(toplam),
        tenant_aktif=int(aktif),
        tenant_askida=int(toplam) - int(aktif),
    )
