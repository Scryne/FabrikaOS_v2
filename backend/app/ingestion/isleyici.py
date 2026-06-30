"""Saf mesaj çözme/doğrulama — broker'a ve DB'ye bağımsız (kolayca test edilir).

Topic biçimi: ``fabrikaos/<tenant_slug>/<cihaz_kod>/olcum``.
"""

from __future__ import annotations

from pydantic import ValidationError

from app.core.db.tenancy import slug_gecerli_mi
from app.modules.saha.schemas import OlcumPaketi

_KOK = "fabrikaos"
_SON = "olcum"


class MesajGecersiz(Exception):
    """Topic veya payload sözleşmeye uymuyor → mesaj güvenle düşürülür."""


def mesaj_coz(topic: str, payload: bytes) -> tuple[str, str, OlcumPaketi]:
    """``(tenant_slug, cihaz_kod, OlcumPaketi)`` döndürür; uymazsa ``MesajGecersiz``."""
    parcalar = topic.split("/")
    if len(parcalar) != 4 or parcalar[0] != _KOK or parcalar[3] != _SON:
        raise MesajGecersiz(f"Beklenmeyen topic: {topic!r}")
    _, slug, cihaz_kod, _ = parcalar
    if not slug_gecerli_mi(slug):
        raise MesajGecersiz(f"Geçersiz tenant slug: {slug!r}")
    if not cihaz_kod:
        raise MesajGecersiz("Cihaz kodu boş")
    try:
        paket = OlcumPaketi.model_validate_json(payload)
    except ValidationError as exc:
        raise MesajGecersiz("Ölçüm payload doğrulanamadı") from exc
    return slug, cihaz_kod, paket
