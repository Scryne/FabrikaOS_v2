"""TOTP (RFC 6238, SHA-1/6 hane/30 sn) — stdlib-saf gerçekleme, bağımlılıksız (S23).

Google Authenticator/Authy/1Password uyumlu. Sır base32 saklanır; kurulumda
``otpauth://`` URI'si FE'de QR koduna çevrilir (antd ``QRCode``). Doğrulama
±``pencere`` adım toleranslıdır (saat kayması) ve sabit-zamanlı karşılaştırır.
"""

from __future__ import annotations

import base64
import hmac
import secrets
import struct
import time
import urllib.parse

ADIM_SN = 30
HANE = 6


def sir_uret() -> str:
    """160 bit rastgele sır, base32 (RFC 4648, dolgu yok) — authenticator girdisi."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def kod_uret(sir_b32: str, *, zaman: float | None = None) -> str:
    """Verilen andaki 6 haneli TOTP kodu (RFC 6238 → RFC 4226 HOTP çekirdeği)."""
    zaman = time.time() if zaman is None else zaman
    sayac = int(zaman) // ADIM_SN
    # b32decode dolgu ister; sondan kırpılmış sırrı 8'in katına tamamla.
    dolgulu = sir_b32.upper() + "=" * (-len(sir_b32) % 8)
    anahtar = base64.b32decode(dolgulu)
    mesaj = struct.pack(">Q", sayac)
    ozet = hmac.new(anahtar, mesaj, "sha1").digest()
    kayma = ozet[-1] & 0x0F
    kesit = struct.unpack(">I", ozet[kayma : kayma + 4])[0] & 0x7FFFFFFF
    return str(kesit % (10**HANE)).zfill(HANE)


def kod_dogrula(sir_b32: str, kod: str, *, zaman: float | None = None, pencere: int = 1) -> bool:
    """Kodu ±``pencere`` zaman adımı toleransıyla, sabit-zamanlı karşılaştırarak doğrular."""
    kod = kod.strip().replace(" ", "")
    if not kod.isdigit() or len(kod) != HANE:
        return False
    zaman = time.time() if zaman is None else zaman
    return any(
        hmac.compare_digest(kod_uret(sir_b32, zaman=zaman + sapma * ADIM_SN), kod)
        for sapma in range(-pencere, pencere + 1)
    )


def otpauth_uri(sir_b32: str, *, eposta: str, tenant_slug: str) -> str:
    """Authenticator kurulum URI'si — FE bunu QR koduna çevirir."""
    etiket = urllib.parse.quote(f"FabrikaOS ({tenant_slug}):{eposta}")
    veren = urllib.parse.quote("FabrikaOS")
    return (
        f"otpauth://totp/{etiket}?secret={sir_b32}&issuer={veren}&algorithm=SHA1&digits=6&period=30"
    )


def kurtarma_kodlari_uret(adet: int = 8) -> list[str]:
    """Bir kez gösterilecek kurtarma kodları — ``XXXX-XXXX`` biçimi, yüksek entropi."""
    alfabe = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"  # karışan karakterler (0/O, 1/I/L) yok
    kodlar = []
    for _ in range(adet):
        ham = "".join(secrets.choice(alfabe) for _ in range(8))
        kodlar.append(f"{ham[:4]}-{ham[4:]}")
    return kodlar
