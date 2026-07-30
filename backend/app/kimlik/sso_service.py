"""Kurumsal SSO akışı — OIDC Authorization Code + PKCE iş kuralları (S23 / ADR-0022).

``core/security/oidc.py`` protokolü/saf çekirdeği taşır; burası **tenant + kullanıcı**
kararlarını verir:

- akış başlatma (state/nonce/PKCE üret → Redis'e yaz → IdP URL'i),
- akış tamamlama (kod değişimi → id_token doğrulama → claim eşleme → alan adı kontrolü),
- **JIT provizyon** (kullanıcı yoksa oluştur — koltuk limiti parola akışıyla AYNI
  ``koltuk_kontrol`` üzerinden zorlanır; SSO limiti delemez),
- **grup → rol senkronu** (yalnız ``grup_rol_eslemesi`` yapılandırılmışsa; IdP
  otoritedir. Eşleme sonuç vermezse mevcut roller KORUNUR — yanlış/eksik grup
  yapılandırması kullanıcıyı yetkisiz bırakmasın),
- 2FA kesişimi: kullanıcı kendi TOTP'sini açmışsa SSO'dan sonra da ikinci adım
  istenir. Tenant'ın ``iki_asama_zorunlu`` ayarı SSO girişinde **karşılanmış sayılır**
  (ikinci faktörü IdP yürütür; ADR-0022).

SSO ile açılan hesaplara kullanılamaz bir parola özeti yazılır: parola akışıyla
giriş yapılamaz (hesap yalnız IdP üzerinden erişilir).
"""

from __future__ import annotations

import logging
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.exceptions import KaynakBulunamadi, KimlikHatasi, YetkiHatasi
from app.core.security import jwt as jwtmod
from app.core.security import oidc
from app.core.security.parola import parola_ozetle
from app.kimlik import service
from app.kimlik.models import Kullanici, Rol

logger = logging.getLogger("app.sso")


def ayar_getir(tenant: Tenant) -> oidc.OidcAyari:
    """Tenant'ın OIDC ayarını çözer; kapalıysa 404 (yüzey görünmez kalır)."""
    ayar = oidc.ayar_coz(tenant.guvenlik_ayarlari)
    if ayar is None:
        raise KaynakBulunamadi("Bu tenant için SSO yapılandırılmamış")
    return ayar


def sso_acik_mi(tenant: Tenant) -> bool:
    """Giriş ekranının SSO düğmesini göstermesi için (kimlik gerektirmeyen sorgu)."""
    return oidc.ayar_coz(tenant.guvenlik_ayarlari) is not None


async def sso_baslat(tenant: Tenant) -> str:
    """State/nonce/PKCE üretir, Redis'e yazar ve IdP yetkilendirme URL'ini döner."""
    ayar = ayar_getir(tenant)
    discovery = await oidc.discovery_al(ayar.issuer)
    yetkilendirme_ucu = str(discovery.get("authorization_endpoint") or "")
    if not yetkilendirme_ucu:
        raise oidc.OidcHatasi("IdP discovery belgesinde authorization_endpoint yok")

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    dogrulayici, meydan = oidc.pkce_uret()
    await oidc.durum_yaz(state, tenant_slug=tenant.slug, nonce=nonce, code_verifier=dogrulayici)
    return oidc.yetkilendirme_url(
        yetkilendirme_ucu, ayar, state=state, nonce=nonce, code_challenge=meydan
    )


async def _roller_esle(db: AsyncSession, rol_adlari: list[str]) -> list[Rol]:
    """Rol adlarını tenant kataloğuyla eşler; **tanımsız adlar sessizce atlanır**.

    Yönetici ucundan farklı (orada 422): IdP tarafında duran eski bir grup adı yüzünden
    giriş komple reddedilmemeli. Atlananlar teşhis için loglanır.
    """
    if not rol_adlari:
        return []
    bulunan = list((await db.execute(select(Rol).where(Rol.ad.in_(rol_adlari)))).scalars().all())
    eksik = set(rol_adlari) - {r.ad for r in bulunan}
    if eksik:
        logger.warning("SSO grup→rol eşlemesinde tanımsız rol(ler) atlandı: %s", sorted(eksik))
    return bulunan


