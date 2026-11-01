"""S27-B (ADR-0046): satınalma siparişi PDF'i — biçim, uç, yetki, denetim izi."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from httpx import AsyncClient

from app.modules.stok.siparis_pdf import PdfFirma, PdfKalem, miktar, para, siparis_pdf
from tests.conftest import ALFA, BETA
from tests.test_s16_entitlement import _giris
from tests.test_s25_depo_sayim import _kullanici
from tests.test_s25b_siparis import _malzeme, _siparis

API = "/api/v1"


def test_turkce_sayi_bicimi() -> None:
    assert para(Decimal("1234567.5"), "TRY") == "1.234.567,50 TRY"
    assert para(Decimal("0"), "EUR") == "0,00 EUR"
    assert miktar(Decimal("12.500")) == "12,5"
    assert miktar(Decimal("3")) == "3"


def test_eksik_fiyatli_kalemle_pdf_uretilir() -> None:
    pdf = siparis_pdf(
        kod="PO-2026-000001",
        tarih=datetime(2026, 11, 1, tzinfo=UTC),
        beklenen_teslim=date(2026, 11, 15),
        para_birimi="TRY",
        aciklama="Teslimat rampa 2'ye.\nİrsaliye zorunlu.",
        talep_kodu="ST-2026-000004",
        alici=PdfFirma(ad="Demo Fabrika A.Ş."),
        tedarikci=PdfFirma(ad="Ege Çelik Ltd.", vergi_no="1234567890", il="İzmir"),
        kalemler=[
            PdfKalem("SAC-3MM", "DKP sac 3 mm", Decimal("150"), "kg", Decimal("38.5")),
            PdfKalem("CIV-M8", "Cıvata M8", Decimal("500"), "adet", None),
        ],
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 5000  # gömülü Türkçe font dahil


async def test_siparis_pdf_ucu_yetki_ve_denetim(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    mid = await _malzeme(kurulu_istemci, h)
    s = await _siparis(kurulu_istemci, h, mid, beklenen=date(2026, 12, 1))
    r = await kurulu_istemci.get(f"{API}/satinalma-siparisleri/{s['id']}/pdf", headers=h)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert s["kod"] in r.headers["content-disposition"]
    assert r.content.startswith(b"%PDF")

    kayit = await kurulu_istemci.get(
        f"{API}/denetim-kayitlari",
        params={"kaynak": "satinalma_siparisi", "eylem": "disa_aktar"},
        headers=h,
    )
    assert kayit.status_code == 200
    assert any(str(s["id"]) == x.get("kaynak_id") for x in kayit.json()["data"])

    ikci = await _kullanici(kurulu_istemci, h, ["ik"])  # satinalma:oku yok
    yasak = await kurulu_istemci.get(f"{API}/satinalma-siparisleri/{s['id']}/pdf", headers=ikci)
    assert yasak.status_code == 403
    beta = await _giris(kurulu_istemci, BETA)
    yok = await kurulu_istemci.get(f"{API}/satinalma-siparisleri/{s['id']}/pdf", headers=beta)
    assert yok.status_code in (403, 404)  # başka kiracı: kayıt yok ya da modül kapalı
