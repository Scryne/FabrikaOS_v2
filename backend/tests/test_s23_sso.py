"""S23 kurumsal SSO (OIDC) testleri — saf çekirdek + sahte IdP ile uçtan uca akış.

Kapsam (ADR-0022 kabul kriterleri):
- saf birim: ayar çözme, claim eşleme (iç içe yol dahil), alan adı, grup→rol, PKCE, URL;
- akış: başlat → IdP → tamamla → JIT kullanıcı + oturum;
- red senaryoları: yanlış nonce, süresi geçmiş token, yanlış audience/issuer, imzasız
  token, izinsiz alan adı, çapraz-tenant state, state tekrar kullanımı (replay);
- saat kayması toleransı; JWKS önbelleği + **anahtar rotasyonu**;
- JIT kapalıyken red, grup→rol senkronu, koltuk limiti, 2FA kesişimi, debug claim logu.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.security import oidc
from tests.conftest import ALFA
from tests.sahte_idp import SahteIdp
from tests.test_s16_entitlement import _giris

# asyncio_mode = "auto" (pyproject) → async testler işaretsiz çalışır; modül düzeyi
# pytestmark saf birim testlerini yanlışlıkla asyncio'ya işaretlediği için kullanılmaz.

KIMLIK = "/api/v1/kimlik"


# --------------------------------------------------------------------------------------
# Saf birim testleri (DB/ağ yok)
# --------------------------------------------------------------------------------------
def _tam_ayar(**ek: Any) -> dict[str, Any]:
    temel = {
        "aktif": True,
        "issuer": "https://idp.test/realms/x",
        "istemci_id": "fos",
        "istemci_sirri": "gizli",
        "donus_url": "https://app.test/sso/donus",
    }
    temel.update(ek)
    return {"oidc": temel}


def test_ayar_coz_eksik_veya_kapali_yapilandirma_none_dondurur() -> None:
    assert oidc.ayar_coz(None) is None
    assert oidc.ayar_coz({}) is None
    assert oidc.ayar_coz(_tam_ayar(aktif=False)) is None
    # Yarım yapılandırma = kapalı (parola akışı çalışmaya devam etsin).
    assert oidc.ayar_coz(_tam_ayar(istemci_sirri="")) is None
    assert oidc.ayar_coz(_tam_ayar(donus_url="")) is None


def test_ayar_coz_varsayilanlar_ve_ozel_claim_eslemesi() -> None:
    ayar = oidc.ayar_coz(_tam_ayar())
    assert ayar is not None
    assert ayar.kapsam == oidc.VARSAYILAN_KAPSAM
    assert ayar.saat_kaymasi_sn == oidc.VARSAYILAN_SAAT_KAYMASI_SN
    assert ayar.claim_eslemesi.eposta == "email"
    assert ayar.jit_provizyon is True
    # issuer sondaki eğik çizgi normalize edilir (discovery URL'i bozulmasın).
    assert oidc.ayar_coz(_tam_ayar(issuer="https://idp.test/x/")).issuer == "https://idp.test/x"  # type: ignore[union-attr]

    ozel = oidc.ayar_coz(
        _tam_ayar(
            claim_eslemesi={
                "eposta": "preferred_username",
                "gruplar": "realm_access.roles",
                "konu": "oid",
            },
            izinli_alan_adlari=["@Firma.test"],
            saat_kaymasi_sn=30,
        )
    )
    assert ozel is not None
    assert ozel.claim_eslemesi.eposta == "preferred_username"
    assert ozel.claim_eslemesi.gruplar == "realm_access.roles"
    assert ozel.claim_eslemesi.ad == "name"  # verilmeyen alan varsayılanda kalır
    assert ozel.izinli_alan_adlari == ("firma.test",)  # normalize: küçük harf, @ atılır
    assert ozel.saat_kaymasi_sn == 30


def test_claim_esle_ic_ice_yol_ve_bicimler() -> None:
    esleme = oidc.ClaimEslemesi(
        eposta="preferred_username", konu="oid", gruplar="realm_access.roles"
    )
    kimlik = oidc.claim_esle(
        {
            "oid": "abc",
            "preferred_username": "Ali@Firma.TEST",
            "name": "Ali Veli",
            "realm_access": {"roles": ["depo", "kalite"]},
        },
        esleme,
    )
    assert kimlik.konu == "abc"
    assert kimlik.eposta == "ali@firma.test"  # normalize
    assert kimlik.ad_soyad == "Ali Veli"
    assert kimlik.gruplar == ("depo", "kalite")


def test_claim_esle_string_gruplar_ve_ad_yoksa_epostadan_turer() -> None:
    kimlik = oidc.claim_esle(
        {"sub": "s", "email": "op@firma.test", "groups": "depo kalite,isg"},
        oidc.ClaimEslemesi(),
    )
    assert set(kimlik.gruplar) == {"depo", "kalite", "isg"}
    assert kimlik.ad_soyad == "op"


def test_claim_esle_eksik_kimlik_claimi_reddedilir() -> None:
    with pytest.raises(oidc.OidcHatasi):
        oidc.claim_esle({"email": "a@b.test"}, oidc.ClaimEslemesi())
    with pytest.raises(oidc.OidcHatasi):
        oidc.claim_esle({"sub": "s"}, oidc.ClaimEslemesi())
    with pytest.raises(oidc.OidcHatasi):
        oidc.claim_esle({"sub": "s", "email": "eposta-degil"}, oidc.ClaimEslemesi())


def test_alan_adi_kurali() -> None:
    assert oidc.alan_adi_izinli_mi("a@firma.test", ()) is True  # kısıt yok
    assert oidc.alan_adi_izinli_mi("a@firma.test", ("firma.test",)) is True
    assert oidc.alan_adi_izinli_mi("a@baska.test", ("firma.test",)) is False


def test_gruplardan_roller_buyuk_kucuk_duyarsiz_ve_varsayilana_duser() -> None:
    esleme = {"Fabrika-Admin": "admin", "depocular": "depo"}
    assert oidc.gruplardan_roller(("FABRIKA-ADMIN",), esleme, ()) == ["admin"]
    assert oidc.gruplardan_roller(("depocular", "Fabrika-Admin"), esleme, ()) == ["admin", "depo"]
    # Eşleşme yoksa varsayılan roller devreye girer.
    assert oidc.gruplardan_roller(("bilinmeyen",), esleme, ("izleyici",)) == ["izleyici"]


def test_pkce_ve_yetkilendirme_url() -> None:
    dogrulayici, meydan = oidc.pkce_uret()
    beklenen = (
        base64.urlsafe_b64encode(hashlib.sha256(dogrulayici.encode("ascii")).digest())
        .decode("ascii")
        .rstrip("=")
    )
    assert meydan == beklenen
    assert "=" not in meydan  # padding'siz base64url (RFC 7636)

    ayar = oidc.ayar_coz(_tam_ayar())
    assert ayar is not None
    url = oidc.yetkilendirme_url(
        "https://idp.test/auth", ayar, state="st", nonce="nn", code_challenge=meydan
    )
    sorgu = parse_qs(urlparse(url).query)
    assert sorgu["client_id"] == ["fos"]
    assert sorgu["redirect_uri"] == ["https://app.test/sso/donus"]
    assert sorgu["code_challenge_method"] == ["S256"]
    assert sorgu["state"] == ["st"] and sorgu["nonce"] == ["nn"]


# --------------------------------------------------------------------------------------
# Akış testleri (sahte IdP + kurulu tenant)
# --------------------------------------------------------------------------------------
async def _guvenlik_ayarla(engine: AsyncEngine, slug: str, ayarlar: dict[str, Any] | None) -> None:
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as db:
        await db.execute(
            text("UPDATE public.tenant SET guvenlik_ayarlari = CAST(:a AS jsonb) WHERE slug = :s"),
            {"a": "null" if ayarlar is None else json.dumps(ayarlar), "s": slug},
        )
        await db.commit()


def _oidc_ayari(idp: SahteIdp, **ek: Any) -> dict[str, Any]:
    temel: dict[str, Any] = {
        "aktif": True,
        "issuer": idp.issuer,
        "istemci_id": idp.istemci_id,
        "istemci_sirri": "gizli-sir",
        "donus_url": "http://localhost:5173/sso/donus",
        "varsayilan_roller": ["izleyici"],
    }
    temel.update(ek)
    return {"oidc": temel}


@pytest_asyncio.fixture
async def idp(test_engine: AsyncEngine) -> AsyncIterator[SahteIdp]:
    """Sahte IdP'yi enjekte eder; test sonunda ayarları ve önbellekleri temizler."""
    sahte = SahteIdp()
    oidc.istemci_ayarla(sahte)
    oidc.onbellekleri_temizle()
    try:
        yield sahte
    finally:
        oidc.istemci_ayarla(None)
        oidc.onbellekleri_temizle()
        await _guvenlik_ayarla(test_engine, "alfa", None)
        await _guvenlik_ayarla(test_engine, "beta", None)