async def _jit_olustur(
    db: AsyncSession,
    tenant: Tenant,
    ayar: oidc.OidcAyari,
    kimlik: oidc.EslenmisKimlik,
) -> Kullanici:
    """IdP'de doğrulanmış ama yerelde olmayan kullanıcıyı oluşturur (koltuk limitli)."""
    if not ayar.jit_provizyon:
        raise YetkiHatasi(
            "Bu hesap sistemde tanımlı değil ve otomatik oluşturma kapalı",
            hata_kodu="SSO_KULLANICI_YOK",
        )
    await service.koltuk_kontrol(db, tenant)
    roller = await _roller_esle(
        db, oidc.gruplardan_roller(kimlik.gruplar, ayar.grup_rol_eslemesi, ayar.varsayilan_roller)
    )
    yeni = Kullanici(
        eposta=kimlik.eposta,
        # Kullanılamaz parola: yerel parola akışıyla giriş imkânsız (yalnız IdP).
        parola_ozet=parola_ozetle(secrets.token_urlsafe(48)),
        ad_soyad=kimlik.ad_soyad,
        aktif=True,
        roller=roller,
    )
    db.add(yeni)
    await db.flush()
    await denetim_yaz(
        db,
        eylem="sso_provizyon",
        kaynak="kullanici",
        kaynak_id=str(yeni.id),
        kullanici=yeni,
        detay={"eposta": yeni.eposta, "roller": sorted(r.ad for r in roller)},
    )
    return yeni


async def _rolleri_senkronla(
    db: AsyncSession, kullanici: Kullanici, ayar: oidc.OidcAyari, kimlik: oidc.EslenmisKimlik
) -> None:
    """Grup eşlemesi yapılandırılmışsa rolleri IdP'ye göre günceller (IdP otoritedir).

    ``varsayilan_roller`` KASITLI olarak devre dışı: o ayar **provizyon anı** içindir
    (yeni hesaba başlangıç rolü). Senkronda geri düşülseydi, IdP'de eşleşmeyen bir grup
    gören mevcut kullanıcı her girişte varsayılana **düşürülürdü** (sessiz yetki kaybı).
    """
    if not ayar.grup_rol_eslemesi:
        return
    hedef_adlar = oidc.gruplardan_roller(kimlik.gruplar, ayar.grup_rol_eslemesi, ())
    roller = await _roller_esle(db, hedef_adlar)
    # Eşleme hiçbir geçerli rol vermediyse dokunma: yetkisiz bırakmaktansa mevcut hâli koru.
    if not roller:
        return
    mevcut = {r.ad for r in kullanici.roller}
    yeni = {r.ad for r in roller}
    if mevcut == yeni:
        return
    kullanici.roller = roller
    await db.flush()
    await denetim_yaz(
        db,
        eylem="sso_rol_senkron",
        kaynak="kullanici",
        kaynak_id=str(kullanici.id),
        kullanici=kullanici,
        detay={"onceki": sorted(mevcut), "yeni": sorted(yeni)},
    )


async def sso_tamamla(
    db: AsyncSession,
    tenant: Tenant,
    *,
    kod: str,
    state: str,
    ip: str | None = None,
    istemci: str = "",
) -> service.GirisSonucu:
    """IdP dönüşünü tamamlar: kod → token → doğrulama → (JIT) kullanıcı → oturum."""
    ayar = ayar_getir(tenant)

    durum = await oidc.durum_tuket(state)  # tek kullanım (CSRF + replay koruması)
    if durum is None:
        raise KimlikHatasi("Geçersiz veya süresi dolmuş SSO oturumu")
    if durum.get("tenant") != tenant.slug:
        # Başka tenant'ta başlatılan akış burada tamamlanamaz (çapraz-tenant koruması).
        raise YetkiHatasi("SSO oturumu bu tenant'a ait değil")

    token_yaniti = await oidc.kod_degis(ayar, kod=kod, code_verifier=durum["verifier"])
    id_token = token_yaniti.get("id_token")
    if not id_token:
        raise oidc.OidcHatasi("IdP yanıtında id_token yok")

    claims = await oidc.id_token_dogrula(str(id_token), ayar, nonce=durum["nonce"])
    kimlik = oidc.claim_esle(claims, ayar.claim_eslemesi)

    if not oidc.alan_adi_izinli_mi(kimlik.eposta, ayar.izinli_alan_adlari):
        raise YetkiHatasi(
            "Bu e-posta alan adı ile SSO girişine izin verilmiyor",
            hata_kodu="SSO_ALAN_ADI",
        )

    kullanici = (
        await db.execute(select(Kullanici).where(Kullanici.eposta == kimlik.eposta))
    ).scalar_one_or_none()
    if kullanici is None:
        kullanici = await _jit_olustur(db, tenant, ayar, kimlik)
    else:
        if not kullanici.aktif:
            raise KimlikHatasi("Kullanıcı aktif değil")
        await _rolleri_senkronla(db, kullanici, ayar, kimlik)

    # Kullanıcı kendi TOTP'sini açtıysa SSO sonrası da ikinci adım istenir.
    if kullanici.iki_asama_aktif:
        gecici, _ = jwtmod.iki_asama_uret(kullanici.id, tenant.slug)
        return service.GirisSonucu(iki_asama_gerekli=True, gecici_token=gecici)

    # Tenant zorunlu-2FA ayarı SSO'da karşılanmış sayılır (ikinci faktör IdP'de).
    return await service.tam_giris(db, tenant, kullanici, ip=ip, istemci=istemci, eylem="sso_giris")
