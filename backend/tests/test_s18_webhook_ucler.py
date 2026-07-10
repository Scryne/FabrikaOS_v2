"""S18 webhook yönetim uçları — CRUD, maskeleme, bir-kez anahtar, RBAC, entitlement, izolasyon."""

from __future__ import annotations

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane import entitlement_service
from tests.conftest import ALFA, BETA
from tests.test_s16_entitlement import (  # noqa: F401  (fixture'lar)
    GAMMA,
    _giris,
    _tenant_id,
    gamma_db,
    oturum,
)

WEBHOOKLAR = "/api/v1/webhooklar"

GECERLI = {
    "ad": "ERP köprüsü",
    "url": "https://erp.ornek.test/webhook",
    "olay_turleri": ["is_emri.kapandi", "stok.kritik"],
}


@pytest_asyncio.fixture
async def alfa_h(kurulu_istemci: AsyncClient) -> dict[str, str]:
    return await _giris(kurulu_istemci, ALFA)


async def test_olustur_tam_anahtar_bir_kez_liste_maskeli(
    kurulu_istemci: AsyncClient, alfa_h: dict[str, str]
) -> None:
    r = await kurulu_istemci.post(WEBHOOKLAR, json=GECERLI, headers=alfa_h)
    assert r.status_code == 201, r.text
    veri = r.json()["data"]
    tam = veri["gizli_anahtar"]
    assert tam.startswith("whs_") and len(tam) > 30  # oluşturmada TAM anahtar
    assert "…" not in tam
    wid = veri["id"]

    # Liste + detay: maskeli (tam değer bir daha asla dönmez).
    r = await kurulu_istemci.get(WEBHOOKLAR, headers=alfa_h)
    assert r.status_code == 200
    satir = next(a for a in r.json()["data"] if a["id"] == wid)
    assert satir["gizli_anahtar"] != tam
    assert "…" in satir["gizli_anahtar"]
    assert satir["gizli_anahtar"].startswith(tam[:8])

    r = await kurulu_istemci.get(f"{WEBHOOKLAR}/{wid}", headers=alfa_h)
    assert "…" in r.json()["data"]["gizli_anahtar"]


async def test_anahtar_yenile_yeni_tam_anahtar(
    kurulu_istemci: AsyncClient, alfa_h: dict[str, str]
) -> None:
    r = await kurulu_istemci.post(WEBHOOKLAR, json=GECERLI, headers=alfa_h)
    eski_tam, wid = r.json()["data"]["gizli_anahtar"], r.json()["data"]["id"]

    r = await kurulu_istemci.post(f"{WEBHOOKLAR}/{wid}/anahtar-yenile", headers=alfa_h)
    assert r.status_code == 200, r.text
    yeni = r.json()["data"]["gizli_anahtar"]
    assert yeni.startswith("whs_") and "…" not in yeni and yeni != eski_tam


async def test_gecersiz_url_ve_olay_turu_422(
    kurulu_istemci: AsyncClient, alfa_h: dict[str, str]
) -> None:
    r = await kurulu_istemci.post(
        WEBHOOKLAR, json={**GECERLI, "url": "http://guvensiz.ornek.test/hook"}, headers=alfa_h
    )
    assert r.status_code == 422, r.text

    # Önek hilesi: host TAM eşleşmeli — "localhost.evil.com" localhost DEĞİLDİR.
    for hileli in (
        "http://localhost.evil.com/hook",
        "http://127.0.0.1.evil.com/hook",
        "http://localhost@evil.com/hook",
    ):
        r = await kurulu_istemci.post(WEBHOOKLAR, json={**GECERLI, "url": hileli}, headers=alfa_h)
        assert r.status_code == 422, f"{hileli}: {r.text}"

    # Yerel test alıcısı (port dahil) serbest kalır.
    r = await kurulu_istemci.post(
        WEBHOOKLAR, json={**GECERLI, "url": "http://localhost:9099/hook"}, headers=alfa_h
    )
    assert r.status_code == 201, r.text

    r = await kurulu_istemci.post(
        WEBHOOKLAR, json={**GECERLI, "olay_turleri": ["olmayan.olay"]}, headers=alfa_h
    )
    assert r.status_code == 422, r.text
    assert "olmayan.olay" in r.text


