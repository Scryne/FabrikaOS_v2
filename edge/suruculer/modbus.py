"""Modbus TCP sürücü iskeleti (Faz 5'te uygulanır).

Uygulama notu: ``pymodbus`` ile holding/input register'ları oku, register→sayaç
ölçeklemesini ``makine_kod`` başına yapılandır ve ``HamOkuma`` üret. Arayüz aynı kalır.
"""

from __future__ import annotations

from edge.paket import HamOkuma


class ModbusSurucu:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self._args = args

    def oku(self) -> list[HamOkuma]:
        raise NotImplementedError(
            "Modbus sürücüsü Faz 5'te uygulanacak (pymodbus). "
            "MVP'de simülasyon sürücüsünü kullanın."
        )
