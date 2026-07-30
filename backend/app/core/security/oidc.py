"""Kurumsal SSO — OpenID Connect Authorization Code + PKCE (S23 / ADR-0022).

Tasarım ilkeleri:

- **Tenant başına yapılandırma.** Ayarlar ``public.tenant.guvenlik_ayarlari["oidc"]``
  altında yaşar (parola politikası / zorunlu-2FA / IP listesiyle aynı yer). Giriş
  tenant şeması açılmadan önce gerçekleştiği için control-plane'de durması şarttır.
- **Claim adları sabit DEĞİL.** Azure AD ``preferred_username``, Google ``email``,
  Keycloak ``groups`` yerine ``realm_access.roles`` verebilir; hangi claim'in neyi
  taşıdığı ``claim_eslemesi`` ile tenant başına ayarlanır (ADR-0022 madde 4).
  İç içe claim yolu nokta ile yazılır: ``realm_access.roles``.
- **Saf çekirdek / ağ kenarı ayrımı.** URL kurma, PKCE, claim eşleme, alan adı ve
  grup→rol kuralları saf fonksiyonlardır (birim testli). Ağ erişimi ``OidcAgIstemcisi``
  protokolünün arkasındadır; testler ``SahteIdp`` enjekte eder (``NesneDepo`` deseni).
- **JWKS önbelleği + anahtar rotasyonu.** JWKS issuer başına TTL'li önbellektedir;
  bilinmeyen ``kid`` görülürse önbellek BİR KEZ zorla tazelenir (IdP anahtar
  rotasyonu kesinti üretmez), tazeleme sonrası da yoksa reddedilir.
- **Saat kayması toleransı.** ``exp``/``iat``/``nbf`` doğrulaması ``saat_kaymasi_sn``
  kadar esnetilir (varsayılan 120 sn) — IdP ile sunucu saati birebir tutmaz.
- **Debug modu (süreli).** ``debug_claim_log: true`` iken ham ID token claim'leri
  WARNING seviyesinde loglanır; ilk canlı Azure AD / Google Workspace denemesi kod
  değişikliği gerektirmeden teşhis edilebilsin diye vardır. Ham claim'ler **kişisel veri**
  (e-posta, ad, grup üyeliği) taşıdığı için mod **kendiliğinden söner**:
  ``debug_claim_log_bitis`` damgası geçince bayrak açık olsa da log yazılmaz.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlencode

import httpx
import jwt
from jwt import PyJWK

from app.core.exceptions import AppError, KimlikHatasi
from app.core.security.redis_istemci import get_redis

logger = logging.getLogger("app.oidc")

# Discovery + JWKS önbellek ömrü (sn). JWKS rotasyonu ayrıca kid-miss ile tetiklenir.
ONBELLEK_TTL_SN = 3600
# SSO akış durumu (state) Redis'te bu kadar yaşar — kullanıcının IdP'de geçireceği süre.
DURUM_TTL_SN = 600
_DURUM_ONEK = "sso:durum:"

VARSAYILAN_KAPSAM = "openid email profile"
VARSAYILAN_SAAT_KAYMASI_SN = 120


class OidcHatasi(AppError):
    """SSO akışında beklenen ama kurtarılamayan durum (yanlış yapılandırma, IdP reddi)."""

    durum_kodu = 400
    hata_kodu = "SSO_HATASI"


# --------------------------------------------------------------------------------------
# Yapılandırma (saf)
# --------------------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class ClaimEslemesi:
    """Hangi ID token claim'i neyi taşıyor — tenant başına ayarlanır.

    Değerler nokta ile iç içe yol olabilir (``realm_access.roles``).
    """

    eposta: str = "email"
    konu: str = "sub"
    ad: str = "name"
    gruplar: str = "groups"


@dataclass(frozen=True, slots=True)
class OidcAyari:
    """Bir tenant'ın çözülmüş, doğrulanmış OIDC yapılandırması."""

    issuer: str
    istemci_id: str
    istemci_sirri: str
    donus_url: str
    kapsam: str = VARSAYILAN_KAPSAM
    claim_eslemesi: ClaimEslemesi = field(default_factory=ClaimEslemesi)
    izinli_alan_adlari: tuple[str, ...] = ()
    jit_provizyon: bool = True
    varsayilan_roller: tuple[str, ...] = ()
    grup_rol_eslemesi: dict[str, str] = field(default_factory=dict)
    saat_kaymasi_sn: int = VARSAYILAN_SAAT_KAYMASI_SN
    debug_claim_log: bool = False
    # Debug logu kendiliğinden söner: bu an geçtiyse bayrak açık olsa da log yazılmaz.
    debug_claim_log_bitis: datetime | None = None


