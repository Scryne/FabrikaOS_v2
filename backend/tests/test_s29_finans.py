"""S29 (ADR-0048) entegrasyon: fatura yaşam döngüsü, cari bakiye, tahsilat/ödeme, eşzamanlılık,
RBAC + görev ayrımı, tenant izolasyonu, raporlar, e-Fatura iskeleti, göç up/down."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import asyncpg
from httpx import AsyncClient

from app.core.db import fanout
from tests.conftest import ALFA, BETA, TEST_URL, onayci_basliklari

API = "/api/v1"
_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
_S28 = "e6b8d0f2a4c6"


async def _giris(istemci: AsyncClient, t: dict[str, str]) -> dict[str, str]:
    r = await istemci.post(
        f"{API}/kimlik/token",
        data={"username": t["eposta"], "password": t["parola"]},
        headers={"X-Tenant": t["slug"]},
    )
    assert r.status_code == 200, r.text
    return {"X-Tenant": t["slug"], "Authorization": f"Bearer {r.json()['data']['access_token']}"}


async def _firma(istemci: AsyncClient, h: dict[str, str], tip: str = "musteri") -> int:
    r = await istemci.post(
        f"{API}/firmalar",
        json={"ad": f"S29 Firma {uuid.uuid4().hex[:6]}", "tip": tip, "vergi_no": "1234567890"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return int(r.json()["data"]["id"])


async def _fatura(
    istemci: AsyncClient,
    h: dict[str, str],
    firma_id: int,
    *,
    tur: str = "satis",
    tarih: str = "2026-10-01",
    vade_gun: int = 30,
) -> dict[str, Any]:
    r = await istemci.post(
        f"{API}/faturalar",
        json={
            "tur": tur,
            "firma_id": firma_id,
            "fatura_tarihi": tarih,
            "vade_gun": vade_gun,
            "kalemler": [
                {"aciklama": "Sac kesim hizmeti", "miktar": "3", "birim_fiyat": "33.335"},
                {"aciklama": "Nakliye", "miktar": "1", "birim_fiyat": "50", "kdv_orani": 10},
            ],
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    return dict(r.json()["data"])


async def _kesilmis(
    istemci: AsyncClient, h: dict[str, str], onayci: dict[str, str], firma_id: int, **kw: Any
) -> dict[str, Any]:
    f = await _fatura(istemci, h, firma_id, **kw)
    assert (await istemci.post(f"{API}/faturalar/{f['id']}/gonder", headers=h)).status_code == 200
    r = await istemci.post(f"{API}/faturalar/{f['id']}/kes", headers=onayci)
    assert r.status_code == 200, r.text
    return dict(r.json()["data"])


async def _bakiye(istemci: AsyncClient, h: dict[str, str], firma_id: int) -> float:
    r = await istemci.get(f"{API}/cari-hesaplar/{firma_id}/ekstre", headers=h)
    assert r.status_code == 200, r.text
    return float(r.json()["data"]["bakiye"])


async def _onayci(istemci: AsyncClient, h: dict[str, str]) -> dict[str, str]:
    return await onayci_basliklari(istemci, h, roller=("finans-onaylayan",))


async def test_fatura_toplamlari_kesim_ve_gorev_ayrimi(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    firma = await _firma(kurulu_istemci, h)
    f = await _fatura(kurulu_istemci, h, firma)
    # 3 × 33,335 = 100,005 → 100,01 (+%20 = 20,00); 50 (+%10 = 5,00)
    assert (f["ara_toplam"], f["kdv_toplam"], f["genel_toplam"]) == (150.01, 25.0, 175.01)
    assert f["kod"].startswith("FT-2026-") and f["durum"] == "taslak"
    assert f["vade_tarihi"] == "2026-10-31"

    # Taslak doğrudan kesilmez; onaya gönderilir; hazırlayan kesemez; başka onaycı keser.
    onayci = await _onayci(kurulu_istemci, h)
    r = await kurulu_istemci.post(f"{API}/faturalar/{f['id']}/kes", headers=onayci)
    assert r.status_code == 409, r.text
    await kurulu_istemci.post(f"{API}/faturalar/{f['id']}/gonder", headers=h)
    r = await kurulu_istemci.post(f"{API}/faturalar/{f['id']}/kes", headers=h)
    assert r.status_code == 403, r.text
    r = await kurulu_istemci.post(f"{API}/faturalar/{f['id']}/kes", headers=onayci)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["durum"] == "kesildi"
    assert await _bakiye(kurulu_istemci, h, firma) == 175.01  # firma bize borçlu

    # Kesilmiş fatura düzenlenemez.
    r = await kurulu_istemci.patch(
        f"{API}/faturalar/{f['id']}", json={"aciklama": "değişti"}, headers=h
    )
    assert r.status_code == 409


async def test_tahsilat_kismi_tam_fazla_ve_idempotent(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    onayci = await _onayci(kurulu_istemci, h)
    firma = await _firma(kurulu_istemci, h)
    f = await _kesilmis(kurulu_istemci, h, onayci, firma)

    def odeme(tutar: str) -> dict[str, Any]:
        return {
            "tur": "tahsilat",
            "firma_id": firma,
            "fatura_id": f["id"],
            "tutar": tutar,
            "tarih": "2026-10-15",
        }

    anahtar = {"Idempotency-Key": f"s29-{uuid.uuid4().hex}"}
    r = await kurulu_istemci.post(f"{API}/odemeler", json=odeme("100"), headers={**h, **anahtar})
    assert r.status_code == 201, r.text
    ilk = r.json()["data"]
    assert ilk["kod"].startswith("TH-2026-")
    # Aynı istek yeniden (ağ kopması): ikinci ödeme açılmaz, bakiye bir kez düşer.
    r = await kurulu_istemci.post(f"{API}/odemeler", json=odeme("100"), headers={**h, **anahtar})
    assert r.status_code == 200 and r.json()["data"]["id"] == ilk["id"]
    assert await _bakiye(kurulu_istemci, h, firma) == 75.01

    r = await kurulu_istemci.post(f"{API}/odemeler", json=odeme("75.02"), headers=h)
    assert r.status_code == 422 and r.json()["hata_kodu"] == "ODEME_FAZLA"
    r = await kurulu_istemci.post(f"{API}/odemeler", json=odeme("75.01"), headers=h)
    assert r.status_code == 201, r.text
    detay = (await kurulu_istemci.get(f"{API}/faturalar/{f['id']}", headers=h)).json()["data"]
    assert detay["durum"] == "kapandi" and detay["acik_tutar"] == 0
    assert await _bakiye(kurulu_istemci, h, firma) == 0
    # Kapanmış faturaya ödeme bağlanmaz.
    r = await kurulu_istemci.post(f"{API}/odemeler", json=odeme("1"), headers=h)
    assert r.status_code == 409


async def test_esanli_tahsilat_fazla_odemeye_izin_vermez(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    onayci = await _onayci(kurulu_istemci, h)
    firma = await _firma(kurulu_istemci, h)
    f = await _kesilmis(kurulu_istemci, h, onayci, firma)
    govde = {"tur": "tahsilat", "firma_id": firma, "fatura_id": f["id"], "tutar": "120"}
    sonuc = await asyncio.gather(
        *(
            kurulu_istemci.post(f"{API}/odemeler", json={**govde, "tarih": "2026-10-20"}, headers=h)
            for _ in range(2)
        )
    )
    assert sorted(r.status_code for r in sonuc) == [201, 422]  # 2 × 120 > 175,01
    assert await _bakiye(kurulu_istemci, h, firma) == 55.01  # yalnız biri işlendi


async def test_alis_faturasi_odeme_onay_ister_ve_iptal_cariyi_geri_alir(
    kurulu_istemci: AsyncClient,
) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    onayci = await _onayci(kurulu_istemci, h)
    tedarikci = await _firma(kurulu_istemci, h, tip="tedarikci")
    f = await _kesilmis(kurulu_istemci, h, onayci, tedarikci, tur="alis")
    assert await _bakiye(kurulu_istemci, h, tedarikci) == -175.01  # biz borçluyuz

    # finans rolü (onaysız) firmaya ödeme kaydedemez; onaycı kaydeder.
    finansci = await onayci_basliklari(kurulu_istemci, h, roller=("finans",))
    odeme = {"tur": "odeme", "firma_id": tedarikci, "tutar": "50", "tarih": "2026-10-10"}
    assert (
        await kurulu_istemci.post(f"{API}/odemeler", json=odeme, headers=finansci)
    ).status_code == 403
    # Tahsilat alış faturasına bağlanmaz.
    yanlis = {**odeme, "tur": "tahsilat", "fatura_id": f["id"]}
    assert (await kurulu_istemci.post(f"{API}/odemeler", json=yanlis, headers=h)).status_code == 422

    # Ödemesiz kesilmiş fatura nedenle iptal edilir; cari geri alınır.
    r = await kurulu_istemci.post(f"{API}/faturalar/{f['id']}/iptal", json={}, headers=onayci)
    assert r.status_code == 422  # neden zorunlu
    r = await kurulu_istemci.post(
        f"{API}/faturalar/{f['id']}/iptal", json={"neden": "Yanlış tedarikçi"}, headers=onayci
    )
    assert r.status_code == 200, r.text
    assert await _bakiye(kurulu_istemci, h, tedarikci) == 0

    # Ödemesi olan fatura iptal edilemez.
    g = await _kesilmis(kurulu_istemci, h, onayci, tedarikci, tur="alis")
    r = await kurulu_istemci.post(
        f"{API}/odemeler", json={**odeme, "fatura_id": g["id"]}, headers=onayci
    )
    assert r.status_code == 201, r.text
    r = await kurulu_istemci.post(
        f"{API}/faturalar/{g['id']}/iptal", json={"neden": "x"}, headers=onayci
    )
    assert r.status_code == 409


async def test_iade_ve_onaylarim(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    onayci = await _onayci(kurulu_istemci, h)
    firma = await _firma(kurulu_istemci, h)
    f = await _fatura(kurulu_istemci, h, firma)
    await kurulu_istemci.post(f"{API}/faturalar/{f['id']}/gonder", headers=h)

    kutu = (await kurulu_istemci.get(f"{API}/onaylarim", headers=onayci)).json()["data"]
    kalem = next(k for k in kutu["kalemler"] if k["tur"] == "fatura" and k["id"] == f["id"])
    assert kalem["red_gerekce_zorunlu"] is True and "TRY" in kalem["ozet"]
    kendi = (await kurulu_istemci.get(f"{API}/onaylarim", headers=h)).json()["data"]
    assert ("fatura", f["id"]) not in {(k["tur"], k["id"]) for k in kendi["kalemler"]}

    # Onaylarım'ın red düğmesi ``red_nedeni`` gönderir: iade nedeni olarak kaydedilir.
    r = await kurulu_istemci.post(
        API + kalem["red_yolu"], json={"red_nedeni": "Vade 60 gün olmalı"}, headers=onayci
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["durum"] == "taslak"
    assert r.json()["data"]["iade_nedeni"] == "Vade 60 gün olmalı"
    r = await kurulu_istemci.patch(f"{API}/faturalar/{f['id']}", json={"vade_gun": 60}, headers=h)
    assert r.status_code == 200 and r.json()["data"]["iade_nedeni"] == ""


async def test_rbac_izolasyon_ve_liste(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    firma = await _firma(kurulu_istemci, h)
    f = await _fatura(kurulu_istemci, h, firma)
    izleyici = await onayci_basliklari(kurulu_istemci, h, roller=("izleyici",))
    assert (await kurulu_istemci.get(f"{API}/faturalar", headers=izleyici)).status_code == 200
    r = await kurulu_istemci.post(
        f"{API}/faturalar",
        json={
            "tur": "satis",
            "firma_id": firma,
            "fatura_tarihi": "2026-10-01",
            "kalemler": [{"aciklama": "x", "miktar": "1", "birim_fiyat": "1"}],
        },
        headers=izleyici,
    )
    assert r.status_code == 403

    beta = await _giris(kurulu_istemci, BETA)
    assert (await kurulu_istemci.get(f"{API}/faturalar/{f['id']}", headers=beta)).status_code == 404
    liste = (await kurulu_istemci.get(f"{API}/faturalar?arama={f['kod']}", headers=h)).json()
    assert [x["id"] for x in liste["data"]] == [f["id"]]
    # Geçersiz KDV oranı ve boş kalem.
    r = await kurulu_istemci.post(
        f"{API}/faturalar",
        json={
            "tur": "satis",
            "firma_id": firma,
            "fatura_tarihi": "2026-10-01",
            "kalemler": [{"aciklama": "x", "miktar": "1", "birim_fiyat": "1", "kdv_orani": 18}],
        },
        headers=h,
    )
    assert r.status_code == 422


async def test_ekstre_yaslandirma_ozet(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    onayci = await _onayci(kurulu_istemci, h)
    firma = await _firma(kurulu_istemci, h)
    eski = await _kesilmis(kurulu_istemci, h, onayci, firma, tarih="2026-06-01", vade_gun=0)
    await _kesilmis(kurulu_istemci, h, onayci, firma, tarih="2026-10-25", vade_gun=30)
    r = await kurulu_istemci.post(
        f"{API}/odemeler",
        json={"tur": "tahsilat", "firma_id": firma, "tutar": "25.01", "tarih": "2026-10-28"},
        headers=h,
    )
    assert r.status_code == 201

    e = (
        await kurulu_istemci.get(
            f"{API}/cari-hesaplar/{firma}/ekstre?baslangic=2026-10-01&bitis=2026-12-31", headers=h
        )
    ).json()["data"]
    assert e["acilis_bakiyesi"] == 175.01  # haziran faturası açılışta
    assert [round(x["bakiye_sonrasi"], 2) for x in e["hareketler"]] == [350.02, 325.01]
    assert e["hareketler"][1]["alacak"] == 25.01

    y = (await kurulu_istemci.get(f"{API}/finans/yaslandirma", headers=h)).json()["data"]
    satir = next(x for x in y["alacak"]["firmalar"] if x["firma_id"] == firma)
    assert satir["gun_90_ustu"] == 175.01  # vade 2026-06-01, bugün ≥ 2026-11-01
    assert satir["toplam"] == 350.02  # cariye bağlanmamış tahsilat faturaları kapatmaz
    assert eski["vade_tarihi"] == "2026-06-01"

    o = (await kurulu_istemci.get(f"{API}/finans/ozet", headers=h)).json()["data"]
    assert o["vadesi_gecen_alacak"] >= 175.01


async def test_maliyet_siparis_fiyatindan_ve_eksik_fiyat(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    ek = uuid.uuid4().hex[:5]
    makine = (
        await kurulu_istemci.post(
            f"{API}/makineler", json={"kod": f"S29-M-{ek}", "ad": "Pres"}, headers=h
        )
    ).json()["data"]["id"]
    malzemeler = []
    for kod in ("FIYATLI", "FIYATSIZ"):
        r = await kurulu_istemci.post(
            f"{API}/malzemeler",
            json={"kod": f"S29-{kod}-{ek}", "ad": kod, "birim": "kg"},
            headers=h,
        )
        mid = r.json()["data"]["id"]
        malzemeler.append(mid)
        await kurulu_istemci.post(
            f"{API}/stok-hareketleri",
            json={"malzeme_id": mid, "tur": "giris", "miktar": "100"},
            headers=h,
        )
    # Fiyat kaynağı: satınalma talebindeki tahmini fiyat (siparişsiz).
    r = await kurulu_istemci.post(
        f"{API}/satinalma-talepleri",
        json={
            "baslik": "Fiyat",
            "kalemler": [
                {
                    "malzeme_id": malzemeler[0],
                    "miktar": 1,
                    "birim": "kg",
                    "tahmini_birim_fiyat": 12.5,
                }
            ],
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    urun = (
        await kurulu_istemci.post(
            f"{API}/urunler", json={"kod": f"S29-U-{ek}", "ad": "Mamul"}, headers=h
        )
    ).json()["data"]["id"]
    await kurulu_istemci.put(
        f"{API}/urunler/{urun}/recete",
        json={
            "kalemler": [
                {"malzeme_id": malzemeler[0], "miktar": "2"},
                {"malzeme_id": malzemeler[1], "miktar": "1"},
            ]
        },
        headers=h,
    )
    ie = (
        await kurulu_istemci.post(
            f"{API}/is-emirleri",
            json={"baslik": "Maliyet", "makine_id": makine, "urun_id": urun, "miktar": "4"},
            headers=h,
        )
    ).json()["data"]["id"]
    ben = (await kurulu_istemci.get(f"{API}/kimlik/ben", headers=h)).json()["data"]["id"]
    for hedef in ("atandi", "devam_ediyor", "kapandi"):
        r = await kurulu_istemci.patch(
            f"{API}/is-emirleri/{ie}/durum",
            json={"durum": hedef, "atanan_kullanici_id": ben},
            headers=h,
        )
        assert r.status_code == 200, r.text

    m = (await kurulu_istemci.get(f"{API}/finans/maliyet?gun=7", headers=h)).json()["data"]
    kayit = next(x for x in m if x["is_emri_id"] == ie)
    fiyatli = next(k for k in kayit["kalemler"] if k["malzeme_id"] == malzemeler[0])
    assert (fiyatli["miktar"], fiyatli["birim_fiyat"], fiyatli["tutar"]) == (8.0, 12.5, 100.0)
    assert fiyatli["fiyat_kaynagi"] == "talep"
    assert kayit["eksik_fiyat"] == 1 and kayit["birim_maliyet"] is None  # 0 sayılmaz
    assert kayit["malzeme_maliyeti"] == 100.0


async def test_efatura_entegrator_ve_gib_durumu(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    onayci = await _onayci(kurulu_istemci, h)
    firma = await _firma(kurulu_istemci, h)
    f = await _kesilmis(kurulu_istemci, h, onayci, firma)
    r = await kurulu_istemci.post(
        f"{API}/api-anahtarlari",
        json={"ad": f"e-Fatura {uuid.uuid4().hex[:4]}", "izinler": ["finans:oku"]},
        headers=h,
    )
    assert r.status_code == 201, r.text
    anahtar = r.json()["data"]["anahtar"]
    dis = {"X-Tenant": ALFA["slug"], "X-API-Anahtar": anahtar}
    liste = (await kurulu_istemci.get(f"{API}/entegrasyon/faturalar", headers=dis)).json()["data"]
    kayit = next(x for x in liste if x["kod"] == f["kod"])
    assert kayit["ettn"] == f["ettn"] and kayit["karsi_taraf_vkn"] == "1234567890"
    assert kayit["genel_toplam"] == 175.01 and len(kayit["kalemler"]) == 2

    r = await kurulu_istemci.put(
        f"{API}/faturalar/{f['id']}/gib-durumu", json={"gib_durumu": "kabul"}, headers=onayci
    )
    assert r.status_code == 200 and r.json()["data"]["gib_durumu"] == "kabul"
    liste = (await kurulu_istemci.get(f"{API}/entegrasyon/faturalar", headers=dis)).json()["data"]
    assert f["kod"] not in [x["kod"] for x in liste]  # varsayılan süzgeç: gönderilmemiş


async def test_fatura_pdf(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    firma = await _firma(kurulu_istemci, h)
    f = await _fatura(kurulu_istemci, h, firma)
    r = await kurulu_istemci.get(f"{API}/faturalar/{f['id']}/pdf", headers=h)
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    assert f["kod"] in r.headers["content-disposition"]


async def _tablo(t: str) -> bool:
    conn = await asyncpg.connect(_DSN)
    try:
        return bool(await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", f"tenant_alfa.{t}"))
    finally:
        await conn.close()


async def test_s29_goc_up_down(test_db: str) -> None:
    tablolar = ("cari_hesaplar", "cari_hareketler", "faturalar", "fatura_kalemleri", "odemeler")
    for t in tablolar:
        assert await _tablo(t), t
    await asyncio.to_thread(fanout.tenant_indir_tek, "alfa", _S28, db_url=TEST_URL)
    for t in tablolar:
        assert not await _tablo(t), t
    await asyncio.to_thread(fanout.tenant_yukselt_tek, "alfa", "head", db_url=TEST_URL)
    for t in tablolar:
        assert await _tablo(t), t
