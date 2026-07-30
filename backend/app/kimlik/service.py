"""Kimlik iş kuralları: giriş (2FA'lı), token yenileme (rotasyon), çıkış, parola,
oturum/cihaz yönetimi, TOTP 2FA kurulum/doğrulama (S23 / ADR-0022).

Tüm sorgular aktif istek oturumunda çalışır; ``search_path`` ``tenant_cozumle`` tarafından
ilgili tenant şemasına ayarlanmıştır. Refresh token rotasyonludur: yenilemede eski ``jti``
Redis iptal listesine eklenir, yeni bir çift üretilir. Her refresh ``jti``'si için
``oturumlar`` tablosuna kayıt düşülür (cihaz listesi + adli iz); Redis anlık zorlama,
DB listeleme kaynağıdır.

2FA akışı: parola doğru + ``iki_asama_aktif`` → tam token YERİNE 5 dk ömürlü ``2fa``
tipli geçici token döner; ``iki_asama_dogrula`` TOTP kodu veya kurtarma koduyla tam
çifti verir. Tenant ``iki_asama_zorunlu`` ise 2FA'sız kullanıcı ``kurulum`` işaretli
geçici tokenla kurulum uçlarına yönlendirilir.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane import entitlement_service
from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.config import get_settings
from app.core.exceptions import (
    CakismaHatasi,
    DogrulamaHatasi,
    KaynakBulunamadi,
    KimlikHatasi,
    YetkiHatasi,
)
from app.core.security import jwt as jwtmod
from app.core.security import totp
from app.core.security.parola import parola_dogrula, parola_ozetle
from app.core.security.politika import guvenlik_ayari, parola_kurali_ihlalleri
from app.core.security.token_deposu import refresh_iptal_et, refresh_iptalli_mi
from app.kimlik.models import Kullanici, KurtarmaKodu, Oturum

# Kullanıcı bulunamadığında zamanlama farkını azaltmak için sahte özet (enumeration koruması).
_SAHTE_OZET = parola_ozetle("zamanlama-sabiti-degil-gercek-parola")


@dataclass(frozen=True, slots=True)
class GirisSonucu:
    """Giriş çıktısı: ya tam token çifti ya da 2FA ara adımı."""

    access: str = ""
    refresh: str = ""
    iki_asama_gerekli: bool = False
    iki_asama_kurulum_gerekli: bool = False
    gecici_token: str = ""


async def _kullanici_bul(db: AsyncSession, eposta: str) -> Kullanici | None:
    sonuc = await db.execute(select(Kullanici).where(Kullanici.eposta == eposta))
    return sonuc.scalar_one_or_none()


def _kalan_omur_sn(exp: int) -> int:
    return max(exp - int(datetime.now(UTC).timestamp()), 1)


def _kod_ozetle(kod: str) -> str:
    return hashlib.sha256(kod.strip().upper().encode()).hexdigest()


async def _oturum_yaz(
    db: AsyncSession,
    *,
    kullanici_id: int,
    jti: str,
    ip: str | None,
    istemci: str,
) -> None:
    """Refresh ``jti``'si için oturum kaydı düşer (cihaz listesi + adli iz)."""
    ayar = get_settings()
    db.add(
        Oturum(
            kullanici_id=kullanici_id,
            jti=jti,
            ip_adresi=ip,
            istemci=istemci[:300],
            son_kullanim=datetime.now(UTC),
            bitis=datetime.now(UTC) + timedelta(days=ayar.refresh_token_gun),
        )
    )
    await db.flush()


