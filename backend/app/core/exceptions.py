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
from sqlalchemy.exc import DBAPIError
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


class HizmetKullanilamaz(AppError):
    """Bağımlı bir altyapı (Redis, nesne deposu) geçici olarak yok (503, S28 / ADR-0047).

    500'den ayrılır: istemci "kalıcı hata" değil "geçici, birazdan yeniden dene" bilgisi alır;
    işlem yarım kalmamıştır (yazma yapılmadan reddedilir).
    """

    durum_kodu = 503
    hata_kodu = "HIZMET_KULLANILAMAZ"


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


# Girdinin kendisinden doğan veritabanı veri hataları (S28 sertleştirme, ADR-0047). Schemathesis
# taraması 76 uçta 500 buldu: sınırsız ``int`` parametresi (2**63) sürücüde, metindeki NUL baytı
# PostgreSQL'de reddediliyordu. Bunlar istemci hatasıdır → 422. Liste bilerek dar: sınıf 22'nin geri
# kalanı (ör. 22012 sıfıra bölme) sunucu kusurudur ve 500 olarak kalır.
_GIRDI_SQLSTATE = {
    "22003",  # numeric_value_out_of_range (int32/int64 sütun sınırı)
    "22021",  # character_not_in_repertoire (metinde NUL baytı)
    "22P02",  # invalid_text_representation
    "22P05",  # untranslatable_character (JSONB içinde \u0000)
}


def _girdi_veri_hatasi_mi(exc: DBAPIError) -> bool:
    kok = exc.orig.__cause__ if exc.orig is not None else None
    if kok is None:
        return False
    # asyncpg'nin istemci taraflı hatası: bağlanan parametre kodlanamadı, sorgu sunucuya hiç
    # gitmedi (ör. 2**63 bir BIGINT'e). Genel 22000 koduyla ve bu mesajla gelir.
    if str(kok).startswith("invalid input for query argument"):
        return True
    return getattr(kok, "sqlstate", None) in _GIRDI_SQLSTATE


def _butunluk_yaniti(exc: DBAPIError) -> JSONResponse | None:
    """Servis katmanının önceden yakalamadığı bütünlük ihlalleri (S28 yazma taraması).

    Hepsi istemcinin gönderdiği değerden doğar: var olmayan kayda referans, PATCH ile var olan bir
    ada yeniden adlandırma, zorunlu alana açık ``null``. Sunucu kusuru sayılmaz, 500 dönmez.
    """
    kok = exc.orig.__cause__ if exc.orig is not None else None
    kod = getattr(kok, "sqlstate", None)
    sutun = getattr(kok, "column_name", None)
    if kod == "23503":
        if str(kok).startswith("update or delete"):  # silinen kayda başka kayıtlar bağlı
            return _hata_yaniti(
                409, "Bu kayda bağlı başka kayıtlar var; önce onları kaldırın", "BAGLI_KAYIT", []
            )
        return _hata_yaniti(
            422, "Seçilen ilişkili kayıtlardan biri bulunamadı", "GECERSIZ_REFERANS", []
        )
    if kod == "23505":
        return _hata_yaniti(409, "Bu değerle başka bir kayıt zaten var", "CAKISMA", [])
    if kod == "23502":
        detay = [{"alan": sutun, "mesaj": "Bu alan boş bırakılamaz"}] if sutun else []
        return _hata_yaniti(422, "Zorunlu bir alan boş gönderildi", "DOGRULAMA", detay)
    return None


async def _db_veri_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DBAPIError)
    butunluk = _butunluk_yaniti(exc)
    if butunluk is not None:
        logger.warning("Bütünlük ihlali (istemci girdisi): %s %s", request.url.path, exc.orig)
        return butunluk
    if not _girdi_veri_hatasi_mi(exc):
        return await _beklenmeyen_handler(request, exc)
    logger.warning("Geçersiz girdi değeri (DB): %s %s", request.url.path, exc.orig)
    return _hata_yaniti(
        422,
        "Girilen değerlerden biri geçerli aralıkta ya da biçimde değil",
        "GECERSIZ_DEGER",
        [],
    )


async def _beklenmeyen_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Beklenmeyen hata: %s", exc)
    return _hata_yaniti(500, "Sunucu hatası", "SUNUCU", [])


def hata_handlerlari_kaydet(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(DBAPIError, _db_veri_handler)
    app.add_exception_handler(Exception, _beklenmeyen_handler)
