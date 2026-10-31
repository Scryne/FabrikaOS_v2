"""Yüklenen tabloyu (CSV ya da XLSX) satır sözlüklerine çevirir.

Türkiye'deki Excel'in "CSV (noktalı virgülle ayrılmış)" çıktısı ``;`` ayraçlı, Windows-1254
kodlu ve ondalıkta virgüllü gelir; aynı dosya başka bir yerde virgül ayraçlı UTF-8 olur.
Ayrıştırıcı ikisini de kabul eder: BOM'lu/BOM'suz UTF-8, olmazsa cp1254; ayraç ilk satırdan
seçilir. Başlıklar küçük harfe, Türkçe karakterleri sadeleştirerek normalleştirilir
("Sicil No" → ``sicil_no``, "Ünvan" → ``unvan``).
"""

from __future__ import annotations

import csv
import io
import unicodedata
from datetime import datetime

from openpyxl import load_workbook

AZAMI_BAYT = 5 * 1024 * 1024
AZAMI_SATIR = 10_000

_TR = str.maketrans("çğıöşüÇĞİÖŞÜâîû", "cgiosuCGIOSUaiu")


class DosyaGecersiz(ValueError):
    """Dosya okunamadı ya da biçim/limit dışı (satır hatası değil)."""


def baslik_normallestir(ham: str) -> str:
    metin = unicodedata.normalize("NFC", (ham or "").strip()).translate(_TR).lower()
    parcalar = "".join(c if c.isalnum() else " " for c in metin).split()
    return "_".join(parcalar)


def _metin_coz(veri: bytes) -> str:
    if veri.startswith(b"\xef\xbb\xbf"):
        return veri[3:].decode("utf-8")
    try:
        return veri.decode("utf-8")
    except UnicodeDecodeError:
        return veri.decode("cp1254")


def _csv(veri: bytes) -> list[dict[str, str]]:
    metin = _metin_coz(veri)
    ilk = metin.split("\n", 1)[0]
    ayrac = max((";", ",", "\t"), key=ilk.count)
    okuyucu = csv.reader(io.StringIO(metin), delimiter=ayrac)
    satirlar = list(okuyucu)
    return _sozluklere(satirlar)


def _xlsx(veri: bytes) -> list[dict[str, str]]:
    try:
        kitap = load_workbook(io.BytesIO(veri), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001 — bozuk/şifreli dosya kullanıcı hatasıdır
        raise DosyaGecersiz("XLSX dosyası okunamadı") from exc
    sayfa = kitap.worksheets[0]
    satirlar: list[list[str]] = []
    for satir in sayfa.iter_rows(values_only=True):
        satirlar.append(["" if h is None else _hucre(h) for h in satir])
    kitap.close()
    return _sozluklere(satirlar)


def _hucre(deger: object) -> str:
    # Tarih hücreleri datetime gelir; tamsayı gibi duran ondalıklar "12.0" değil "12" yazılır.
    if isinstance(deger, datetime):
        return deger.date().isoformat()
    if isinstance(deger, float) and deger.is_integer():
        return str(int(deger))
    return str(deger)


def _sozluklere(satirlar: list[list[str]]) -> list[dict[str, str]]:
    satirlar = [s for s in satirlar if any((h or "").strip() for h in s)]
    if not satirlar:
        raise DosyaGecersiz("Dosya boş")
    basliklar = [baslik_normallestir(b) for b in satirlar[0]]
    if len(satirlar) - 1 > AZAMI_SATIR:
        raise DosyaGecersiz(f"En fazla {AZAMI_SATIR} satır yüklenebilir")
    sonuc = []
    for s in satirlar[1:]:
        sonuc.append(
            {
                b: (s[i].strip() if i < len(s) and s[i] is not None else "")
                for i, b in enumerate(basliklar)
                if b
            }
        )
    return sonuc


def dosya_oku(ad: str, veri: bytes) -> list[dict[str, str]]:
    if len(veri) > AZAMI_BAYT:
        raise DosyaGecersiz("Dosya 5 MB'tan büyük")
    if ad.lower().endswith(".xlsx"):
        return _xlsx(veri)
    if ad.lower().endswith((".csv", ".txt")):
        return _csv(veri)
    raise DosyaGecersiz("Desteklenen biçimler: .csv, .xlsx")
