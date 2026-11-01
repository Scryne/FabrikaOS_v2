"""İş takvimi "bugün"ü (S27-B düzeltmesi): tarihli iş kuralları kiracının yerel gününe göre işler.

Sunucu saati UTC'dir; Türkiye'de 00:00–03:00 arasında UTC tarihi bir gün geridedir. "Bugün" UTC'den
alınınca bu saatlerde bugünün tarihli kalibrasyon kaydı "gelecek tarih" diye reddediliyor, bakiye ve
vade hesapları bir gün kayıyordu (S27 tam test koşusunun gece yarısını geçerken düşmesiyle bulundu).
Zaman damgaları UTC kalır; yalnız takvim günü gerektiren kararlar bu fonksiyonu kullanır.
"""

from __future__ import annotations

from datetime import date, datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

from app.core.config import get_settings


@lru_cache(maxsize=1)
def is_saat_dilimi() -> ZoneInfo:
    return ZoneInfo(get_settings().is_saat_dilimi)


def is_gunu(an: datetime | None = None) -> date:
    """Verilen anın (yoksa şimdinin) iş saat dilimindeki takvim günü."""
    return (an or datetime.now(is_saat_dilimi())).astimezone(is_saat_dilimi()).date()
