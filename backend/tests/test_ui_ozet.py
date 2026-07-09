"""UI planı (uiplani.md) özet uçları — ``/<kaynak>/ozet`` sayaç doğruluğu + RBAC 403.

Her uç tenant-izole (``search_path``) + ``<modul>:oku`` korumalı, salt-okunur toplulaştırma.
Beta tenant izole sayaç için, alfa RBAC negatif senaryosu için kullanılır.
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

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


async def _rolsuz_kullanici(istemci: AsyncClient, admin_h: dict, roller: list[str]) -> dict:
    """Verilen rollerle yeni kullanıcı açar ve giriş header'ını döndürür (RBAC negatif test)."""
    eposta = f"r-{uuid4().hex[:8]}@alfa.test"
    r = await istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": eposta, "parola": "Gecici123!", "roller": roller},
        headers=admin_h,
    )
    assert r.status_code in (200, 201), r.text
    return _h(
        "alfa", await _giris(istemci, {"slug": "alfa", "eposta": eposta, "parola": "Gecici123!"})
    )


# --------------------------------------------------------------------------- Üretim
async def test_uretim_ozet_sayaclar(kurulu_istemci: AsyncClient) -> None:
    h = _h("beta", await _giris(kurulu_istemci, BETA))
    kod = f"OZ-{uuid4().hex[:6]}"
    mr = await kurulu_istemci.post(
        "/api/v1/makineler", json={"kod": kod, "ad": "Özet Makine", "oee_hedefi": 0.85}, headers=h
    )
    assert mr.status_code == 201, mr.text
    mid = mr.json()["data"]["id"]
    await kurulu_istemci.patch(f"/api/v1/makineler/{mid}/durum", json={"durum": "ariza"}, headers=h)
    await kurulu_istemci.post(
        "/api/v1/uretim-verileri",
        json={
            "makine_id": mid,
            "planlanan_sure_dk": 480,
            "durus_sure_dk": 30,
            "toplam_adet": 1000,
            "saglam_adet": 960,
            "ideal_cevrim_sn": 25,
        },
        headers=h,
    )

    r = await kurulu_istemci.get("/api/v1/uretim/ozet", headers=h)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert veri["toplam_makine"] >= 1
    assert veri["arizali"] >= 1
    assert veri["uretimli_makine"] >= 1
    assert 0.0 < veri["ortalama_oee"] <= 1.0
    durumlar = {d["durum"] for d in veri["durum_dagilimi"]}
    assert {"calisiyor", "durdu", "bakimda", "ariza"} <= durumlar


async def test_uretim_ozet_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    dok = await _rolsuz_kullanici(kurulu_istemci, admin, ["dokuman"])  # uretim:oku yok
    r = await kurulu_istemci.get("/api/v1/uretim/ozet", headers=dok)
    assert r.status_code == 403, r.text


# --------------------------------------------------------------------------- Stok
async def test_stok_ozet_sayaclar(kurulu_istemci: AsyncClient) -> None:
    h = _h("beta", await _giris(kurulu_istemci, BETA))
    kod = f"MZ-{uuid4().hex[:6]}"
    mr = await kurulu_istemci.post(
        "/api/v1/malzemeler",
        json={
            "kod": kod,
            "ad": "Kritik Malzeme",
            "birim": "adet",
            "kategori": f"kat-{uuid4().hex[:4]}",
            "min_stok": 10,
            "kritik_stok": 5,
        },
        headers=h,
    )
    assert mr.status_code == 201, mr.text  # mevcut 0 ≤ kritik 5 → kritik altı

    r = await kurulu_istemci.get("/api/v1/stok/ozet", headers=h)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert veri["toplam_malzeme"] >= 1
    assert veri["kritik_alti"] >= 1
    assert veri["min_alti"] >= 1
    assert veri["kategori_sayisi"] >= 1


async def test_stok_ozet_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    dok = await _rolsuz_kullanici(kurulu_istemci, admin, ["dokuman"])  # stok:oku yok
    r = await kurulu_istemci.get("/api/v1/stok/ozet", headers=dok)
    assert r.status_code == 403, r.text


# --------------------------------------------------------------------------- Satınalma
async def test_satinalma_ozet_sayaclar(kurulu_istemci: AsyncClient) -> None:
    h = _h("beta", await _giris(kurulu_istemci, BETA))
    mr = await kurulu_istemci.post(
        "/api/v1/malzemeler",
        json={"kod": f"SM-{uuid4().hex[:6]}", "ad": "Sipariş Malzeme", "birim": "adet"},
        headers=h,
    )
    mid = mr.json()["data"]["id"]
    tr = await kurulu_istemci.post(
        "/api/v1/satinalma-talepleri",
        json={
            "baslik": "Özet Talep",
            "kalemler": [{"malzeme_id": mid, "miktar": 3, "birim": "adet"}],
        },
        headers=h,
    )
    assert tr.status_code == 201, tr.text  # taslak

    r = await kurulu_istemci.get("/api/v1/satinalma/ozet", headers=h)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert veri["toplam"] >= 1
    assert veri["taslak"] >= 1
    assert any(d["durum"] == "taslak" for d in veri["durum_dagilimi"])


