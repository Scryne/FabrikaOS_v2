"""İstek ortasında commit → ``search_path`` kaybı koruması (tenant izolasyonu, R3).

``set_config('search_path', ..., is_local=true)`` **işlem kapsamlıdır**: commit ile düşer.
Bu bilinçli bir tercihtir (bağlantı havuza dönerken sızmasın — ADR-0003). Ama istek
ORTASINDA commit eden bir uç, sonraki sorgularını şemasız çalıştırır: sorgu ya hata verir
ya da ``public``e düşerek **yanlış veriye** dokunur.

Koruma: ``after_begin`` oturum kancası, doğrulanmış tenant bağlamı varsa her yeni işlemde
``search_path``'i yeniden kurar. Bu dosya korumanın çalıştığını ve **ham başlıkla
kandırılamayacağını** sınar.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.context import cozulmus_tenant_ctx, tenant_slug_ctx
from app.core.db.tenancy import search_path_ayarla
from tests.conftest import ALFA
from tests.test_s16_entitlement import _giris


async def _search_path(db: object) -> str:
    sonuc = await db.execute(text("SHOW search_path"))  # type: ignore[attr-defined]
    return str(sonuc.scalar_one())


async def test_commit_sonrasi_search_path_otomatik_geri_gelir(
    test_db: str, test_engine: AsyncEngine
) -> None:
    """SÖZLEŞME: commit sonrası ilk sorgu yine tenant şemasında koşar."""
    jeton = cozulmus_tenant_ctx.set("alfa")
    try:
        sm = async_sessionmaker(test_engine, expire_on_commit=False)
        async with sm() as db:
            await search_path_ayarla(db, "alfa")
            assert "tenant_alfa" in await _search_path(db)

            await db.commit()  # SET LOCAL düşer

            # Kanca devrede: yeni işlem açılır açılmaz şema geri kurulmalı.
            assert "tenant_alfa" in await _search_path(db), (
                "commit sonrası search_path geri gelmedi — tenant izolasyonu riski"
            )
            # Şemaya bağlı bir tablo hâlâ görülebiliyor olmalı.
            await db.execute(text("SELECT count(*) FROM kullanici"))
    finally:
        cozulmus_tenant_ctx.reset(jeton)


async def test_tenant_baglami_yokken_kanca_calismaz(test_db: str, test_engine: AsyncEngine) -> None:
    """Control-plane (platform) istekleri ``public`` kapsamında kalmalı — düzlem ayrımı."""
    jeton = cozulmus_tenant_ctx.set(None)
    try:
        sm = async_sessionmaker(test_engine, expire_on_commit=False)
        async with sm() as db:
            await db.execute(text("SELECT 1"))
            yol = await _search_path(db)
            assert "tenant_" not in yol, f"tenant bağlamı yokken şema set edildi: {yol}"
    finally:
        cozulmus_tenant_ctx.reset(jeton)


async def test_HAM_baslik_ile_sema_secilemez(test_db: str, test_engine: AsyncEngine) -> None:
    """Güvenlik: kanca ham ``X-Tenant`` başlığını DEĞİL, doğrulanmış slug'ı okur.

    Aksi hâlde istemci başlığa istediği tenant'ı yazarak, doğrulamadan geçmeden o şemayı
    seçtirebilirdi. Burada log korelasyonu için kullanılan ham contextvar 'beta' iken
    doğrulanmış bağlam boştur → şema ayarlanmamalıdır.
    """
    ham = tenant_slug_ctx.set("beta")
    dogrulanmis = cozulmus_tenant_ctx.set(None)
    try:
        sm = async_sessionmaker(test_engine, expire_on_commit=False)
        async with sm() as db:
            await db.execute(text("SELECT 1"))
            yol = await _search_path(db)
            assert "tenant_beta" not in yol, f"ham başlık şema seçtirdi: {yol}"
    finally:
        tenant_slug_ctx.reset(ham)
        cozulmus_tenant_ctx.reset(dogrulanmis)


@pytest.mark.parametrize(
    ("yol", "yontem"),
    [
        ("/api/v1/kvkk/ihraclar/temizle", "post"),  # istek içinde commit eden uç
    ],
)
async def test_commit_eden_uclar_dogru_semada_kalir(
    test_db: str, kurulu_istemci: AsyncClient, yol: str, yontem: str
) -> None:
    """İstek içinde commit eden uçlar 500 vermeden tamamlanmalı (şema kaybolmamalı).

    Bu testin kırılması, o uçtaki commit'ten sonra sorguların tenant şemasını
    göremediği anlamına gelir — 'relation does not exist' ya da sessizce yanlış veri.
    """
    h = await _giris(kurulu_istemci, ALFA)
    cevap = await getattr(kurulu_istemci, yontem)(yol, headers=h)
    assert cevap.status_code == 200, cevap.text
