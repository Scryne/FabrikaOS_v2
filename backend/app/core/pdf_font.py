"""PDF'lerde Türkçe karakter: ReportLab'in yerleşik Helvetica'sı WinAnsi kodlamasıyla
sınırlıdır, ``ş ğ ı İ`` basılmaz (kutu çıkar). DejaVu Sans (serbest lisans,
``assets/fonts``) bir kez kaydedilir.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_KLASOR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

FONT = "DejaVuSans"
FONT_KALIN = "DejaVuSans-Bold"


@cache
def fontlari_kaydet() -> None:
    pdfmetrics.registerFont(TTFont(FONT, str(_KLASOR / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_KALIN, str(_KLASOR / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=FONT_KALIN)