async def test_satinalma_ozet_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    dok = await _rolsuz_kullanici(kurulu_istemci, admin, ["dokuman"])  # satinalma:oku yok
    r = await kurulu_istemci.get("/api/v1/satinalma/ozet", headers=dok)
    assert r.status_code == 403, r.text


# --------------------------------------------------------------------------- Kalite / CAPA
async def test_kalite_ozet_sayaclar(kurulu_istemci: AsyncClient) -> None:
    h = _h("beta", await _giris(kurulu_istemci, BETA))
    ur = await kurulu_istemci.post(
        "/api/v1/uygunsuzluklar",
        json={"baslik": "Özet uygunsuzluk", "onem": "orta"},
        headers=h,
    )
    assert ur.status_code == 201, ur.text  # yeni → durum "acik"
    await kurulu_istemci.post("/api/v1/kalite-kontrolleri", json={"sonuc": "gecti"}, headers=h)

    r = await kurulu_istemci.get("/api/v1/kalite/ozet", headers=h)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert veri["toplam_uygunsuzluk"] >= 1
    assert veri["acik_uygunsuzluk"] >= 1
    assert veri["toplam_kontrol"] >= 1
    assert 0.0 <= veri["gecti_orani"] <= 1.0


async def test_kalite_ozet_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    dok = await _rolsuz_kullanici(kurulu_istemci, admin, ["dokuman"])  # kalite:oku yok
    r = await kurulu_istemci.get("/api/v1/kalite/ozet", headers=dok)
    assert r.status_code == 403, r.text


# --------------------------------------------------------------------------- İK
async def test_ik_ozet_sayaclar(kurulu_istemci: AsyncClient) -> None:
    h = _h("beta", await _giris(kurulu_istemci, BETA))
    pr = await kurulu_istemci.post(
        "/api/v1/personeller",
        json={"sicil_no": f"P-{uuid4().hex[:6]}", "ad": "Ada", "soyad": "Soyad"},
        headers=h,
    )
    assert pr.status_code == 201, pr.text

    r = await kurulu_istemci.get("/api/v1/ik/ozet", headers=h)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert veri["toplam_personel"] >= 1
    assert veri["aktif_personel"] >= 1


async def test_ik_ozet_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    dok = await _rolsuz_kullanici(kurulu_istemci, admin, ["dokuman"])  # ik:oku yok
    r = await kurulu_istemci.get("/api/v1/ik/ozet", headers=dok)
    assert r.status_code == 403, r.text


# --------------------------------------------------------------------------- Sözleşme
async def test_sozlesme_ozet_sayaclar(kurulu_istemci: AsyncClient) -> None:
    h = _h("beta", await _giris(kurulu_istemci, BETA))
    fr = await kurulu_istemci.post(
        "/api/v1/firmalar", json={"ad": f"F-{uuid4().hex[:6]}"}, headers=h
    )
    fid = fr.json()["data"]["id"]
    yakin = (date.today() + timedelta(days=15)).isoformat()
    sr = await kurulu_istemci.post(
        "/api/v1/sozlesmeler",
        json={
            "firma_id": fid,
            "baslik": "Özet sözleşme",
            "baslangic_tarihi": "2026-01-01",
            "bitis_tarihi": yakin,
        },
        headers=h,
    )
    assert sr.status_code == 201, sr.text
    sid = sr.json()["data"]["id"]
    await kurulu_istemci.patch(
        f"/api/v1/sozlesmeler/{sid}/durum", json={"durum": "aktif"}, headers=h
    )

    r = await kurulu_istemci.get("/api/v1/sozlesme/ozet", headers=h)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert veri["toplam"] >= 1
    assert veri["aktif"] >= 1
    assert veri["yaklasan"] >= 1


async def test_sozlesme_ozet_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    dok = await _rolsuz_kullanici(kurulu_istemci, admin, ["dokuman"])  # sozlesme:oku yok
    r = await kurulu_istemci.get("/api/v1/sozlesme/ozet", headers=dok)
    assert r.status_code == 403, r.text


# --------------------------------------------------------------------------- İSG
async def test_isg_ozet_sayaclar(kurulu_istemci: AsyncClient) -> None:
    h = _h("beta", await _giris(kurulu_istemci, BETA))
    rr = await kurulu_istemci.post(
        "/api/v1/risk-degerlendirmeleri",
        json={"baslik": "Özet risk", "olasilik": 5, "siddet": 5},
        headers=h,
    )
    assert rr.status_code == 201, rr.text  # 5×5=25 → cok_yuksek
    await kurulu_istemci.post(
        "/api/v1/is-kazalari", json={"tur": "kaza", "kaybedilen_gun": 3}, headers=h
    )

    r = await kurulu_istemci.get("/api/v1/isg/ozet", headers=h)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert veri["toplam_risk"] >= 1
    assert veri["yuksek_risk"] >= 1
    assert veri["bu_yil_kaza"] >= 1
    assert veri["toplam_kayip_gun"] >= 3
    assert any(c["olasilik"] == 5 and c["siddet"] == 5 for c in veri["risk_matrisi"])


