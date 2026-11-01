"""S25-B: satınalma siparişi → kısmi teslim → iade, hızlı kabul eşleşmesi (ADR-0024 kabul testleri).

- Sipariş yalnız onaylı talepten, tedarikçi tipli firmaya açılır; talep başına tek aktif sipariş.
- Teslim kısmi olabilir, aynı irsaliye ikinci kez stok yazmaz (eşzamanlı gönderimde de).
- Fazla teslim kümülatif ölçülür: tolerans içi işaretlenir, aşan 422 ``FAZLA_TESLIM``.
- İade stoktan düşer, siparişin teslim miktarını azaltır, teslim edileni aşamaz.
- Hızlı mal kabul resmî teslimde eşleşir, çift sayılmaz.
- Fiili tarih gelecekte olamaz; zamanında oranı tedarikçi skoruna girer.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, date, datetime, timedelta

from httpx import AsyncClient

from tests.conftest import ALFA, onayci_basliklari
from tests.test_s16_entitlement import _giris
from tests.test_s25_depo_sayim import _bakiye, _genel, _kullanici, _lokasyon, _toplam

API = "/api/v1"


async def _malzeme(istemci: AsyncClient, h: dict[str, str], ad: str = "Sac levha") -> int:
    r = await istemci.post(
        f"{API}/malzemeler",
        json={"kod": f"S25B-{uuid.uuid4().hex[:8]}", "ad": ad, "birim": "adet"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return int(r.json()["data"]["id"])


async def _tedarikci(istemci: AsyncClient, h: dict[str, str], tip: str = "tedarikci") -> int:
    r = await istemci.post(
        f"{API}/firmalar", json={"ad": f"Tedarik {uuid.uuid4().hex[:6]}", "tip": tip}, headers=h
    )
    assert r.status_code == 201, r.text
    return int(r.json()["data"]["id"])


async def _onayli_talep(
    istemci: AsyncClient, h: dict[str, str], mid: int, miktar: float = 10, onayla: bool = True
) -> dict:
    r = await istemci.post(
        f"{API}/satinalma-talepleri",
        json={
            "baslik": "S25-B talebi",
            "kalemler": [
                {"malzeme_id": mid, "miktar": miktar, "birim": "adet", "tahmini_birim_fiyat": 50}
            ],
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    talep = r.json()["data"]
    if onayla:
        r = await istemci.post(f"{API}/satinalma-talepleri/{talep['id']}/gonder", headers=h)
        assert r.status_code == 200, r.text
        onayci = await onayci_basliklari(istemci, h)  # görev ayrımı: açan onaylayamaz (S28)
        r = await istemci.post(f"{API}/satinalma-talepleri/{talep['id']}/onayla", headers=onayci)
        assert r.status_code == 200, r.text
    r = await istemci.get(f"{API}/satinalma-talepleri/{talep['id']}", headers=h)
    return r.json()["data"]


async def _siparis(
    istemci: AsyncClient,
    h: dict[str, str],
    mid: int,
    miktar: float = 10,
    tolerans: float = 0,
    beklenen: date | None = None,
) -> dict:
    talep = await _onayli_talep(istemci, h, mid, miktar)
    firma = await _tedarikci(istemci, h)
    r = await istemci.post(
        f"{API}/satinalma-siparisleri",
        json={
            "talep_id": talep["id"],
            "tedarikci_firma_id": firma,
            "beklenen_teslim_tarihi": beklenen.isoformat() if beklenen else None,
            "kalemler": [
                {
                    "talep_kalemi_id": talep["kalemler"][0]["id"],
                    "fazla_teslim_toleransi_yuzde": tolerans,
                }
            ],
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def _teslim(istemci, h, siparis: dict, irsaliye: str, miktar: float, **ek):
    kalem = siparis["kalemler"][0]["id"]
    satir = {"siparis_kalemi_id": kalem, "miktar": miktar}
    satir.update({k: v for k, v in ek.items() if k in ("birim", "lot_no", "lokasyon_id")})
    govde = {"irsaliye_no": irsaliye, "kalemler": [satir]}
    govde.update({k: v for k, v in ek.items() if k in ("fiili_tarih",)})
    return await istemci.post(
        f"{API}/satinalma-siparisleri/{siparis['id']}/teslim-al", json=govde, headers=h
    )


async def test_siparis_yalniz_onayli_talepten_ve_tek_aktif(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    mid = await _malzeme(kurulu_istemci, h)
    firma = await _tedarikci(kurulu_istemci, h)

    taslak = await _onayli_talep(kurulu_istemci, h, mid, onayla=False)
    r = await kurulu_istemci.post(
        f"{API}/satinalma-siparisleri",
        json={"talep_id": taslak["id"], "tedarikci_firma_id": firma},
        headers=h,
    )
    assert r.status_code == 409, r.text

    talep = await _onayli_talep(kurulu_istemci, h, mid, miktar=7)
    musteri = await _tedarikci(kurulu_istemci, h, tip="musteri")
    r = await kurulu_istemci.post(
        f"{API}/satinalma-siparisleri",
        json={"talep_id": talep["id"], "tedarikci_firma_id": musteri},
        headers=h,
    )
    assert r.status_code == 422, r.text

    r = await kurulu_istemci.post(
        f"{API}/satinalma-siparisleri",
        json={"talep_id": talep["id"], "tedarikci_firma_id": firma},
        headers=h,
    )
    assert r.status_code == 201, r.text
    s = r.json()["data"]
    assert s["kod"].startswith("SS-") and s["durum"] == "acik"
    assert s["kalemler"][0]["miktar"] == 7 and s["kalemler"][0]["birim_fiyat"] == 50
    assert s["toplam_tutar"] == 350

    ikinci = await kurulu_istemci.post(
        f"{API}/satinalma-siparisleri",
        json={"talep_id": talep["id"], "tedarikci_firma_id": firma},
        headers=h,
    )
    assert ikinci.status_code == 409, ikinci.text
    # İptal edilen siparişin yerine yenisi açılabilir.
    assert (
        await kurulu_istemci.post(f"{API}/satinalma-siparisleri/{s['id']}/iptal", headers=h)
    ).status_code == 200
    yeni = await kurulu_istemci.post(
        f"{API}/satinalma-siparisleri",
        json={"talep_id": talep["id"], "tedarikci_firma_id": firma},
        headers=h,
    )
    assert yeni.status_code == 201, yeni.text


async def test_kismi_teslim_idempotent_ve_durum(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    genel = await _genel(kurulu_istemci, h)
    raf = await _lokasyon(kurulu_istemci, h)
    mid = await _malzeme(kurulu_istemci, h)
    s = await _siparis(kurulu_istemci, h, mid, miktar=10)

    r = await _teslim(kurulu_istemci, h, s, "IRS-1", 4)
    assert r.status_code == 201, r.text
    d = r.json()["data"]
    assert d["durum"] == "kismi_teslim" and d["kalemler"][0]["teslim_alinan_miktar"] == 4
    assert d["teslim_orani"] == 0.4
    assert await _bakiye(kurulu_istemci, h, mid) == {genel: 4}

    tekrar = await _teslim(kurulu_istemci, h, s, "IRS-1", 4)
    assert tekrar.status_code == 200, tekrar.text
    assert await _toplam(kurulu_istemci, h, mid) == 4  # ikinci kez stok yazılmadı

    r = await _teslim(kurulu_istemci, h, s, "IRS-2", 6, lokasyon_id=raf)
    assert r.status_code == 201, r.text
    d = r.json()["data"]
    assert d["durum"] == "tamamlandi" and len(d["teslimler"]) == 2
    assert await _bakiye(kurulu_istemci, h, mid) == {genel: 4, raf: 6}

    kapali = await _teslim(kurulu_istemci, h, s, "IRS-3", 1)
    assert kapali.status_code == 409, kapali.text


async def test_fazla_teslim_kumulatif_tolerans(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    mid = await _malzeme(kurulu_istemci, h)

    kati = await _siparis(kurulu_istemci, h, mid, miktar=10)
    r = await _teslim(kurulu_istemci, h, kati, "K-1", 11)
    assert r.status_code == 422 and r.json()["hata_kodu"] == "FAZLA_TESLIM", r.text

    s = await _siparis(kurulu_istemci, h, mid, miktar=100, tolerans=5)
    r = await _teslim(kurulu_istemci, h, s, "T-1", 60)
    assert r.status_code == 201, r.text
    r = await _teslim(kurulu_istemci, h, s, "T-2", 43)  # 103: tolerans içinde, işaretli
    assert r.status_code == 201, r.text
    son = r.json()["data"]["teslimler"][-1]["kalemler"][0]
    assert son["fazla_teslim"] is True
    assert r.json()["data"]["durum"] == "tamamlandi"


async def test_fazla_teslim_kismi_teslimlerin_toplamindan_olculur(
    kurulu_istemci: AsyncClient,
) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    mid = await _malzeme(kurulu_istemci, h)
    s = await _siparis(kurulu_istemci, h, mid, miktar=100, tolerans=5)
    assert (await _teslim(kurulu_istemci, h, s, "P-1", 99)).status_code == 201
    # Tek başına 7 < %5 × 100 ama kümülatif 106 > 105 → reddedilir, stok değişmez.
    r = await _teslim(kurulu_istemci, h, s, "P-2", 7)
    assert r.status_code == 422 and r.json()["hata_kodu"] == "FAZLA_TESLIM", r.text
    assert await _toplam(kurulu_istemci, h, mid) == 99


async def test_birim_uyusmazligi_422(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    mid = await _malzeme(kurulu_istemci, h)
    s = await _siparis(kurulu_istemci, h, mid)
    r = await _teslim(kurulu_istemci, h, s, "B-1", 2, birim="kg")
    assert r.status_code == 422 and r.json()["hata_kodu"] == "BIRIM_UYUSMAZLIGI", r.text
    assert (await _teslim(kurulu_istemci, h, s, "B-1", 2, birim="adet")).status_code == 201


async def test_iade_stoktan_duser_siparisi_geri_acar(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    mid = await _malzeme(kurulu_istemci, h)
    s = await _siparis(kurulu_istemci, h, mid, miktar=10)
    d = (await _teslim(kurulu_istemci, h, s, "I-1", 10)).json()["data"]
    teslim = d["teslimler"][0]
    tk = teslim["kalemler"][0]["id"]

    anahtar = {"Idempotency-Key": f"iade-{uuid.uuid4().hex}"}
    govde = {"irsaliye_no": "IADE-1", "kalemler": [{"teslim_alma_kalemi_id": tk, "miktar": 4}]}
    r = await kurulu_istemci.post(
        f"{API}/teslim-almalar/{teslim['id']}/iade", json=govde, headers={**h, **anahtar}
    )
    assert r.status_code == 201, r.text
    d = r.json()["data"]
    assert d["durum"] == "kismi_teslim" and d["kalemler"][0]["teslim_alinan_miktar"] == 6
    assert await _toplam(kurulu_istemci, h, mid) == 6

    tekrar = await kurulu_istemci.post(
        f"{API}/teslim-almalar/{teslim['id']}/iade", json=govde, headers={**h, **anahtar}
    )
    assert tekrar.status_code == 200, tekrar.text
    assert await _toplam(kurulu_istemci, h, mid) == 6

    fazla = await kurulu_istemci.post(
        f"{API}/teslim-almalar/{teslim['id']}/iade",
        json={"irsaliye_no": "IADE-2", "kalemler": [{"teslim_alma_kalemi_id": tk, "miktar": 7}]},
        headers=h,
    )
    assert fazla.status_code == 422 and fazla.json()["hata_kodu"] == "IADE_FAZLA", fazla.text
    detay = (await kurulu_istemci.get(f"{API}/satinalma-siparisleri/{s['id']}", headers=h)).json()
    orj = next(t for t in detay["data"]["teslimler"] if t["tur"] == "teslim")
    assert orj["kalemler"][0]["iade_edilen_miktar"] == 4


async def test_hizli_kabul_eslesir_cift_sayilmaz(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    mid = await _malzeme(kurulu_istemci, h)
    s = await _siparis(kurulu_istemci, h, mid, miktar=10)
    irs = f"H-{uuid.uuid4().hex[:6]}"

    eksik = await kurulu_istemci.post(
        f"{API}/stok-hareketleri",
        json={"malzeme_id": mid, "tur": "giris", "miktar": 5, "hizli_kabul": True},
        headers=h,
    )
    assert eksik.status_code == 422, eksik.text
    r = await kurulu_istemci.post(
        f"{API}/stok-hareketleri",
        json={"malzeme_id": mid, "tur": "giris", "miktar": 5, "kaynak": irs, "hizli_kabul": True},
        headers=h,
    )
    assert r.status_code == 201 and r.json()["data"]["hizli_kabul"] is True, r.text
    liste = (await kurulu_istemci.get(f"{API}/teslim-almalar/eslesmemis", headers=h)).json()
    assert any(x["irsaliye_no"] == irs and x["malzeme_id"] == mid for x in liste["data"])

    uyusmaz = await _teslim(kurulu_istemci, h, s, irs, 4)
    assert uyusmaz.status_code == 422 and uyusmaz.json()["hata_kodu"] == "ESLESME_MIKTAR"

    r = await _teslim(kurulu_istemci, h, s, irs, 5)
    assert r.status_code == 201, r.text
    assert r.json()["data"]["teslimler"][0]["kalemler"][0]["hizli_kabulden"] is True
    assert await _toplam(kurulu_istemci, h, mid) == 5  # 10 değil: çift sayım yok
    liste = (await kurulu_istemci.get(f"{API}/teslim-almalar/eslesmemis", headers=h)).json()
    assert not any(x["irsaliye_no"] == irs for x in liste["data"])


async def test_eszamanli_ayni_irsaliye_tek_kez_yazar(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    mid = await _malzeme(kurulu_istemci, h)
    s = await _siparis(kurulu_istemci, h, mid, miktar=10)
    a, b = await asyncio.gather(
        _teslim(kurulu_istemci, h, s, "E-1", 5), _teslim(kurulu_istemci, h, s, "E-1", 5)
    )
    assert sorted([a.status_code, b.status_code]) == [200, 201], (a.text, b.text)
    assert await _toplam(kurulu_istemci, h, mid) == 5


async def test_fiili_tarih_zamaninda_ve_tedarikci_skoru(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    mid = await _malzeme(kurulu_istemci, h)
    dun = (datetime.now(UTC) + timedelta(hours=3)).date() - timedelta(days=1)
    s = await _siparis(kurulu_istemci, h, mid, miktar=10, beklenen=dun)

    gelecek = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    r = await _teslim(kurulu_istemci, h, s, "F-1", 1, fiili_tarih=gelecek)
    assert r.status_code == 422, r.text
    eski = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    r = await _teslim(kurulu_istemci, h, s, "F-1", 1, fiili_tarih=eski)
    assert r.status_code == 422, r.text

    r = await _teslim(kurulu_istemci, h, s, "F-1", 10)
    assert r.status_code == 201, r.text
    assert r.json()["data"]["teslimler"][0]["zamaninda"] is False  # beklenen dündü

    skor = await kurulu_istemci.get(f"{API}/firmalar/{s['tedarikci_firma_id']}/skor", headers=h)
    data = skor.json()["data"]
    assert data["zamaninda_teslim"] == 0.0 and "teslim" not in data["yetersiz_veri"]


async def test_teslim_depo_isi_onaylayan_teslim_alamaz(kurulu_istemci: AsyncClient) -> None:
    admin = await _giris(kurulu_istemci, ALFA)
    mid = await _malzeme(kurulu_istemci, admin)
    s = await _siparis(kurulu_istemci, admin, mid, miktar=10)
    onaylayan = await _kullanici(kurulu_istemci, admin, ["satinalma-onaylayan"])
    depocu = await _kullanici(kurulu_istemci, admin, ["depo"])
    assert (await _teslim(kurulu_istemci, onaylayan, s, "R-1", 2)).status_code == 403
    assert (await _teslim(kurulu_istemci, depocu, s, "R-1", 2)).status_code == 201
    # Sipariş açmak depo rolünün işi değil mi? depo `satinalma:yaz` taşır (talep açar);
    # ama yalnız ONAYLI talepten açılabildiği için görev ayrımı korunur.
    r = await kurulu_istemci.get(f"{API}/satinalma-siparisleri", headers=onaylayan)
    assert r.status_code == 200 and any(x["id"] == s["id"] for x in r.json()["data"])


async def test_kismi_siparis_kapatilir(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    mid = await _malzeme(kurulu_istemci, h)
    s = await _siparis(kurulu_istemci, h, mid, miktar=10)
    erken = await kurulu_istemci.post(
        f"{API}/satinalma-siparisleri/{s['id']}/kapat",
        json={"neden": "Tedarikçi kalanı yok"},
        headers=h,
    )
    assert erken.status_code == 409, erken.text
    await _teslim(kurulu_istemci, h, s, "C-1", 3)
    assert (
        await kurulu_istemci.post(f"{API}/satinalma-siparisleri/{s['id']}/iptal", headers=h)
    ).status_code == 409  # teslim varken iptal yok
    r = await kurulu_istemci.post(
        f"{API}/satinalma-siparisleri/{s['id']}/kapat",
        json={"neden": "Tedarikçi kalanı yok"},
        headers=h,
    )
    assert r.status_code == 200 and r.json()["data"]["durum"] == "kapatildi", r.text
    assert (await _teslim(kurulu_istemci, h, s, "C-2", 1)).status_code == 409


async def test_etiket_pdf_ve_kodla_bulma(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    mid = await _malzeme(kurulu_istemci, h, ad="Şerit testere ğıİüöç")
    r = await kurulu_istemci.get(
        f"{API}/malzemeler/{mid}/etiket.pdf", params={"adet": 2}, headers=h
    )
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF") and b"DejaVuSans" in r.content
    assert b"/Count 2" in r.content  # adet=2 → iki sayfa (etiket)

    kod = (await kurulu_istemci.get(f"{API}/malzemeler/{mid}", headers=h)).json()["data"]["kod"]
    bul = await kurulu_istemci.get(f"{API}/malzeme-kodu", params={"kod": kod}, headers=h)
    assert bul.status_code == 200 and bul.json()["data"]["id"] == mid
    yok = await kurulu_istemci.get(f"{API}/malzeme-kodu", params={"kod": "YOK-KOD"}, headers=h)
    assert yok.status_code == 404