async def _sso_baslat(istemci: AsyncClient, slug: str = "alfa") -> str:
    r = await istemci.post(f"{KIMLIK}/sso/baslat", headers={"X-Tenant": slug})
    assert r.status_code == 200, r.text
    return str(r.json()["data"]["yetkilendirme_url"])


async def _sso_tamamla(istemci: AsyncClient, kod: str, state: str, slug: str = "alfa") -> Any:
    return await istemci.post(
        f"{KIMLIK}/sso/tamamla",
        json={"kod": kod, "state": state},
        headers={"X-Tenant": slug},
    )


async def _akis(istemci: AsyncClient, idp: SahteIdp, slug: str = "alfa") -> Any:
    url = await _sso_baslat(istemci, slug)
    kod, state = idp.yetkilendir(url)
    return await _sso_tamamla(istemci, kod, state, slug)


async def test_sso_durum_kapali_ve_baslat_404(
    test_db: str, kurulu_istemci: AsyncClient, idp: SahteIdp, test_engine: AsyncEngine
) -> None:
    await _guvenlik_ayarla(test_engine, "alfa", None)
    r = await kurulu_istemci.get(f"{KIMLIK}/sso/durum", headers={"X-Tenant": "alfa"})
    assert r.status_code == 200 and r.json()["data"]["aktif"] is False
    # Yapılandırılmamış tenant'ta SSO yüzeyi görünmez kalır (404).
    r = await kurulu_istemci.post(f"{KIMLIK}/sso/baslat", headers={"X-Tenant": "alfa"})
    assert r.status_code == 404