async def test_guncelle_ve_sil(kurulu_istemci: AsyncClient, alfa_h: dict[str, str]) -> None:
    r = await kurulu_istemci.post(WEBHOOKLAR, json=GECERLI, headers=alfa_h)
    wid = r.json()["data"]["id"]

    r = await kurulu_istemci.patch(
        f"{WEBHOOKLAR}/{wid}", json={"aktif": False, "olay_turleri": []}, headers=alfa_h
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["aktif"] is False
    assert r.json()["data"]["olay_turleri"] == []  # boş liste = tüm olaylar

    r = await kurulu_istemci.delete(f"{WEBHOOKLAR}/{wid}", headers=alfa_h)
    assert r.status_code == 200, r.text
    r = await kurulu_istemci.get(f"{WEBHOOKLAR}/{wid}", headers=alfa_h)
    assert r.status_code == 404


async def test_olay_turleri_katalogu(kurulu_istemci: AsyncClient, alfa_h: dict[str, str]) -> None:
    r = await kurulu_istemci.get(f"{WEBHOOKLAR}/olay-turleri", headers=alfa_h)
    assert r.status_code == 200, r.text
    kodlar = {o["kod"] for o in r.json()["data"]}
    assert {
        "is_emri.kapandi",
        "ariza.olustu",
        "stok.kritik",
        "oee.dustu",
        "sozlesme.yaklasiyor",
        "anomali.tespit",
        "kalite.uygunsuzluk",
        "isg.kaza",
    } == kodlar


async def test_teslimat_gunlugu_bos_ve_yeniden_dene_404(
    kurulu_istemci: AsyncClient, alfa_h: dict[str, str]
) -> None:
    r = await kurulu_istemci.get(f"{WEBHOOKLAR}/teslimatlar", headers=alfa_h)
    assert r.status_code == 200, r.text
    assert isinstance(r.json()["data"], list)

    r = await kurulu_istemci.post(f"{WEBHOOKLAR}/teslimatlar/999999/yeniden-dene", headers=alfa_h)
    assert r.status_code == 404


async def test_rbac_izleyici_okur_yazamaz(
    kurulu_istemci: AsyncClient, alfa_h: dict[str, str]
) -> None:
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "izleyici18@alfa.test", "parola": "Izleyici18!", "roller": ["izleyici"]},
        headers=alfa_h,
    )
    izleyici = await _giris(
        kurulu_istemci,
        {"slug": "alfa", "eposta": "izleyici18@alfa.test", "parola": "Izleyici18!"},
    )
    r = await kurulu_istemci.get(WEBHOOKLAR, headers=izleyici)
    assert r.status_code == 200, r.text  # entegrasyon:oku (*:oku kümesinde)
    r = await kurulu_istemci.post(WEBHOOKLAR, json=GECERLI, headers=izleyici)
    assert r.status_code == 403, r.text  # entegrasyon:yaz yok


async def test_temel_planda_403_bayrak_override_acar(
    gamma_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
    oturum: AsyncSession,  # noqa: F811
) -> None:
    h = await _giris(kurulu_istemci, GAMMA)

    r = await kurulu_istemci.get(WEBHOOKLAR, headers=h)
    assert r.status_code == 403, r.text  # temel planda entegrasyon modülü yok
    assert r.json()["hata_kodu"] == "MODUL_KAPALI"

    gamma_id = await _tenant_id(oturum, GAMMA["slug"])
    try:
        # S16 tüketimi: platform admin bayrakla ön izleme verir → bir SONRAKİ istekte açık.
        await entitlement_service.ozellik_bayragi_ayarla(oturum, gamma_id, "webhook-onizleme", True)
        await oturum.commit()
        r = await kurulu_istemci.get(WEBHOOKLAR, headers=h)
        assert r.status_code == 200, r.text
    finally:
        await entitlement_service.ozellik_bayragi_ayarla(oturum, gamma_id, "webhook-onizleme", None)
        await oturum.commit()

    r = await kurulu_istemci.get(WEBHOOKLAR, headers=h)
    assert r.status_code == 403  # bayrak kalktı → plana döndü


async def test_tenant_izolasyonu(kurulu_istemci: AsyncClient, alfa_h: dict[str, str]) -> None:
    r = await kurulu_istemci.post(WEBHOOKLAR, json={**GECERLI, "ad": "izolasyon-a"}, headers=alfa_h)
    wid = r.json()["data"]["id"]

    beta_h = await _giris(kurulu_istemci, BETA)
    r = await kurulu_istemci.get(WEBHOOKLAR, headers=beta_h)
    assert all(a["ad"] != "izolasyon-a" for a in r.json()["data"])
    r = await kurulu_istemci.get(f"{WEBHOOKLAR}/{wid}", headers=beta_h)
    assert r.status_code == 404  # başka tenant'ın kaydı görünmezdir
