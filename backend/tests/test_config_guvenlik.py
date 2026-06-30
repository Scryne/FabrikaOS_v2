"""Yapılandırma güvenlik doğrulaması: üretimde güvensiz SECRET_KEY fail-fast reddedilir.

Saf birim testi (DB gerektirmez). Üretim ortamında varsayılan/zayıf secret ile açılış
engellenir; aksi hâlde JWT'ler taklit edilebilirdi.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import VARSAYILAN_SECRET, Settings


def test_prod_varsayilan_secret_reddedilir() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="prod", secret_key=VARSAYILAN_SECRET)


def test_prod_zayif_secret_reddedilir() -> None:
    # 32 karakterden kısa secret üretimde reddedilir.
    with pytest.raises(ValidationError):
        Settings(app_env="prod", secret_key="kisa-secret")


def test_prod_guclu_secret_kabul() -> None:
    ayar = Settings(app_env="prod", secret_key="g" * 48)
    assert ayar.is_prod is True
    assert ayar.secret_key == "g" * 48


def test_dev_varsayilan_secret_serbest() -> None:
    # Geliştirme/test ortamında varsayılan secret sorun değildir (fail-fast yalnız prod).
    ayar = Settings(app_env="dev", secret_key=VARSAYILAN_SECRET)
    assert ayar.is_prod is False