async def tam_giris(
    db: AsyncSession,
    tenant: Tenant,
    kullanici: Kullanici,
    *,
    ip: str | None,
    istemci: str,
    eylem: str = "giris",
) -> GirisSonucu:
    """Tam token çifti üretir + oturum satırı yazar (parola ve SSO akışlarının ortak sonu).

    ``eylem`` denetim izine yazılır: parola girişi ``giris``, SSO girişi ``sso_giris``.
    """
    kullanici.son_giris_tarihi = datetime.now(UTC)
    await denetim_yaz(db, eylem=eylem, kaynak="kimlik", kullanici=kullanici)
    access, _ = jwtmod.access_uret(kullanici.id, tenant.slug, kullanici.eposta)
    refresh, refresh_jti = jwtmod.refresh_uret(kullanici.id, tenant.slug)
    await _oturum_yaz(db, kullanici_id=kullanici.id, jti=refresh_jti, ip=ip, istemci=istemci)
    return GirisSonucu(access=access, refresh=refresh)


async def giris_yap(
    db: AsyncSession,
    tenant: Tenant,
    *,
    eposta: str,
    parola: str,
    ip: str | None = None,
    istemci: str = "",
) -> GirisSonucu:
    """E-posta/parola doğrular. 2FA aktifse geçici token, değilse tam çift döner."""
    kullanici = await _kullanici_bul(db, eposta)
    if kullanici is None or not kullanici.aktif:
        parola_dogrula(_SAHTE_OZET, parola)  # zamanlamayı dengele
        raise KimlikHatasi("E-posta veya parola hatalı")
    if not parola_dogrula(kullanici.parola_ozet, parola):
        raise KimlikHatasi("E-posta veya parola hatalı")

    if kullanici.iki_asama_aktif:
        gecici, _ = jwtmod.iki_asama_uret(kullanici.id, tenant.slug)
        return GirisSonucu(iki_asama_gerekli=True, gecici_token=gecici)

    # Tenant 2FA'yı zorunlu kılmışsa kurulumsuz kullanıcı önce kurulumu tamamlar.
    if guvenlik_ayari(tenant.guvenlik_ayarlari, "iki_asama_zorunlu", False):
        gecici, _ = jwtmod.iki_asama_uret(kullanici.id, tenant.slug, kurulum=True)
        return GirisSonucu(iki_asama_kurulum_gerekli=True, gecici_token=gecici)

    return await tam_giris(db, tenant, kullanici, ip=ip, istemci=istemci)


async def _gecici_tokendan_kullanici(
    db: AsyncSession, tenant: Tenant, gecici_token: str
) -> tuple[Kullanici, jwtmod.TokenIcerigi]:
    try:
        icerik = jwtmod.coz(gecici_token, "2fa")
    except jwtmod.TokenGecersiz as exc:
        raise KimlikHatasi("Geçersiz veya süresi dolmuş doğrulama adımı") from exc
    if icerik.tenant_slug != tenant.slug:
        raise YetkiHatasi("Token tenant'ı ile istek tenant'ı uyuşmuyor")
    if await refresh_iptalli_mi(icerik.jti):  # tek kullanım (replay koruması)
        raise KimlikHatasi("Doğrulama adımı zaten kullanılmış")
    kullanici = (
        await db.execute(select(Kullanici).where(Kullanici.id == icerik.kullanici_id))
    ).scalar_one_or_none()
    if kullanici is None or not kullanici.aktif:
        raise KimlikHatasi("Kullanıcı bulunamadı veya aktif değil")
    return kullanici, icerik


async def _kurtarma_kodu_dene(db: AsyncSession, kullanici: Kullanici, kod: str) -> bool:
    """Kurtarma kodunu dener; eşleşen kullanılmamış kod varsa tüketir (bir kez)."""
    ozet = _kod_ozetle(kod)
    kayit = (
        await db.execute(
            select(KurtarmaKodu).where(
                KurtarmaKodu.kullanici_id == kullanici.id,
                KurtarmaKodu.kod_ozet == ozet,
                KurtarmaKodu.kullanildi.is_(False),
            )
        )
    ).scalar_one_or_none()
    if kayit is None:
        return False
    kayit.kullanildi = True
    await denetim_yaz(db, eylem="kurtarma_kodu", kaynak="kimlik", kullanici=kullanici)
    return True


