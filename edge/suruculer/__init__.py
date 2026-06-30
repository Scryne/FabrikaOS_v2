"""Saha sürücüsü arayüzü. Yeni protokoller (OPC-UA/Modbus) bu Protocol'ü uygular."""

from __future__ import annotations

from typing import Protocol

from edge.paket import HamOkuma


class SahaSurucu(Protocol):
    """Bir veri kaynağından makine sayaç görüntülerini okur."""

    def oku(self) -> list[HamOkuma]:
        """Köprülenen her makine için güncel ham okumayı döndürür."""
        ...
