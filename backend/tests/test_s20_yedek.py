"""S20 tenant-farkında yedek/geri yükleme (ADR-0041) — gerçek PostgreSQL + TimescaleDB.

Kabul: tek tenant şeması bağımsız geri yüklenir (kanıtlı); hypertable verisi yedekte (şema
bazlı pg_dump'ın kaçırdığı yer); bozuk ya da tutmayan yedek canlı şemaya dokunmaz.
"""

from __future__ import annotations

import asyncio
import json
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import asyncpg
import pytest
from httpx import AsyncClient

from app.control_plane.provizyon import tenant_provizyonla
from app.operasyon.yedek import (
    YedekHatasi,
    manifest_oku,
    parmak_izi,
    tablolar,
    tenant_geri_yukle,
    tenant_yedekle,
    yazilabilir_sutunlar,
)
from tests.conftest import ASYNCPG_URL, TEST_URL

SLUG = "yedekt"
SEMA = f"tenant_{SLUG}"
ADMIN = {"eposta": "admin@yedekt.test", "parola": "Yedek12345!"}


@pytest.fixture(scope="module")
def yedek_tenant(test_db: str) -> str:
    async def kur() -> None:
        await tenant_provizyonla(
            slug=SLUG,
            ad="Yedek Fabrika",
            admin_eposta=ADMIN["eposta"],
            admin_parola=ADMIN["parola"],
            plan_kodu="kurumsal",
            db_url=TEST_URL,
        )
        conn = await asyncpg.connect(ASYNCPG_URL)
        try:
            await _tohumla(conn)
        finally:
            await conn.close()

    asyncio.run(kur())
    return SLUG


async def _tohumla(conn: asyncpg.Connection) -> None:
    for i in (1, 2, 3):
        await conn.execute(
            f"INSERT INTO {SEMA}.makineler (kod, ad, durum) VALUES ($1, $2, 'calisiyor')",
            f"YM-{i}",
            f"Yedek makinesi {i}",
        )
    ids = [r["id"] for r in await conn.fetch(f"SELECT id FROM {SEMA}.makineler ORDER BY id")]
    bas = datetime(2026, 9, 1, tzinfo=UTC)
    # 40 gün → birden çok hypertable chunk'ı (varsayılan chunk aralığı 7 gün).
    for gun in range(40):
        for m in ids:
            await conn.execute(
                f"""INSERT INTO {SEMA}.uretim_verileri
                    (zaman, makine_id, planlanan_sure_dk, durus_sure_dk, toplam_adet,
                     saglam_adet, ideal_cevrim_sn, lot_no)
                    VALUES ($1, $2, 480, 30, 900, 880, 25, $3)""",
                bas + timedelta(days=gun),
                m,
                f"LOT-{gun:03d}",
            )
    for saat in range(48):
        await conn.execute(
            f"""INSERT INTO {SEMA}.enerji_tuketim (zaman, makine_id, enerji_turu, tuketim, birim)
                VALUES ($1, $2, 'elektrik', $3, 'kWh')""",
            bas + timedelta(hours=saat),
            ids[0],
            12.5 + saat,
        )


async def _parmak_izleri(conn: asyncpg.Connection, sema: str) -> dict[str, str]:
    sonuc = {}
    for t in await tablolar(conn, sema):
        sonuc[t] = await parmak_izi(conn, sema, t, await yazilabilir_sutunlar(conn, sema, t))
    return sonuc


async def _semalar(conn: asyncpg.Connection, onek: str) -> list[str]:
    return [
        r["schema_name"]
        for r in await conn.fetch(
            "SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE $1",
            onek + "%",
        )
    ]


async def _eski_semalari_sil(conn: asyncpg.Connection) -> None:
    for s in await _semalar(conn, f"eski_{SLUG}_"):
        await conn.execute(f'DROP SCHEMA "{s}" CASCADE')


# --- Uçtan uca ------------------------------------------------------------------------


