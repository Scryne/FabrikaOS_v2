"""Uygulama düzeyinde alan şifrelemesi (S28, ADR-0047): TOTP sırrı ve webhook imza anahtarı.

İkisi de özetlenemez (doğrulama/imza için düz hâli gerekir); bu yüzden veritabanında şifreli durur.
Bir yedek dosyası ya da salt-okur veritabanı erişimi tek başına ikinci faktörü vermesin diye
(ISO 27001 A.8.24). Fernet (AES-128-CBC + HMAC-SHA256, zaman damgalı) kullanılır.

Anahtar: ``VERI_SIFRELEME_ANAHTARLARI`` (virgülle ayrılmış Fernet anahtarları; ilki yeni yazımlar
için, diğerleri yalnız okuma — anahtar döndürme). Verilmezse ``SECRET_KEY``'den HKDF ile türetilir;
türetilmiş anahtar her zaman son okuma anahtarı olarak kalır, böylece sonradan ayrı anahtara
geçmek eski kayıtları kırmaz. **Anahtar yedekle birlikte saklanmalıdır**: başka bir kurulumda
geri yüklenen tenant'ın 2FA'sı aynı anahtar olmadan çalışmaz (``docs/operasyon/dr.md``).

Biçim ``f1:<fernet-token>``. Öneksiz değer eski düz metindir ve olduğu gibi okunur; göç
(``e6b8d0f2a4c6``) mevcutları şifreler.
"""

from __future__ import annotations

import base64
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import String
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

from app.core.config import get_settings

ONEK = "f1:"


def _turetilmis_anahtar(secret_key: str) -> bytes:
    hkdf = HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None, info=b"fabrikaos-alan-sifreleme-v1"
    )
    return base64.urlsafe_b64encode(hkdf.derive(secret_key.encode()))


@lru_cache(maxsize=1)
def _fernet() -> MultiFernet:
    ayar = get_settings()
    anahtarlar = [a.strip() for a in ayar.veri_sifreleme_anahtarlari.split(",") if a.strip()]
    fernetler = [Fernet(a) for a in anahtarlar]
    fernetler.append(Fernet(_turetilmis_anahtar(ayar.secret_key)))
    return MultiFernet(fernetler)


def anahtar_onbellegini_temizle() -> None:
    """Ayar değişince (testler, anahtar döndürme) bir sonraki çağrı anahtarları yeniden okur."""
    _fernet.cache_clear()


def sifrele(duz: str) -> str:
    return ONEK + _fernet().encrypt(duz.encode()).decode()


def coz(deger: str) -> str:
    if not deger.startswith(ONEK):
        return deger  # göç öncesi düz metin
    try:
        return _fernet().decrypt(deger[len(ONEK) :].encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError(
            "Şifreli alan çözülemedi: VERI_SIFRELEME_ANAHTARLARI / SECRET_KEY bu veriyi yazan "
            "kurulumla aynı değil"
        ) from exc


def yeniden_sifrele(deger: str) -> str:
    """Anahtar döndürmeden sonra: kaydı birincil anahtarla yeniden yazar."""
    return sifrele(coz(deger))


class SifreliMetin(TypeDecorator[str]):
    """Yazarken şifreleyen, okurken çözen metin sütunu (ORM'e şeffaf)."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        if value is None or value.startswith(ONEK):
            return value
        return sifrele(value)

    def process_result_value(self, value: str | None, dialect: Dialect) -> str | None:
        return None if value is None else coz(value)
