"""Platform kimlik iş kuralları: giriş, token yenileme (rotasyon), çıkış.

``kimlik/service.py``'nin control-plane aynasıdır: aynı argon2id doğrulaması,
aynı rotasyonlu refresh + Redis iptal listesi — ama ``platform_access`` /
``platform_refresh`` token tipleriyle ve ``public.platform_yonetici`` üzerinde.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import PlatformYonetici
from app.core.exceptions import KimlikHatasi
from app.core.security import jwt as jwtmod
from app.core.security.parola import parola_dogrula, parola_ozetle
from app.core.security.token_deposu import refresh_iptal_et, refresh_iptalli_mi
from app.platform.denetim import platform_denetim_yaz

# Enumeration koruması: yönetici yokken de parola doğrulama zamanı harcanır.
_SAHTE_OZET = parola_ozetle("zamanlama-sabiti-degil-gercek-parola")


async def _yonetici_bul(db: AsyncSession, eposta: str) -> PlatformYonetici | None:
    sonuc = await db.execute(select(PlatformYonetici).where(PlatformYonetici.eposta == eposta))
    return sonuc.scalar_one_or_none()


def _kalan_omur_sn(exp: int) -> int:
    return max(exp - int(datetime.now(UTC).timestamp()), 1)


async def platform_giris(db: AsyncSession, *, eposta: str, parola: str) -> tuple[str, str]:
    """E-posta/parola doğrular; (access, refresh) döner. Hatada ``KimlikHatasi`` (401)."""
    yonetici = await _yonetici_bul(db, eposta)
    if yonetici is None or not yonetici.aktif:
        parola_dogrula(_SAHTE_OZET, parola)  # zamanlamayı dengele
        raise KimlikHatasi("E-posta veya parola hatalı")
    if not parola_dogrula(yonetici.parola_ozet, parola):
        raise KimlikHatasi("E-posta veya parola hatalı")

    yonetici.son_giris_tarihi = datetime.now(UTC)
    await platform_denetim_yaz(db, eylem="giris", kaynak="platform_kimlik", yonetici=yonetici)

    access, _ = jwtmod.platform_access_uret(yonetici.id, yonetici.eposta)
    refresh, _ = jwtmod.platform_refresh_uret(yonetici.id)
    return access, refresh


async def platform_token_yenile(db: AsyncSession, *, refresh_token: str) -> tuple[str, str]:
    """Platform refresh token'ını rotasyonla yeniler; eski ``jti`` iptal edilir."""
    try:
        icerik = jwtmod.coz(refresh_token, "platform_refresh")
    except jwtmod.TokenGecersiz as exc:
        raise KimlikHatasi("Geçersiz veya süresi dolmuş refresh token") from exc
    if await refresh_iptalli_mi(icerik.jti):
        raise KimlikHatasi("Refresh token iptal edilmiş")

    yonetici = (
        await db.execute(select(PlatformYonetici).where(PlatformYonetici.id == icerik.kullanici_id))
    ).scalar_one_or_none()
    if yonetici is None or not yonetici.aktif:
        raise KimlikHatasi("Platform yöneticisi bulunamadı veya aktif değil")

    await refresh_iptal_et(icerik.jti, _kalan_omur_sn(icerik.exp))
    access, _ = jwtmod.platform_access_uret(yonetici.id, yonetici.eposta)
    yeni_refresh, _ = jwtmod.platform_refresh_uret(yonetici.id)
    return access, yeni_refresh


async def platform_cikis(*, refresh_token: str) -> None:
    """Refresh token'ı iptal listesine ekler (idempotent; geçersiz token sessizce yutulur)."""
    try:
        icerik = jwtmod.coz(refresh_token, "platform_refresh")
    except jwtmod.TokenGecersiz:
        return
    await refresh_iptal_et(icerik.jti, _kalan_omur_sn(icerik.exp))


async def platform_yonetici_olustur(
    db: AsyncSession, *, eposta: str, parola: str, ad_soyad: str = ""
) -> PlatformYonetici:
    """Platform yöneticisini açar/eşitler (eposta üzerinden idempotent upsert).

    CLI (``scripts/platform_yonetici_olustur.py``) ve test fixture'larının ortak
    çekirdeği: varsa parolası/adı güncellenir ve yeniden aktifleştirilir.
    """
    yonetici = await _yonetici_bul(db, eposta)
    if yonetici is None:
        yonetici = PlatformYonetici(eposta=eposta, parola_ozet=parola_ozetle(parola))
        db.add(yonetici)
    else:
        yonetici.parola_ozet = parola_ozetle(parola)
        yonetici.aktif = True
    if ad_soyad:
        yonetici.ad_soyad = ad_soyad
    await db.flush()
    return yonetici