async def test_yedek_hypertable_verisini_icerir(yedek_tenant: str, tmp_path: Path) -> None:
    manifest = await tenant_yedekle(ASYNCPG_URL, yedek_tenant, tmp_path / "y.zip")
    satir = {t.ad: t.satir for t in manifest.tablolar}
    assert satir["uretim_verileri"] == 120  # 40 gün × 3 makine; şema dökümü burada 0 verirdi
    assert satir["enerji_tuketim"] == 48
    assert satir["makineler"] == 3
    assert satir["kullanici"] >= 1
    assert "alembic_version" not in satir
    assert manifest.alembic_revizyonu
    with zipfile.ZipFile(tmp_path / "y.zip") as z:
        kontrol = json.loads(z.read("kontrol-duzlemi.json"))
    assert kontrol["tenant"][0]["slug"] == SLUG
    assert not (tmp_path / "y.zip.yaziliyor").exists()


async def test_geri_yukleme_canli_semayi_birebir_kurar(
    yedek_tenant: str, tmp_path: Path, kurulu_istemci: AsyncClient
) -> None:
    conn = await asyncpg.connect(ASYNCPG_URL)
    try:
        once = await _parmak_izleri(conn, SEMA)
        komsu_once = await _parmak_izleri(conn, "tenant_alfa")
        await tenant_yedekle(ASYNCPG_URL, yedek_tenant, tmp_path / "y.zip")

        # Felaket: veri silindi, değiştirildi, çöp eklendi.
        await conn.execute(f"DELETE FROM {SEMA}.uretim_verileri WHERE zaman > '2026-09-20'")
        await conn.execute(f"UPDATE {SEMA}.makineler SET ad = 'BOZULDU'")
        await conn.execute(
            f"INSERT INTO {SEMA}.makineler (kod, ad, durum) VALUES ('COP', 'çöp', 'durdu')"
        )
        assert await _parmak_izleri(conn, SEMA) != once

        rapor = await tenant_geri_yukle(TEST_URL, tmp_path / "y.zip")
        assert rapor.degistirildi and rapor.eski_sema
        assert set(rapor.adimlar) >= {
            "yapi_goc",
            "veri_yukleme",
            "icerik_dogrulama",
            "yer_degistirme",
        }

        # İçerik yedek anıyla birebir; komşu tenant'a dokunulmadı.
        assert await _parmak_izleri(conn, SEMA) == once
        assert await _parmak_izleri(conn, "tenant_alfa") == komsu_once
        # Eski şema geri dönüş için duruyor ve felaket hâlini taşıyor.
        assert await conn.fetchval(f'SELECT count(*) FROM "{rapor.eski_sema}".makineler') == 4

        # Hypertable kimliği ve chunk'lar yeni şemada; CAGG yeniden hesaplandı.
        assert (
            await conn.fetchval(
                "SELECT count(*) FROM timescaledb_information.hypertables "
                "WHERE hypertable_schema = $1",
                SEMA,
            )
            == 2
        )
        assert (
            await conn.fetchval(
                "SELECT count(*) FROM timescaledb_information.chunks WHERE hypertable_schema = $1"
                " AND hypertable_name = 'uretim_verileri'",
                SEMA,
            )
            >= 2
        )
        # CAGG gerçek zamanlı (materialized_only=false) olduğu için görünüm yenilemesiz de veri
        # gösterir; yenilemenin kanıtı materyalize tablodaki satırlardır.
        mat = await conn.fetchrow(
            """SELECT materialization_hypertable_schema AS s, materialization_hypertable_name AS t
               FROM timescaledb_information.continuous_aggregates WHERE view_schema = $1""",
            SEMA,
        )
        assert await conn.fetchval(f'SELECT count(*) FROM "{mat["s"]}"."{mat["t"]}"') > 0

        # Diziler ileri alındı: yeni kayıt kimlik çakışması yaşamaz.
        yeni_id = await conn.fetchval(
            f"INSERT INTO {SEMA}.makineler (kod, ad, durum) "
            "VALUES ('YENI', 'yeni', 'durdu') RETURNING id"
        )
        assert yeni_id > max(
            r["id"]
            for r in await conn.fetch(f"SELECT id FROM {SEMA}.makineler WHERE kod <> 'YENI'")
        )
        await conn.execute(f"DELETE FROM {SEMA}.makineler WHERE kod = 'YENI'")
    finally:
        await _eski_semalari_sil(conn)
        await conn.close()

    # Uygulama geri yüklenmiş tenant'la uçtan uca çalışıyor (giriş + liste).
    r = await kurulu_istemci.post(
        "/api/v1/kimlik/token",
        data={"username": ADMIN["eposta"], "password": ADMIN["parola"]},
        headers={"X-Tenant": SLUG},
    )
    assert r.status_code == 200, r.text
    token = r.json()["data"]["access_token"]
    r = await kurulu_istemci.get(
        "/api/v1/makineler", headers={"X-Tenant": SLUG, "Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert sorted(m["kod"] for m in r.json()["data"]) == ["YM-1", "YM-2", "YM-3"]


async def test_tatbikat_canli_semaya_dokunmaz(yedek_tenant: str, tmp_path: Path) -> None:
    conn = await asyncpg.connect(ASYNCPG_URL)
    try:
        await tenant_yedekle(ASYNCPG_URL, yedek_tenant, tmp_path / "y.zip")
        once = await _parmak_izleri(conn, SEMA)
        rapor = await tenant_geri_yukle(TEST_URL, tmp_path / "y.zip", yalniz_dogrula=True)
        assert not rapor.degistirildi and rapor.eski_sema is None
        assert rapor.satir > 0 and rapor.sure_sn > 0
        assert await _parmak_izleri(conn, SEMA) == once
        assert await _semalar(conn, f"geri_{SLUG}_") == []
        assert await _semalar(conn, f"eski_{SLUG}_") == []
    finally:
        await conn.close()


async def test_bozuk_dosya_reddedilir_canliya_dokunulmaz(yedek_tenant: str, tmp_path: Path) -> None:
    await tenant_yedekle(ASYNCPG_URL, yedek_tenant, tmp_path / "y.zip")
    bozuk = tmp_path / "bozuk.zip"
    with zipfile.ZipFile(tmp_path / "y.zip") as kaynak, zipfile.ZipFile(bozuk, "w") as hedef:
        for oge in kaynak.infolist():
            veri = kaynak.read(oge)
            if oge.filename == "veri/makineler.bin":
                veri = veri[:-3] + bytes(b ^ 0xFF for b in veri[-3:])
            hedef.writestr(oge, veri)
    conn = await asyncpg.connect(ASYNCPG_URL)
    try:
        once = await _parmak_izleri(conn, SEMA)
        with pytest.raises(YedekHatasi, match="makineler"):
            await tenant_geri_yukle(TEST_URL, bozuk)
        assert await _parmak_izleri(conn, SEMA) == once
        assert await _semalar(conn, f"geri_{SLUG}_") == []
    finally:
        await conn.close()


async def test_icerik_tutmazsa_gecici_sema_silinir(yedek_tenant: str, tmp_path: Path) -> None:
    """Dosya özetleri tutarlı ama içerik beklenenle tutmuyor → doğrulama yakalar, yer değişmez."""
    await tenant_yedekle(ASYNCPG_URL, yedek_tenant, tmp_path / "y.zip")
    m = manifest_oku(tmp_path / "y.zip")
    sahte = tmp_path / "sahte.zip"
    with zipfile.ZipFile(tmp_path / "y.zip") as kaynak, zipfile.ZipFile(sahte, "w") as hedef:
        for oge in kaynak.infolist():
            veri = kaynak.read(oge)
            if oge.filename == "manifest.json":
                ham = json.loads(veri)
                for t in ham["tablolar"]:
                    if t["ad"] == "uretim_verileri":
                        t["parmak_izi"] = "0" * 32
                veri = json.dumps(ham).encode()
            hedef.writestr(oge, veri)
    assert m.tablolar
    conn = await asyncpg.connect(ASYNCPG_URL)
    try:
        once = await _parmak_izleri(conn, SEMA)
        with pytest.raises(YedekHatasi, match="uretim_verileri"):
            await tenant_geri_yukle(TEST_URL, sahte)
        assert await _parmak_izleri(conn, SEMA) == once
        assert await _semalar(conn, f"geri_{SLUG}_") == []
        assert await _semalar(conn, f"eski_{SLUG}_") == []
    finally:
        await conn.close()


async def test_olmayan_sema_yedeklenmez(test_db: str, tmp_path: Path) -> None:
    with pytest.raises(YedekHatasi, match="Şema yok"):
        await tenant_yedekle(ASYNCPG_URL, "boyle-bir-tenant-yok", tmp_path / "y.zip")
    assert not (tmp_path / "y.zip").exists()


# --- Anonim staging kopyası -------------------------------------------------------------

STAGING = "yedekt-staging"
PII = {
    "tc": "10000000146",  # sağlama toplamı geçerli biçimde (gerçek kişiye ait değil)
    "ad": "Ayşegül",
    "soyad": "Kocabıyık",
    "personel_eposta": "aysegul.kocabiyik@ornekfabrika.com.tr",
    "telefon": "+90 500 000 00 01",
    "ortak": "Mehmet Demirkıran",
    "ortak_eposta": "mehmet@tedarikci-ornek.com.tr",
    "firma": "Demirkıran Hırdavat (şahıs)",
    "ip": "203.0.113.77",
    "webhook": "https://musteri-ornek.com.tr/fabrikaos-kanca",
}


async def _pii_tohumla(conn: asyncpg.Connection) -> None:
    await conn.execute(
        f"""INSERT INTO {SEMA}.personel
            (sicil_no, ad, soyad, tc_kimlik_no, telefon, eposta, dogum_tarihi)
            VALUES ('S-001', $1, $2, $3, $4, $5, '1990-04-12')""",
        PII["ad"],
        PII["soyad"],
        PII["tc"],
        PII["telefon"],
        PII["personel_eposta"],
    )
    firma = await conn.fetchval(
        f"INSERT INTO {SEMA}.firmalar (ad, tip, telefon, eposta) "
        "VALUES ($1, 'tedarikci', $2, $3) RETURNING id",
        PII["firma"],
        PII["telefon"],
        PII["ortak_eposta"],
    )
    await conn.execute(
        f"INSERT INTO {SEMA}.ortaklar (firma_id, ad_soyad, eposta, telefon) "
        "VALUES ($1, $2, $3, $4)",
        firma,
        PII["ortak"],
        PII["ortak_eposta"],
        PII["telefon"],
    )
    kullanici = await conn.fetchval(f"SELECT min(id) FROM {SEMA}.kullanici")
    await conn.execute(
        f"""INSERT INTO {SEMA}.consent_kayitlari (kullanici_id, tur, metin_surumu, kabul, ip_adresi)
            VALUES ($1, 'aydinlatma', 'v1', true, $2)""",
        kullanici,
        PII["ip"],
    )
    await conn.execute(
        f"""INSERT INTO {SEMA}.denetim_izi (eylem, kaynak, kullanici_eposta, ip_adresi, detay)
            VALUES ('guncelle', 'personel', $1, $2, $3::jsonb)""",
        ADMIN["eposta"],
        PII["ip"],
        json.dumps({"eski_ad": PII["ad"]}),
    )
    await conn.execute(
        f"INSERT INTO {SEMA}.webhook_abonelikleri (ad, url, gizli_anahtar) "
        "VALUES ('erp', $1, 'prod-sir')",
        PII["webhook"],
    )


async def _metinde_ara(conn: asyncpg.Connection, sema: str, aranan: list[str]) -> list[str]:
    """Şemadaki her metin/jsonb sütununda aranan değerleri arar; bulunanları döner."""
    sutunlar = await conn.fetch(
        """SELECT table_name, column_name FROM information_schema.columns
           WHERE table_schema = $1 AND data_type IN ('character varying', 'text', 'jsonb')
             AND table_name IN (SELECT table_name FROM information_schema.tables
                                WHERE table_schema = $1 AND table_type = 'BASE TABLE')""",
        sema,
    )
    bulunan = []
    for s in sutunlar:
        for deger in aranan:
            if await conn.fetchval(
                f'SELECT 1 FROM "{sema}"."{s["table_name"]}" '
                f'WHERE "{s["column_name"]}"::text LIKE $1 LIMIT 1',
                f"%{deger}%",
            ):
                bulunan.append(f"{s['table_name']}.{s['column_name']}={deger}")
    return bulunan


async def test_staging_kopyasi_kisisel_veri_tasimaz(
    yedek_tenant: str, tmp_path: Path, kurulu_istemci: AsyncClient
) -> None:
    from app.operasyon.anonim import AnonimHatasi, tenant_anonimlestir

    await tenant_provizyonla(
        slug=STAGING,
        ad="Yedek Staging",
        admin_eposta="gecici@staging.test",
        admin_parola="Gecici12345!",
        plan_kodu="kurumsal",
        db_url=TEST_URL,
    )
    hedef = f"tenant_{STAGING}"
    conn = await asyncpg.connect(ASYNCPG_URL)
    try:
        await _pii_tohumla(conn)
        await tenant_yedekle(ASYNCPG_URL, yedek_tenant, tmp_path / "prod.zip")
        await tenant_geri_yukle(TEST_URL, tmp_path / "prod.zip", hedef_slug=STAGING)
        aranan = [v for k, v in PII.items()] + [ADMIN["eposta"]]
        assert await _metinde_ara(conn, hedef, aranan), "geri yükleme sonrası PII kopyada olmalı"

        with pytest.raises(AnonimHatasi, match="staging"):
            await tenant_anonimlestir(ASYNCPG_URL, yedek_tenant)  # prod'a asla

        rapor = await tenant_anonimlestir(
            ASYNCPG_URL, STAGING, yonetici=("yonetici@staging.test", "Staging12345!")
        )
        assert rapor.guncellenen["personel"] >= 1 and rapor.guncellenen["denetim_izi"] >= 1

        # Hiçbir metin sütununda gerçek kişisel veri, prod e-postası, webhook adresi kalmadı.
        assert await _metinde_ara(conn, hedef, aranan) == []
        assert (
            await conn.fetchval(
                f'SELECT count(*) FROM "{hedef}".personel WHERE dogum_tarihi IS NOT NULL'
            )
            == 0
        )
        assert (
            await conn.fetchval(f'SELECT bool_or(aktif) FROM "{hedef}".webhook_abonelikleri')
            is False
        )
        tc = await conn.fetchval(f'SELECT tc_kimlik_no FROM "{hedef}".personel LIMIT 1')
        assert len(tc) == 11 and tc.startswith("9")
        # Kaynak (prod) şemaya dokunulmadı.
        assert await _metinde_ara(conn, SEMA, [PII["tc"]])
        # Denetim izi koruması staging'de de yeniden açık.
        with pytest.raises(asyncpg.PostgresError):
            await conn.execute(f'DELETE FROM "{hedef}".denetim_izi')
    finally:
        await _eski_semalari_sil(conn)
        for s in await _semalar(conn, f"eski_{STAGING.replace('-', '_')}"):
            await conn.execute(f'DROP SCHEMA "{s}" CASCADE')
        await conn.close()

    giris = {"X-Tenant": STAGING}
    r = await kurulu_istemci.post(
        "/api/v1/kimlik/token",
        data={"username": "yonetici@staging.test", "password": "Staging12345!"},
        headers=giris,
    )
    assert r.status_code == 200, r.text
    r = await kurulu_istemci.post(
        "/api/v1/kimlik/token",
        data={"username": ADMIN["eposta"], "password": ADMIN["parola"]},
        headers=giris,
    )
    assert r.status_code == 401
