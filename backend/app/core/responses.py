"""Standart başarı yanıtı zarfı + sayfalama.

Zarf üst anahtarları İngilizce (plan ile tutarlı), domain/meta alanları Türkçe-ASCII:
    {"success": true, "message": "...", "data": {...},
     "meta": {"sayfa": 1, "adet": 20, "toplam": 137}}
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SayfaMeta(BaseModel):
    sayfa: int
    adet: int
    toplam: int


class Zarf[T](BaseModel):
    """OpenAPI/Swagger'da yanıt şemasını belgelemek için jenerik zarf."""

    success: bool = True
    message: str = "İşlem başarılı"
    data: T | None = None
    meta: SayfaMeta | None = None


def basari(
    data: Any = None,
    *,
    mesaj: str = "İşlem başarılı",
    meta: dict[str, Any] | SayfaMeta | None = None,
) -> dict[str, Any]:
    """Başarı zarfı dict'i üretir."""
    govde: dict[str, Any] = {"success": True, "message": mesaj, "data": data}
    if meta is not None:
        govde["meta"] = meta.model_dump() if isinstance(meta, SayfaMeta) else meta
    return govde


def sayfalama_meta(sayfa: int, adet: int, toplam: int) -> dict[str, int]:
    return {"sayfa": sayfa, "adet": adet, "toplam": toplam}


def sayfali(
    kayitlar: list[Any], *, sayfa: int, adet: int, toplam: int, mesaj: str = "İşlem başarılı"
) -> dict[str, Any]:
    """Sayfalı liste yanıtı (data + meta) üretir."""
    return basari(kayitlar, mesaj=mesaj, meta=sayfalama_meta(sayfa, adet, toplam))
