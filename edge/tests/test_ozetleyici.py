"""Edge aralık özetleyici: sayaç deltası → OlcumPaketi."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from edge.ozetleyici import ozetle
from edge.paket import HamOkuma


def _okuma(t: datetime, toplam: int, saglam: int, durus: float) -> HamOkuma:
    return HamOkuma(
        makine_kod="MAK-1",
        zaman=t,
        toplam_sayac=toplam,
        saglam_sayac=saglam,
        durus_dk_sayac=durus,
        ideal_cevrim_sn=30.0,
    )


def test_delta_ve_aralik_hesabi() -> None:
    t0 = datetime(2026, 6, 30, 8, 0, tzinfo=UTC)
    t1 = t0 + timedelta(minutes=60)
    p = ozetle(_okuma(t0, 100, 95, 2.0), _okuma(t1, 250, 240, 5.0), vardiya="A")
    assert p.toplam_adet == 150
    assert p.saglam_adet == 145
    assert p.durus_sure_dk == 3.0
    assert p.planlanan_sure_dk == 60.0
    assert p.makine_kod == "MAK-1"
    assert p.vardiya == "A"


def test_her_paket_benzersiz_id() -> None:
    t0 = datetime(2026, 6, 30, 8, 0, tzinfo=UTC)
    t1 = t0 + timedelta(minutes=10)
    a = ozetle(_okuma(t0, 0, 0, 0.0), _okuma(t1, 10, 10, 0.0))
    b = ozetle(_okuma(t0, 0, 0, 0.0), _okuma(t1, 10, 10, 0.0))
    assert a.olcum_id != b.olcum_id
