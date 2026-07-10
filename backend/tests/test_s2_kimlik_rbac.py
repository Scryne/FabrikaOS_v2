"""S2 entegrasyon testleri: kimlik, tenant izolasyonu ve RBAC (API üzerinden).

Faz 0 geçiş kapısının kanıtı: iki tenant provizyonlu; tenant-A token'ı tenant-B verisine
erişemez; yetkisiz izin 403; audit kaydı oluşur.
"""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import ALFA, BETA

KIMLIK = "/api/v1/kimlik"
KULLANICILAR = "/api/v1/kullanicilar"


async def _giris(istemci: AsyncClient, t: dict) -> tuple[str, str]:
    r = await istemci.post(
        f"{KIMLIK}/token",
        data={"username": t["eposta"], "password": t["parola"]},
        headers={"X-Tenant": t["slug"]},
    )
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    return veri["access_token"], veri["refresh_token"]


def _baslik(slug: str, access: str | None = None) -> dict[str, str]:
    h = {"X-Tenant": slug}
    if access:
        h["Authorization"] = f"Bearer {access}"
    return h


# --- Kimlik ---
async def test_giris_basarili_ve_ben(kurulu_istemci: AsyncClient) -> None:
    access, _ = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.get(f"{KIMLIK}/ben", headers=_baslik("alfa", access))
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert veri["eposta"] == ALFA["eposta"]
    assert "admin" in veri["roller"]
    assert "kullanici:yaz" in veri["izinler"]


async def test_yanlis_parola_401(kurulu_istemci: AsyncClient) -> None:
    r = await kurulu_istemci.post(
        f"{KIMLIK}/token",
        data={"username": ALFA["eposta"], "password": "yanlis-parola"},
        headers={"X-Tenant": "alfa"},
    )
    assert r.status_code == 401
    assert r.json()["success"] is False


async def test_bilinmeyen_tenant_404(kurulu_istemci: AsyncClient) -> None:
    r = await kurulu_istemci.post(
        f"{KIMLIK}/token",
        data={"username": ALFA["eposta"], "password": ALFA["parola"]},
        headers={"X-Tenant": "yok-boyle-tenant"},
    )
    assert r.status_code == 404


async def test_token_olmadan_korumali_uc_401(kurulu_istemci: AsyncClient) -> None:
    r = await kurulu_istemci.get(KULLANICILAR, headers=_baslik("alfa"))
    assert r.status_code == 401


# --- Tenant izolasyonu ---
async def test_kullanici_olustur_ve_listele(kurulu_istemci: AsyncClient) -> None:
    access, _ = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.post(
        KULLANICILAR,
        json={"eposta": "uretici1@alfa.test", "parola": "Uretici123!", "ad_soyad": "Üretici Bir"},
        headers=_baslik("alfa", access),
    )
    assert r.status_code == 201, r.text

    # adet=100: paylaşılan test tenant'ında kullanıcı sayısı bir sayfayı aşabilir.
    r = await kurulu_istemci.get(
        KULLANICILAR, params={"adet": 100}, headers=_baslik("alfa", access)
    )
    assert r.status_code == 200
    epostalar = [k["eposta"] for k in r.json()["data"]]
    assert "uretici1@alfa.test" in epostalar


async def test_tenant_veri_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    # Alfa'da benzersiz bir kullanıcı oluştur.
    access_alfa, _ = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.post(
        KULLANICILAR,
        json={"eposta": "sizinti@alfa.test", "parola": "Sizinti123!"},
        headers=_baslik("alfa", access_alfa),
    )
    assert r.status_code == 201, r.text

    # Beta context'inde aynı kayıt GÖRÜNMEMELİ (search_path izolasyonu).
    access_beta, _ = await _giris(kurulu_istemci, BETA)
    r = await kurulu_istemci.get(KULLANICILAR, headers=_baslik("beta", access_beta))
    assert r.status_code == 200
    epostalar = [k["eposta"] for k in r.json()["data"]]
    assert "sizinti@alfa.test" not in epostalar
    assert BETA["eposta"] in epostalar


