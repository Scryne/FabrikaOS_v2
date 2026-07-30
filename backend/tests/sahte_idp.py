"""Sahte OIDC sağlayıcı (test ikizi) — gerçek IdP olmadan SSO akışını uçtan uca sınar.

``NesneDepo``/``BellekNesneDepo`` desenini izler: üretimde ``HttpxOidcIstemcisi``,
testte bu sınıf ``oidc.istemci_ayarla`` ile enjekte edilir.

Gerçek bir IdP gibi davranır:
- RSA anahtar çifti üretir, **gerçek JWKS** yayınlar ve id_token'ı RS256 ile imzalar,
- discovery belgesi sunar (authorization/token/jwks uçları),
- yetkilendirme URL'inden ``state``/``nonce``/``code_challenge`` okur, kod üretir,
- token değişiminde **PKCE doğrulaması** yapar (S256) ve nonce'u id_token'a koyar,
- ``anahtar_dondur()`` ile anahtar rotasyonunu (yeni ``kid``) simüle eder,
- ``json_getir`` çağrı sayacı tutar → JWKS önbelleğinin çalıştığı ispatlanabilir.
"""

from __future__ import annotations

import base64
import hashlib
import time
import uuid
from typing import Any
from urllib.parse import parse_qs, urlparse

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = "https://idp.test/realms/fabrikaos"


def _b64u(sayi: int) -> str:
    ham = sayi.to_bytes((sayi.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(ham).decode("ascii").rstrip("=")


class SahteIdp:
    """Bellek içi OIDC sağlayıcı; ``OidcAgIstemcisi`` protokolünü karşılar."""

    def __init__(self, issuer: str = ISSUER, istemci_id: str = "fabrikaos-test") -> None:
        self.issuer = issuer
        self.istemci_id = istemci_id
        self.json_cagri_sayisi = 0
        self.jwks_cagri_sayisi = 0
        self.pkce_reddi = 0
        self.son_token_istegi: dict[str, str] = {}
        self._kodlar: dict[str, dict[str, str]] = {}
        # Sonraki id_token'a enjekte edilecek claim override'ları (test senaryoları).
        self.ek_claimler: dict[str, Any] = {}
        self.claim_sil: set[str] = set()
        self._anahtar_uret()

    # --- anahtar yönetimi ---
    def _anahtar_uret(self) -> None:
        self._ozel = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.kid = uuid.uuid4().hex[:8]

    def anahtar_dondur(self) -> str:
        """Yeni ``kid``'li anahtar çiftine geçer (IdP rotasyonu); yeni kid'i döner."""
        self._anahtar_uret()
        return self.kid

    @property
    def jwks(self) -> dict[str, Any]:
        pub = self._ozel.public_key().public_numbers()
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "alg": "RS256",
                    "kid": self.kid,
                    "n": _b64u(pub.n),
                    "e": _b64u(pub.e),
                }
            ]
        }

    @property
    def discovery(self) -> dict[str, Any]:
        return {
            "issuer": self.issuer,
            "authorization_endpoint": f"{self.issuer}/protocol/openid-connect/auth",
            "token_endpoint": f"{self.issuer}/protocol/openid-connect/token",
            "jwks_uri": f"{self.issuer}/protocol/openid-connect/certs",
        }

    # --- OidcAgIstemcisi protokolü ---
    async def json_getir(self, url: str) -> dict[str, Any]:
        self.json_cagri_sayisi += 1
        if url.endswith("/.well-known/openid-configuration"):
            return self.discovery
        if url == self.discovery["jwks_uri"]:
            self.jwks_cagri_sayisi += 1
            return self.jwks
        raise AssertionError(f"SahteIdp bilinmeyen URL: {url}")

    async def token_degis(self, token_ucu: str, veri: dict[str, str]) -> dict[str, Any]:
        assert token_ucu == self.discovery["token_endpoint"]
        self.son_token_istegi = dict(veri)  # testler gönderilen alanları denetleyebilsin
        kayit = self._kodlar.pop(veri.get("code", ""), None)
        if kayit is None:
            return {"error": "invalid_grant", "error_description": "bilinmeyen kod"}

        # PKCE doğrulaması (S256) — gerçek IdP davranışı: uyuşmazlıkta OAuth hata
        # gövdesi döner (istisna fırlatmaz), böylece istemcinin hatayı nasıl ele
        # aldığı da sınanabilir.
        dogrulayici = veri.get("code_verifier", "")
        ozet = hashlib.sha256(dogrulayici.encode("ascii")).digest()
        meydan = base64.urlsafe_b64encode(ozet).decode("ascii").rstrip("=")
        if meydan != kayit["challenge"]:
            self.pkce_reddi += 1
            return {"error": "invalid_grant", "error_description": "PKCE dogrulamasi basarisiz"}

        return {
            "access_token": "sahte-access",
            "token_type": "Bearer",
            "id_token": self.id_token_uret(nonce=kayit["nonce"]),
        }

    # --- tarayıcı adımının yerine geçen yardımcı ---
    def yetkilendir(self, yetkilendirme_url: str) -> tuple[str, str]:
        """Yetkilendirme URL'ini "ziyaret eder" → (authorization code, state)."""
        sorgu = parse_qs(urlparse(yetkilendirme_url).query)
        assert sorgu["response_type"] == ["code"]
        assert sorgu["code_challenge_method"] == ["S256"]
        kod = uuid.uuid4().hex
        self._kodlar[kod] = {
            "nonce": sorgu["nonce"][0],
            "challenge": sorgu["code_challenge"][0],
        }
        return kod, sorgu["state"][0]

    # --- token üretimi (senaryo kancalarıyla) ---
    def id_token_uret(
        self,
        *,
        nonce: str,
        eposta: str = "sso.kullanici@firma.test",
        konu: str = "idp-konu-1",
        ad: str = "SSO Kullanıcı",
        gruplar: list[str] | None = None,
        iat_kaymasi_sn: int = 0,
        omur_sn: int = 300,
        audience: str | None = None,
        issuer: str | None = None,
        imza_kid: str | None = None,
    ) -> str:
        simdi = int(time.time()) + iat_kaymasi_sn
        claims: dict[str, Any] = {
            "iss": issuer or self.issuer,
            "aud": audience or self.istemci_id,
            "sub": konu,
            "email": eposta,
            "name": ad,
            "groups": gruplar if gruplar is not None else [],
            "nonce": nonce,
            "iat": simdi,
            "exp": simdi + omur_sn,
        }
        claims.update(self.ek_claimler)
        for anahtar in self.claim_sil:
            claims.pop(anahtar, None)
        return jwt.encode(
            claims,
            self._ozel,
            algorithm="RS256",
            headers={"kid": imza_kid or self.kid},
        )
