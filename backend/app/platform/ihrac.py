"""KVKK tenant veri ihracı — arka plan ZIP üretimi (S17 / ADR-0019).

S14 rapor deseninin control-plane aynası: ``POST /platform/tenantlar/{id}/ihrac``
``kuyrukta`` durumlu bir ``TenantIhrac`` açar, router commit'ten sonra
``uretim_planla`` ile arka plan görevini başlatır ve 202 döner.

"Eksiksizlik" garantisi şemaya değil KEŞFE bağlıdır: tenant şemasındaki tablolar
``information_schema``'dan okunur — gelecek sprintlerde eklenen modül tabloları
otomatik kapsanır. Public control-plane kayıtları (tenant/abonelik/haklar/bayraklar)
ayrıca eklenir. Artefakt anahtarı ``platform/ihrac/...`` önekiyle tenant
(``tenant_<slug>/...``) düzleminin DIŞINDA tutulur: ihraç control-plane'e aittir.

Testler ``oturum_fabrikasi_ayarla`` + ``es_zamanli_ayarla(True)`` enjeksiyonlarını
kullanır (S13/S14 imzaları).
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import zipfile
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.control_plane.models import TenantIhrac
from app.core.db.session import get_sessionmaker
from app.core.db.tenancy import sema_adi
from app.modules.dys.depolama import nesne_depo_al

logger = logging.getLogger("app.platform.ihrac")

_oturum_fabrikasi: async_sessionmaker[AsyncSession] | None = None
_es_zamanli = False
_gorevler: set[asyncio.Task[None]] = set()


def oturum_fabrikasi_ayarla(fabrika: async_sessionmaker[AsyncSession] | None) -> None:
    """Arka plan görevlerinin oturum fabrikasını enjekte eder (testler için)."""
    global _oturum_fabrikasi
    _oturum_fabrikasi = fabrika


def es_zamanli_ayarla(deger: bool) -> None:
    """``True`` iken ihraç görevi beklenerek koşar (deterministik testler için)."""
    global _es_zamanli
    _es_zamanli = deger


def _fabrika() -> async_sessionmaker[AsyncSession]:
    return _oturum_fabrikasi if _oturum_fabrikasi is not None else get_sessionmaker()


def ihrac_nesne_anahtari(slug: str, ihrac_id: int) -> str:
    """Control-plane artefakt anahtarı: ``platform/ihrac/<slug>/<id>/<dosya>``."""
    return f"platform/ihrac/{slug}/{ihrac_id}/tenant-{slug}-ihrac-{ihrac_id}.zip"


def _json_bayt(veri: Any) -> bytes:
    # default=str: datetime/Decimal/UUID gibi tipler kayıpsız metinleşir.
    return json.dumps(veri, ensure_ascii=False, default=str, indent=1).encode("utf-8")


def _zip_uret(dosyalar: dict[str, bytes]) -> bytes:
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        for ad, icerik in dosyalar.items():
            z.writestr(ad, icerik)
    return tampon.getvalue()


async def _satirlar(db: AsyncSession, sql: str, /, **params: Any) -> list[dict[str, Any]]:
    sonuc = await db.execute(text(sql), params)
    return [dict(m) for m in sonuc.mappings().all()]


async def uretim_planla(ihrac_id: int) -> None:
    """İhraç üretimini arka plana atar (test modunda bekler)."""
    if _es_zamanli:
        await ihrac_calistir(ihrac_id)
        return
    gorev = asyncio.create_task(ihrac_calistir(ihrac_id))
    _gorevler.add(gorev)
    gorev.add_done_callback(_gorevler.discard)


async def ihrac_calistir(ihrac_id: int) -> None:
    """Arka plan ihraç üretimi — kendi oturumu; asla exception sızdırmaz."""
    try:
        await _uret_dene(ihrac_id)
    except Exception as exc:  # noqa: BLE001 — arka plan görevi süreci düşürmemeli
        logger.warning("tenant ihracı başarısız (kayit=%s): %s", ihrac_id, exc)
        await _basarisiz_isaretle(ihrac_id, exc)


async def _uret_dene(ihrac_id: int) -> None:
    async with _fabrika()() as db:
        kayit = await db.get(TenantIhrac, ihrac_id)
        if kayit is None:
            raise RuntimeError(f"İhraç kaydı bulunamadı: {ihrac_id}")
        kayit.durum = "hazirlaniyor"
        await db.commit()

        dosyalar: dict[str, bytes] = {}
        tablo_satirlari: dict[str, int] = {}

        # 1) Public control-plane kayıtları (tenant'a ait olanlar).
        public_paketi = {
            "tenant": await _satirlar(
                db, "SELECT * FROM public.tenant WHERE id = :tid", tid=kayit.tenant_id
            ),
            "abonelik": await _satirlar(
                db, "SELECT * FROM public.abonelik WHERE tenant_id = :tid", tid=kayit.tenant_id
            ),
            "modul_haklari": await _satirlar(
                db,
                "SELECT * FROM public.modul_haklari WHERE tenant_id = :tid",
                tid=kayit.tenant_id,
            ),
            "ozellik_bayraklari": await _satirlar(
                db,
                "SELECT * FROM public.ozellik_bayraklari WHERE tenant_id = :tid",
                tid=kayit.tenant_id,
            ),
        }
        for ad, satirlar in public_paketi.items():
            dosyalar[f"public/{ad}.json"] = _json_bayt(satirlar)

        # 2) Tenant şemasının TÜM tabloları (keşif — gelecek modüller otomatik kapsanır).
        sema = sema_adi(kayit.slug)
        tablolar = await _satirlar(
            db,
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = :sema AND table_type = 'BASE TABLE' ORDER BY table_name",
            sema=sema,
        )
        if not tablolar:
            raise RuntimeError(f"Tenant şeması boş veya yok: {sema}")
        for satir in tablolar:
            tablo = str(satir["table_name"])
            # Şema+tablo adları information_schema'dan gelir ve tırnaklanır
            # (sema_adi doğrulamalı) — control-plane çapraz-şema istisnası.
            veriler = await _satirlar(db, f'SELECT * FROM "{sema}"."{tablo}"')
            dosyalar[f"tenant/{tablo}.json"] = _json_bayt(veriler)
            tablo_satirlari[tablo] = len(veriler)

        dosyalar["manifest.json"] = _json_bayt(
            {
                "slug": kayit.slug,
                "ihrac_id": kayit.id,
                "olusturma_tarihi": kayit.olusturma_tarihi,
                "tenant_tablolari": tablo_satirlari,
                "public_kayitlari": {ad: len(s) for ad, s in public_paketi.items()},
            }
        )

        veri = await asyncio.to_thread(_zip_uret, dosyalar)
        anahtar = ihrac_nesne_anahtari(kayit.slug, kayit.id)
        depo = nesne_depo_al()
        await asyncio.to_thread(depo.yukle, anahtar, veri, "application/zip")

        kayit.durum = "hazir"
        kayit.nesne_anahtari = anahtar
        kayit.boyut = len(veri)
        kayit.tablo_sayisi = len(tablo_satirlari)
        await db.commit()
    logger.info(
        "tenant ihracı üretildi (slug=%s, tablo=%s, bayt=%s)",
        kayit.slug,
        kayit.tablo_sayisi,
        len(veri),
    )


async def _basarisiz_isaretle(ihrac_id: int, hata: Exception) -> None:
    try:
        async with _fabrika()() as db:
            kayit = await db.get(TenantIhrac, ihrac_id)
            if kayit is None:
                return
            kayit.durum = "basarisiz"
            kayit.hata = str(hata)[:1000]
            await db.commit()
    except Exception:  # noqa: BLE001 — işaretleme de düşerse yalnız logla
        logger.exception("başarısız ihraç kaydı işaretlenemedi (kayit=%s)", ihrac_id)


async def ihrac_icerik_indir(kayit: TenantIhrac) -> bytes:
    """Hazır ihracın ZIP baytlarını nesne deposundan okur."""
    if kayit.nesne_anahtari is None:
        raise RuntimeError("İhraç kaydının nesne anahtarı yok")
    depo = nesne_depo_al()
    return await asyncio.to_thread(depo.indir, kayit.nesne_anahtari)
