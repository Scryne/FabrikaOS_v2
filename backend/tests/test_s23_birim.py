"""S23 saf birim testleri — TOTP (RFC 6238 vektörleri) + parola politikası + IP izin listesi."""

from __future__ import annotations

from app.core.security.politika import guvenlik_ayari, ip_izinli_mi, parola_kurali_ihlalleri
from app.core.security.totp import (
    kod_dogrula,
    kod_uret,
    kurtarma_kodlari_uret,
    otpauth_uri,
    sir_uret,
)

# RFC 6238 Ek B test sırrı: ASCII "12345678901234567890" → base32.
_RFC_SIR = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"


# --- TOTP ---
def test_totp_rfc6238_vektorleri() -> None:
    # RFC 8 haneli değerlerin son 6 hanesi (SHA-1): 59 → 94287082, 1111111109 → 07081804.
    assert kod_uret(_RFC_SIR, zaman=59) == "287082"
    assert kod_uret(_RFC_SIR, zaman=1111111109) == "081804"
    assert kod_uret(_RFC_SIR, zaman=1234567890) == "005924"


def test_totp_dogrulama_penceresi_ve_bicim() -> None:
    zaman = 1111111109.0
    kod = kod_uret(_RFC_SIR, zaman=zaman)
    assert kod_dogrula(_RFC_SIR, kod, zaman=zaman)
    assert kod_dogrula(_RFC_SIR, kod, zaman=zaman + 30)  # ±1 adım toleransı
    assert not kod_dogrula(_RFC_SIR, kod, zaman=zaman + 120)  # pencere dışı
    assert not kod_dogrula(_RFC_SIR, "abc123", zaman=zaman)  # rakam değil
    assert not kod_dogrula(_RFC_SIR, "12345", zaman=zaman)  # 6 hane değil


def test_sir_ve_kurtarma_uretimi() -> None:
    sir = sir_uret()
    assert len(sir) == 32 and sir.isalnum()  # 160 bit base32, dolgu yok
    kodlar = kurtarma_kodlari_uret()
    assert len(kodlar) == 8 and len(set(kodlar)) == 8
    assert all(len(k) == 9 and k[4] == "-" for k in kodlar)
    uri = otpauth_uri(sir, eposta="a@b.test", tenant_slug="alfa")
    assert uri.startswith("otpauth://totp/") and f"secret={sir}" in uri


# --- Parola politikası ---
def test_parola_politikasi_ihlalleri() -> None:
    politika = {"min_uzunluk": 12, "buyuk_kucuk": True, "rakam": True, "ozel_karakter": True}
    assert parola_kurali_ihlalleri("Guclu-Parola-99!", politika) == []
    # "kisa": kısa + tek harf türü + rakamsız + özel karaktersiz = 4 ihlal.
    ihlaller = parola_kurali_ihlalleri("kisa", politika)
    assert len(ihlaller) == 4
    assert any("12 karakter" in m for m in ihlaller)


def test_parola_politikasi_yoksa_serbest() -> None:
    assert parola_kurali_ihlalleri("x", None) == []
    assert parola_kurali_ihlalleri("x", {}) == []


# --- IP izin listesi ---
def test_ip_izin_listesi() -> None:
    assert ip_izinli_mi("10.1.2.3", ["10.0.0.0/8"])
    assert ip_izinli_mi("192.168.1.5", ["192.168.1.5"])  # tek IP
    assert not ip_izinli_mi("8.8.8.8", ["10.0.0.0/8"])
    assert ip_izinli_mi("8.8.8.8", [])  # boş liste = kısıt kapalı
    assert ip_izinli_mi("8.8.8.8", None)
    assert not ip_izinli_mi(None, ["10.0.0.0/8"])  # IP yoksa reddet
    assert not ip_izinli_mi("bozuk-ip", ["10.0.0.0/8"])
    assert ip_izinli_mi("10.0.0.1", ["bozuk-girdi", "10.0.0.0/8"])  # bozuk satır es geçilir


def test_guvenlik_ayari_okuma() -> None:
    assert guvenlik_ayari(None, "x", 1) == 1
    assert guvenlik_ayari({"x": 2}, "x", 1) == 2
    assert guvenlik_ayari("bozuk", "x", 1) == 1  # type: ignore[arg-type]
