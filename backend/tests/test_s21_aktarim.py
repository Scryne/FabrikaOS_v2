"""S21 veri içe aktarma (ADR-0042): ayrıştırma, önizleme, hepsi-ya-hiç uygulama, idempotency.

Kabul: onboarding verisi (firma → malzeme → açılış stoğu, makine, personel) dosyayla yüklenir;
aynı dosya ikinci kez çift kayıt üretmez; tek hatalı satır hiçbir şey yazdırmaz; izin ve modül
kapısı türe göre uygulanır; T.C. kimlik no doğrulanır ve yanıtlara girmez.
"""

from __future__ import annotations

import io
import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from openpyxl import Workbook

from app.modules.aktarim.ayristir import DosyaGecersiz, baslik_normallestir, dosya_oku
from app.modules.aktarim.tanimlar import AlanHatasi, oran, sayi, tarih, tckn_gecerli
from tests.conftest import ALFA
from tests.test_s16_entitlement import GAMMA, _giris, gamma_db  # noqa: F401 — fixture
from tests.test_s25_depo_sayim import _kullanici

API = "/api/v1/ice-aktarma"


def _dosya(
    metin: str, ad: str = "veri.csv", kodlama: str = "utf-8"
) -> dict[str, tuple[str, bytes, str]]:
    return {"dosya": (ad, metin.encode(kodlama), "text/csv")}


def _ek() -> str:
    return uuid.uuid4().hex[:6].upper()


# --- Saf birim ----------------------------------------------------------------------------


def test_sayi_tr_ve_en_bicimleri() -> None:
    d = sayi()
    assert d("1.234,5") == Decimal("1234.5")
    assert d("1,234.5") == Decimal("1234.5")
    assert d("12,5") == Decimal("12.5")
    assert d("2.000") == Decimal("2.000")  # tek nokta: ondalık ayracı sayılır (İngilizce Excel)
    with pytest.raises(AlanHatasi):
        d("on iki")
    with pytest.raises(AlanHatasi):
        sayi(en_az=Decimal(0))("-1")


def test_tckn_saglamasi_ve_tarih_oran() -> None:
    assert tckn_gecerli("10000000146")
    assert not tckn_gecerli("10000000147")  # son hane yanlış
    assert not tckn_gecerli("01234567890")  # 0 ile başlayamaz
    assert tarih("31.12.2026").isoformat() == "2026-12-31"
    assert tarih("2026-12-31").isoformat() == "2026-12-31"
    assert oran("85") == pytest.approx(0.85) and oran("%85") == pytest.approx(0.85)
    assert oran("0,85") == pytest.approx(0.85)


def test_ayristirici_noktali_virgul_bom_cp1254_ve_xlsx() -> None:
    assert baslik_normallestir(" Sicil No ") == "sicil_no"
    assert baslik_normallestir("Ünvan") == "unvan"
    utf = "﻿Kod;Ad\nCNC-1;Torna Şişli\n".encode()
    assert dosya_oku("a.csv", utf) == [{"kod": "CNC-1", "ad": "Torna Şişli"}]
    ansi = "kod;ad\nCNC-1;Torna Şişli\n".encode("cp1254")
    assert dosya_oku("a.csv", ansi)[0]["ad"] == "Torna Şişli"
    assert dosya_oku("a.csv", b"kod,ad\nX,Y\n\n\n") == [{"kod": "X", "ad": "Y"}]

    kitap = Workbook()
    sayfa = kitap.active
    assert sayfa is not None
    sayfa.append(["kod", "ad", "oee_hedefi"])
    sayfa.append(["CNC-9", "Freze", 85.0])
    tampon = io.BytesIO()
    kitap.save(tampon)
    assert dosya_oku("a.xlsx", tampon.getvalue()) == [
        {"kod": "CNC-9", "ad": "Freze", "oee_hedefi": "85"}
    ]

    with pytest.raises(DosyaGecersiz, match="biçim"):
        dosya_oku("a.pdf", b"%PDF")
    with pytest.raises(DosyaGecersiz, match="boş"):
        dosya_oku("a.csv", b"\n\n")


# --- Uçtan uca ----------------------------------------------------------------------------


