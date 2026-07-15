"""S24 MES derinleşmesi API testleri — vardiya/OEE kırılımı, duruş→OEE, BOM, izlenebilirlik."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from tests.conftest import ALFA, BETA
from tests.test_s16_entitlement import _giris

pytestmark = pytest.mark.asyncio


async def _makine(istemci: AsyncClient, h: dict[str, str], kod: str) -> int:
    r = await istemci.post("/api/v1/makineler", json={"kod": kod, "ad": f"{kod} m."}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


async def _uretim(istemci: AsyncClient, h: dict[str, str], makine_id: int, **ekstra) -> None:
    govde = {
        "makine_id": makine_id,
        "planlanan_sure_dk": 100.0,
        "durus_sure_dk": 0.0,
        "toplam_adet": 100,
        "saglam_adet": 100,
        "ideal_cevrim_sn": 60.0,
        **ekstra,
    }
    r = await istemci.post("/api/v1/uretim-verileri", json=govde, headers=h)
    assert r.status_code == 201, r.text


async def test_vardiya_tanimi_ve_oee_vardiya_kirilimi(
    test_db: str, kurulu_istemci: AsyncClient
) -> None:
    h = await _giris(kurulu_istemci, ALFA)

    r = await kurulu_istemci.post(
        "/api/v1/vardiyalar",
        json={"ad": "S24-Gündüz", "baslangic_saat": "08:00:00", "bitis_saat": "16:00:00"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    # Aynı ad ikinci kez 409.
    r = await kurulu_istemci.post(
        "/api/v1/vardiyalar",
        json={"ad": "S24-Gündüz", "baslangic_saat": "08:00:00", "bitis_saat": "16:00:00"},
        headers=h,
    )
    assert r.status_code == 409

    mid = await _makine(kurulu_istemci, h, "S24-VRD")
    await _uretim(kurulu_istemci, h, mid, vardiya="S24-Gündüz", toplam_adet=80, saglam_adet=80)
    await _uretim(kurulu_istemci, h, mid, vardiya="S24-Gece", toplam_adet=20, saglam_adet=10)

    # Vardiya kırılımı: yalnız o vardiyanın kayıtları toplanır.
    r = await kurulu_istemci.get(f"/api/v1/makineler/{mid}/oee?vardiya=S24-Gündüz", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["kayit_sayisi"] == 1
    assert r.json()["data"]["kalite"] == pytest.approx(1.0)

    r = await kurulu_istemci.get(f"/api/v1/makineler/{mid}/oee?vardiya=S24-Gece", headers=h)
    assert r.json()["data"]["kalite"] == pytest.approx(0.5)


async def test_durus_kaydi_oee_yi_deterministik_dusurur_ve_pareto(
    test_db: str, kurulu_istemci: AsyncClient
) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    mid = await _makine(kurulu_istemci, h, "S24-DRS")
    # ideal = 60sn × 100 adet = 100 dk = planlanan → P=1.0 kırpılır; OEE = A.
    await _uretim(kurulu_istemci, h, mid)

    r = await kurulu_istemci.get(f"/api/v1/makineler/{mid}/oee", headers=h)
    assert r.json()["data"]["oee"] == pytest.approx(1.0)

    # Neden + 30 dk duruş kaydı (pencere içinde).
    r = await kurulu_istemci.post(
        "/api/v1/durus-nedenleri", json={"ad": "S24 Arıza", "sinif": "plansiz"}, headers=h
    )
    assert r.status_code == 201, r.text
    neden_id = r.json()["data"]["id"]
    simdi = datetime.now(UTC)
    r = await kurulu_istemci.post(
        "/api/v1/durus-kayitlari",
        json={
            "makine_id": mid,
            "neden_id": neden_id,
            "baslangic": (simdi - timedelta(minutes=30)).isoformat(),
            "bitis": simdi.isoformat(),
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["data"]["sure_dk"] == pytest.approx(30.0)

    # OEE deterministik düşer: A = (100-30)/100 = 0.7 (P=1.0 kırpık, K=1).
    r = await kurulu_istemci.get(f"/api/v1/makineler/{mid}/oee", headers=h)
    assert r.json()["data"]["kullanilabilirlik"] == pytest.approx(0.7, abs=0.01)
    assert r.json()["data"]["oee"] == pytest.approx(0.7, abs=0.01)

    # Pareto: neden görünür + yüzdeler tutarlı.
    r = await kurulu_istemci.get("/api/v1/durus/pareto?gun=7", headers=h)
    assert r.status_code == 200
    satirlar = r.json()["data"]
    hedef = next(s for s in satirlar if s["neden"] == "S24 Arıza")
    assert hedef["toplam_dk"] == pytest.approx(30.0, abs=0.1)
    assert satirlar[-1]["kumulatif_yuzde"] == pytest.approx(100.0, abs=0.1)

    # Geçersiz aralık 422.
    r = await kurulu_istemci.post(
        "/api/v1/durus-kayitlari",
        json={
            "makine_id": mid,
            "neden_id": neden_id,
            "baslangic": simdi.isoformat(),
            "bitis": (simdi - timedelta(minutes=5)).isoformat(),
        },
        headers=h,
    )
    assert r.status_code == 422


async def test_bom_patlatma_kapaniste_stok_tuketir_ve_yetersiz_stok_kapanisi_durdurur(
    test_db: str, kurulu_istemci: AsyncClient
) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    mid = await _makine(kurulu_istemci, h, "S24-BOM")

    # Malzeme + 100 birim giriş.
    r = await kurulu_istemci.post(
        "/api/v1/malzemeler",
        json={"kod": "S24-HAM-1", "ad": "Hammadde", "birim": "kg"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    malzeme_id = r.json()["data"]["id"]
    r = await kurulu_istemci.post(
        "/api/v1/stok-hareketleri",
        json={"malzeme_id": malzeme_id, "tur": "giris", "miktar": "100"},
        headers=h,
    )
    assert r.status_code == 201, r.text

    # Ürün + reçete (1 birim ürün = 2 kg hammadde).
    r = await kurulu_istemci.post(
        "/api/v1/urunler", json={"kod": "S24-URN-1", "ad": "Mamul"}, headers=h
    )
    assert r.status_code == 201, r.text
    urun_id = r.json()["data"]["id"]
    r = await kurulu_istemci.put(
        f"/api/v1/urunler/{urun_id}/recete",
        json={"ad": "v1", "kalemler": [{"malzeme_id": malzeme_id, "miktar": "2"}]},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["kalemler"][0]["malzeme_kod"] == "S24-HAM-1"

    # Mükerrer malzeme reçetede 422.
    r = await kurulu_istemci.put(
        f"/api/v1/urunler/{urun_id}/recete",
        json={
            "kalemler": [
                {"malzeme_id": malzeme_id, "miktar": "1"},
                {"malzeme_id": malzeme_id, "miktar": "2"},
            ]
        },
        headers=h,
    )
    assert r.status_code == 422

    # İş emri (ürün ×10, lot bağlı) → kapat → 20 kg tüketilir.
    r = await kurulu_istemci.post(
        "/api/v1/is-emirleri",
        json={
            "baslik": "BOM işi",
            "makine_id": mid,
            "urun_id": urun_id,
            "miktar": "10",
            "lot_no": "S24-LOT-1",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    ie_id = r.json()["data"]["id"]
    ben = await kurulu_istemci.get("/api/v1/kimlik/ben", headers=h)
    benim_id = ben.json()["data"]["id"]
    for hedef in ("atandi", "devam_ediyor", "kapandi"):
        r = await kurulu_istemci.patch(
            f"/api/v1/is-emirleri/{ie_id}/durum",
            json={"durum": hedef, "atanan_kullanici_id": benim_id},
            headers=h,
        )
        assert r.status_code == 200, r.text

    r = await kurulu_istemci.get(f"/api/v1/malzemeler/{malzeme_id}", headers=h)
    assert r.json()["data"]["mevcut_miktar"] == pytest.approx(80.0)

    # Yetersiz stok: 100 birimlik iş (200 kg gerekir; 80 var) kapanamaz → 422; durum korunur.
    r = await kurulu_istemci.post(
        "/api/v1/is-emirleri",
        json={"baslik": "BOM büyük", "makine_id": mid, "urun_id": urun_id, "miktar": "100"},
        headers=h,
    )
    ie2 = r.json()["data"]["id"]
    for hedef in ("atandi", "devam_ediyor"):
        await kurulu_istemci.patch(
            f"/api/v1/is-emirleri/{ie2}/durum",
            json={"durum": hedef, "atanan_kullanici_id": benim_id},
            headers=h,
        )
    r = await kurulu_istemci.patch(
        f"/api/v1/is-emirleri/{ie2}/durum", json={"durum": "kapandi"}, headers=h
    )
    assert r.status_code == 422, r.text
    r = await kurulu_istemci.get(f"/api/v1/is-emirleri/{ie2}", headers=h)
    assert r.json()["data"]["durum"] == "devam_ediyor"  # kapanış geri alındı
    r = await kurulu_istemci.get(f"/api/v1/malzemeler/{malzeme_id}", headers=h)
    assert r.json()["data"]["mevcut_miktar"] == pytest.approx(80.0)  # bakiye değişmedi

    # İzlenebilirlik: lot → iş emri + üretim kaydı + tüketilen malzeme zinciri.
    await _uretim(kurulu_istemci, h, mid, lot_no="S24-LOT-1", toplam_adet=10, saglam_adet=10)
    r = await kurulu_istemci.get("/api/v1/izlenebilirlik?lot=S24-LOT-1", headers=h)
    assert r.status_code == 200, r.text
    zincir = r.json()["data"]
    assert [ie["id"] for ie in zincir["is_emirleri"]] == [ie_id]
    assert zincir["uretim"][0]["toplam_adet"] == 10
    assert zincir["tuketilen_malzemeler"][0]["malzeme_kod"] == "S24-HAM-1"
    assert zincir["tuketilen_malzemeler"][0]["miktar"] == pytest.approx(20.0)


async def test_urun_rbac_ve_tenant_izolasyonu(test_db: str, kurulu_istemci: AsyncClient) -> None:
    alfa_h = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.post(
        "/api/v1/urunler", json={"kod": "S24-IZO-1", "ad": "İzole ürün"}, headers=alfa_h
    )
    assert r.status_code == 201

    # RBAC: rolsüz kullanıcı yazamaz/okuyamaz (403).
    r = await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "s24-rolsuz@alfa.test", "parola": "Deneme12345!", "ad_soyad": "R"},
        headers=alfa_h,
    )
    assert r.status_code == 201, r.text
    rolsuz_h = await _giris(
        kurulu_istemci,
        {"slug": "alfa", "eposta": "s24-rolsuz@alfa.test", "parola": "Deneme12345!"},
    )
    r = await kurulu_istemci.get("/api/v1/urunler", headers=rolsuz_h)
    assert r.status_code == 403
    r = await kurulu_istemci.get("/api/v1/vardiyalar", headers=rolsuz_h)
    assert r.status_code == 403

    # İzolasyon: beta'da alfa ürünü kod aramasıyla görünmez.
    beta_h = await _giris(kurulu_istemci, BETA)
    r = await kurulu_istemci.get("/api/v1/urunler?arama=S24-IZO-1", headers=beta_h)
    assert r.status_code == 200 and r.json()["data"] == []