async def test_sso_mutlu_yol_jit_provizyon_ve_oturum(
    test_db: str, kurulu_istemci: AsyncClient, idp: SahteIdp, test_engine: AsyncEngine
) -> None:
    eposta = f"sso-{uuid.uuid4().hex[:8]}@firma.test"
    await _guvenlik_ayarla(test_engine, "alfa", _oidc_ayari(idp))
    idp.ek_claimler = {"email": eposta}

    r = await kurulu_istemci.get(f"{KIMLIK}/sso/durum", headers={"X-Tenant": "alfa"})
    assert r.json()["data"]["aktif"] is True

    cevap = await _akis(kurulu_istemci, idp)
    assert cevap.status_code == 200, cevap.text
    veri = cevap.json()["data"]
    assert veri["access_token"] and veri["refresh_token"]
    assert veri["iki_asama_gerekli"] is False

    # Üretilen token gerçek oturum açar; kullanıcı JIT provizyonlanmış ve rolü atanmış.
    ben = await kurulu_istemci.get(
        f"{KIMLIK}/ben",
        headers={"X-Tenant": "alfa", "Authorization": f"Bearer {veri['access_token']}"},
    )
    assert ben.status_code == 200
    assert ben.json()["data"]["eposta"] == eposta
    assert ben.json()["data"]["roller"] == ["izleyici"]

    # Oturum kaydı (cihaz listesi) yazılmış olmalı.
    oturumlar = await kurulu_istemci.get(
        f"{KIMLIK}/oturumlar",
        headers={"X-Tenant": "alfa", "Authorization": f"Bearer {veri['access_token']}"},
    )
    assert oturumlar.status_code == 200 and len(oturumlar.json()["data"]) >= 1


async def test_sso_state_tek_kullanimlik_ve_capraz_tenant_reddi(
    test_db: str, kurulu_istemci: AsyncClient, idp: SahteIdp, test_engine: AsyncEngine
) -> None:
    await _guvenlik_ayarla(test_engine, "alfa", _oidc_ayari(idp))
    await _guvenlik_ayarla(test_engine, "beta", _oidc_ayari(idp))
    idp.ek_claimler = {"email": f"sso-{uuid.uuid4().hex[:8]}@firma.test"}

    url = await _sso_baslat(kurulu_istemci, "alfa")
    kod, state = idp.yetkilendir(url)

    # Alfa'da başlatılan akış beta'da tamamlanamaz (çapraz-tenant koruması).
    capraz = await _sso_tamamla(kurulu_istemci, kod, state, "beta")
    assert capraz.status_code == 403

    # State tek kullanımlıktır: çapraz denemede tüketildiği için tekrar kullanılamaz.
    tekrar = await _sso_tamamla(kurulu_istemci, kod, state, "alfa")
    assert tekrar.status_code == 401


