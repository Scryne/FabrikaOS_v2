"""Tek tip hata yönetimi.

Tüm hatalar standart hata zarfıyla döner:
    {"success": false, "message": "...", "hata_kodu": "...", "detaylar": [{"alan","mesaj"}]}
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.exceptions")


class AppError(Exception):
    """Uygulama hataları için temel sınıf."""

    durum_kodu: int = 400
    hata_kodu: str = "HATA"

    def __init__(
        self,
        mesaj: str,
        *,
        hata_kodu: str | None = None,
        durum_kodu: int | None = None,
        detaylar: list[dict[str, Any]] | None = None,
    ) -> None:
        self.mesaj = mesaj
        if hata_kodu is not None:
            self.hata_kodu = hata_kodu
        if durum_kodu is not None:
            self.durum_kodu = durum_kodu
        self.detaylar: list[dict[str, Any]] = detaylar or []
        super().__init__(mesaj)


class KimlikHatasi(AppError):
    durum_kodu = 401
    hata_kodu = "KIMLIK"


class YetkiHatasi(AppError):
    durum_kodu = 403
    hata_kodu = "YETKISIZ"


class KaynakBulunamadi(AppError):
    durum_kodu = 404
    hata_kodu = "BULUNAMADI"


class CakismaHatasi(AppError):
    durum_kodu = 409
    hata_kodu = "CAKISMA"


class SureDoldu(AppError):
    """Kaynak vardı ama saklama süresi dolduğu için kalıcı olarak kaldırıldı (410 Gone).

    404'ten ayrılır: istemciye "böyle bir kayıt hiç yoktu" değil, "vardı, süresi doldu,
    yeniden talep et" bilgisi verilir (KVKK ihraç artefaktları — S23/ADR-0022).
    """

    durum_kodu = 410
    hata_kodu = "SURE_DOLDU"


class DogrulamaHatasi(AppError):
    durum_kodu = 422
    hata_kodu = "DOGRULAMA"


def _hata_yaniti(
    durum_kodu: int, mesaj: str, hata_kodu: str, detaylar: list[dict[str, Any]]
) -> JSONResponse:
    return JSONResponse(
        status_code=durum_kodu,
        content={
            "success": False,
            "message": mesaj,
            "hata_kodu": hata_kodu,
            "detaylar": detaylar,
        },
    )


async def _app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return _hata_yaniti(exc.durum_kodu, exc.mesaj, exc.hata_kodu, exc.detaylar)


async def _http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    return _hata_yaniti(exc.status_code, str(exc.detail), "HTTP", [])


async def _validation_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    detaylar = [
        {"alan": ".".join(str(p) for p in err.get("loc", [])), "mesaj": err.get("msg", "")}
        for err in exc.errors()
    ]
    return _hata_yaniti(422, "Doğrulama hatası", "DOGRULAMA", detaylar)


async def _beklenmeyen_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Beklenmeyen hata: %s", exc)
    return _hata_yaniti(500, "Sunucu hatası", "SUNUCU", [])


def hata_handlerlari_kaydet(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(Exception, _beklenmeyen_handler)
