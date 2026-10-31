"""Malzeme etiketi PDF'i (S25-B): 100×50 mm termal etiket, sayfa başına bir etiket.

Sol: QR (içerik yalnız malzeme kodu — el tipi okuyucu klavye gibi yazar, arama kutusu ve
``GET /malzemeler/kod/{kod}`` doğrudan bulur). Sağ: kod, ad, birim/kategori. Alt: Code 128.
"""

from __future__ import annotations

import io

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import code128
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from app.core.pdf_font import FONT, FONT_KALIN, fontlari_kaydet
from app.modules.stok.models import Malzeme

GENISLIK = 100 * mm
YUKSEKLIK = 50 * mm
_KENAR = 3 * mm


def _sar(metin: str, font: str, boyut: float, genislik: float, en_cok: int) -> list[str]:
    """Kelime kelime satıra böler; sığmayan son satırı üç noktayla keser."""
    satirlar: list[str] = []
    mevcut = ""
    for kelime in metin.split():
        aday = f"{mevcut} {kelime}".strip()
        if stringWidth(aday, font, boyut) <= genislik:
            mevcut = aday
            continue
        if mevcut:
            satirlar.append(mevcut)
        mevcut = kelime
    if mevcut:
        satirlar.append(mevcut)
    if len(satirlar) > en_cok:
        satirlar = satirlar[:en_cok]
        son = satirlar[-1]
        while son and stringWidth(son + "…", font, boyut) > genislik:
            son = son[:-1]
        satirlar[-1] = son + "…"
    return satirlar


def _etiket(c: canvas.Canvas, m: Malzeme) -> None:
    qr_boy = 30 * mm
    qr = QrCodeWidget(m.kod, barLevel="M")
    x0, y0, x1, y1 = qr.getBounds()
    cizim = Drawing(qr_boy, qr_boy, transform=[qr_boy / (x1 - x0), 0, 0, qr_boy / (y1 - y0), 0, 0])
    cizim.add(qr)
    renderPDF.draw(cizim, c, _KENAR, YUKSEKLIK - _KENAR - qr_boy)

    metin_x = _KENAR + qr_boy + 3 * mm
    metin_gen = GENISLIK - metin_x - _KENAR
    y = YUKSEKLIK - _KENAR - 5 * mm
    c.setFont(FONT_KALIN, 13)
    c.drawString(metin_x, y, _sar(m.kod, FONT_KALIN, 13, metin_gen, 1)[0])
    y -= 5.5 * mm
    c.setFont(FONT, 9)
    for satir in _sar(m.ad, FONT, 9, metin_gen, 3):
        c.drawString(metin_x, y, satir)
        y -= 4 * mm
    c.setFont(FONT, 7.5)
    alt = f"Birim: {m.birim}" + (f" · {m.kategori}" if m.kategori else "")
    c.drawString(
        metin_x, YUKSEKLIK - _KENAR - qr_boy + 1 * mm, _sar(alt, FONT, 7.5, metin_gen, 1)[0]
    )

    barkod = code128.Code128(m.kod, barHeight=10 * mm, barWidth=0.3 * mm, humanReadable=False)
    if barkod.width > GENISLIK - 2 * _KENAR:
        barkod = code128.Code128(
            m.kod,
            barHeight=10 * mm,
            barWidth=(GENISLIK - 2 * _KENAR) / barkod.width * 0.3 * mm,
            humanReadable=False,
        )
    barkod.drawOn(c, (GENISLIK - barkod.width) / 2, _KENAR)


def etiket_pdf(malzeme: Malzeme, adet: int = 1) -> bytes:
    fontlari_kaydet()
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=(GENISLIK, YUKSEKLIK))
    c.setTitle(f"Etiket {malzeme.kod}")
    c.setAuthor("FabrikaOS")
    for _ in range(adet):
        _etiket(c, malzeme)
        c.showPage()
    c.save()
    return tampon.getvalue()
