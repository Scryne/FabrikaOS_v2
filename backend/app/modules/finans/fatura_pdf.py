"""Fatura PDF'i (S29, ADR-0048): kesilmiş faturanın yazdırılabilir/paylaşılabilir kopyası.

Resmî e-Fatura değildir: GİB'e giden belge entegratörde UBL-TR olarak üretilir. Bu çıktı müşteriye
ön bilgi ya da kâğıt arşiv içindir ve bunu başlığın altında açıkça yazar. Taslak ya da onay
bekleyen faturada filigran "TASLAK"tır. Biçim satınalma siparişi PDF'iyle aynı (künye, Türkçe sayı,
DejaVu) — yardımcılar oradan.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.pdf_font import FONT, FONT_KALIN, fontlari_kaydet
from app.modules.stok.siparis_pdf import (
    _CIZGI,
    _KOYU,
    _SOLUK,
    _ZEMIN,
    PdfFirma,
    _kunye,
    _stil,
    para,
)
from app.modules.stok.siparis_pdf import miktar as miktar_metni


@dataclass(frozen=True)
class FaturaPdfKalem:
    aciklama: str
    miktar: Decimal
    birim: str
    birim_fiyat: Decimal
    kdv_orani: int
    satir_tutari: Decimal
    kdv_tutari: Decimal


def fatura_pdf(
    *,
    kod: str,
    tur: str,
    durum: str,
    fatura_tarihi: date,
    vade_tarihi: date,
    para_birimi: str,
    ettn: str,
    aciklama: str,
    satici: PdfFirma,
    alici: PdfFirma,
    kalemler: Sequence[FaturaPdfKalem],
    ara_toplam: Decimal,
    kdv_toplam: Decimal,
    genel_toplam: Decimal,
    odenen: Decimal,
) -> bytes:
    fontlari_kaydet()
    tampon = io.BytesIO()
    doc = SimpleDocTemplate(
        tampon,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=f"Fatura {kod}",
        author=satici.ad,
    )
    genislik = A4[0] - 32 * mm
    taslak = durum in ("taslak", "onay_bekliyor")
    baslik = "SATIŞ FATURASI" if tur == "satis" else "ALIŞ FATURASI"
    akis: list[object] = []

    ust = Table(
        [
            [
                Paragraph(baslik, _stil(15, True)),
                Paragraph(
                    f"<b>{kod}</b><br/>Tarih {fatura_tarihi:%d.%m.%Y}"
                    f"<br/>Vade {vade_tarihi:%d.%m.%Y}",
                    _stil(10, alignment=TA_RIGHT),
                ),
            ]
        ],
        colWidths=[genislik * 0.6, genislik * 0.4],
    )
    ust.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    akis += [
        ust,
        Paragraph(
            f"Bilgi nüshasıdır; resmî e-Fatura entegratör üzerinden iletilir. ETTN {ettn}",
            _stil(7.5, renk=_SOLUK),
        ),
        Spacer(1, 5 * mm),
    ]
    taraflar = Table(
        [[_kunye("SATICI", satici), _kunye("ALICI", alici)]],
        colWidths=[genislik / 2, genislik / 2],
    )
    taraflar.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (0, 0), 0.6, _CIZGI),
                ("BOX", (1, 0), (1, 0), 0.6, _CIZGI),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    akis += [taraflar, Spacer(1, 5 * mm)]

    basliklar = ["#", "Açıklama", "Miktar", "Birim", "Birim fiyat", "KDV", "Tutar"]
    sayisal = {"Miktar", "Birim fiyat", "KDV", "Tutar"}
    sag = _stil(8.5, alignment=TA_RIGHT)
    satirlar: list[list[object]] = [
        [Paragraph(b, _stil(8, True, alignment=TA_RIGHT if b in sayisal else 0)) for b in basliklar]
    ]
    for i, k in enumerate(kalemler, 1):
        satirlar.append(
            [
                Paragraph(str(i), _stil(8.5)),
                Paragraph(k.aciklama, _stil(8.5)),
                Paragraph(miktar_metni(k.miktar), sag),
                Paragraph(k.birim, _stil(8.5)),
                Paragraph(para(k.birim_fiyat, para_birimi), sag),
                Paragraph(f"%{k.kdv_orani}", sag),
                Paragraph(para(k.satir_tutari, para_birimi), sag),
            ]
        )
    oranlar = [0.05, 0.37, 0.1, 0.08, 0.15, 0.08, 0.17]
    tablo = Table(satirlar, colWidths=[genislik * o for o in oranlar], repeatRows=1)
    tablo.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _ZEMIN),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, _CIZGI),
                ("LINEBELOW", (0, 1), (-1, -1), 0.3, _CIZGI),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    akis += [tablo, Spacer(1, 3 * mm)]

    toplamlar = [
        ("Ara toplam", para(ara_toplam, para_birimi), False),
        ("KDV", para(kdv_toplam, para_birimi), False),
        ("Genel toplam", para(genel_toplam, para_birimi), True),
    ]
    if odenen > 0:
        toplamlar += [
            ("Ödenen", para(odenen, para_birimi), False),
            ("Kalan", para(genel_toplam - odenen, para_birimi), True),
        ]
    ozet = Table(
        [
            [
                Paragraph(ad, _stil(9, kalin)),
                Paragraph(deger, _stil(9, kalin, alignment=TA_RIGHT)),
            ]
            for ad, deger, kalin in toplamlar
        ],
        colWidths=[genislik * 0.2, genislik * 0.22],
        hAlign="RIGHT",
    )
    ozet.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 2), (-1, 2), 0.9, _KOYU),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    akis.append(ozet)
    if aciklama:
        akis += [
            Spacer(1, 6 * mm),
            Paragraph("Notlar", _stil(8, True, _SOLUK)),
            Paragraph(aciklama.replace("\n", "<br/>"), _stil(9)),
        ]

    def sayfa(c: object, d: object) -> None:
        c.saveState()  # type: ignore[attr-defined]
        if taslak:
            c.setFont(FONT_KALIN, 70)  # type: ignore[attr-defined]
            c.setFillColor(colors.Color(0.85, 0.2, 0.2, alpha=0.12))  # type: ignore[attr-defined]
            c.translate(A4[0] / 2, A4[1] / 2)  # type: ignore[attr-defined]
            c.rotate(40)  # type: ignore[attr-defined]
            c.drawCentredString(0, 0, "TASLAK")  # type: ignore[attr-defined]
            c.rotate(-40)  # type: ignore[attr-defined]
            c.translate(-A4[0] / 2, -A4[1] / 2)  # type: ignore[attr-defined]
        c.setFont(FONT, 7.5)  # type: ignore[attr-defined]
        c.setFillColor(_SOLUK)  # type: ignore[attr-defined]
        c.drawString(16 * mm, 10 * mm, f"{kod} · {satici.ad}")  # type: ignore[attr-defined]
        c.drawRightString(A4[0] - 16 * mm, 10 * mm, f"Sayfa {d.page}")  # type: ignore[attr-defined]
        c.restoreState()  # type: ignore[attr-defined]

    doc.build(akis, onFirstPage=sayfa, onLaterPages=sayfa)
    return tampon.getvalue()
