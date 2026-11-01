"""S31 (ADR-0050) entegrasyon: sipariş → MRP → iş emri + satınalma talebi zinciri, idempotency,
görev ayrımı, RBAC, tenant izolasyonu, dış portal talebi bağlama, göç up/down."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import asyncpg
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.db import fanout
from app.modules.satis import service
from tests.conftest import ALFA, BETA, TEST_URL, onayci_basliklari

API = "/api/v1"
_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
_S30 = "a1c3e5f7b9d1"


async def _giris(istemci: AsyncClient, t: dict[str, str]) -> dict[str, str]:
    r = await istemci.post(
        f"{API}/kimlik/token",
        data={"username": t["eposta"], "password": t["parola"]},
        headers={"X-Tenant": t["slug"]},
    )
    assert r.status_code == 200, r.text
    return {"X-Tenant": t["slug"], "Authorization": f"Bearer {r.json()['data']['access_token']}"}


async def _post(istemci: AsyncClient, h: dict[str, str], yol: str, govde: dict[str, Any]) -> Any:
    r = await istemci.post(f"{API}{yol}", json=govde, headers=h)
    assert r.status_code in (200, 201), r.text
    return r.json()["data"]


async def _kurulum(istemci: AsyncClient, h: dict[str, str]) -> dict[str, int]:
    """Müşteri, makine, iki malzeme (stoklu), reçeteli ürün: 1 ürün = 2 sac + 4 civata."""
    e = uuid.uuid4().hex[:6]
    firma = await _post(istemci, h, "/firmalar", {"ad": f"S31 Müşteri {e}", "tip": "musteri"})
    makine = await _post(istemci, h, "/makineler", {"kod": f"S31-M-{e}", "ad": "Montaj"})
    sac = await _post(
        istemci, h, "/malzemeler", {"kod": f"S31-SAC-{e}", "ad": "Sac", "birim": "kg"}
    )
    civata = await _post(
        istemci, h, "/malzemeler", {"kod": f"S31-CVT-{e}", "ad": "Civata", "birim": "adet"}
    )
    await _post(
        istemci, h, "/stok-hareketleri", {"malzeme_id": sac["id"], "tur": "giris", "miktar": "30"}
    )
    await _post(
        istemci,
        h,
        "/stok-hareketleri",
        {"malzeme_id": civata["id"], "tur": "giris", "miktar": "1000"},
    )
    urun = await _post(istemci, h, "/urunler", {"kod": f"S31-URN-{e}", "ad": "Pano"})
    r = await istemci.put(
        f"{API}/urunler/{urun['id']}/recete",
        json={
            "ad": "v1",
            "kalemler": [
                {"malzeme_id": sac["id"], "miktar": "2"},
                {"malzeme_id": civata["id"], "miktar": "4"},
            ],
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    return {
        "firma": firma["id"],
        "makine": makine["id"],
        "sac": sac["id"],
        "civata": civata["id"],
        "urun": urun["id"],
    }


async def _siparis(
    istemci: AsyncClient, h: dict[str, str], k: dict[str, int], miktar: str = "25", **ek: Any
) -> dict[str, Any]:
    govde = {
        "firma_id": k["firma"],
        "teslim_tarihi": "2030-03-01",
        "kalemler": [{"urun_id": k["urun"], "miktar": miktar, "birim_fiyat": "100"}],
        **ek,
    }
    r = await istemci.post(f"{API}/satis-siparisleri", json=govde, headers=h)
    assert r.status_code == 201, r.text
    return dict(r.json()["data"])


async def test_mrp_onay_tetik_ve_idempotency(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    k = await _kurulum(kurulu_istemci, h)
    s = await _siparis(kurulu_istemci, h, k)
    assert s["kod"].startswith("SP-") and s["durum"] == "taslak" and s["tutar"] == 2500.0

    # MRP: 25 pano → 50 kg sac (stok 30 → net 20), 100 civata (stok 1000 → net 0).
    r = await kurulu_istemci.get(f"{API}/satis-siparisleri/{s['id']}/mrp", headers=h)
    assert r.status_code == 200, r.text
    m = {i["malzeme_id"]: i for i in r.json()["data"]["ihtiyaclar"]}
    assert (m[k["sac"]]["brut"], m[k["sac"]]["eldeki"], m[k["sac"]]["net"]) == (50, 30, 20)
    assert m[k["civata"]]["net"] == 0 and r.json()["data"]["eksik_sayisi"] == 1

    # Görev ayrımı: siparişi açan (admin) onaylayamaz.
    r = await kurulu_istemci.post(
        f"{API}/satis-siparisleri/{s['id']}/onayla", json={"makine_id": k["makine"]}, headers=h
    )
    assert r.status_code == 403, r.text

    onayci = await onayci_basliklari(kurulu_istemci, h, roller=("satis-onaylayan",))
    # Makine yoksa onay 422 (iş emri makinesiz açılamaz).
    r = await kurulu_istemci.post(
        f"{API}/satis-siparisleri/{s['id']}/onayla", json={}, headers=onayci
    )
    assert r.status_code == 422, r.text
    r = await kurulu_istemci.post(
        f"{API}/satis-siparisleri/{s['id']}/onayla",
        json={"makine_id": k["makine"]},
        headers=onayci,
    )
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["durum"] == "onaylandi"
    turler = sorted(t["tur"] for t in d["tetikler"])
    assert turler == ["is_emri", "satinalma_talebi"]
    st = next(t for t in d["tetikler"] if t["tur"] == "satinalma_talebi")
    assert st["durum"] == "onay_bekliyor"

    # Talep tek kalem: 20 kg sac (civata yeterli).
    r = await kurulu_istemci.get(f"{API}/satinalma-talepleri/{st['id']}", headers=h)
    assert r.status_code == 200, r.text
    kalemler = r.json()["data"]["kalemler"]
    assert [(x["malzeme_id"], x["miktar"]) for x in kalemler] == [(k["sac"], 20.0)]

    # İş emri: ürün + miktar + makine + teslim hedefi bağlı.
    ie = next(t for t in d["tetikler"] if t["tur"] == "is_emri")
    r = await kurulu_istemci.get(f"{API}/is-emirleri/{ie['id']}", headers=h)
    assert r.status_code == 200, r.text
    ie_d = r.json()["data"]
    assert (ie_d["urun_id"], float(ie_d["miktar"]), ie_d["makine_id"]) == (
        k["urun"],
        25.0,
        k["makine"],
    )

    # Onaydan sonra MRP: kendi iş emri "ayrılmış", kendi talebi "açık tedarik" sayılmaz.
    r = await kurulu_istemci.get(f"{API}/satis-siparisleri/{s['id']}/mrp", headers=h)
    m2 = {i["malzeme_id"]: i for i in r.json()["data"]["ihtiyaclar"]}
    assert (m2[k["sac"]]["ayrilmis"], m2[k["sac"]]["acik_tedarik"], m2[k["sac"]]["net"]) == (
        0,
        0,
        20,
    )

    # İkinci onay 409 (durum); tetik ikinci kez çalışsa da yeni kayıt açmaz.
    r = await kurulu_istemci.post(
        f"{API}/satis-siparisleri/{s['id']}/onayla",
        json={"makine_id": k["makine"]},
        headers=onayci,
    )
    assert r.status_code == 409


async def test_ikinci_siparis_ilk_siparisin_tuketimini_ve_talebini_gorur(
    kurulu_istemci: AsyncClient,
) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    onayci = await onayci_basliklari(kurulu_istemci, h, roller=("satis-onaylayan",))
    k = await _kurulum(kurulu_istemci, h)
    s1 = await _siparis(kurulu_istemci, h, k, miktar="10")  # 20 kg sac: stok 30'dan karşılanır
    r = await kurulu_istemci.post(
        f"{API}/satis-siparisleri/{s1['id']}/onayla",
        json={"makine_id": k["makine"]},
        headers=onayci,
    )
    assert r.status_code == 200, r.text
    assert [t["tur"] for t in r.json()["data"]["tetikler"]] == ["is_emri"]  # eksik yok → talep yok

    # İkinci sipariş 10 pano daha: 20 kg sac, ama 30'un 20'si ilk siparişin açık iş emrine ayrılmış.
    s2 = await _siparis(kurulu_istemci, h, k, miktar="10")
    r = await kurulu_istemci.get(f"{API}/satis-siparisleri/{s2['id']}/mrp", headers=h)
    sac = next(i for i in r.json()["data"]["ihtiyaclar"] if i["malzeme_id"] == k["sac"])
    assert (sac["eldeki"], sac["ayrilmis"], sac["kullanilabilir"], sac["net"]) == (30, 20, 10, 10)


async def test_tetik_yeniden_calisinca_cift_uretim_yok(
    kurulu_istemci: AsyncClient, test_engine: AsyncEngine
) -> None:
    """Servis düzeyinde: mrp_tetikle ikinci kez çağrılırsa yeni iş emri/talep açılmaz."""
    from sqlalchemy import func, select

    from app.core.db.tenancy import search_path_ayarla
    from app.kimlik.models import Kullanici
    from app.modules.isemri.models import IsEmri
    from app.modules.satis.models import SatisSiparisi
    from app.modules.stok.models import SatinalmaTalebi

    h = await _giris(kurulu_istemci, ALFA)
    onayci = await onayci_basliklari(kurulu_istemci, h, roller=("satis-onaylayan",))
    k = await _kurulum(kurulu_istemci, h)
    s = await _siparis(kurulu_istemci, h, k, miktar="40")
    r = await kurulu_istemci.post(
        f"{API}/satis-siparisleri/{s['id']}/onayla",
        json={"makine_id": k["makine"]},
        headers=onayci,
    )
    assert r.status_code == 200, r.text

    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm() as db, db.begin():
        await search_path_ayarla(db, "alfa")
        sip = await db.get(SatisSiparisi, s["id"])
        assert sip is not None
        kullanici = await db.scalar(select(Kullanici).limit(1))
        assert kullanici is not None
        once_ie = await db.scalar(select(func.count()).select_from(IsEmri))
        once_st = await db.scalar(select(func.count()).select_from(SatinalmaTalebi))
        sonuc = await service.mrp_tetikle(db, sip, kullanici, k["makine"])
        assert sonuc.yeni == 0 and len(sonuc.is_emirleri) == 1 and sonuc.satinalma_talebi
        assert await db.scalar(select(func.count()).select_from(IsEmri)) == once_ie
        assert await db.scalar(select(func.count()).select_from(SatinalmaTalebi)) == once_st


async def test_dogrulama_rbac_izolasyon_ve_durumlar(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    k = await _kurulum(kurulu_istemci, h)

    # "Her ikisi" tipindeki firma müşteri sayılır.
    iki = await _post(kurulu_istemci, h, "/firmalar", {"ad": "S31 İkisi", "tip": "her_ikisi"})
    r = await kurulu_istemci.post(
        f"{API}/satis-siparisleri",
        json={
            "firma_id": iki["id"],
            "teslim_tarihi": "2030-03-01",
            "kalemler": [{"urun_id": k["urun"], "miktar": "1"}],
        },
        headers=h,
    )
    assert r.status_code == 201, r.text

    # Tedarikçi firmaya satış siparişi açılmaz; olmayan ürün 404.
    ted = await _post(kurulu_istemci, h, "/firmalar", {"ad": "S31 Tedarikçi", "tip": "tedarikci"})
    r = await kurulu_istemci.post(
        f"{API}/satis-siparisleri",
        json={
            "firma_id": ted["id"],
            "teslim_tarihi": "2030-03-01",
            "kalemler": [{"urun_id": k["urun"], "miktar": "1"}],
        },
        headers=h,
    )
    assert r.status_code == 422, r.text
    r = await kurulu_istemci.post(
        f"{API}/satis-siparisleri",
        json={
            "firma_id": k["firma"],
            "teslim_tarihi": "2030-03-01",
            "kalemler": [{"urun_id": 999999, "miktar": "1"}],
        },
        headers=h,
    )
    assert r.status_code == 404
    r = await kurulu_istemci.post(
        f"{API}/satis-siparisleri",
        json={"firma_id": k["firma"], "teslim_tarihi": "2030-03-01", "kalemler": []},
        headers=h,
    )
    assert r.status_code == 422

    s = await _siparis(kurulu_istemci, h, k, miktar="1")
    # RBAC: izleyici okur, yazamaz; satış temsilcisi hazırlar ama onaylayamaz.
    izleyici = await onayci_basliklari(kurulu_istemci, h, roller=("izleyici",))
    r = await kurulu_istemci.get(f"{API}/satis-siparisleri/{s['id']}", headers=izleyici)
    assert r.status_code in (200, 403)
    r = await kurulu_istemci.put(
        f"{API}/satis-siparisleri/{s['id']}", json={"aciklama": "x"}, headers=izleyici
    )
    assert r.status_code == 403
    temsilci = await onayci_basliklari(kurulu_istemci, h, roller=("satis",))
    r = await kurulu_istemci.post(
        f"{API}/satis-siparisleri/{s['id']}/onayla",
        json={"makine_id": k["makine"]},
        headers=temsilci,
    )
    assert r.status_code == 403

    # Tenant izolasyonu.
    beta = await _giris(kurulu_istemci, BETA)
    r = await kurulu_istemci.get(f"{API}/satis-siparisleri/{s['id']}", headers=beta)
    assert r.status_code == 404
    r = await kurulu_istemci.get(f"{API}/satis-siparisleri", headers=beta)
    assert all(x["id"] != s["id"] for x in r.json()["data"])

    # Durumlar: taslaktan sevk 409; onay ayrı uçtan; taslak iptal edilir, sonra düzenlenemez.
    r = await kurulu_istemci.post(
        f"{API}/satis-siparisleri/{s['id']}/durum", json={"durum": "sevk_edildi"}, headers=h
    )
    assert r.status_code == 409
    r = await kurulu_istemci.post(
        f"{API}/satis-siparisleri/{s['id']}/durum", json={"durum": "onaylandi"}, headers=h
    )
    assert r.status_code == 409
    r = await kurulu_istemci.post(
        f"{API}/satis-siparisleri/{s['id']}/durum", json={"durum": "iptal"}, headers=h
    )
    assert r.status_code == 200 and r.json()["data"]["durum"] == "iptal"
    r = await kurulu_istemci.put(
        f"{API}/satis-siparisleri/{s['id']}", json={"aciklama": "x"}, headers=h
    )
    assert r.status_code == 409


async def test_onayli_siparis_sevk_kapanis_ve_portal_talebi(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    onayci = await onayci_basliklari(kurulu_istemci, h, roller=("satis-onaylayan",))
    k = await _kurulum(kurulu_istemci, h)
    talep = await _post(
        kurulu_istemci,
        h,
        "/talepler",
        {"baslik": "Teklif: 5 pano", "tur": "teklif", "firma_id": k["firma"]},
    )
    s = await _siparis(
        kurulu_istemci, h, k, miktar="5", talep_id=talep["id"], makine_id=k["makine"]
    )
    assert s["talep_id"] == talep["id"]
    # Aynı talep ikinci siparişe dönüşmez.
    r = await kurulu_istemci.post(
        f"{API}/satis-siparisleri",
        json={
            "firma_id": k["firma"],
            "teslim_tarihi": "2030-03-01",
            "talep_id": talep["id"],
            "kalemler": [{"urun_id": k["urun"], "miktar": "1"}],
        },
        headers=h,
    )
    assert r.status_code == 409

    r = await kurulu_istemci.post(
        f"{API}/satis-siparisleri/{s['id']}/onayla", json={}, headers=onayci
    )
    assert r.status_code == 200, r.text  # makine siparişten
    for hedef in ("sevk_edildi", "kapandi"):
        r = await kurulu_istemci.post(
            f"{API}/satis-siparisleri/{s['id']}/durum", json={"durum": hedef}, headers=h
        )
        assert r.status_code == 200, r.text
    r = await kurulu_istemci.get(f"{API}/satis/ozet", headers=h)
    assert r.status_code == 200 and r.json()["data"]["kapandi"] >= 1


async def _tablo(t: str) -> bool:
    conn = await asyncpg.connect(_DSN)
    try:
        return bool(await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", f"tenant_alfa.{t}"))
    finally:
        await conn.close()


async def test_s31_goc_up_down(test_db: str) -> None:
    tablolar = ("satis_siparisleri", "satis_siparisi_kalemleri", "mrp_tetikleri")
    assert all([await _tablo(t) for t in tablolar])
    await asyncio.to_thread(fanout.tenant_indir_tek, "alfa", _S30, db_url=TEST_URL)
    assert not any([await _tablo(t) for t in tablolar])
    await asyncio.to_thread(fanout.tenant_yukselt_tek, "alfa", "head", db_url=TEST_URL)
    assert all([await _tablo(t) for t in tablolar])