async def iki_asama_dogrula(
    db: AsyncSession,
    tenant: Tenant,
    *,
    gecici_token: str,
    kod: str,
    ip: str | None = None,
    istemci: str = "",
) -> GirisSonucu:
    """2FA ikinci adımı: TOTP kodu veya kurtarma kodu → tam token çifti."""
    kullanici, icerik = await _gecici_tokendan_kullanici(db, tenant, gecici_token)
    if not kullanici.iki_asama_aktif or not kullanici.totp_sirri:
        raise KimlikHatasi("Bu hesapta iki aşamalı doğrulama etkin değil")

    gecerli = totp.kod_dogrula(kullanici.totp_sirri, kod) or await _kurtarma_kodu_dene(
        db, kullanici, kod
    )
    if not gecerli:
        raise KimlikHatasi("Doğrulama kodu hatalı")

    await refresh_iptal_et(icerik.jti, _kalan_omur_sn(icerik.exp))  # tek kullanım
    return await tam_giris(db, tenant, kullanici, ip=ip, istemci=istemci)


async def token_yenile(db: AsyncSession, tenant: Tenant, *, refresh_token: str) -> tuple[str, str]:
    """Refresh token'ı rotasyonla yeniler; eski ``jti`` iptal edilir, oturum devralınır."""
    try:
        icerik = jwtmod.coz(refresh_token, "refresh")
    except jwtmod.TokenGecersiz as exc:
        raise KimlikHatasi("Geçersiz veya süresi dolmuş refresh token") from exc

    if icerik.tenant_slug != tenant.slug:
        raise YetkiHatasi("Token tenant'ı ile istek tenant'ı uyuşmuyor")
    if await refresh_iptalli_mi(icerik.jti):
        raise KimlikHatasi("Refresh token iptal edilmiş")

    kullanici = (
        await db.execute(select(Kullanici).where(Kullanici.id == icerik.kullanici_id))
    ).scalar_one_or_none()
    if kullanici is None or not kullanici.aktif:
        raise KimlikHatasi("Kullanıcı bulunamadı veya aktif değil")

    # Rotasyon: eski refresh'i iptal et, yeni çift üret; oturum satırı yeni jti'yi devralır.
    await refresh_iptal_et(icerik.jti, _kalan_omur_sn(icerik.exp))
    access, _ = jwtmod.access_uret(kullanici.id, tenant.slug, kullanici.eposta)
    yeni_refresh, yeni_jti = jwtmod.refresh_uret(kullanici.id, tenant.slug)

    eski_oturum = (
        await db.execute(select(Oturum).where(Oturum.jti == icerik.jti))
    ).scalar_one_or_none()
    ayar = get_settings()
    if eski_oturum is not None:
        eski_oturum.jti = yeni_jti
        eski_oturum.son_kullanim = datetime.now(UTC)
        eski_oturum.bitis = datetime.now(UTC) + timedelta(days=ayar.refresh_token_gun)
        await db.flush()
    else:
        # S23 öncesi oturumlar için geriye dönük kayıt (kayıtsız refresh de listelensin).
        await _oturum_yaz(db, kullanici_id=kullanici.id, jti=yeni_jti, ip=None, istemci="")
    return access, yeni_refresh


async def cikis(db: AsyncSession, *, refresh_token: str) -> None:
    """Refresh token'ı iptal listesine ekler (idempotent; geçersiz token sessizce yutulur)."""
    try:
        icerik = jwtmod.coz(refresh_token, "refresh")
    except jwtmod.TokenGecersiz:
        return
    await refresh_iptal_et(icerik.jti, _kalan_omur_sn(icerik.exp))
    oturum = (await db.execute(select(Oturum).where(Oturum.jti == icerik.jti))).scalar_one_or_none()
    if oturum is not None:
        oturum.iptal = True
        await db.flush()


