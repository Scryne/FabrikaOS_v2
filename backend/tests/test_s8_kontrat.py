"""S8 ölçüm kontratı (OlcumPaketi) doğrulama birim testleri."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.modules.saha.schemas import OlcumPaketi


def _gecerli() -> dict:
    return {
        "olcum_id": str(uuid.uuid4()),
        "makine_kod": "MAK-1",
        "zaman": datetime.now(UTC).isoformat(),
        "vardiya": "A",
        "planlanan_sure_dk": 60.0,
        "durus_sure_dk": 5.0,
        "toplam_adet": 100,
        "saglam_adet": 98,
        "ideal_cevrim_sn": 30.0,
    }


def test_gecerli_paket_dogrulanir() -> None:
    p = OlcumPaketi.model_validate(_gecerli())
    assert p.makine_kod == "MAK-1"
    assert p.toplam_adet == 100


def test_saglam_toplamdan_buyuk_olamaz() -> None:
    veri = _gecerli() | {"saglam_adet": 200}
    with pytest.raises(ValidationError):
        OlcumPaketi.model_validate(veri)


def test_negatif_adet_reddedilir() -> None:
    with pytest.raises(ValidationError):
        OlcumPaketi.model_validate(_gecerli() | {"toplam_adet": -1})


def test_json_round_trip() -> None:
    p = OlcumPaketi.model_validate(_gecerli())
    geri = OlcumPaketi.model_validate_json(p.model_dump_json())
    assert geri.olcum_id == p.olcum_id
