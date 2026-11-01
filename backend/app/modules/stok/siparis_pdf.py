"""Satınalma siparişi PDF'i (S27-B, ADR-0046): tedarikçiye gönderilen sipariş formu.

A4 dikey; alıcı (kiracı) ve tedarikçi künyesi, sipariş numarası, tarih, beklenen teslim, kalem
tablosu (malzeme, miktar, birim, birim fiyat, tutar), ara toplam ve iki imza alanı. Fiyatı
girilmemiş kalem tutarı "—" yazar ve toplam "eksik fiyatlı kalem var" uyarısı taşır: eksik fiyat
sessizce 0 sayılmaz. Türkçe karakterler için DejaVu (``core.pdf_font``).
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.pdf_font import FONT, FONT_KALIN, fontlari_kaydet

_KOYU = colors.HexColor("#1f2937")
_SOLUK = colors.HexColor("#6b7280")
_CIZGI = colors.HexColor("#d1d5db")
_ZEMIN = colors.HexColor("#f3f4f6")


@dataclass(frozen=True)
class PdfKalem:
    malzeme_kod: str
    malzeme_ad: str
    miktar: Decimal
    birim: str
    birim_fiyat: Decimal | None


@dataclass(frozen=True)
class PdfFirma:
    ad: str
    vergi_dairesi: str = ""
    vergi_no: str = ""
    adres: str = ""
    il: str = ""
    telefon: str = ""
    eposta: str = ""


def para(v: Decimal, birim: str) -> str:
    """1234567.5 → '1.234.567,50 TRY' (Türkçe binlik/ondalık)."""
    metin = f"{v:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{metin} {birim}"


def miktar(v: Decimal) -> str:
    return f"{v.normalize():f}".replace(".", ",")


def _stil(
    boyut: float = 9, kalin: bool = False, renk: colors.Color = _KOYU, **ek: object
) -> ParagraphStyle:
    return ParagraphStyle(
        "s",
        fontName=FONT_KALIN if kalin else FONT,
        fontSize=boyut,
        leading=boyut * 1.35,
        textColor=renk,
        **ek,
    )


def _kunye(baslik: str, f: PdfFirma) -> list[Paragraph]:
    satirlar = [Paragraph(baslik, _stil(7.5, True, _SOLUK)), Paragraph(f.ad, _stil(10, True))]
    vergi = " · ".join(x for x in (f.vergi_dairesi, f.vergi_no and f"VKN {f.vergi_no}") if x)
    for x in (vergi, f.adres, f.il, " · ".join(y for y in (f.telefon, f.eposta) if y)):
        if x:
            satirlar.append(Paragraph(x, _stil(8.5, renk=_SOLUK)))
    return satirlar


def siparis_pdf(
    *,
    kod: str,
    tarih: datetime,
    beklenen_teslim: date | None,
    para_birimi: str,
    aciklama: str,
    talep_kodu: str | None,
    alici: PdfFirma,
    tedarikci: PdfFirma,
    kalemler: Sequence[PdfKalem],
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
        title=f"Satınalma siparişi {kod}",
        author=alici.ad,
    )
    genislik = A4[0] - 32 * mm
    akis: list[object] = []

    ust = Table(
        [
            [
                Paragraph("SATINALMA SİPARİŞİ", _stil(15, True)),
                Paragraph(f"<b>{kod}</b><br/>{tarih:%d.%m.%Y}", _stil(10, alignment=TA_RIGHT)),
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
    akis += [ust, Spacer(1, 6 * mm)]

    taraflar = Table(
        [[_kunye("ALICI", alici), _kunye("TEDARİKÇİ", tedarikci)]],
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
    akis += [taraflar, Spacer(1, 4 * mm)]

    bilgi = [f"Para birimi: {para_birimi}"]
    if beklenen_teslim:
        bilgi.append(f"Beklenen teslim: {beklenen_teslim:%d.%m.%Y}")
    if talep_kodu:
        bilgi.append(f"Talep: {talep_kodu}")
    akis += [Paragraph("  ·  ".join(bilgi), _stil(8.5, renk=_SOLUK)), Spacer(1, 3 * mm)]

    basliklar = ["#", "Malzeme", "Miktar", "Birim", "Birim fiyat", "Tutar"]
    sayisal = {"Miktar", "Birim fiyat", "Tutar"}
    satirlar: list[list[object]] = [
        [Paragraph(b, _stil(8, True, alignment=TA_RIGHT if b in sayisal else 0)) for b in basliklar]
    ]
    toplam = Decimal(0)
    eksik_fiyat = False
    sag = _stil(8.5, alignment=TA_RIGHT)
    for i, k in enumerate(kalemler, 1):
        if k.birim_fiyat is None:
            eksik_fiyat = True
            bf = tutar = "—"
        else:
            t = (k.miktar * k.birim_fiyat).quantize(Decimal("0.01"))
            toplam += t
            bf, tutar = para(k.birim_fiyat, para_birimi), para(t, para_birimi)
        satirlar.append(
            [
                Paragraph(str(i), _stil(8.5)),
                Paragraph(f"<b>{k.malzeme_kod}</b> {k.malzeme_ad}", _stil(8.5)),
                Paragraph(miktar(k.miktar), sag),
                Paragraph(k.birim, _stil(8.5)),
                Paragraph(bf, sag),
                Paragraph(tutar, sag),
            ]
        )
    toplam_metin = para(toplam, para_birimi) + (" *" if eksik_fiyat else "")
    satirlar.append(
        [
            "",
            Paragraph("Ara toplam (KDV hariç)", _stil(9, True)),
            "",
            "",
            Paragraph(toplam_metin, _stil(9, True, alignment=TA_RIGHT)),
            "",
        ]
    )
    oranlar = [0.05, 0.43, 0.11, 0.08, 0.16, 0.17]
    tablo = Table(satirlar, colWidths=[genislik * o for o in oranlar], repeatRows=1)
    tablo.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _ZEMIN),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, _CIZGI),
                ("LINEBELOW", (0, 1), (-1, -2), 0.3, _CIZGI),
                ("LINEABOVE", (0, -1), (-1, -1), 0.9, _KOYU),
                ("SPAN", (1, -1), (3, -1)),
                ("SPAN", (4, -1), (5, -1)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    akis.append(tablo)
    if eksik_fiyat:
        akis += [
            Spacer(1, 2 * mm),
            Paragraph(
                "* Fiyatı girilmemiş kalem var; ara toplam yalnız fiyatlı kalemleri içerir.",
                _stil(8, renk=_SOLUK),
            ),
        ]
    if aciklama:
        akis += [
            Spacer(1, 5 * mm),
            Paragraph("Notlar", _stil(8, True, _SOLUK)),
            Paragraph(aciklama.replace("\n", "<br/>"), _stil(9)),
        ]

    akis.append(Spacer(1, 16 * mm))
    imza = Table(
        [
            [
                Paragraph("Hazırlayan", _stil(8, True, _SOLUK)),
                Paragraph("Onaylayan", _stil(8, True, _SOLUK)),
                Paragraph("Tedarikçi kabulü", _stil(8, True, _SOLUK)),
            ]
        ],
        colWidths=[genislik / 3] * 3,
        rowHeights=[22 * mm],
    )
    imza.setStyle(
        TableStyle(
            [("LINEABOVE", (0, 0), (-1, 0), 0.6, _CIZGI), ("VALIGN", (0, 0), (-1, -1), "TOP")]
        )
    )
    akis.append(imza)

    def altbilgi(c: object, d: object) -> None:
        c.saveState()  # type: ignore[attr-defined]
        c.setFont(FONT, 7.5)  # type: ignore[attr-defined]
        c.setFillColor(_SOLUK)  # type: ignore[attr-defined]
        c.drawString(16 * mm, 10 * mm, f"{kod} · {alici.ad}")  # type: ignore[attr-defined]
        c.drawRightString(A4[0] - 16 * mm, 10 * mm, f"Sayfa {d.page}")  # type: ignore[attr-defined]
        c.restoreState()  # type: ignore[attr-defined]

    doc.build(akis, onFirstPage=altbilgi, onLaterPages=altbilgi)
    return tampon.getvalue()