async def parola_degistir(
    db: AsyncSession,
    kullanici: Kullanici,
    *,
    eski_parola: str,
    yeni_parola: str,
    tenant: Tenant | None = None,
) -> None:
    """Mevcut parolayı doğrulayıp yenisini ayarlar (tenant parola politikası uygulanır)."""
    if not parola_dogrula(kullanici.parola_ozet, eski_parola):
        raise DogrulamaHatasi(
            "Eski parola hatalı",
            detaylar=[{"alan": "eski_parola", "mesaj": "Mevcut parola doğrulanamadı"}],
        )
    parola_politikasi_uygula(tenant, yeni_parola)
    kullanici.parola_ozet = parola_ozetle(yeni_parola)
    await denetim_yaz(db, eylem="parola_degistir", kaynak="kimlik", kullanici=kullanici)


async def koltuk_kontrol(db: AsyncSession, tenant: Tenant) -> None:
    """Koltuk (seat) limiti — S16/ADR-0018: eşzamanlı yazmalar ``public.tenant`` satırı
    kilidiyle serileştirilir; aktif kullanıcı sayısı limiti aşamaz (pasifler sayılmaz).

    Kullanıcı oluşturan HER yol buradan geçer: yönetici ucu ve SSO JIT provizyonu (S23) —
    aksi hâlde SSO limiti sessizce delerdi.
    """
    await db.execute(select(Tenant.id).where(Tenant.id == tenant.id).with_for_update())
    koltuk = await entitlement_service.koltuk_limiti_getir(db, tenant)
    if koltuk is None:
        return
    aktif_sayi = (
        await db.scalar(
            select(func.count()).select_from(Kullanici).where(Kullanici.aktif.is_(True))
        )
        or 0
    )
    if aktif_sayi >= koltuk:
        raise CakismaHatasi(
            f"Koltuk limiti doldu ({aktif_sayi}/{koltuk}) — plan yükseltin veya "
            "bir kullanıcıyı pasifleştirin",
            hata_kodu="KOLTUK_LIMITI",
        )


def parola_politikasi_uygula(tenant: Tenant | None, parola: str) -> None:
    """Tenant parola politikası ihlallerini 422'ye çevirir (politika yoksa geçer)."""
    politika = guvenlik_ayari(tenant.guvenlik_ayarlari, "parola") if tenant else None
    ihlaller = parola_kurali_ihlalleri(parola, politika)
    if ihlaller:
        raise DogrulamaHatasi(
            "Parola politikaya uymuyor",
            detaylar=[{"alan": "parola", "mesaj": m} for m in ihlaller],
        )


# --- 2FA kurulum / kapatma ---
async def iki_asama_kur(db: AsyncSession, kullanici: Kullanici, tenant: Tenant) -> tuple[str, str]:
    """Yeni TOTP sırrı üretir ve (sır, otpauth URI) döner — etkinleştirme kodla yapılır."""
    if kullanici.iki_asama_aktif:
        raise DogrulamaHatasi(
            "İki aşamalı doğrulama zaten etkin",
            detaylar=[{"alan": "iki_asama", "mesaj": "Önce kapatın"}],
        )
    sir = totp.sir_uret()
    kullanici.totp_sirri = sir  # aktif değil; doğrulanana dek giriş etkilenmez
    await db.flush()
    return sir, totp.otpauth_uri(sir, eposta=kullanici.eposta, tenant_slug=tenant.slug)


async def iki_asama_etkinlestir(db: AsyncSession, kullanici: Kullanici, *, kod: str) -> list[str]:
    """Kurulum kodunu doğrular, 2FA'yı etkinleştirir; kurtarma kodlarını BİR KEZ döner."""
    if kullanici.iki_asama_aktif:
        raise DogrulamaHatasi(
            "İki aşamalı doğrulama zaten etkin",
            detaylar=[{"alan": "iki_asama", "mesaj": "Önce kapatın"}],
        )
    if not kullanici.totp_sirri:
        raise DogrulamaHatasi(
            "Önce kurulum başlatılmalı",
            detaylar=[{"alan": "kod", "mesaj": "2fa-kur çağrılmadı"}],
        )
    if not totp.kod_dogrula(kullanici.totp_sirri, kod):
        raise DogrulamaHatasi(
            "Doğrulama kodu hatalı",
            detaylar=[{"alan": "kod", "mesaj": "Authenticator kodu eşleşmedi"}],
        )
    kullanici.iki_asama_aktif = True

    # Eski kurtarma kodlarını geçersiz kıl, yenilerini üret (yalnız özet saklanır).
    eskiler = (
        (await db.execute(select(KurtarmaKodu).where(KurtarmaKodu.kullanici_id == kullanici.id)))
        .scalars()
        .all()
    )
    for e in eskiler:
        await db.delete(e)
    kodlar = totp.kurtarma_kodlari_uret()
    for k in kodlar:
        db.add(KurtarmaKodu(kullanici_id=kullanici.id, kod_ozet=_kod_ozetle(k)))
    await db.flush()
    await denetim_yaz(db, eylem="2fa_etkinlestir", kaynak="kimlik", kullanici=kullanici)
    return kodlar


