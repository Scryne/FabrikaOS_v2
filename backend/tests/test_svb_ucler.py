"""S-VB uç testleri — operatör eşleştirme, tedarikçi skoru, coğrafi koordinat."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import ALFA, BETA
from tests.test_s16_entitlement import _giris

pytestmark = pytest.mark.asyncio

OPERATOR = "/api/v1/tahmin/operator-eslesme"


async def _rolsuz_kullanici(istemci: AsyncClient, alfa_h: dict[str, str], eposta: str) -> dict:
    r = await istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": eposta, "parola": "Deneme12345!", "ad_soyad": "Rolsüz"},
        headers=alfa_h,
    )
    assert r.status_code == 201, r.text
    return await _giris(istemci, {"slug": "alfa", "eposta": eposta, "parola": "Deneme12345!"})


async def test_operator_eslesme_sirali_oneri_ve_rbac(
    test_db: str, kurulu_istemci: AsyncClient
) -> None:
    h = await _giris(kurulu_istemci, ALFA)

    # Operatör adayı olacak kullanıcı + personel bağlantısı.
    r = await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "svb-op@alfa.test", "parola": "Deneme12345!", "ad_soyad": "Op Bir"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    op_kullanici_id = r.json()["data"]["id"]

    r = await kurulu_istemci.post(
        "/api/v1/personeller",
        json={
            "sicil_no": "SVB-P1",
            "ad": "Op",
            "soyad": "Bir",
            "departman": "Üretim",
            "unvan": "Operatör",
            "kullanici_id": op_kullanici_id,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text

    r = await kurulu_istemci.post(
        "/api/v1/personeller",
        json={
            "sicil_no": "SVB-P2",
            "ad": "Ofis",
            "soyad": "İki",
            "departman": "Muhasebe",
            "unvan": "Uzman",
            "kullanici_id": None,  # kullanıcı bağlantısı yok → aday değil
        },
        headers=h,
    )
    assert r.status_code == 201, r.text

    r = await kurulu_istemci.post(OPERATOR, json={"is_turu": "uretim"}, headers=h)
    assert r.status_code == 200, r.text
    oneriler = r.json()["data"]
    sicil_adlari = [o["ad_soyad"] for o in oneriler]
    assert "Op Bir" in sicil_adlari  # üretim departmanı aday
    assert "Ofis İki" not in sicil_adlari  # kullanıcısız personel aday olamaz
    # Skorlar sıralı (azalan) ve gerekçe dolu.
    skorlar = [o["skor"] for o in oneriler]
    assert skorlar == sorted(skorlar, reverse=True)
    assert all(o["gerekce"] for o in oneriler)

    # Var olmayan iş emri 404.
    r = await kurulu_istemci.post(OPERATOR, json={"is_emri_id": 999999}, headers=h)
    assert r.status_code == 404

    # RBAC: ai:oku olmayan kullanıcı 403.
    rolsuz_h = await _rolsuz_kullanici(kurulu_istemci, h, "svb-op-rolsuz@alfa.test")
    r = await kurulu_istemci.post(OPERATOR, json={"is_turu": "uretim"}, headers=rolsuz_h)
    assert r.status_code == 403

    # İzolasyon: beta'da alfa personeli önerilere sızmaz.
    beta_h = await _giris(kurulu_istemci, BETA)
    r = await kurulu_istemci.post(OPERATOR, json={"is_turu": "uretim"}, headers=beta_h)
    assert r.status_code == 200
    assert all(o["ad_soyad"] != "Op Bir" for o in r.json()["data"])


async def test_firma_skoru_sinyal_zinciri_ve_izolasyon(
    test_db: str, kurulu_istemci: AsyncClient
) -> None:
    h = await _giris(kurulu_istemci, ALFA)

    r = await kurulu_istemci.post(
        "/api/v1/firmalar", json={"ad": "SVB Tedarik AŞ", "tip": "tedarikci"}, headers=h
    )
    assert r.status_code == 201, r.text
    firma_id = r.json()["data"]["id"]

    # Sinyalsiz skor: tüm bileşenler nötr → 50 + yetersiz_veri.
    r = await kurulu_istemci.get(f"/api/v1/firmalar/{firma_id}/skor", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["skor"] == 50.0
    assert set(data["yetersiz_veri"]) == {"kalite", "sozlesme", "talep"}
    assert data["zamaninda_teslim"] is None  # S25'te dolar

    # Kalite sinyali: firmaya bağlı malzeme + geçen giriş kontrolü.
    r = await kurulu_istemci.post(
        "/api/v1/malzemeler",
        json={
            "kod": "SVB-MLZ-1",
            "ad": "Tedarik malzemesi",
            "birim": "adet",
            "tedarikci_firma_id": firma_id,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    malzeme_id = r.json()["data"]["id"]
    assert r.json()["data"]["tedarikci_firma_id"] == firma_id

    r = await kurulu_istemci.post(
        "/api/v1/kalite-kontrolleri",
        json={"malzeme_id": malzeme_id, "kontrol_turu": "giris", "sonuc": "gecti"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["data"]["malzeme_id"] == malzeme_id

    r = await kurulu_istemci.get(f"/api/v1/firmalar/{firma_id}/skor", headers=h)
    data = r.json()["data"]
    assert data["kalite_gecme_orani"] == 1.0
    assert data["skor"] == 70.0  # 40*1.0 + 30*0.5 + 30*0.5
    assert "kalite" not in data["yetersiz_veri"]

    # RBAC: crm:oku olmayan 403.
    rolsuz_h = await _rolsuz_kullanici(kurulu_istemci, h, "svb-skor-rolsuz@alfa.test")
    r = await kurulu_istemci.get(f"/api/v1/firmalar/{firma_id}/skor", headers=rolsuz_h)
    assert r.status_code == 403

    # İzolasyon: beta'dan alfa firması görünmez. Aynı sayısal id beta'nın KENDİ
    # firmasına denk gelebilir (şema-bazlı bağımsız diziler) — doğru iddia, alfa
    # kaydının beta'da adıyla bulunamamasıdır.
    beta_h = await _giris(kurulu_istemci, BETA)
    r = await kurulu_istemci.get(f"/api/v1/firmalar/{firma_id}", headers=beta_h)
    assert r.status_code == 404 or r.json()["data"]["ad"] != "SVB Tedarik AŞ"
    r = await kurulu_istemci.get("/api/v1/firmalar?arama=SVB Tedarik", headers=beta_h)
    if r.status_code == 200:
        assert all(f["ad"] != "SVB Tedarik AŞ" for f in r.json()["data"])


async def test_makine_koordinat_guncelleme_ve_ikiz_durumda_gorunur(
    test_db: str, kurulu_istemci: AsyncClient
) -> None:
    h = await _giris(kurulu_istemci, ALFA)

    r = await kurulu_istemci.post(
        "/api/v1/makineler",
        json={"kod": "SVB-GEO-1", "ad": "Geo makinesi", "enlem": 40.99, "boylam": 29.03},
        headers=h,
    )
    assert r.status_code == 201, r.text
    mid = r.json()["data"]["id"]
    assert r.json()["data"]["enlem"] == pytest.approx(40.99)

    # PATCH ile koordinat güncellenebilir.
    r = await kurulu_istemci.patch(
        f"/api/v1/makineler/{mid}", json={"enlem": 41.01, "boylam": 28.98}, headers=h
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["enlem"] == pytest.approx(41.01)

    # Geçersiz koordinat 422.
    r = await kurulu_istemci.patch(f"/api/v1/makineler/{mid}", json={"enlem": 123.0}, headers=h)
    assert r.status_code == 422

    # /ikiz/durum yanıtı koordinatı taşır (yerleşmemiş listede).
    r = await kurulu_istemci.get("/api/v1/ikiz/durum", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    hepsi = data["dugumler"] + data["yerlesmemis"]
    geo = next(m for m in hepsi if m["makine_kod"] == "SVB-GEO-1")
    assert geo["enlem"] == pytest.approx(41.01)
    assert geo["boylam"] == pytest.approx(28.98)
