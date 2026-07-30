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

    # İzin SATIRI silinmişse rol bağları da onarılır: izin hiç yokken "rolden bilinçli
    # kaldırılmış" olamaz — bu şema sürüklenmesidir, köken defteri devreye girmez.
    sm2 = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm2() as s:
        await search_path_ayarla(s, "alfa")
        rol = (await s.execute(select(Rol).where(Rol.ad == "uyum"))).scalar_one()
        assert kurban in {i.kod for i in rol.izinler}, "izin satırı onarıldı ama rol bağı kurulmadı"


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


async def test_tenantin_BILINCLI_kaldirdigi_izin_GERI_VERILMEZ(
    test_db: str, test_engine: AsyncEngine
) -> None:
    """EN KRİTİK SÖZLEŞME: uzlaştırma yetki restorasyonu yapmaz.

    Yönetici bir rolden izni kaldırdıysa (köken defterinde kayıtlı = katalogdan gelmişti),
    sonraki dağıtım onu sessizce geri açmamalı. Aksi hâlde denetlenemeyen bir yetki
    yükseltmesi oluşur: "kaldırdım ama geri geldi".
    """
    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm() as s, s.begin():
        await search_path_ayarla(s, "alfa")
        # Köken defterinde kayıtlı olduğundan emin ol (backfill migration'ı yapmış olmalı).
        kayitli = await s.scalar(
            text("SELECT count(*) FROM rol_izin_tohumu WHERE rol_ad = 'uyum' AND izin_kod = :k"),
            {"k": "kvkk:yonet"},
        )
        assert kayitli == 1, "backfill köken defterini doldurmamış"
        # Yönetici bilinçli olarak kaldırıyor.
        await s.execute(
            text(
                "DELETE FROM rol_izin WHERE rol_id = (SELECT id FROM rol WHERE ad = 'uyum') "
                "AND izin_id = (SELECT id FROM izin WHERE kod = 'kvkk:yonet')"
            )
        )

    async with sm() as s, s.begin():
        sonuc = await izin_rol_uzlastir(s, "alfa")

    assert "uyum:kvkk:yonet" in sonuc.korunan_kaldirma, "kaldırma raporlanmadı"
    assert "uyum" not in sonuc.guncellenen_rol, "rol sessizce değiştirildi"

    async with sm() as s:
        await search_path_ayarla(s, "alfa")
        rol = (await s.execute(select(Rol).where(Rol.ad == "uyum"))).scalar_one()
        assert "kvkk:yonet" not in {i.kod for i in rol.izinler}, "kaldırılan yetki GERİ VERİLDİ"

    # Temizlik: bağı geri kur (diğer testler tam rol bekliyor).
    async with sm() as s, s.begin():
        await search_path_ayarla(s, "alfa")
        await s.execute(
            text(
                "INSERT INTO rol_izin (rol_id, izin_id) SELECT "
                "(SELECT id FROM rol WHERE ad = 'uyum'), "
                "(SELECT id FROM izin WHERE kod = 'kvkk:yonet')"
            )
        )


async def test_YENI_katalog_izni_mevcut_role_eklenir(
    test_db: str, test_engine: AsyncEngine
) -> None:
    """Köken defterinde OLMAYAN katalog izni = yeni sprint izni → role eklenir.

    Bu, modülün varlık sebebidir: "hiç tohumlanmamış" ile "kaldırılmış" ayrımı doğru
    çalışmazsa ya sürüklenme sürer ya da restorasyon yapılır.
    """
    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm() as s, s.begin():
        await search_path_ayarla(s, "alfa")
        # Yeni bir sprintin izni gibi davran: bağı da köken kaydını da kaldır.
        await s.execute(
            text(
                "DELETE FROM rol_izin WHERE rol_id = (SELECT id FROM rol WHERE ad = 'uyum') "
                "AND izin_id = (SELECT id FROM izin WHERE kod = 'denetim:oku')"
            )
        )
        await s.execute(
            text("DELETE FROM rol_izin_tohumu WHERE rol_ad = 'uyum' AND izin_kod = 'denetim:oku'")
        )

    async with sm() as s, s.begin():
        sonuc = await izin_rol_uzlastir(s, "alfa")
    assert "uyum" in sonuc.guncellenen_rol

    async with sm() as s:
        await search_path_ayarla(s, "alfa")
        rol = (await s.execute(select(Rol).where(Rol.ad == "uyum"))).scalar_one()
        assert "denetim:oku" in {i.kod for i in rol.izinler}
        # Artık tohumlanmış sayılır: bundan sonra kaldırılırsa geri verilmez.
        kayitli = await s.scalar(
            text(
                "SELECT count(*) FROM rol_izin_tohumu WHERE rol_ad = 'uyum' "
                "AND izin_kod = 'denetim:oku'"
            )
        )
        assert kayitli == 1


async def test_yeni_rol_katalog_izinlerinin_TAMAMINI_alir(
    test_db: str, test_engine: AsyncEngine
) -> None:
    """Hiç var olmayan rol oluşturulurken kısıtlama yok: katalog kümesinin tamamı verilir."""
    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm() as s, s.begin():
        await search_path_ayarla(s, "alfa")
        await s.execute(
            text("DELETE FROM rol_izin WHERE rol_id = (SELECT id FROM rol WHERE ad = 'uyum')")
        )
        await s.execute(text("DELETE FROM rol WHERE ad = 'uyum'"))
        await s.execute(text("DELETE FROM rol_izin_tohumu WHERE rol_ad = 'uyum'"))

    async with sm() as s, s.begin():
        sonuc = await izin_rol_uzlastir(s, "alfa")
    assert "uyum" in sonuc.eklenen_rol

    async with sm() as s:
        await search_path_ayarla(s, "alfa")
        rol = (await s.execute(select(Rol).where(Rol.ad == "uyum"))).scalar_one()
        assert {i.kod for i in rol.izinler} == set(VARSAYILAN_ROLLER["uyum"])


def test_tum_tenantlari_uzlastir_hepsini_kapsar(test_db: str) -> None:
    """Toplu uzlaştırma her tenant için bir sonuç döndürür (hata yutmadan)."""
    sonuclar = asyncio.run(tum_tenantlari_uzlastir(db_url=TEST_URL))
    sluglar = {s.slug for s in sonuclar}
    assert {"alfa", "beta"} <= sluglar, sluglar