async def iki_asama_kapat(db: AsyncSession, kullanici: Kullanici, *, parola: str, kod: str) -> None:
    """2FA'yı kapatır — parola VE geçerli kod (ya da kurtarma kodu) ister."""
    if not kullanici.iki_asama_aktif or not kullanici.totp_sirri:
        raise DogrulamaHatasi(
            "İki aşamalı doğrulama etkin değil",
            detaylar=[{"alan": "iki_asama", "mesaj": "Kapatılacak kurulum yok"}],
        )
    if not parola_dogrula(kullanici.parola_ozet, parola):
        raise DogrulamaHatasi(
            "Parola hatalı", detaylar=[{"alan": "parola", "mesaj": "Doğrulanamadı"}]
        )
    if not totp.kod_dogrula(kullanici.totp_sirri, kod) and not await _kurtarma_kodu_dene(
        db, kullanici, kod
    ):
        raise DogrulamaHatasi(
            "Doğrulama kodu hatalı", detaylar=[{"alan": "kod", "mesaj": "Eşleşmedi"}]
        )
    kullanici.iki_asama_aktif = False
    kullanici.totp_sirri = None
    kodlar = (
        (await db.execute(select(KurtarmaKodu).where(KurtarmaKodu.kullanici_id == kullanici.id)))
        .scalars()
        .all()
    )
    for k in kodlar:
        await db.delete(k)
    await db.flush()
    await denetim_yaz(db, eylem="2fa_kapat", kaynak="kimlik", kullanici=kullanici)


# --- Oturum / cihaz yönetimi ---
async def oturumlar_listele(db: AsyncSession, kullanici: Kullanici) -> list[Oturum]:
    """Kullanıcının aktif (iptal edilmemiş, süresi geçmemiş) oturumları — yeniden eskiye."""
    return list(
        (
            await db.execute(
                select(Oturum)
                .where(
                    Oturum.kullanici_id == kullanici.id,
                    Oturum.iptal.is_(False),
                    Oturum.bitis > datetime.now(UTC),
                )
                .order_by(Oturum.son_kullanim.desc().nulls_last())
            )
        )
        .scalars()
        .all()
    )


async def oturum_sonlandir(db: AsyncSession, kullanici: Kullanici, oturum_id: int) -> None:
    """Kendi oturumunu uzaktan sonlandırır: Redis iptali + DB işareti (403/404 korumalı)."""
    oturum = (await db.execute(select(Oturum).where(Oturum.id == oturum_id))).scalar_one_or_none()
    # Başkasının oturumu da görünmez kalır (tenant-rbac-conventions: 404).
    if oturum is None or oturum.kullanici_id != kullanici.id:
        raise KaynakBulunamadi("Oturum bulunamadı")
    kalan = max(int((oturum.bitis - datetime.now(UTC)).total_seconds()), 1)
    await refresh_iptal_et(oturum.jti, kalan)
    oturum.iptal = True
    await db.flush()
    await denetim_yaz(
        db,
        eylem="oturum_sonlandir",
        kaynak="kimlik",
        kaynak_id=str(oturum_id),
        kullanici=kullanici,
    )
