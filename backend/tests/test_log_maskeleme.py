"""Log akışına sorgu parametresindeki access token düz metin düşmez (WS ``?token=``)."""

from __future__ import annotations

import json
import logging

from app.core.logging import JsonFormatter, gizli_maskele

JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.imza"


def test_ws_token_maskelenir_diger_parametre_kalir() -> None:
    satir = f'127.0.0.1:1 - "WebSocket /api/v1/ws/olaylar?token={JWT}&tenant=demo" [accepted]'
    maskeli = gizli_maskele(satir)
    assert JWT not in maskeli
    assert "token=[gizli]&tenant=demo" in maskeli


def test_json_formatlayici_mesaji_maskeler() -> None:
    kayit = logging.LogRecord(
        "uvicorn.access", logging.INFO, __file__, 1, "%s", (f"GET /x?access_token={JWT}",), None
    )
    mesaj = json.loads(JsonFormatter().format(kayit))["mesaj"]
    assert JWT not in mesaj
    assert mesaj.endswith("access_token=[gizli]")


def test_tokensiz_satir_degismez() -> None:
    satir = 'GET /api/v1/makineler?sayfa=1&adet=20 HTTP/1.1" 200'
    assert gizli_maskele(satir) == satir