def ayar_coz(guvenlik_ayarlari: dict[str, Any] | None) -> OidcAyari | None:
    """``guvenlik_ayarlari["oidc"]`` → ``OidcAyari``; kapalı/eksikse ``None``.

    Zorunlu alanlardan biri eksikse ``None`` döner (yarım yapılandırma = kapalı):
    giriş ekranında SSO düğmesi çıkmaz, parola akışı çalışmaya devam eder.
    """
    if not isinstance(guvenlik_ayarlari, dict):
        return None
    ham = guvenlik_ayarlari.get("oidc")
    if not isinstance(ham, dict) or not ham.get("aktif", False):
        return None

    issuer = str(ham.get("issuer") or "").rstrip("/")
    istemci_id = str(ham.get("istemci_id") or "")
    istemci_sirri = str(ham.get("istemci_sirri") or "")
    donus_url = str(ham.get("donus_url") or "")
    if not (issuer and istemci_id and istemci_sirri and donus_url):
        return None

    ham_esleme = ham.get("claim_eslemesi")
    esleme = ClaimEslemesi()
    if isinstance(ham_esleme, dict):
        esleme = ClaimEslemesi(
            eposta=str(ham_esleme.get("eposta") or "email"),
            konu=str(ham_esleme.get("konu") or "sub"),
            ad=str(ham_esleme.get("ad") or "name"),
            gruplar=str(ham_esleme.get("gruplar") or "groups"),
        )

    grup_rol = ham.get("grup_rol_eslemesi")
    return OidcAyari(
        issuer=issuer,
        istemci_id=istemci_id,
        istemci_sirri=istemci_sirri,
        donus_url=donus_url,
        kapsam=str(ham.get("kapsam") or VARSAYILAN_KAPSAM),
        claim_eslemesi=esleme,
        izinli_alan_adlari=tuple(
            str(a).lower().lstrip("@") for a in ham.get("izinli_alan_adlari") or () if a
        ),
        jit_provizyon=bool(ham.get("jit_provizyon", True)),
        varsayilan_roller=tuple(str(r) for r in ham.get("varsayilan_roller") or () if r),
        grup_rol_eslemesi=(
            {str(k): str(v) for k, v in grup_rol.items()} if isinstance(grup_rol, dict) else {}
        ),
        saat_kaymasi_sn=int(ham.get("saat_kaymasi_sn") or VARSAYILAN_SAAT_KAYMASI_SN),
        debug_claim_log=bool(ham.get("debug_claim_log", False)),
        debug_claim_log_bitis=_zaman_coz(ham.get("debug_claim_log_bitis")),
    )


def _zaman_coz(deger: Any) -> datetime | None:
    """ISO-8601 metnini UTC ``datetime``e çevirir; bozuk/eksik değer ``None``."""
    if not deger:
        return None
    try:
        an = datetime.fromisoformat(str(deger))
    except ValueError:
        return None
    return an if an.tzinfo else an.replace(tzinfo=UTC)


def debug_aktif_mi(ayar: OidcAyari, *, simdi: datetime | None = None) -> bool:
    """Ham claim logu şu an yazılmalı mı (bayrak AÇIK **ve** süre dolmamış)?

    Süre damgası yoksa bayrak tek başına yetmez: bu, elle JSONB düzenleyip
    ``debug_claim_log: true`` bırakarak kalıcı PII loglaması açılmasını engeller.
    """
    if not ayar.debug_claim_log or ayar.debug_claim_log_bitis is None:
        return False
    return (simdi or datetime.now(UTC)) < ayar.debug_claim_log_bitis


# --------------------------------------------------------------------------------------
# PKCE + yetkilendirme URL'i (saf)
# --------------------------------------------------------------------------------------
def pkce_uret() -> tuple[str, str]:
    """(code_verifier, code_challenge) üretir — S256 yöntemi (RFC 7636)."""
    dogrulayici = secrets.token_urlsafe(64)[:128]
    ozet = hashlib.sha256(dogrulayici.encode("ascii")).digest()
    meydan = base64.urlsafe_b64encode(ozet).decode("ascii").rstrip("=")
    return dogrulayici, meydan


