"""İş günü (S27-B düzeltmesi): takvim günü UTC değil, Türkiye günüdür."""

from __future__ import annotations

from datetime import UTC, date, datetime

from app.core.zaman import is_gunu


def test_utc_gece_yarisi_oncesi_turkiyede_ertesi_gun() -> None:
    # 31 Ekim 22:30 UTC = 1 Kasım 01:30 İstanbul.
    assert is_gunu(datetime(2026, 10, 31, 22, 30, tzinfo=UTC)) == date(2026, 11, 1)
    assert is_gunu(datetime(2026, 10, 31, 20, 59, tzinfo=UTC)) == date(2026, 10, 31)
    assert isinstance(is_gunu(), date)
