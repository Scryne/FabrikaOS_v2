"""Webhook relay — outbox fan-out + imzalı HTTP teslimat (S18 / ADR-0020).

İki idempotent aşama; her tenant için kendi transaction'ında koşar:

1. **Fan-out** (``olaylari_fanout_et``): ``giden_olaylar.durum='beklemede'`` satırları,
   olay türüne abone **aktif** aboneliklere ``webhook_teslimatlari`` satırı olarak
   açılır; olay ``gonderildi`` işaretlenir (S18'den itibaren ``gonderildi`` = "fan-out
   yapıldı" — teslimat durumu satır başına ``webhook_teslimatlari``'nda yaşar).
   Eşleşen abonelik yoksa da olay tüketilmiş sayılır (0 teslimat).
2. **Teslimat** (``teslimatlari_gonder``): vadesi gelen satırlara imzalı POST atılır.
   2xx → ``basarili``; aksi hâlde backoff (``sonraki_deneme_gecikmesi_sn``) ile
   ``yeniden_denenecek``; deneme hakkı bitince terminal ``basarisiz``.

HTTP çağrıları teslimat transaction'ı içinde yapılır (satır başına durum güncellenir,
tur sonunda tek commit). ``PARTI_BOYU`` sınırı + 10 sn zaman aşımı bir turun süresini
sınırlar; kalan iş sonraki tura devreder. Relay hiçbir iş verisi okumaz — yalnız
outbox + webhook tabloları (kiracı-izole; ``search_path`` çağıran tarafından ayarlanır).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db.tenancy import search_path_ayarla
from app.core.olaylar import GidenOlay
from app.modules.entegrasyon.imza import (
    IMZA_BASLIGI,
    OLAY_BASLIGI,
    TESLIMAT_BASLIGI,
    imza_uret,
    sonraki_deneme_gecikmesi_sn,
    zarf_bytelari,
    zarf_olustur,
)
from app.modules.entegrasyon.models import WebhookAboneligi, WebhookTeslimati

logger = logging.getLogger("app.entegrasyon.relay")

HTTP_ZAMAN_ASIMI_SN = 10.0
PARTI_BOYU = 100  # tur başına işlenecek satır sınırı (olay ve teslimat ayrı ayrı)


async def olaylari_fanout_et(db: AsyncSession) -> int:
    """Bekleyen outbox olaylarını abonelik teslimatlarına açar; üretilen satır sayısını döner."""
    olaylar = (
        (
            await db.execute(
                select(GidenOlay)
                .where(GidenOlay.durum == "beklemede")
                .order_by(GidenOlay.id)
                .limit(PARTI_BOYU)
            )
        )
        .scalars()
        .all()
    )
    if not olaylar:
        return 0
    abonelikler = (
        (await db.execute(select(WebhookAboneligi).where(WebhookAboneligi.aktif))).scalars().all()
    )
    simdi = datetime.now(UTC)
    uretilen = 0
    for olay in olaylar:
        zarf = zarf_olustur(olay)
        for abonelik in abonelikler:
            # Boş olay_turleri listesi = tüm olaylara abone.
            if abonelik.olay_turleri and olay.olay_turu not in abonelik.olay_turleri:
                continue
            db.add(
                WebhookTeslimati(
                    abonelik_id=abonelik.id,
                    olay_id=olay.id,
                    olay_turu=olay.olay_turu,
                    govde=zarf,
                    sonraki_deneme_tarihi=simdi,
                )
            )
            uretilen += 1
        olay.durum = "gonderildi"
        olay.gonderim_tarihi = simdi
    await db.flush()
    return uretilen


async def teslimatlari_gonder(
    db: AsyncSession, *, http: httpx.AsyncClient, simdi: datetime | None = None
) -> int:
    """Vadesi gelen teslimatlara imzalı POST atar; işlenen satır sayısını döner."""
    simdi = simdi or datetime.now(UTC)
    teslimatlar = (
        (
            await db.execute(
                select(WebhookTeslimati)
                .where(
                    WebhookTeslimati.durum.in_(("beklemede", "yeniden_denenecek")),
                    WebhookTeslimati.sonraki_deneme_tarihi <= simdi,
                )
                .order_by(WebhookTeslimati.id)
                .limit(PARTI_BOYU)
            )
        )
        .scalars()
        .all()
    )
    for teslimat in teslimatlar:
        abonelik = await db.get(WebhookAboneligi, teslimat.abonelik_id)
        if abonelik is None or not abonelik.aktif:
            # Fan-out sonrası pasifleşmiş/silinmiş abonelik: deneme harcamadan terminal.
            teslimat.durum = "basarisiz"
            teslimat.yanit_ozeti = "abonelik pasif veya silinmiş"
            continue

        govde = zarf_bytelari(dict(teslimat.govde))
        zaman = int(simdi.timestamp())
        basliklar = {
            "Content-Type": "application/json",
            IMZA_BASLIGI: imza_uret(abonelik.gizli_anahtar, zaman, govde),
            OLAY_BASLIGI: teslimat.olay_turu,
            TESLIMAT_BASLIGI: str(teslimat.dis_anahtar),
        }
        teslimat.deneme_sayisi += 1
        teslimat.son_deneme_tarihi = simdi
        try:
            yanit = await http.post(abonelik.url, content=govde, headers=basliklar)
            teslimat.yanit_kodu = yanit.status_code
            teslimat.yanit_ozeti = yanit.text[:500]
            basarili = 200 <= yanit.status_code < 300
        except httpx.HTTPError as exc:
            teslimat.yanit_kodu = None
            teslimat.yanit_ozeti = f"bağlantı hatası: {exc}"[:500]
            basarili = False

        if basarili:
            teslimat.durum = "basarili"
        else:
            gecikme = sonraki_deneme_gecikmesi_sn(teslimat.deneme_sayisi)
            if gecikme is None:
                teslimat.durum = "basarisiz"  # deneme hakkı bitti — terminal
            else:
                teslimat.durum = "yeniden_denenecek"
                teslimat.sonraki_deneme_tarihi = simdi + timedelta(seconds=gecikme)
    await db.flush()
    return len(teslimatlar)


async def tenant_relay_turu(
    sm: async_sessionmaker[AsyncSession],
    slug: str,
    *,
    http: httpx.AsyncClient,
    simdi: datetime | None = None,
) -> tuple[int, int]:
    """Tek tenant için bir fan-out + teslimat turu; (fanout, islenen) sayılarını döner."""
    async with sm() as session, session.begin():
        await search_path_ayarla(session, slug)
        fanout = await olaylari_fanout_et(session)
        islenen = await teslimatlari_gonder(session, http=http, simdi=simdi)
    if fanout or islenen:
        logger.info("relay turu: tenant=%s fanout=%d teslimat=%d", slug, fanout, islenen)
    return fanout, islenen
