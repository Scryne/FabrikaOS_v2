"""İçe aktarma türleri ve alan dönüştürücüleri (S21, ADR-0042).

Her tür: hangi tabloya yazıldığı, satırı tekil kılan anahtar, kolonlar (tür, zorunluluk, sınır)
ve gereken izin + modül. Dönüştürücüler Türkiye'deki tablo alışkanlıklarını kabul eder:
``1.234,5`` ve ``1234.5``; ``31.12.2026`` ve ``2026-12-31``; ``evet/hayır``.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


class AlanHatasi(ValueError):
    """Hücre değeri geçersiz; mesaj kullanıcıya gösterilir."""


def metin(azami: int) -> Callable[[str], str]:
    def donustur(ham: str) -> str:
        if len(ham) > azami:
            raise AlanHatasi(f"En fazla {azami} karakter")
        return ham

    return donustur


def secim(*degerler: str) -> Callable[[str], str]:
    def donustur(ham: str) -> str:
        d = ham.strip().lower().replace("ı", "i").replace(" ", "_")
        if d not in degerler:
            raise AlanHatasi(f"Geçerli değerler: {', '.join(degerler)}")
        return d

    return donustur


def sayi(
    *, en_az: Decimal | None = None, en_cok: Decimal | None = None
) -> Callable[[str], Decimal]:
    def donustur(ham: str) -> Decimal:
        s = ham.replace(" ", "").replace(" ", "")
        if "," in s and "." in s:
            # Son görülen ayraç ondalıktır: 1.234,5 (TR) ya da 1,234.5 (EN).
            s = (
                s.replace(".", "").replace(",", ".")
                if s.rfind(",") > s.rfind(".")
                else s.replace(",", "")
            )
        elif "," in s:
            s = s.replace(",", ".")
        try:
            d = Decimal(s)
        except InvalidOperation as exc:
            raise AlanHatasi("Sayı değil") from exc
        if not d.is_finite():
            raise AlanHatasi("Sayı değil")
        if en_az is not None and d < en_az:
            raise AlanHatasi(f"En az {en_az}")
        if en_cok is not None and d > en_cok:
            raise AlanHatasi(f"En çok {en_cok}")
        return d

    return donustur


def tamsayi(*, en_az: int, en_cok: int) -> Callable[[str], int]:
    taban = sayi(en_az=Decimal(en_az), en_cok=Decimal(en_cok))

    def donustur(ham: str) -> int:
        d = taban(ham)
        if d != d.to_integral_value():
            raise AlanHatasi("Tam sayı olmalı")
        return int(d)

    return donustur


def oran(ham: str) -> float:
    """OEE hedefi: 0,85 / 85 / %85 → 0.85."""
    d = sayi(en_az=Decimal(0), en_cok=Decimal(100))(ham.replace("%", ""))
    return float(d / 100 if d > 1 else d)


_TARIH_BICIMLERI = ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y")


def tarih(ham: str) -> date:
    for bicim in _TARIH_BICIMLERI:
        try:
            return datetime.strptime(ham.strip(), bicim).date()
        except ValueError:
            continue
    raise AlanHatasi("Tarih GG.AA.YYYY ya da YYYY-AA-GG olmalı")


def mantiksal(ham: str) -> bool:
    d = ham.strip().lower()
    if d in {"evet", "e", "true", "1", "var", "x"}:
        return True
    if d in {"hayır", "hayir", "h", "false", "0", "yok"}:
        return False
    raise AlanHatasi("evet / hayır olmalı")


def tckn_gecerli(no: str) -> bool:
    """T.C. kimlik numarası sağlama kuralı (11 hane, ilk hane 0 değil, 10. ve 11. hane)."""
    if not re.fullmatch(r"[1-9]\d{10}", no):
        return False
    h = [int(c) for c in no]
    onuncu = ((h[0] + h[2] + h[4] + h[6] + h[8]) * 7 - (h[1] + h[3] + h[5] + h[7])) % 10
    return h[9] == onuncu and h[10] == sum(h[:10]) % 10


def tckn(ham: str) -> str:
    no = ham.strip()
    if not tckn_gecerli(no):
        raise AlanHatasi("Geçerli bir T.C. kimlik numarası değil")
    return no


def vergi_no(ham: str) -> str:
    no = ham.strip()
    if not re.fullmatch(r"\d{10}|\d{11}", no):
        raise AlanHatasi("10 haneli vergi no ya da 11 haneli T.C. kimlik no olmalı")
    return no


def eposta(ham: str) -> str:
    adres = ham.strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", adres) or len(adres) > 255:
        raise AlanHatasi("Geçerli bir e-posta adresi değil")
    return adres.lower()


@dataclass(frozen=True)
class Alan:
    ad: str
    donustur: Callable[[str], Any]
    zorunlu: bool = False
    aciklama: str = ""
    ornek: str = ""


@dataclass(frozen=True)
class Tur:
    kod: str
    baslik: str
    izin: str
    modul: str
    anahtar: tuple[str, ...]
    alanlar: tuple[Alan, ...]
    aciklama: str = ""
    sira: int = 0
    takma_adlar: dict[str, str] = field(default_factory=dict)

    def alan(self, ad: str) -> Alan | None:
        return next((a for a in self.alanlar if a.ad == ad), None)


SIFIR = Decimal(0)

TURLER: dict[str, Tur] = {
    t.kod: t
    for t in (
        Tur(
            kod="firma",
            baslik="Firmalar (müşteri / tedarikçi)",
            izin="crm:yaz",
            modul="crm",
            anahtar=("vergi_no", "ad"),
            aciklama="Vergi numarası varsa eşleştirme ona göre, yoksa firma adına göre yapılır.",
            sira=1,
            alanlar=(
                Alan("ad", metin(200), True, "Firma unvanı", "Örnek Metal San. Ltd. Şti."),
                Alan(
                    "tip",
                    secim("musteri", "tedarikci", "her_ikisi"),
                    False,
                    "musteri / tedarikci / her_ikisi",
                    "tedarikci",
                ),
                Alan("vergi_no", vergi_no, False, "10 hane (şahıs firması: 11 hane)", "1234567890"),
                Alan("vergi_dairesi", metin(100), False, "", "Nilüfer"),
                Alan("telefon", metin(30), False, "", "+90 224 000 00 00"),
                Alan("eposta", eposta, False, "", "satis@ornekmetal.com.tr"),
                Alan("adres", metin(500), False, "", "OSB 5. Cad. No:12"),
                Alan("il", metin(100), False, "", "Bursa"),
                Alan("sektor", metin(100), False, "", "Metal işleme"),
                Alan("web_sitesi", metin(255), False, "", "ornekmetal.com.tr"),
            ),
        ),
        Tur(
            kod="makine",
            baslik="Makineler",
            izin="uretim:yaz",
            modul="uretim",
            anahtar=("kod",),
            sira=2,
            alanlar=(
                Alan("kod", metin(50), True, "Fabrika içi benzersiz kod", "CNC-01"),
                Alan("ad", metin(200), True, "", "CNC Torna 1"),
                Alan(
                    "durum",
                    secim("calisiyor", "durdu", "bakimda", "ariza"),
                    False,
                    "Varsayılan: durdu",
                    "durdu",
                ),
                Alan("oee_hedefi", oran, False, "0,85 · 85 · %85", "85"),
                Alan(
                    "enlem",
                    sayi(en_az=Decimal(-90), en_cok=Decimal(90)),
                    False,
                    "Harita için",
                    "40,2167",
                ),
                Alan(
                    "boylam", sayi(en_az=Decimal(-180), en_cok=Decimal(180)), False, "", "28,9622"
                ),
            ),
        ),
        Tur(
            kod="malzeme",
            baslik="Malzemeler",
            izin="stok:yaz",
            modul="stok",
            anahtar=("kod",),
            aciklama="Stok miktarı buradan girilmez; açılış stoğu ayrı yüklenir (hareketle).",
            sira=3,
            alanlar=(
                Alan("kod", metin(50), True, "", "SAC-2MM"),
                Alan("ad", metin(200), True, "", "Sac levha 2 mm"),
                Alan("birim", metin(20), True, "adet, kg, m, lt…", "kg"),
                Alan("kategori", metin(100), False, "", "Hammadde"),
                Alan("min_stok", sayi(en_az=SIFIR), False, "", "100"),
                Alan("max_stok", sayi(en_az=SIFIR), False, "", "2.000"),
                Alan("kritik_stok", sayi(en_az=SIFIR), False, "Altına inince uyarı", "50"),
                Alan("lot_takipli", mantiksal, False, "evet / hayır", "hayır"),
                Alan(
                    "tedarikci_vergi_no",
                    vergi_no,
                    False,
                    "Önce firma olarak yüklenmiş olmalı",
                    "1234567890",
                ),
            ),
        ),
        Tur(
            kod="personel",
            baslik="Personel",
            izin="ik:yaz",
            modul="ik",
            anahtar=("sicil_no",),
            aciklama="T.C. kimlik no doğrulanır, yanıtta ve önizlemede gösterilmez (KVKK).",
            sira=4,
            alanlar=(
                Alan("sicil_no", metin(50), True, "", "P-0001"),
                Alan("ad", metin(100), True, "", "Ayşe"),
                Alan("soyad", metin(100), True, "", "Yılmaz"),
                Alan("tc_kimlik_no", tckn, False, "11 hane, sağlama kontrollü", "10000000146"),
                Alan("dogum_tarihi", tarih, False, "GG.AA.YYYY", "12.04.1990"),
                Alan("telefon", metin(30), False, "", "+90 5xx xxx xx xx"),
                Alan("eposta", eposta, False, "", "ayse.yilmaz@fabrika.com.tr"),
                Alan("departman", metin(100), False, "", "Üretim"),
                Alan("unvan", metin(100), False, "", "Operatör"),
                Alan("ise_giris_tarihi", tarih, False, "GG.AA.YYYY", "01.03.2021"),
                Alan("yillik_izin_hakki", tamsayi(en_az=0, en_cok=60), False, "Gün", "14"),
            ),
        ),
        Tur(
            kod="acilis_stogu",
            baslik="Açılış stoğu",
            izin="stok:yaz",
            modul="stok",
            anahtar=("malzeme_kod", "lokasyon", "lot_no"),
            aciklama=(
                "Her satır bir giriş hareketi yazar. Aynı malzeme/lokasyon/lot ikinci kez "
                "yüklenirse yeni hareket yazılmaz; fark için sayım kullanılır."
            ),
            sira=5,
            alanlar=(
                Alan(
                    "malzeme_kod",
                    metin(50),
                    True,
                    "Önce malzeme olarak yüklenmiş olmalı",
                    "SAC-2MM",
                ),
                Alan("miktar", sayi(en_az=Decimal("0.001")), True, "", "1.250,5"),
                Alan("lokasyon", metin(80), False, "DEPO/LOKASYON; boşsa ANA/GENEL", "ANA/GENEL"),
                Alan("lot_no", metin(50), False, "Lot takipli malzemede zorunlu", ""),
            ),
        ),
    )
}