async def test_tur_listesi_yetkiye_gore_isaretler(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.get(f"{API}/turler", headers=h)
    assert r.status_code == 200
    turler = {t["kod"]: t for t in r.json()["data"]}
    assert list(turler) == ["firma", "makine", "malzeme", "personel", "acilis_stogu"]
    assert all(t["yetkili"] for t in turler.values())
    depocu = await _kullanici(kurulu_istemci, h, ["depo"])
    r = await kurulu_istemci.get(f"{API}/turler", headers=depocu)
    yetki = {t["kod"]: t["yetkili"] for t in r.json()["data"]}
    assert yetki["malzeme"] and yetki["acilis_stogu"]
    assert not yetki["personel"] and not yetki["makine"]


async def test_sablon_bom_ve_noktali_virgul(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.get(f"{API}/personel/sablon", headers=h)
    assert r.status_code == 200
    assert r.content.startswith(b"\xef\xbb\xbf")
    ilk = r.content.decode("utf-8-sig").splitlines()[0]
    assert ilk.startswith("sicil_no;ad;soyad;tc_kimlik_no")
    # Şablon kendi kendine geçerli: önizleme hatasız.
    r = await kurulu_istemci.post(
        f"{API}/personel/onizle", files={"dosya": ("s.csv", r.content, "text/csv")}, headers=h
    )
    assert r.json()["data"]["hatali"] == 0, r.text


async def test_makine_onizle_uygula_idempotent(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    e = _ek()
    csv = f"kod;ad;durum;oee_hedefi\nM{e}-1;Pres 1;calisiyor;85\nM{e}-2;Pres 2;;%70\n"

    r = await kurulu_istemci.post(f"{API}/makine/onizle", files=_dosya(csv), headers=h)
    o = r.json()["data"]
    assert (o["toplam"], o["yeni"], o["hatali"]) == (2, 2, 0)
    # Önizleme yazmaz.
    liste = (await kurulu_istemci.get("/api/v1/makineler?boyut=200", headers=h)).json()["data"]
    assert not any(m["kod"].startswith(f"M{e}") for m in liste)

    r = await kurulu_istemci.post(f"{API}/makine/uygula", files=_dosya(csv), headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["yeni"] == 2
    liste = (await kurulu_istemci.get("/api/v1/makineler?boyut=200", headers=h)).json()["data"]
    m2 = next(m for m in liste if m["kod"] == f"M{e}-2")
    assert m2["durum"] == "durdu" and m2["oee_hedefi"] == pytest.approx(0.70)

    # Aynı dosya: her satır "ayni", yeni kayıt yok.
    r = await kurulu_istemci.post(f"{API}/makine/uygula", files=_dosya(csv), headers=h)
    assert (r.json()["data"]["yeni"], r.json()["data"]["ayni"]) == (0, 2)

    # Kısmi güncelleme: yalnız dosyadaki dolu hücre değişir.
    r = await kurulu_istemci.post(
        f"{API}/makine/onizle", files=_dosya(f"kod;ad;durum\nM{e}-1;Pres 1;bakimda\n"), headers=h
    )
    satir = r.json()["data"]["satirlar"][0]
    assert satir["islem"] == "guncelle" and satir["degisen"] == ["durum"]


async def test_tek_hatali_satir_hicbir_sey_yazdirmaz(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    e = _ek()
    csv = (
        f"kod;ad;durum\nH{e}-1;İyi;durdu\nH{e}-2;Kötü;uçuyor\nH{e}-1;Tekrar;durdu\n;Kodsuz;durdu\n"
    )
    o = (await kurulu_istemci.post(f"{API}/makine/onizle", files=_dosya(csv), headers=h)).json()[
        "data"
    ]
    islem = {s["satir"]: s for s in o["satirlar"]}
    assert islem[2]["islem"] == "yeni"
    assert islem[3]["hatalar"][0]["alan"] == "durum"
    assert "aynı kayıt" in islem[4]["hatalar"][0]["mesaj"]
    assert islem[5]["hatalar"][0] == {"alan": "kod", "mesaj": "Zorunlu"}

    r = await kurulu_istemci.post(f"{API}/makine/uygula", files=_dosya(csv), headers=h)
    assert r.status_code == 422
    assert r.json()["hata_kodu"] == "ICE_AKTARMA_HATALI"
    assert any("satır 3" in d["alan"] for d in r.json()["detaylar"])
    liste = (await kurulu_istemci.get("/api/v1/makineler?boyut=200", headers=h)).json()["data"]
    assert not any(m["kod"].startswith(f"H{e}") for m in liste), "geçerli satır da yazılmamalı"


async def test_eksik_zorunlu_kolon(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    o = (
        await kurulu_istemci.post(f"{API}/malzeme/onizle", files=_dosya("kod;ad\nX;Y\n"), headers=h)
    ).json()["data"]
    assert o["eksik_kolonlar"] == ["birim"] and o["hatali"] == 1


async def test_firma_malzeme_acilis_stogu_zinciri(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    e = _ek()
    vergi = str(uuid.uuid4().int)[:10]
    firma = f"ad;tip;vergi_no\nTedarik {e} A.Ş.;tedarikci;{vergi}\n"
    assert (
        await kurulu_istemci.post(f"{API}/firma/uygula", files=_dosya(firma), headers=h)
    ).status_code == 200

    malzeme = (
        f"kod;ad;birim;kritik_stok;lot_takipli;tedarikci_vergi_no\n"
        f"S{e};Sac {e};kg;50;hayır;{vergi}\n"
        f"L{e};Boya {e};lt;0;evet;\n"
    )
    r = await kurulu_istemci.post(f"{API}/malzeme/uygula", files=_dosya(malzeme), headers=h)
    assert r.status_code == 200, r.text
    # Bilinmeyen tedarikçi vergi no → satır hatası.
    yanlis = f"kod;ad;birim;tedarikci_vergi_no\nX{e};X;kg;9999999999\n"
    o = (
        await kurulu_istemci.post(f"{API}/malzeme/onizle", files=_dosya(yanlis), headers=h)
    ).json()["data"]
    assert o["satirlar"][0]["hatalar"][0]["alan"] == "tedarikci_vergi_no"

    acilis = (
        f"malzeme_kod;miktar;lokasyon;lot_no\nS{e};1.250,5;;\nL{e};40;ANA/GENEL;LOT-A\nL{e};10;;\n"
    )
    o = (
        await kurulu_istemci.post(f"{API}/acilis_stogu/onizle", files=_dosya(acilis), headers=h)
    ).json()["data"]
    assert o["hatali"] == 1 and o["satirlar"][2]["hatalar"][0]["alan"] == "lot_no"

    acilis = f"malzeme_kod;miktar;lokasyon;lot_no\nS{e};1.250,5;;\nL{e};40;ANA/GENEL;LOT-A\n"
    r = await kurulu_istemci.post(f"{API}/acilis_stogu/uygula", files=_dosya(acilis), headers=h)
    assert r.status_code == 200, r.text
    malzemeler = (await kurulu_istemci.get("/api/v1/malzemeler?boyut=200", headers=h)).json()[
        "data"
    ]
    sac = next(m for m in malzemeler if m["kod"] == f"S{e}")
    assert Decimal(str(sac["mevcut_miktar"])) == Decimal("1250.5")

    # İkinci yükleme stoğu ikiye katlamaz; farklı miktar sayıma yönlendirilir.
    r = await kurulu_istemci.post(f"{API}/acilis_stogu/uygula", files=_dosya(acilis), headers=h)
    assert r.json()["data"]["ayni"] == 2
    malzemeler = (await kurulu_istemci.get("/api/v1/malzemeler?boyut=200", headers=h)).json()[
        "data"
    ]
    assert Decimal(
        str(next(m for m in malzemeler if m["kod"] == f"S{e}")["mevcut_miktar"])
    ) == Decimal("1250.5")
    farkli = f"malzeme_kod;miktar\nS{e};1300\n"
    o = (
        await kurulu_istemci.post(f"{API}/acilis_stogu/onizle", files=_dosya(farkli), headers=h)
    ).json()["data"]
    assert "sayım" in o["satirlar"][0]["hatalar"][0]["mesaj"]


async def test_personel_tckn_dogrulanir_ve_yanita_girmez(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    e = _ek()
    csv = (
        "sicil_no;ad;soyad;tc_kimlik_no;dogum_tarihi;eposta\n"
        f"P{e}-1;Ayşe;Yılmaz;10000000146;12.04.1990;ayse{e}@ornek.com.tr\n"
        f"P{e}-2;Ali;Kaya;10000000147;;\n"
    )
    r = await kurulu_istemci.post(f"{API}/personel/onizle", files=_dosya(csv), headers=h)
    assert "10000000146" not in r.text and "10000000147" not in r.text
    o = r.json()["data"]
    assert o["satirlar"][1]["hatalar"][0]["alan"] == "tc_kimlik_no"
    duzgun = "\n".join(csv.splitlines()[:2]) + "\n"
    r = await kurulu_istemci.post(f"{API}/personel/uygula", files=_dosya(duzgun), headers=h)
    assert r.status_code == 200 and "10000000146" not in r.text


async def test_izin_ve_modul_kapisi(kurulu_istemci: AsyncClient, gamma_db: None) -> None:  # noqa: F811
    h = await _giris(kurulu_istemci, ALFA)
    depocu = await _kullanici(kurulu_istemci, h, ["depo"])
    r = await kurulu_istemci.post(
        f"{API}/personel/onizle", files=_dosya("sicil_no;ad;soyad\nX;Y;Z\n"), headers=depocu
    )
    assert r.status_code == 403
    # Temel planda CRM kapalı: firma yükleme admin için de kapalı.
    g = await _giris(kurulu_istemci, GAMMA)
    r = await kurulu_istemci.post(f"{API}/firma/onizle", files=_dosya("ad\nX\n"), headers=g)
    assert r.status_code == 403 and r.json()["hata_kodu"] == "MODUL_KAPALI"


async def test_buyuk_ve_yanlis_bicimli_dosya(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.post(
        f"{API}/makine/onizle",
        files={"dosya": ("x.pdf", b"%PDF-1.4", "application/pdf")},
        headers=h,
    )
    assert r.status_code == 422 and r.json()["hata_kodu"] == "DOSYA_GECERSIZ"