async def test_sso_state_replay_ikinci_kullanimda_reddedilir(
    test_db: str, kurulu_istemci: AsyncClient, idp: SahteIdp, test_engine: AsyncEngine
) -> None:
    await _guvenlik_ayarla(test_engine, "alfa", _oidc_ayari(idp))
    idp.ek_claimler = {"email": f"sso-{uuid.uuid4().hex[:8]}@firma.test"}

    url = await _sso_baslat(kurulu_istemci, "alfa")
    kod, state = idp.yetkilendir(url)
    ilk = await _sso_tamamla(kurulu_istemci, kod, state)
    assert ilk.status_code == 200
    ikinci = await _sso_tamamla(kurulu_istemci, kod, state)
    assert ikinci.status_code == 401


async def test_sso_yanlis_nonce_reddedilir(
    test_db: str, kurulu_istemci: AsyncClient, idp: SahteIdp, test_engine: AsyncEngine
) -> None:
    await _guvenlik_ayarla(test_engine, "alfa", _oidc_ayari(idp))
    idp.ek_claimler = {"nonce": "saldirganin-nonce-u"}
    cevap = await _akis(kurulu_istemci, idp)
    assert cevap.status_code == 401
    assert "nonce" in cevap.json()["message"].lower()


async def test_sso_suresi_gecmis_token_reddedilir(
    test_db: str, kurulu_istemci: AsyncClient, idp: SahteIdp, test_engine: AsyncEngine
) -> None:
    await _guvenlik_ayarla(test_engine, "alfa", _oidc_ayari(idp, saat_kaymasi_sn=10))
    # Token 10.000 sn önce üretilmiş ve 9.940 sn önce dolmuş → 10 sn toleransın dışında.
    simdi = int(time.time())
    idp.ek_claimler = {"iat": simdi - 10_000, "exp": simdi - 9_940}
    cevap = await _akis(kurulu_istemci, idp)
    assert cevap.status_code == 401


async def test_sso_saat_kaymasi_toleransi_kabul_eder(
    test_db: str, kurulu_istemci: AsyncClient, idp: SahteIdp, test_engine: AsyncEngine
) -> None:
    """IdP saati 60 sn ileri; tolerans 120 sn → giriş başarılı olmalı."""
    await _guvenlik_ayarla(test_engine, "alfa", _oidc_ayari(idp, saat_kaymasi_sn=120))
    simdi = int(time.time())
    idp.ek_claimler = {
        "email": f"sso-{uuid.uuid4().hex[:8]}@firma.test",
        "iat": simdi + 60,
        "exp": simdi + 360,
    }
    cevap = await _akis(kurulu_istemci, idp)
    assert cevap.status_code == 200, cevap.text


async def test_sso_yanlis_audience_ve_issuer_reddedilir(
    test_db: str, kurulu_istemci: AsyncClient, idp: SahteIdp, test_engine: AsyncEngine
) -> None:
    await _guvenlik_ayarla(test_engine, "alfa", _oidc_ayari(idp))
    idp.ek_claimler = {"aud": "baska-istemci"}
    assert (await _akis(kurulu_istemci, idp)).status_code == 401

    idp.ek_claimler = {"iss": "https://sahte-idp.test"}
    assert (await _akis(kurulu_istemci, idp)).status_code == 401


async def test_sso_izinsiz_alan_adi_reddedilir(
    test_db: str, kurulu_istemci: AsyncClient, idp: SahteIdp, test_engine: AsyncEngine
) -> None:
    await _guvenlik_ayarla(test_engine, "alfa", _oidc_ayari(idp, izinli_alan_adlari=["firma.test"]))
    idp.ek_claimler = {"email": "disaridan@baska.test"}
    cevap = await _akis(kurulu_istemci, idp)
    assert cevap.status_code == 403
    assert cevap.json()["hata_kodu"] == "SSO_ALAN_ADI"


