"""OPC-UA sürücü iskeleti (Faz 5'te uygulanır).

Uygulama notu: ``asyncua`` istemcisiyle sunucuya bağlan, düğüm kimliklerini (NodeId)
``makine_kod``'a eşle, ``read_value`` ile sayaçları oku ve ``HamOkuma`` üret. mTLS için
istemci sertifikası + güven listesi yapılandır. Arayüz (``SahaSurucu.oku``) aynı kalır.
"""

from __future__ import annotations

from edge.paket import HamOkuma


class OpcUaSurucu:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self._args = args

    def oku(self) -> list[HamOkuma]:
        raise NotImplementedError(
            "OPC-UA sürücüsü Faz 5'te uygulanacak (asyncua + mTLS). "
            "MVP'de simülasyon sürücüsünü kullanın."
        )
