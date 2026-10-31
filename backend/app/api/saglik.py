"""Sağlık (health) ve metrik uçları — kimlik/tenant gerektirmez."""

from __future__ import annotations

import asyncio
import hmac
import time
from typing import Any

from fastapi import APIRouter, Header, Response
from opentelemetry.instrumentation.utils import suppress_instrumentation
from sqlalchemy import text

from app import __version__
from app.core.config import get_settings
from app.core.db.session import get_engine
from app.core.exceptions import KimlikHatasi
from app.core.metrikler import metrik_ciktisi
from app.core.responses import Zarf, basari
from app.core.security.redis_istemci import get_redis

router = APIRouter(tags=["Sağlık"])

# Hazırlık yoklaması bir bağımlılık asılı kaldığında da hızlı dönmeli: orkestratör (Traefik/
# K8s) bu ucu saniyeler içinde bekler; 30 sn'lik varsayılan bağlantı zaman aşımı yoklamayı
# kilitler.
HAZIRLIK_ZAMAN_ASIMI_SN = 2.0


@router.get("/saglik", response_model=Zarf[dict[str, Any]], summary="Canlılık (liveness)")
async def saglik() -> dict[str, Any]:
    ayar = get_settings()
    return basari(
        {
            "durum": "ayakta",
            "uygulama": ayar.app_name,
            "surum": __version__,
            "ortam": ayar.app_env,
        },
        mesaj="Servis ayakta",
    )


async def _db_yokla() -> None:
    # Yoklama yolu iz üretmez (``_HARIC_URL``); bastırılmazsa her yoklamanın ``SELECT 1``'i
    # sahipsiz bir kök iz olarak Jaeger'i doldurur (canlı turda görüldü).
    with suppress_instrumentation():
        async with get_engine().connect() as baglanti:
            await baglanti.execute(text("SELECT 1"))


async def _redis_yokla() -> None:
    await get_redis().ping()


async def _yokla(ad: str, islem: Any) -> dict[str, Any]:
    baslangic = time.perf_counter()
    try:
        await asyncio.wait_for(islem(), timeout=HAZIRLIK_ZAMAN_ASIMI_SN)
    except TimeoutError:
        return {"ad": ad, "durum": "zaman_asimi", "sure_ms": round(HAZIRLIK_ZAMAN_ASIMI_SN * 1000)}
    except Exception as exc:  # noqa: BLE001 — bağımlılık hatası yanıta dönüşür, yükselmez
        return {"ad": ad, "durum": "hata", "hata": type(exc).__name__}
    return {
        "ad": ad,
        "durum": "ayakta",
        "sure_ms": round((time.perf_counter() - baslangic) * 1000, 1),
    }


@router.get(
    "/saglik/hazir",
    response_model=Zarf[dict[str, Any]],
    summary="Hazırlık (readiness): veritabanı + Redis",
    responses={503: {"description": "En az bir bağımlılık hazır değil"}},
)
async def hazir(response: Response) -> dict[str, Any]:
    kontroller = list(
        await asyncio.gather(_yokla("veritabani", _db_yokla), _yokla("redis", _redis_yokla))
    )
    hazir_mi = all(k["durum"] == "ayakta" for k in kontroller)
    govde = basari(
        {"hazir": hazir_mi, "kontroller": kontroller},
        mesaj="Servis hazır" if hazir_mi else "Servis hazır değil",
    )
    if not hazir_mi:
        # Durum kodu ile zarf aynı şeyi söylemeli: 503 + success=false (veri yine dönülür ki
        # hangi bağımlılığın düştüğü yanıtta görünsün).
        response.status_code = 503
        govde["success"] = False
    return govde


@router.get("/metrics", include_in_schema=False)
async def metrikler(authorization: str | None = Header(default=None)) -> Response:
    """Prometheus kazıma ucu. ``METRIK_TOKEN`` tanımlıysa Bearer token ister."""
    token = get_settings().metrik_token
    if token:
        beklenen = f"Bearer {token}"
        if not authorization or not hmac.compare_digest(authorization, beklenen):
            raise KimlikHatasi("Metrik ucu için geçerli token gerekli")
    govde, tur = metrik_ciktisi()
    return Response(govde, media_type=tur)
