"""Tenant güvenlik politikaları — saf doğrulama fonksiyonları (S23 / ADR-0022).

``tenant.guvenlik_ayarlari`` JSONB'den beslenir; NULL/eksik anahtar = o kural kapalı.
Parola politikası yeni parola belirlenirken (kullanıcı oluşturma + parola değiştirme)
uygulanır; IP izin listesi tenant çözümlemesinde her istekte kontrol edilir.
"""

from __future__ import annotations

import ipaddress
from typing import Any


def parola_kurali_ihlalleri(parola: str, politika: dict[str, Any] | None) -> list[str]:
    """Politika ihlallerinin insan-okur listesi; boş liste = geçerli.

    Desteklenen anahtarlar: ``min_uzunluk`` (int), ``buyuk_kucuk`` (bool — en az bir
    büyük VE bir küçük harf), ``rakam`` (bool), ``ozel_karakter`` (bool).
    """
    if not politika:
        return []
    ihlaller: list[str] = []
    min_uzunluk = politika.get("min_uzunluk")
    if isinstance(min_uzunluk, int) and len(parola) < min_uzunluk:
        ihlaller.append(f"En az {min_uzunluk} karakter olmalı")
    if politika.get("buyuk_kucuk") and not (
        any(c.isupper() for c in parola) and any(c.islower() for c in parola)
    ):
        ihlaller.append("Büyük ve küçük harf birlikte olmalı")
    if politika.get("rakam") and not any(c.isdigit() for c in parola):
        ihlaller.append("En az bir rakam olmalı")
    if politika.get("ozel_karakter") and not any(not c.isalnum() for c in parola):
        ihlaller.append("En az bir özel karakter olmalı")
    return ihlaller


def ip_izinli_mi(ip: str | None, izin_listesi: list[str] | None) -> bool:
    """IP izin listesi kontrolü. Liste boş/None = kısıt kapalı (herkes girer).

    Girdiler CIDR (``10.0.0.0/8``) veya tek IP (``1.2.3.4``) olabilir; bozuk girdi
    satırı **es geçilir** (yanlış konfigürasyon tenant'ı komple kilitlemesin —
    fail-open satır bazında, liste bazında değil). IP çözülemiyorsa reddedilir.
    """
    if not izin_listesi:
        return True
    if not ip:
        return False
    try:
        adres = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for girdi in izin_listesi:
        try:
            if adres in ipaddress.ip_network(str(girdi), strict=False):
                return True
        except ValueError:
            continue
    return False


def guvenlik_ayari(ayarlar: dict[str, Any] | None, anahtar: str, varsayilan: Any = None) -> Any:
    """``guvenlik_ayarlari`` JSONB'den güvenli okuma (NULL/yanlış tip → varsayılan)."""
    if not isinstance(ayarlar, dict):
        return varsayilan
    return ayarlar.get(anahtar, varsayilan)