async def test_sso_jwks_onbellegi_ve_anahtar_rotasyonu(
    test_db: str, kurulu_istemci: AsyncClient, idp: SahteIdp, test_engine: AsyncEngine
) -> None:
    """JWKS önbelleklenir; IdP anahtar döndürünce önbellek bir kez tazelenip giriş sürer."""
    await _guvenlik_ayarla(test_engine, "alfa", _oidc_ayari(idp))
    idp.ek_claimler = {"email": f"sso-{uuid.uuid4().hex[:8]}@firma.test"}

    assert (await _akis(kurulu_istemci, idp)).status_code == 200
    ilk_jwks_cagrisi = idp.jwks_cagri_sayisi
    assert ilk_jwks_cagrisi == 1

    # İkinci giriş: JWKS önbellekten gelir, yeni ağ çağrısı olmaz.
    assert (await _akis(kurulu_istemci, idp)).status_code == 200
    assert idp.jwks_cagri_sayisi == ilk_jwks_cagrisi

    # IdP anahtarını döndürür → bilinmeyen kid → önbellek zorla tazelenir, giriş çalışır.
    idp.anahtar_dondur()
    assert (await _akis(kurulu_istemci, idp)).status_code == 200
    assert idp.jwks_cagri_sayisi == ilk_jwks_cagrisi + 1


async def test_sso_jit_kapaliyken_bilinmeyen_kullanici_reddedilir(
    test_db: str, kurulu_istemci: AsyncClient, idp: SahteIdp, test_engine: AsyncEngine
) -> None:
    await _guvenlik_ayarla(test_engine, "alfa", _oidc_ayari(idp, jit_provizyon=False))
    idp.ek_claimler = {"email": f"yok-{uuid.uuid4().hex[:8]}@firma.test"}
    cevap = await _akis(kurulu_istemci, idp)
    assert cevap.status_code == 403
    assert cevap.json()["hata_kodu"] == "SSO_KULLANICI_YOK"


async def test_sso_grup_rol_senkronu_girislerde_guncellenir(
    test_db: str, kurulu_istemci: AsyncClient, idp: SahteIdp, test_engine: AsyncEngine
) -> None:
    eposta = f"sso-{uuid.uuid4().hex[:8]}@firma.test"
    await _guvenlik_ayarla(
        test_engine,
        "alfa",
        _oidc_ayari(idp, grup_rol_eslemesi={"depocular": "depo", "kaliteciler": "kalite"}),
    )

    idp.ek_claimler = {"email": eposta, "groups": ["depocular"]}
    ilk = await _akis(kurulu_istemci, idp)
    assert ilk.status_code == 200
    ben = await kurulu_istemci.get(
        f"{KIMLIK}/ben",
        headers={
            "X-Tenant": "alfa",
            "Authorization": f"Bearer {ilk.json()['data']['access_token']}",
        },
    )
    assert ben.json()["data"]["roller"] == ["depo"]

    # IdP'de grup değişti → sonraki girişte roller senkronlanır (IdP otoritedir).
    idp.ek_claimler = {"email": eposta, "groups": ["kaliteciler"]}
    ikinci = await _akis(kurulu_istemci, idp)
    assert ikinci.status_code == 200
    ben2 = await kurulu_istemci.get(
        f"{KIMLIK}/ben",
        headers={
            "X-Tenant": "alfa",
            "Authorization": f"Bearer {ikinci.json()['data']['access_token']}",
        },
    )
    assert ben2.json()["data"]["roller"] == ["kalite"]

    # Tanımsız grup: eşleme sonuç vermez → mevcut roller KORUNUR (yetkisiz bırakma).
    idp.ek_claimler = {"email": eposta, "groups": ["idp-de-kalmis-eski-grup"]}
    ucuncu = await _akis(kurulu_istemci, idp)
    assert ucuncu.status_code == 200
    ben3 = await kurulu_istemci.get(
        f"{KIMLIK}/ben",
        headers={
            "X-Tenant": "alfa",
            "Authorization": f"Bearer {ucuncu.json()['data']['access_token']}",
        },
    )
    assert ben3.json()["data"]["roller"] == ["kalite"]


async def test_sso_kullanicinin_2fa_si_aciksa_ikinci_adim_istenir(
    test_db: str, kurulu_istemci: AsyncClient, idp: SahteIdp, test_engine: AsyncEngine
) -> None:
    """SSO IdP'de doğrulasa da kullanıcı kendi TOTP'sini açtıysa ikinci adım korunur."""
    eposta = f"sso-{uuid.uuid4().hex[:8]}@firma.test"
    await _guvenlik_ayarla(test_engine, "alfa", _oidc_ayari(idp))
    idp.ek_claimler = {"email": eposta}
    assert (await _akis(kurulu_istemci, idp)).status_code == 200

    # Kullanıcının 2FA'sını doğrudan DB'de etkinleştir (kurulum akışı ayrı testte).
    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm() as db:
        await db.execute(
            text(
                "UPDATE tenant_alfa.kullanici SET iki_asama_aktif = true, "
                "totp_sirri = 'JBSWY3DPEHPK3PXP' WHERE eposta = :e"
            ),
            {"e": eposta},
        )
        await db.commit()

    cevap = await _akis(kurulu_istemci, idp)
    assert cevap.status_code == 200
    veri = cevap.json()["data"]
    assert veri["iki_asama_gerekli"] is True
    assert veri["gecici_token"] and not veri["access_token"]


