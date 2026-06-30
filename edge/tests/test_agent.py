"""Edge ajan döngü adımı: ikinci okumada özet tampona yazılır."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from edge.agent import calistir, dongu_adimi, surucu_yap
from edge.ayar import EdgeAyar
from edge.paket import HamOkuma
from edge.tampon import Tampon


def test_ikinci_okumada_tampona_yazar(tmp_path: Path) -> None:
    ayar = EdgeAyar(makine_kodlari=["MAK-1"], tohum=3, tampon_yolu=str(tmp_path / "t.sqlite"))
    surucu = surucu_yap(ayar)
    tampon = Tampon(ayar.tampon_yolu)
    onceki: dict[str, HamOkuma] = {}
    onceki = dongu_adimi(surucu, tampon, onceki)  # ilk okuma — özet yok
    assert tampon.bekleyen_sayisi() == 0
    for _ in range(5):
        onceki = dongu_adimi(surucu, tampon, onceki)
    assert tampon.bekleyen_sayisi() >= 1  # üretim birikti → paketler tamponda


def test_surucu_yap_bilinmeyen_hata() -> None:
    with pytest.raises(ValueError, match="Bilinmeyen sürücü"):
        surucu_yap(EdgeAyar(surucu="yok"))


@pytest.mark.asyncio
async def test_calistir_temiz_kapanir(tmp_path: Path) -> None:
    # dur önceden set → döngü gövdesi atlanır; tamponu kapatma sırası hatasız olmalı.
    ayar = EdgeAyar(makine_kodlari=["MAK-1"], tampon_yolu=str(tmp_path / "t.sqlite"))
    dur = asyncio.Event()
    dur.set()
    await calistir(ayar, dur=dur)  # hata fırlatmamalı (regresyon: kapat→bekleyen_sayisi)
