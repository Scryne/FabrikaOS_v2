"""S10 entegrasyon: Tam CAPA yaşam döngüsü + aksiyonlar + RBAC + izolasyon."""

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


async def _uygunsuzluk(istemci: AsyncClient, h: dict[str, str], **ek: object) -> dict:
    govde = {"baslik": "Yüzey çizik", "onem": "yuksek", **ek}
    r = await istemci.post("/api/v1/uygunsuzluklar", json=govde, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def _durum(
    istemci: AsyncClient, h: dict[str, str], uid: int, hedef: str, **ek: object
) -> None:
    r = await istemci.patch(
        f"/api/v1/uygunsuzluklar/{uid}/durum", json={"hedef": hedef, **ek}, headers=h
    )
    assert r.status_code == 200, r.text


async def test_capa_tam_yasam_dongusu(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _uygunsuzluk(kurulu_istemci, h)
    assert d["kod"].startswith("UY-")
    assert d["durum"] == "acik"
    uid = d["id"]

    await _durum(kurulu_istemci, h, uid, "kok_neden", kok_neden="Kalıp aşınması")
    await _durum(kurulu_istemci, h, uid, "aksiyon_plani")

    # düzeltici + önleyici aksiyon ekle
    for tur in ("duzeltici", "onleyici"):
        r = await kurulu_istemci.post(
            f"/api/v1/uygunsuzluklar/{uid}/aksiyonlar",
            json={"tur": tur, "aciklama": f"{tur} aksiyon"},
            headers=h,
        )
        assert r.status_code == 201, r.text

    await _durum(kurulu_istemci, h, uid, "uygulama")
    await _durum(kurulu_istemci, h, uid, "dogrulama")
    await _durum(kurulu_istemci, h, uid, "kapandi", dogrulama_notu="Etkin")

    r = await kurulu_istemci.get(f"/api/v1/uygunsuzluklar/{uid}", headers=h)
    body = r.json()["data"]
    assert body["durum"] == "kapandi"
    assert body["kok_neden"] == "Kalıp aşınması"
    assert body["kapanis_tarihi"] is not None
    assert len(body["aksiyonlar"]) == 2


async def test_capa_gecersiz_gecis_409(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _uygunsuzluk(kurulu_istemci, h)
    # acik → kapandi doğrudan yasak
    r = await kurulu_istemci.patch(
        f"/api/v1/uygunsuzluklar/{d['id']}/durum", json={"hedef": "kapandi"}, headers=h
    )
    assert r.status_code == 409, r.text


async def test_capa_gecersiz_hedef_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _uygunsuzluk(kurulu_istemci, h)
    r = await kurulu_istemci.patch(
        f"/api/v1/uygunsuzluklar/{d['id']}/durum", json={"hedef": "yok"}, headers=h
    )
    assert r.status_code == 422, r.text


async def test_dogrulamadan_uygulamaya_geri(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _uygunsuzluk(kurulu_istemci, h)
    uid = d["id"]
    for hedef in ("kok_neden", "aksiyon_plani", "uygulama", "dogrulama"):
        await _durum(kurulu_istemci, h, uid, hedef)
    # doğrulama başarısız → uygulamaya geri
    await _durum(kurulu_istemci, h, uid, "uygulama")
    r = await kurulu_istemci.get(f"/api/v1/uygunsuzluklar/{uid}", headers=h)
    assert r.json()["data"]["durum"] == "uygulama"


async def test_aksiyon_durum_guncelle(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _uygunsuzluk(kurulu_istemci, h)
    uid = d["id"]
    r = await kurulu_istemci.post(
        f"/api/v1/uygunsuzluklar/{uid}/aksiyonlar",
        json={"tur": "duzeltici", "aciklama": "Kalıbı değiştir"},
        headers=h,
    )
    aid = r.json()["data"]["aksiyonlar"][-1]["id"]
    r = await kurulu_istemci.patch(
        f"/api/v1/uygunsuzluklar/{uid}/aksiyonlar/{aid}",
        json={"durum": "tamamlandi"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    hedef = next(a for a in r.json()["data"]["aksiyonlar"] if a["id"] == aid)
    assert hedef["durum"] == "tamamlandi"
    assert hedef["tamamlanma_tarihi"] is not None


async def test_uygunsuzluk_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "izl-uy@alfa.test", "parola": "Izleyici123!", "roller": ["izleyici"]},
        headers=admin,
    )
    izl = _h(
        "alfa",
        await _giris(
            kurulu_istemci, {"slug": "alfa", "eposta": "izl-uy@alfa.test", "parola": "Izleyici123!"}
        ),
    )
    assert (await kurulu_istemci.get("/api/v1/uygunsuzluklar", headers=izl)).status_code == 200
    r = await kurulu_istemci.post(
        "/api/v1/uygunsuzluklar", json={"baslik": "X", "onem": "orta"}, headers=izl
    )
    assert r.status_code == 403, r.text


async def test_uygunsuzluk_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    ha = _h("alfa", await _giris(kurulu_istemci, ALFA))
    da = await _uygunsuzluk(kurulu_istemci, ha)
    hb = _h("beta", await _giris(kurulu_istemci, BETA))
    assert (
        await kurulu_istemci.get(f"/api/v1/uygunsuzluklar/{da['id']}", headers=hb)
    ).status_code == 404