def yetkilendirme_url(
    yetkilendirme_ucu: str,
    ayar: OidcAyari,
    *,
    state: str,
    nonce: str,
    code_challenge: str,
) -> str:
    """IdP'ye yönlendirilecek tam yetkilendirme URL'ini kurar (saf)."""
    parametreler = {
        "response_type": "code",
        "client_id": ayar.istemci_id,
        "redirect_uri": ayar.donus_url,
        "scope": ayar.kapsam,
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    ayirac = "&" if "?" in yetkilendirme_ucu else "?"
    return f"{yetkilendirme_ucu}{ayirac}{urlencode(parametreler)}"


# --------------------------------------------------------------------------------------
# Claim eşleme (saf)
# --------------------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class EslenmisKimlik:
    """ID token claim'lerinden çıkarılmış, uygulamanın anladığı kimlik."""

    konu: str
    eposta: str
    ad_soyad: str
    gruplar: tuple[str, ...]


def claim_oku(claims: dict[str, Any], yol: str) -> Any:
    """Nokta ile ayrılmış claim yolunu okur (``realm_access.roles``); yoksa ``None``."""
    gecerli: Any = claims
    for parca in yol.split("."):
        if not isinstance(gecerli, dict) or parca not in gecerli:
            return None
        gecerli = gecerli[parca]
    return gecerli


def claim_esle(claims: dict[str, Any], esleme: ClaimEslemesi) -> EslenmisKimlik:
    """Ham claim sözlüğünü ``EslenmisKimlik``'e çevirir (saf).

    E-posta veya subject yoksa ``OidcHatasi`` — kimliksiz kullanıcı üretilemez.
    Gruplar tek string ise (bazı IdP'ler boşlukla ayırır) listeye çevrilir.
    """
    konu = claim_oku(claims, esleme.konu)
    eposta = claim_oku(claims, esleme.eposta)
    if not konu:
        raise OidcHatasi(f"ID token'da subject claim'i yok: {esleme.konu!r}")
    if not eposta or "@" not in str(eposta):
        raise OidcHatasi(f"ID token'da geçerli e-posta claim'i yok: {esleme.eposta!r}")

    ham_gruplar = claim_oku(claims, esleme.gruplar)
    if isinstance(ham_gruplar, str):
        gruplar = tuple(g for g in ham_gruplar.replace(",", " ").split() if g)
    elif isinstance(ham_gruplar, list):
        gruplar = tuple(str(g) for g in ham_gruplar if g)
    else:
        gruplar = ()

    ad = claim_oku(claims, esleme.ad)
    eposta_str = str(eposta).strip().lower()
    return EslenmisKimlik(
        konu=str(konu),
        eposta=eposta_str,
        ad_soyad=str(ad).strip() if ad else eposta_str.split("@")[0],
        gruplar=gruplar,
    )


def alan_adi_izinli_mi(eposta: str, izinli_alan_adlari: tuple[str, ...]) -> bool:
    """Boş liste = kısıt yok. Doluysa e-postanın alan adı listede olmalı (saf)."""
    if not izinli_alan_adlari:
        return True
    if "@" not in eposta:
        return False
    return eposta.rsplit("@", 1)[1].lower() in izinli_alan_adlari


def gruplardan_roller(
    gruplar: tuple[str, ...], grup_rol_eslemesi: dict[str, str], varsayilan_roller: tuple[str, ...]
) -> list[str]:
    """IdP gruplarını tenant rol adlarına çevirir; eşleşme yoksa varsayılanlar (saf).

    Eşleme büyük/küçük harf duyarsızdır (Azure AD grup adları tutarsız gelir).
    """
    kucuk_esleme = {k.lower(): v for k, v in grup_rol_eslemesi.items()}
    roller = {kucuk_esleme[g.lower()] for g in gruplar if g.lower() in kucuk_esleme}
    if roller:
        return sorted(roller)
    return sorted(set(varsayilan_roller))


# --------------------------------------------------------------------------------------
# Ağ kenarı — protokol + varsayılan httpx uygulaması + test ikizi
# --------------------------------------------------------------------------------------
class OidcAgIstemcisi(Protocol):
    """IdP ile HTTP konuşan yüzey — testte ``SahteIdp`` ile değiştirilir."""

    async def json_getir(self, url: str) -> dict[str, Any]:
        """GET → JSON (discovery belgesi, JWKS)."""
        ...

    async def token_degis(self, token_ucu: str, veri: dict[str, str]) -> dict[str, Any]:
        """POST form → JSON (authorization code → token)."""
        ...


class HttpxOidcIstemcisi:
    """Varsayılan (gerçek) istemci — httpx ile."""

    def __init__(self, zaman_asimi_sn: float = 10.0) -> None:
        self._zaman_asimi = zaman_asimi_sn

    async def json_getir(self, url: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._zaman_asimi) as istemci:
            cevap = await istemci.get(url)
        if cevap.status_code != 200:
            raise OidcHatasi(f"IdP isteği başarısız ({cevap.status_code}): {url}")
        veri: dict[str, Any] = cevap.json()
        return veri

    async def token_degis(self, token_ucu: str, veri: dict[str, str]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._zaman_asimi) as istemci:
            cevap = await istemci.post(
                token_ucu,
                data=veri,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if cevap.status_code != 200:
            # IdP hata gövdesi teşhis için kritiktir ama sırrı sızdırmaz (client_secret gitmez).
            raise OidcHatasi(f"Token değişimi başarısız ({cevap.status_code}): {cevap.text[:300]}")
        sonuc: dict[str, Any] = cevap.json()
        return sonuc


_istemci: OidcAgIstemcisi | None = None


def get_istemci() -> OidcAgIstemcisi:
    """Süreç-genelinde tekil ağ istemcisi (tembel)."""
    global _istemci
    if _istemci is None:
        _istemci = HttpxOidcIstemcisi()
    return _istemci


def istemci_ayarla(istemci: OidcAgIstemcisi | None) -> None:
    """İstemciyi override eder (testlerde ``SahteIdp``); ``None`` sıfırlar."""
    global _istemci
    _istemci = istemci


# --------------------------------------------------------------------------------------
# Discovery + JWKS önbelleği (rotasyon farkında)
# --------------------------------------------------------------------------------------
# issuer -> (bitis_zamani, belge)
_discovery_onbellek: dict[str, tuple[float, dict[str, Any]]] = {}
# issuer -> (bitis_zamani, jwks)
_jwks_onbellek: dict[str, tuple[float, dict[str, Any]]] = {}


def onbellekleri_temizle() -> None:
    """Discovery/JWKS önbelleklerini boşaltır (testler + yapılandırma değişimi)."""
    _discovery_onbellek.clear()
    _jwks_onbellek.clear()


async def discovery_al(issuer: str, *, zorla_yenile: bool = False) -> dict[str, Any]:
    """``/.well-known/openid-configuration`` belgesini TTL'li önbellekle getirir."""
    simdi = time.monotonic()
    onbellekli = _discovery_onbellek.get(issuer)
    if onbellekli and not zorla_yenile and onbellekli[0] > simdi:
        return onbellekli[1]
    belge = await get_istemci().json_getir(f"{issuer}/.well-known/openid-configuration")
    _discovery_onbellek[issuer] = (simdi + ONBELLEK_TTL_SN, belge)
    return belge


async def jwks_al(issuer: str, jwks_ucu: str, *, zorla_yenile: bool = False) -> dict[str, Any]:
    """JWKS'i TTL'li önbellekle getirir; ``zorla_yenile`` rotasyon için önbelleği atlar."""
    simdi = time.monotonic()
    onbellekli = _jwks_onbellek.get(issuer)
    if onbellekli and not zorla_yenile and onbellekli[0] > simdi:
        return onbellekli[1]
    jwks = await get_istemci().json_getir(jwks_ucu)
    _jwks_onbellek[issuer] = (simdi + ONBELLEK_TTL_SN, jwks)
    return jwks


def _anahtar_bul(jwks: dict[str, Any], kid: str | None) -> PyJWK | None:
    """JWKS içinden ``kid``'e uyan anahtarı çıkarır; ``kid`` yoksa tek anahtarı kullanır."""
    anahtarlar = jwks.get("keys")
    if not isinstance(anahtarlar, list) or not anahtarlar:
        return None
    if kid is None:
        return PyJWK(anahtarlar[0]) if len(anahtarlar) == 1 else None
    for ham in anahtarlar:
        if isinstance(ham, dict) and ham.get("kid") == kid:
            return PyJWK(ham)
    return None


async def id_token_dogrula(id_token: str, ayar: OidcAyari, *, nonce: str) -> dict[str, Any]:
    """ID token'ı imza + iss + aud + exp/iat + nonce yönünden doğrular → claim'ler.

    Anahtar rotasyonu: token'ın ``kid``'i önbellekteki JWKS'te yoksa JWKS **bir kez**
    zorla tazelenir. Böylece IdP anahtar döndürdüğünde ilk istek de başarılı olur.
    """
    try:
        basliklar = jwt.get_unverified_header(id_token)
    except jwt.PyJWTError as exc:
        raise KimlikHatasi(f"ID token okunamadı: {exc}") from exc
    kid = basliklar.get("kid")

    discovery = await discovery_al(ayar.issuer)
    jwks_ucu = str(discovery.get("jwks_uri") or "")
    if not jwks_ucu:
        raise OidcHatasi("IdP discovery belgesinde jwks_uri yok")

    jwks = await jwks_al(ayar.issuer, jwks_ucu)
    anahtar = _anahtar_bul(jwks, kid)
    if anahtar is None:
        # Rotasyon senaryosu: önbellek eski, IdP yeni anahtara geçmiş → bir kez tazele.
        jwks = await jwks_al(ayar.issuer, jwks_ucu, zorla_yenile=True)
        anahtar = _anahtar_bul(jwks, kid)
    if anahtar is None:
        raise KimlikHatasi(f"ID token imza anahtarı bulunamadı (kid={kid!r})")

    algoritma = str(basliklar.get("alg") or "RS256")
    if algoritma.lower() == "none":
        raise KimlikHatasi("İmzasız ID token kabul edilmez")

    try:
        claims: dict[str, Any] = jwt.decode(
            id_token,
            key=anahtar.key,
            algorithms=[algoritma],
            audience=ayar.istemci_id,
            issuer=ayar.issuer,
            leeway=ayar.saat_kaymasi_sn,
            options={"require": ["exp", "iat", "iss", "aud"]},
        )
    except jwt.PyJWTError as exc:
        raise KimlikHatasi(f"ID token doğrulanamadı: {exc}") from exc

    if debug_aktif_mi(ayar):
        # Canlı IdP teşhisi için kasıtlı: kod değişikliği olmadan claim'leri görebilmek.
        # Süre dolduğunda kendiliğinden susar (PII log akışına sızmasın).
        logger.warning("OIDC ham claim'ler (debug_claim_log açık): %s", claims)

    if nonce and claims.get("nonce") != nonce:
        raise KimlikHatasi("ID token nonce eşleşmedi (replay koruması)")
    return claims


async def kod_degis(ayar: OidcAyari, *, kod: str, code_verifier: str) -> dict[str, Any]:
    """Authorization code'u token uçlarında değiştirir → token yanıtı (id_token dahil)."""
    discovery = await discovery_al(ayar.issuer)
    token_ucu = str(discovery.get("token_endpoint") or "")
    if not token_ucu:
        raise OidcHatasi("IdP discovery belgesinde token_endpoint yok")
    return await get_istemci().token_degis(
        token_ucu,
        {
            "grant_type": "authorization_code",
            "code": kod,
            "redirect_uri": ayar.donus_url,
            "client_id": ayar.istemci_id,
            "client_secret": ayar.istemci_sirri,
            "code_verifier": code_verifier,
        },
    )


# --------------------------------------------------------------------------------------
# Akış durumu (Redis; tek kullanımlık)
# --------------------------------------------------------------------------------------
async def durum_yaz(state: str, *, tenant_slug: str, nonce: str, code_verifier: str) -> None:
    """SSO akış durumunu TTL'li saklar (state → nonce + PKCE doğrulayıcı + tenant)."""
    await get_redis().hset(
        _DURUM_ONEK + state,
        mapping={"tenant": tenant_slug, "nonce": nonce, "verifier": code_verifier},
    )
    await get_redis().expire(_DURUM_ONEK + state, DURUM_TTL_SN)


async def durum_tuket(state: str) -> dict[str, str] | None:
    """Durumu okur ve SİLER (tek kullanım — CSRF/replay koruması); yoksa ``None``."""
    anahtar = _DURUM_ONEK + state
    veri = await get_redis().hgetall(anahtar)
    await get_redis().delete(anahtar)
    if not veri:
        return None
    return {str(k): str(v) for k, v in veri.items()}
