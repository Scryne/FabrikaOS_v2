"""İzin/rol kataloğu ↔ tenant şeması uzlaştırması (sürüklenme koruması).

Bu dosya **kalıcı bir sözleşme testidir**: her sprint izin kataloğuna yeni kod ekler
(`denetim:oku`, `stok:duzeltme`, `finans:onay`…). Mevcut tenant'lara inmeyen bir kod
sessizce 403 üretir. Buradaki testler o sürüklenmeyi CI'da yakalar.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.control_plane.models import Tenant
from app.control_plane.uzlastirma import izin_rol_uzlastir, tum_tenantlari_uzlastir
from app.core.db.tenancy import search_path_ayarla
from app.kimlik.izinler import IZIN_KATALOGU, VARSAYILAN_ROLLER
from app.kimlik.models import Izin, Rol
from tests.conftest import TEST_URL


async def _tenant_izinleri(engine: AsyncEngine, slug: str) -> set[str]:
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as s:
        await search_path_ayarla(s, slug)
        return {i.kod for i in (await s.execute(select(Izin))).scalars()}


async def test_hicbir_tenantta_katalog_izni_eksik_degil(
    test_db: str, test_engine: AsyncEngine
) -> None:
    """SÖZLEŞME: katalogdaki her izin kodu, HER tenant şemasında bulunmalı."""
    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm() as s:
        sluglar = [t.slug for t in (await s.execute(select(Tenant))).scalars()]
    assert sluglar, "test veritabaninda tenant yok"

    eksikler: dict[str, list[str]] = {}
    for slug in sluglar:
        mevcut = await _tenant_izinleri(test_engine, slug)
        eksik = sorted(set(IZIN_KATALOGU) - mevcut)
        if eksik:
            eksikler[slug] = eksik
    assert not eksikler, f"katalog izinleri bazi tenant'larda eksik: {eksikler}"


async def test_uzlastirma_eksik_izni_geri_getirir(test_db: str, test_engine: AsyncEngine) -> None:
    """Bir izin şemadan silinse bile uzlaştırma onu geri koyar (onarım yeteneği)."""
    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    kurban = "denetim:oku"

    # Sürüklenmeyi simüle et: izni rol bağlarıyla birlikte sil.
    async with sm() as s, s.begin():
        await search_path_ayarla(s, "alfa")
        await s.execute(
            text("DELETE FROM rol_izin WHERE izin_id IN (SELECT id FROM izin WHERE kod = :k)"),
            {"k": kurban},
        )
        await s.execute(text("DELETE FROM izin WHERE kod = :k"), {"k": kurban})
    assert kurban not in await _tenant_izinleri(test_engine, "alfa")

    async with sm() as s, s.begin():
        sonuc = await izin_rol_uzlastir(s, "alfa")

    assert kurban in sonuc.eklenen_izin
    assert kurban in await _tenant_izinleri(test_engine, "alfa")


async def test_uzlastirma_idempotent(test_db: str, test_engine: AsyncEngine) -> None:
    """İkinci koşu hiçbir şey değiştirmemeli (idempotentlik)."""
    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm() as s, s.begin():
        await izin_rol_uzlastir(s, "alfa")
    async with sm() as s, s.begin():
        ikinci = await izin_rol_uzlastir(s, "alfa")
    assert not ikinci.degisti, (
        f"ikinci kosu degisiklik uretti: {ikinci.eklenen_izin} {ikinci.guncellenen_rol}"
    )


async def test_uzlastirma_katalog_disi_izni_ve_ozel_rolu_SILMEZ(
    test_db: str, test_engine: AsyncEngine
) -> None:
    """Yalnızca eklemeli: elle tanımlanmış izin/rol korunur."""
    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm() as s, s.begin():
        await search_path_ayarla(s, "alfa")
        s.add(Izin(kod="ozel:kod", aciklama="elle eklenmis"))
        await s.flush()
        s.add(Rol(ad="ozel-rol", aciklama="elle eklenmis rol"))

    async with sm() as s, s.begin():
        await izin_rol_uzlastir(s, "alfa")

    async with sm() as s:
        await search_path_ayarla(s, "alfa")
        izinler = {i.kod for i in (await s.execute(select(Izin))).scalars()}
        roller = {r.ad for r in (await s.execute(select(Rol))).scalars()}
    assert "ozel:kod" in izinler
    assert "ozel-rol" in roller

    # Temizlik (diğer testlerin rol sayımını bozmasın).
    async with sm() as s, s.begin():
        await search_path_ayarla(s, "alfa")
        await s.execute(text("DELETE FROM rol WHERE ad = 'ozel-rol'"))
        await s.execute(text("DELETE FROM izin WHERE kod = 'ozel:kod'"))


async def test_varsayilan_rollerin_izin_kumesi_katalogla_esitlenir(
    test_db: str, test_engine: AsyncEngine
) -> None:
    """Rolden izin düşerse uzlaştırma geri ekler (rol matrisi katalogla aynı kalır)."""
    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm() as s, s.begin():
        await search_path_ayarla(s, "alfa")
        await s.execute(
            text("DELETE FROM rol_izin WHERE rol_id IN (SELECT id FROM rol WHERE ad = 'uyum')")
        )

    async with sm() as s, s.begin():
        sonuc = await izin_rol_uzlastir(s, "alfa")
    assert "uyum" in sonuc.guncellenen_rol

    async with sm() as s:
        await search_path_ayarla(s, "alfa")
        rol = (await s.execute(select(Rol).where(Rol.ad == "uyum"))).scalar_one()
        assert {i.kod for i in rol.izinler} == set(VARSAYILAN_ROLLER["uyum"])


def test_tum_tenantlari_uzlastir_hepsini_kapsar(test_db: str) -> None:
    """Toplu uzlaştırma her tenant için bir sonuç döndürür (hata yutmadan)."""
    sonuclar = asyncio.run(tum_tenantlari_uzlastir(db_url=TEST_URL))
    sluglar = {s.slug for s in sonuclar}
    assert {"alfa", "beta"} <= sluglar, sluglar
