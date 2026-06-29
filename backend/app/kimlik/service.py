"""Kimlik iş kuralları: giriş, token yenileme (rotasyon), çıkış, parola değiştirme.

Tüm sorgular aktif istek oturumunda çalışır; ``search_path`` ``tenant_cozumle`` tarafından
ilgili tenant şemasına ayarlanmıştır. Refresh token rotasyonludur: yenilemede eski ``jti``
Redis iptal listesine eklenir, yeni bir çift üretilir.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.exceptions import DogrulamaHatasi, KimlikHatasi, YetkiHatasi
from app.core.security import jwt as jwtmod
from app.core.security.parola import parola_dogrula, parola_ozetle
from app.core.security.token_deposu import refresh_iptal_et, refresh_iptalli_mi
from app.kimlik.models import Kullanici

# Kullanıcı bulunamadığında zamanlama farkını azaltmak için sahte özet (enumeration koruması).
_SAHTE_OZET = parola_ozetle("zamanlama-sabiti-degil-gercek-parola")


async def _kullanici_bul(db: AsyncSession, eposta: str) -> Kullanici | None:
    sonuc = await db.execute(select(Kullanici).where(Kullanici.eposta == eposta))
    return sonuc.scalar_one_or_none()


def _kalan_omur_sn(exp: int) -> int:
    return max(exp - int(datetime.now(UTC).timestamp()), 1)


async def giris_yap(
    db: AsyncSession, tenant: Tenant, *, eposta: str, parola: str
) -> tuple[str, str]:
    """E-posta/parola doğrular; (access, refresh) döner. Hatada ``KimlikHatasi`` (401)."""
    kullanici = await _kullanici_bul(db, eposta)
    if kullanici is None or not kullanici.aktif:
        parola_dogrula(_SAHTE_OZET, parola)  # zamanlamayı dengele
        raise KimlikHatasi("E-posta veya parola hatalı")
    if not parola_dogrula(kullanici.parola_ozet, parola):
        raise KimlikHatasi("E-posta veya parola hatalı")

    kullanici.son_giris_tarihi = datetime.now(UTC)
    await denetim_yaz(db, eylem="giris", kaynak="kimlik", kullanici=kullanici)

    access, _ = jwtmod.access_uret(kullanici.id, tenant.slug, kullanici.eposta)
    refresh, _ = jwtmod.refresh_uret(kullanici.id, tenant.slug)
    return access, refresh


async def token_yenile(db: AsyncSession, tenant: Tenant, *, refresh_token: str) -> tuple[str, str]:
    """Refresh token'ı rotasyonla yeniler; eski ``jti`` iptal edilir."""
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

    # Rotasyon: eski refresh'i iptal et, yeni çift üret.
    await refresh_iptal_et(icerik.jti, _kalan_omur_sn(icerik.exp))
    access, _ = jwtmod.access_uret(kullanici.id, tenant.slug, kullanici.eposta)
    yeni_refresh, _ = jwtmod.refresh_uret(kullanici.id, tenant.slug)
    return access, yeni_refresh


async def cikis(*, refresh_token: str) -> None:
    """Refresh token'ı iptal listesine ekler (idempotent; geçersiz token sessizce yutulur)."""
    try:
        icerik = jwtmod.coz(refresh_token, "refresh")
    except jwtmod.TokenGecersiz:
        return
    await refresh_iptal_et(icerik.jti, _kalan_omur_sn(icerik.exp))


async def parola_degistir(
    db: AsyncSession, kullanici: Kullanici, *, eski_parola: str, yeni_parola: str
) -> None:
    """Mevcut parolayı doğrulayıp yenisini ayarlar."""
    if not parola_dogrula(kullanici.parola_ozet, eski_parola):
        raise DogrulamaHatasi(
            "Eski parola hatalı",
            detaylar=[{"alan": "eski_parola", "mesaj": "Mevcut parola doğrulanamadı"}],
        )
    kullanici.parola_ozet = parola_ozetle(yeni_parola)
    await denetim_yaz(db, eylem="parola_degistir", kaynak="kimlik", kullanici=kullanici)
