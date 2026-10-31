"""Zamanlanmış taramalar (S26-A, ADR-0025): tarih geçtiğinde kendiliğinden doğan olaylar.

Sözleşme bitişi, iş emri SLA'sı ve kalibrasyon geçerliliği bir kullanıcı eylemiyle değil, zamanın
geçmesiyle olay üretir. Üçünün de tarama fonksiyonu kenar tetiklidir (aynı kayıt için ikinci kez
olay yazmaz); bu yüzden sık koşmak güvenlidir, yalnız gereksizdir. Bildirim üreticisi bunları
``--tarama-araligi`` (varsayılan 15 dk) aralıkla, tenant başına ve tarama başına ayrı
transaction'da çağırır: bir taramanın hatası diğerlerini ve bildirim turunu durdurmaz.

Bakım vadesi (``bakim.service.vade_tara``) burada değil: olay değil iş emri üretir ve bir
kullanıcı kimliği ister; o karar bakım modülünde kalır.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db.tenancy import search_path_ayarla
from app.core.hata_izleme import hata_bildir
from app.modules.isemri.service import sla_tara
from app.modules.kalite.spc_service import kalibrasyon_tara
from app.modules.sozlesme.service import yaklasan_tara

logger = logging.getLogger("app.bildirim.zamanli")

Tarama = Callable[[AsyncSession, str], Awaitable[int]]

TARAMALAR: dict[str, Tarama] = {
    "sozlesme.yaklasiyor": lambda db, slug: yaklasan_tara(db, tenant_slug=slug),
    "sla.asildi": lambda db, slug: sla_tara(db, tenant_slug=slug),
    "kalibrasyon.yaklasiyor": lambda db, slug: kalibrasyon_tara(db, tenant_slug=slug),
}


async def tenant_zamanli_taramalar(
    sm: async_sessionmaker[AsyncSession], slug: str
) -> dict[str, int | None]:
    """Tenant'ta her taramayı ayrı transaction'da koşar; ad → işlenen kayıt (hata: ``None``)."""
    sonuc: dict[str, int | None] = {}
    for ad, tarama in TARAMALAR.items():
        try:
            async with sm() as session, session.begin():
                await search_path_ayarla(session, slug)
                sonuc[ad] = await tarama(session, slug)
        except Exception as exc:  # noqa: BLE001 — bir tarama diğerlerini düşürmez
            sonuc[ad] = None
            hata_bildir(exc)
            logger.exception("zamanlı tarama hatası: tenant=%s tarama=%s", slug, ad)
    if any(sonuc.values()):
        logger.info("zamanlı taramalar: tenant=%s %s", slug, sonuc)
    return sonuc
