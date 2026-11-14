"""S10 entegrasyon: kalite kontrol oluştur/listele + RBAC + tenant izolasyonu."""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import ALFA, BETA

KIMLIK = "/api/v1/kimlik"


async def _giris(istemci: AsyncClient, t: dict) -> str:
    r = await istemci.post(
        f"{KIMLIK}/token",
        data={"username": t["eposta"], "password": t["parola"]},
        headers={"X-Tenant": t["slug"]},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["access_token"]


def _h(slug: str, access: str) -> dict[str, str]:
    return {"X-Tenant": slug, "Authorization": f"Bearer {access}"}


async def _kontrol(istemci: AsyncClient, h: dict[str, str], **ek: object) -> dict:
    govde = {"kontrol_turu": "uretim", "sonuc": "gecti", "numune_adedi": 10, **ek}
    r = await istemci.post("/api/v1/kalite-kontrolleri", json=govde, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_kontrol_olustur_oto_kod(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _kontrol(kurulu_istemci, h)
    assert d["kod"].startswith("KK-")
    assert d["sonuc"] == "gecti"


async def test_kontrol_gecersiz_sonuc_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/kalite-kontrolleri",
        json={"sonuc": "belirsiz", "numune_adedi": 1},
        headers=h,
    )
    assert r.status_code == 422, r.text


async def test_kontrol_uygunsuz_numuneden_fazla_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/kalite-kontrolleri",
        json={"sonuc": "kaldi", "numune_adedi": 5, "uygunsuz_adet": 9},
        headers=h,
    )
    assert r.status_code == 422, r.text


async def test_kontrol_listele_filtre_sonuc(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await _kontrol(kurulu_istemci, h, sonuc="gecti")
    await _kontrol(kurulu_istemci, h, sonuc="kaldi")
    r = await kurulu_istemci.get("/api/v1/kalite-kontrolleri?sonuc=kaldi", headers=h)
    assert r.status_code == 200, r.text
    assert all(x["sonuc"] == "kaldi" for x in r.json()["data"])


async def test_kontrol_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "izl-kl@alfa.test", "parola": "Izleyici123!", "roller": ["izleyici"]},
        headers=admin,
    )
    izl = _h(
        "alfa",
        await _giris(
            kurulu_istemci, {"slug": "alfa", "eposta": "izl-kl@alfa.test", "parola": "Izleyici123!"}
        ),
    )
    # kalite:oku var → liste 200
    assert (await kurulu_istemci.get("/api/v1/kalite-kontrolleri", headers=izl)).status_code == 200
    # kalite:yaz yok → oluştur 403
    r = await kurulu_istemci.post(
        "/api/v1/kalite-kontrolleri", json={"sonuc": "gecti", "numune_adedi": 1}, headers=izl
    )
    assert r.status_code == 403, r.text


async def test_kontrol_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    ha = _h("alfa", await _giris(kurulu_istemci, ALFA))
    da = await _kontrol(kurulu_istemci, ha)
    hb = _h("beta", await _giris(kurulu_istemci, BETA))
    assert (
        await kurulu_istemci.get(f"/api/v1/kalite-kontrolleri/{da['id']}", headers=hb)
    ).status_code == 404


async def test_kontrol_gecersiz_tur_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/kalite-kontrolleri",
        json={"sonuc": "gecti", "kontrol_turu": "sihirli", "numune_adedi": 1},
        headers=h,
    )
    assert r.status_code == 422, r.text


async def test_kontrol_limit_ters_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/kalite-kontrolleri",
        json={"sonuc": "gecti", "numune_adedi": 1, "alt_limit": 10, "ust_limit": 5},
        headers=h,
    )
    assert r.status_code == 422, r.text


async def test_kalite_makine_secenekleri_dar_okuma_yetki_ve_yalitim(
    kurulu_istemci: AsyncClient,
) -> None:
    """Kalite rolü uretim:oku olmadan formun makine seçicisini doldurur; yalnız id/kod/ad."""
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/makineler", json={"kod": "KAL-SEC-1", "ad": "Seçenek Makinesi"}, headers=admin
    )
    assert r.status_code == 201, r.text
    for eposta, rol in (("kal-sec@alfa.test", "kalite"), ("depo-sec@alfa.test", "depo")):
        await kurulu_istemci.post(
            "/api/v1/kullanicilar",
            json={"eposta": eposta, "parola": "Secenek123!", "roller": [rol]},
            headers=admin,
        )
    kal = _h(
        "alfa",
        await _giris(
            kurulu_istemci, {"slug": "alfa", "eposta": "kal-sec@alfa.test", "parola": "Secenek123!"}
        ),
    )
    # Geniş üretim okuması kalite rolünde kapalı kalır.
    assert (await kurulu_istemci.get("/api/v1/makineler", headers=kal)).status_code == 403
    r = await kurulu_istemci.get("/api/v1/kalite/makine-secenekleri", headers=kal)
    assert r.status_code == 200, r.text
    satirlar = r.json()["data"]
    secenek = next(x for x in satirlar if x["kod"] == "KAL-SEC-1")
    assert set(secenek) == {"id", "kod", "ad"}  # durum/OEE/konum sızmaz
    # kalite:oku olmayan rol 403.
    depo = _h(
        "alfa",
        await _giris(
            kurulu_istemci,
            {"slug": "alfa", "eposta": "depo-sec@alfa.test", "parola": "Secenek123!"},
        ),
    )
    r = await kurulu_istemci.get("/api/v1/kalite/makine-secenekleri", headers=depo)
    assert r.status_code == 403, r.text
    # Kiracı yalıtımı: beta alfa'nın makinesini görmez.
    beta = _h("beta", await _giris(kurulu_istemci, BETA))
    r = await kurulu_istemci.get("/api/v1/kalite/makine-secenekleri", headers=beta)
    assert r.status_code == 200, r.text
    assert all(x["kod"] != "KAL-SEC-1" for x in r.json()["data"])
