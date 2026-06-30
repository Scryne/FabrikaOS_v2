"""S8 ingestion mesaj çözücü (mesaj_coz) birim testleri — broker'sız, saf."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import pytest

from app.ingestion.isleyici import MesajGecersiz, mesaj_coz


def _payload() -> bytes:
    return json.dumps(
        {
            "olcum_id": str(uuid.uuid4()),
            "makine_kod": "MAK-1",
            "zaman": datetime.now(UTC).isoformat(),
            "vardiya": "A",
            "planlanan_sure_dk": 60,
            "durus_sure_dk": 5,
            "toplam_adet": 100,
            "saglam_adet": 98,
            "ideal_cevrim_sn": 30,
        }
    ).encode()


def test_gecerli_topic_ve_payload() -> None:
    slug, cihaz, paket = mesaj_coz("fabrikaos/alfa/GW-1/olcum", _payload())
    assert slug == "alfa"
    assert cihaz == "GW-1"
    assert paket.makine_kod == "MAK-1"


def test_bozuk_topic_reddedilir() -> None:
    with pytest.raises(MesajGecersiz):
        mesaj_coz("yanlis/alfa/GW-1/olcum", _payload())
    with pytest.raises(MesajGecersiz):
        mesaj_coz("fabrikaos/alfa/GW-1", _payload())


def test_gecersiz_slug_reddedilir() -> None:
    with pytest.raises(MesajGecersiz):
        mesaj_coz("fabrikaos/Gecersiz_Slug/GW-1/olcum", _payload())


def test_bozuk_payload_reddedilir() -> None:
    with pytest.raises(MesajGecersiz):
        mesaj_coz("fabrikaos/alfa/GW-1/olcum", b"{bozuk-json")
