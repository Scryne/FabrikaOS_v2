"""İş günü penceresi: 00:00-03:00 arasında kayıt pencerenin dışında kalmamalı."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from app.core.zaman import gun_araligi, is_gunu


def test_gun_siniri_is_saat_diliminde() -> None:
    bas, bit = gun_araligi(date(2026, 11, 4))
    assert bas.astimezone(UTC) == datetime(2026, 11, 3, 21, 0, tzinfo=UTC)
    assert bit.astimezone(UTC) == datetime(2026, 11, 4, 21, 0, tzinfo=UTC)
    assert bit - bas == timedelta(days=1)


@pytest.mark.parametrize(
    "an",
    [
        datetime(2026, 11, 3, 21, 0, tzinfo=UTC),  # İstanbul 00:00
        datetime(2026, 11, 3, 21, 30, tzinfo=UTC),  # İstanbul 00:30, hatanın penceresi
        datetime(2026, 11, 3, 23, 59, tzinfo=UTC),  # İstanbul 02:59
        datetime(2026, 11, 4, 0, 0, tzinfo=UTC),  # İstanbul 03:00
        datetime(2026, 11, 4, 12, 0, tzinfo=UTC),
        datetime(2026, 11, 4, 20, 59, tzinfo=UTC),  # İstanbul 23:59
    ],
)
def test_an_kendi_is_gununun_penceresinde(an: datetime) -> None:
    bas, bit = gun_araligi(is_gunu(an))
    assert bas <= an < bit


def test_varsayilan_bugunun_penceresi() -> None:
    bas, bit = gun_araligi()
    assert (bas, bit) == gun_araligi(is_gunu())
    assert bas <= datetime.now(UTC) < bit