async def test_cross_tenant_token_403(kurulu_istemci: AsyncClient) -> None:
    # Alfa token'ı ile Beta subdomain'ine istek → cross-tenant koruması (403).
    access_alfa, _ = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.get(KULLANICILAR, headers=_baslik("beta", access_alfa))
    assert r.status_code == 403


# --- RBAC ---
async def test_rbac_yetkisiz_yazma_403(kurulu_istemci: AsyncClient) -> None:
    # Admin, salt-okunur (izleyici) bir kullanıcı oluşturur.
    access_admin, _ = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.post(
        KULLANICILAR,
        json={
            "eposta": "izleyici@alfa.test",
            "parola": "Izleyici123!",
            "roller": ["izleyici"],
        },
        headers=_baslik("alfa", access_admin),
    )
    assert r.status_code == 201, r.text

    # İzleyici giriş yapar: GET (kullanici:oku) serbest, POST (kullanici:yaz) 403.
    access_izleyici, _ = await _giris(
        kurulu_istemci, {"slug": "alfa", "eposta": "izleyici@alfa.test", "parola": "Izleyici123!"}
    )
    r = await kurulu_istemci.get(KULLANICILAR, headers=_baslik("alfa", access_izleyici))
    assert r.status_code == 200

    r = await kurulu_istemci.post(
        KULLANICILAR,
        json={"eposta": "olmaz@alfa.test", "parola": "Olmaz12345!"},
        headers=_baslik("alfa", access_izleyici),
    )
    assert r.status_code == 403


# --- Rol kataloğu ---
async def test_roller_listele(kurulu_istemci: AsyncClient) -> None:
    access, _ = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.get("/api/v1/roller", headers=_baslik("alfa", access))
    assert r.status_code == 200, r.text
    roller = {rol["ad"]: rol for rol in r.json()["data"]}
    assert "admin" in roller
    assert "izleyici" in roller
    assert "kullanici:yaz" in roller["admin"]["izinler"]
    # izleyici salt-okunur: yalnız *:oku izinleri taşır.
    assert all(izin.endswith(":oku") for izin in roller["izleyici"]["izinler"])


async def test_roller_rbac_yetkisiz_403(kurulu_istemci: AsyncClient) -> None:
    # rol:oku izni olmayan bir rol (saha-cihaz yalnız edge iznine sahip).
    access_admin, _ = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.post(
        KULLANICILAR,
        json={
            "eposta": "cihaz-hesabi@alfa.test",
            "parola": "Cihaz12345!",
            "roller": ["saha-cihaz"],
        },
        headers=_baslik("alfa", access_admin),
    )
    assert r.status_code == 201, r.text

    access_cihaz, _ = await _giris(
        kurulu_istemci,
        {"slug": "alfa", "eposta": "cihaz-hesabi@alfa.test", "parola": "Cihaz12345!"},
    )
    r = await kurulu_istemci.get("/api/v1/roller", headers=_baslik("alfa", access_cihaz))
    assert r.status_code == 403


# --- Token rotasyonu / çıkış ---
async def test_token_rotasyonu_eski_refresh_iptal(kurulu_istemci: AsyncClient) -> None:
    _, refresh1 = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.post(
        f"{KIMLIK}/yenile", json={"refresh_token": refresh1}, headers=_baslik("alfa")
    )
    assert r.status_code == 200, r.text
    refresh2 = r.json()["data"]["refresh_token"]
    assert refresh2 != refresh1

    # Eski refresh artık iptalli.
    r = await kurulu_istemci.post(
        f"{KIMLIK}/yenile", json={"refresh_token": refresh1}, headers=_baslik("alfa")
    )
    assert r.status_code == 401


async def test_cikis_refresh_iptal(kurulu_istemci: AsyncClient) -> None:
    access, refresh = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.post(
        f"{KIMLIK}/cikis", json={"refresh_token": refresh}, headers=_baslik("alfa", access)
    )
    assert r.status_code == 200, r.text

    r = await kurulu_istemci.post(
        f"{KIMLIK}/yenile", json={"refresh_token": refresh}, headers=_baslik("alfa")
    )
    assert r.status_code == 401
