"""Kullanıcı güncelleme (``PATCH /kullanicilar/{id}``) testleri.

Kapsam: kısmi güncelleme (ad/roller/aktif), kendi hesabını kilitleme koruması,
tanımsız rol 422, firma bağla/kaldır (S18 dış portal), yeniden aktifleştirmede
koltuk limiti (S16 — pasifleştirme koltuk açar, aktifleştirme limite tabidir).
"""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from app.control_plane.provizyon import tenant_provizyonla
from tests.conftest import ALFA, TEST_URL
from tests.test_s16_entitlement import _giris

KULLANICILAR = "/api/v1/kullanicilar"

DELTA = {
    "slug": "delta18g",
    "ad": "Delta Güncelleme Fabrika",
    "eposta": "admin@delta18g.test",
    "parola": "Delta12345!",
}


async def _kullanici_olustur(
    istemci: AsyncClient, h: dict[str, str], eposta: str, **ek: Any
) -> dict[str, Any]:
    r = await istemci.post(
        KULLANICILAR,
        json={"eposta": eposta, "parola": "Gecici12345!", "ad_soyad": "Test Kullanıcı", **ek},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_kismi_guncelleme_ad_rol_aktif(test_db: str, kurulu_istemci: AsyncClient) -> None:
    """Yalnız gönderilen alan değişir; ad → roller → aktif sırayla doğrulanır."""
    h = await _giris(kurulu_istemci, ALFA)
    k = await _kullanici_olustur(kurulu_istemci, h, "guncelle1@alfa.test", roller=["izleyici"])

    # Yalnız ad değişir; roller/aktif korunur.
    r = await kurulu_istemci.patch(
        f"{KULLANICILAR}/{k['id']}", json={"ad_soyad": "Yeni Ad"}, headers=h
    )
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert veri["ad_soyad"] == "Yeni Ad"
    assert veri["roller"] == ["izleyici"]
    assert veri["aktif"] is True

    # Roller değişir (boş liste = tüm roller kaldırılır).
    r = await kurulu_istemci.patch(f"{KULLANICILAR}/{k['id']}", json={"roller": []}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["roller"] == []

    # Pasifleştirme.
    r = await kurulu_istemci.patch(f"{KULLANICILAR}/{k['id']}", json={"aktif": False}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["aktif"] is False


async def test_kendi_aktif_ve_rolunu_degistiremez(
    test_db: str, kurulu_istemci: AsyncClient
) -> None:
    """Kilitlenme koruması: kendi hesabında aktif/roller 422; ad_soyad serbesttir."""
    h = await _giris(kurulu_istemci, ALFA)
    ben = (await kurulu_istemci.get("/api/v1/kimlik/ben", headers=h)).json()["data"]

    r = await kurulu_istemci.patch(f"{KULLANICILAR}/{ben['id']}", json={"aktif": False}, headers=h)
    assert r.status_code == 422, r.text

    r = await kurulu_istemci.patch(f"{KULLANICILAR}/{ben['id']}", json={"roller": []}, headers=h)
    assert r.status_code == 422, r.text

    # Ad değişikliği kendi hesabında serbest.
    r = await kurulu_istemci.patch(
        f"{KULLANICILAR}/{ben['id']}", json={"ad_soyad": ben["ad_soyad"]}, headers=h
    )
    assert r.status_code == 200, r.text


async def test_tanimsiz_rol_ve_bulunamayan(test_db: str, kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    k = await _kullanici_olustur(kurulu_istemci, h, "guncelle2@alfa.test")

    r = await kurulu_istemci.patch(
        f"{KULLANICILAR}/{k['id']}", json={"roller": ["kozmik-yonetici"]}, headers=h
    )
    assert r.status_code == 422, r.text

    r = await kurulu_istemci.patch(f"{KULLANICILAR}/999999", json={"aktif": False}, headers=h)
    assert r.status_code == 404, r.text


async def test_firma_bagla_ve_kaldir(test_db: str, kurulu_istemci: AsyncClient) -> None:
    """S18: firma_id bağlanır; açık ``null`` göndermek bağlantıyı kaldırır."""
    h = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.post(
        "/api/v1/firmalar", json={"ad": "Güncelleme Testi A.Ş."}, headers=h
    )
    assert r.status_code == 201, r.text
    firma_id = r.json()["data"]["id"]

    k = await _kullanici_olustur(kurulu_istemci, h, "guncelle3@alfa.test")
    r = await kurulu_istemci.patch(
        f"{KULLANICILAR}/{k['id']}", json={"firma_id": firma_id}, headers=h
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["firma_id"] == firma_id

    # Var olmayan firma 422.
    r = await kurulu_istemci.patch(
        f"{KULLANICILAR}/{k['id']}", json={"firma_id": 999999}, headers=h
    )
    assert r.status_code == 422, r.text

    # Açık null → bağlantı kalkar.
    r = await kurulu_istemci.patch(f"{KULLANICILAR}/{k['id']}", json={"firma_id": None}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["firma_id"] is None


async def test_yeniden_aktiflestirme_koltuk_limitine_tabi(
    test_db: str, kurulu_istemci: AsyncClient
) -> None:
    """`temel` planda (koltuk=10) pasifleştirme koltuk açar; dolu tenant'ta
    yeniden aktifleştirme 409 KOLTUK_LIMITI."""
    await tenant_provizyonla(
        slug=DELTA["slug"],
        ad=DELTA["ad"],
        admin_eposta=DELTA["eposta"],
        admin_parola=DELTA["parola"],
        plan_kodu="temel",
        db_url=TEST_URL,
    )
    h = await _giris(kurulu_istemci, DELTA)

    # Limite kadar doldur (admin dahil 10 aktif).
    for i in range(9):
        await _kullanici_olustur(kurulu_istemci, h, f"koltukg{i}@delta18g.test")

    # Birini pasifleştir → koltuk açılır, yeni kullanıcı oluşturulabilir.
    liste = (await kurulu_istemci.get(KULLANICILAR, params={"adet": 100}, headers=h)).json()
    pasif_id = next(k["id"] for k in liste["data"] if k["eposta"] == "koltukg0@delta18g.test")
    r = await kurulu_istemci.patch(f"{KULLANICILAR}/{pasif_id}", json={"aktif": False}, headers=h)
    assert r.status_code == 200, r.text
    yeni = await _kullanici_olustur(kurulu_istemci, h, "koltukg-yeni@delta18g.test")

    # Tenant yine dolu: pasif kullanıcıyı aktifleştirme 409 KOLTUK_LIMITI.
    r = await kurulu_istemci.patch(f"{KULLANICILAR}/{pasif_id}", json={"aktif": True}, headers=h)
    assert r.status_code == 409, r.text
    assert r.json()["hata_kodu"] == "KOLTUK_LIMITI"

    # Başka biri pasifleşince aynı aktifleştirme geçer.
    r = await kurulu_istemci.patch(f"{KULLANICILAR}/{yeni['id']}", json={"aktif": False}, headers=h)
    assert r.status_code == 200, r.text
    r = await kurulu_istemci.patch(f"{KULLANICILAR}/{pasif_id}", json={"aktif": True}, headers=h)
    assert r.status_code == 200, r.text


async def test_yetkisiz_kullanici_guncelleyemez(test_db: str, kurulu_istemci: AsyncClient) -> None:
    """`kullanici:yaz` izni olmayan rol (izleyici) 403 alır."""
    h = await _giris(kurulu_istemci, ALFA)
    hedef = await _kullanici_olustur(kurulu_istemci, h, "guncelle4@alfa.test")
    izleyici = {"slug": "alfa", "eposta": "guncelle-izle@alfa.test", "parola": "Gecici12345!"}
    await _kullanici_olustur(kurulu_istemci, h, izleyici["eposta"], roller=["izleyici"])

    hi = await _giris(kurulu_istemci, izleyici)
    r = await kurulu_istemci.patch(
        f"{KULLANICILAR}/{hedef['id']}", json={"ad_soyad": "Hack"}, headers=hi
    )
    assert r.status_code == 403, r.text