async def test_sso_debug_claim_logu_ham_claimleri_yazar(
    test_db: str,
    kurulu_istemci: AsyncClient,
    idp: SahteIdp,
    test_engine: AsyncEngine,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Canlı IdP teşhisi: ayar açıkken ham claim'ler loglanır (kod değişikliği gerekmeden)."""
    eposta = f"sso-{uuid.uuid4().hex[:8]}@firma.test"
    await _guvenlik_ayarla(test_engine, "alfa", _oidc_ayari(idp, debug_claim_log=True))
    idp.ek_claimler = {"email": eposta}

    # create_app() kök logger handler'larını temizlediği için caplog'a güvenilmez;
    # kendi toplayıcımızı doğrudan ilgili logger'a bağlarız.
    class _Toplayici(logging.Handler):
        def __init__(self) -> None:
            super().__init__()
            self.mesajlar: list[str] = []

        def emit(self, record: logging.LogRecord) -> None:
            self.mesajlar.append(record.getMessage())

    toplayici = _Toplayici()
    oidc_logger = logging.getLogger("app.oidc")
    onceki_seviye = oidc_logger.level
    oidc_logger.addHandler(toplayici)
    oidc_logger.setLevel(logging.WARNING)
    try:
        assert (await _akis(kurulu_istemci, idp)).status_code == 200
    finally:
        oidc_logger.removeHandler(toplayici)
        oidc_logger.setLevel(onceki_seviye)
    assert any(eposta in m for m in toplayici.mesajlar), toplayici.mesajlar


async def test_sso_yapilandirilmamis_tenantta_tamamla_404(
    test_db: str, kurulu_istemci: AsyncClient, idp: SahteIdp, test_engine: AsyncEngine
) -> None:
    await _guvenlik_ayarla(test_engine, "alfa", _oidc_ayari(idp))
    url = await _sso_baslat(kurulu_istemci, "alfa")
    kod, state = idp.yetkilendir(url)
    # Akış ortasında SSO kapatılırsa tamamlama da kapanır.
    await _guvenlik_ayarla(test_engine, "alfa", None)
    assert (await _sso_tamamla(kurulu_istemci, kod, state)).status_code == 404


async def test_sso_parola_akisi_bozulmadan_calismaya_devam_eder(
    test_db: str, kurulu_istemci: AsyncClient, idp: SahteIdp, test_engine: AsyncEngine
) -> None:
    """SSO açıkken normal parola girişi de çalışır (regresyon koruması)."""
    await _guvenlik_ayarla(test_engine, "alfa", _oidc_ayari(idp))
    h = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.get(f"{KIMLIK}/ben", headers=h)
    assert r.status_code == 200
    assert r.json()["data"]["eposta"] == ALFA["eposta"]


async def test_sso_beta_tenantinda_alfa_kullanicisi_olusmaz(
    test_db: str, kurulu_istemci: AsyncClient, idp: SahteIdp, test_engine: AsyncEngine
) -> None:
    """Tenant izolasyonu: SSO ile beta'da açılan kullanıcı alfa şemasında görünmez."""
    eposta = f"sso-izole-{uuid.uuid4().hex[:8]}@firma.test"
    await _guvenlik_ayarla(test_engine, "beta", _oidc_ayari(idp))
    idp.ek_claimler = {"email": eposta}
    assert (await _akis(kurulu_istemci, idp, "beta")).status_code == 200

    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm() as db:
        beta_sayi = await db.scalar(
            text("SELECT count(*) FROM tenant_beta.kullanici WHERE eposta = :e"), {"e": eposta}
        )
        alfa_sayi = await db.scalar(
            text("SELECT count(*) FROM tenant_alfa.kullanici WHERE eposta = :e"), {"e": eposta}
        )
    assert beta_sayi == 1
    assert alfa_sayi == 0