async def test_isg_ozet_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    dok = await _rolsuz_kullanici(kurulu_istemci, admin, ["dokuman"])  # isg:oku yok
    r = await kurulu_istemci.get("/api/v1/isg/ozet", headers=dok)
    assert r.status_code == 403, r.text


# --------------------------------------------------------------------------- Bakım
async def test_bakim_ozet(kurulu_istemci: AsyncClient) -> None:
    h = _h("beta", await _giris(kurulu_istemci, BETA))
    mr = await kurulu_istemci.post(
        "/api/v1/makineler", json={"kod": f"BM-{uuid4().hex[:6]}", "ad": "Bakım Makine"}, headers=h
    )
    mid = mr.json()["data"]["id"]
    await kurulu_istemci.post(
        "/api/v1/bakim-planlari",
        json={"makine_id": mid, "ad": "Aylık", "tip": "periyodik"},
        headers=h,
    )
    r = await kurulu_istemci.get("/api/v1/bakim/ozet", headers=h)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert veri["toplam_plan"] >= 1
    assert veri["aktif_plan"] >= 1

    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    dok = await _rolsuz_kullanici(kurulu_istemci, admin, ["dokuman"])
    assert (await kurulu_istemci.get("/api/v1/bakim/ozet", headers=dok)).status_code == 403


# --------------------------------------------------------------------------- Saha
async def test_saha_ozet(kurulu_istemci: AsyncClient) -> None:
    h = _h("beta", await _giris(kurulu_istemci, BETA))
    await kurulu_istemci.post(
        "/api/v1/saha/cihazlar",
        json={"kod": f"SC-{uuid4().hex[:6]}", "ad": "Gateway"},
        headers=h,
    )
    r = await kurulu_istemci.get("/api/v1/saha/ozet", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["toplam_cihaz"] >= 1

    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    dok = await _rolsuz_kullanici(kurulu_istemci, admin, ["dokuman"])
    assert (await kurulu_istemci.get("/api/v1/saha/ozet", headers=dok)).status_code == 403


# --------------------------------------------------------------------------- Talep
async def test_talep_ozet(kurulu_istemci: AsyncClient) -> None:
    h = _h("beta", await _giris(kurulu_istemci, BETA))
    await kurulu_istemci.post("/api/v1/talepler", json={"baslik": "Özet talep"}, headers=h)
    r = await kurulu_istemci.get("/api/v1/talep/ozet", headers=h)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert veri["toplam"] >= 1
    assert veri["acik"] >= 1

    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    dok = await _rolsuz_kullanici(kurulu_istemci, admin, ["dokuman"])
    assert (await kurulu_istemci.get("/api/v1/talep/ozet", headers=dok)).status_code == 403


# --------------------------------------------------------------------------- DYS
async def test_dys_ozet(kurulu_istemci: AsyncClient) -> None:
    h = _h("beta", await _giris(kurulu_istemci, BETA))
    await kurulu_istemci.post(
        "/api/v1/belgeler", json={"ad": "Özet belge", "kategori": f"k-{uuid4().hex[:4]}"}, headers=h
    )
    r = await kurulu_istemci.get("/api/v1/dys/ozet", headers=h)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert veri["toplam_belge"] >= 1
    assert veri["kategori_sayisi"] >= 1

    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    dok = await _rolsuz_kullanici(kurulu_istemci, admin, ["isg"])  # dys:oku yok
    assert (await kurulu_istemci.get("/api/v1/dys/ozet", headers=dok)).status_code == 403


# --------------------------------------------------------------------------- Kullanıcı
async def test_kullanici_ozet(kurulu_istemci: AsyncClient) -> None:
    h = _h("beta", await _giris(kurulu_istemci, BETA))
    r = await kurulu_istemci.get("/api/v1/kullanicilar/ozet", headers=h)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert veri["toplam"] >= 1
    assert veri["aktif"] >= 1

    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    dok = await _rolsuz_kullanici(kurulu_istemci, admin, ["dokuman"])  # kullanici:oku yok
    assert (await kurulu_istemci.get("/api/v1/kullanicilar/ozet", headers=dok)).status_code == 403


# --------------------------------------------------------------------------- Enerji
async def test_enerji_ozet(kurulu_istemci: AsyncClient) -> None:
    h = _h("beta", await _giris(kurulu_istemci, BETA))
    await kurulu_istemci.post(
        "/api/v1/enerji-tuketimleri",
        json={"enerji_turu": "elektrik", "tuketim": 120, "birim": "kWh"},
        headers=h,
    )
    r = await kurulu_istemci.get("/api/v1/enerji/ozet", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["toplam_kayit"] >= 1

    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    dok = await _rolsuz_kullanici(kurulu_istemci, admin, ["dokuman"])
    assert (await kurulu_istemci.get("/api/v1/enerji/ozet", headers=dok)).status_code == 403
