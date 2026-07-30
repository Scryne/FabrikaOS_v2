"""S23 uyum API testleri — denetim görünürlüğü + append-only trigger + KVKK ihraç/anonimleştirme
+ consent + RBAC/izolasyon."""

from __future__ import annotations

import io
import json
import uuid
import zipfile
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.modules.dys.depolama import BellekNesneDepo, nesne_depo_ayarla
from app.modules.uyum import service as uyum_service
from tests.conftest import ALFA, BETA
from tests.test_s16_entitlement import _giris

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def kvkk_ortami(test_engine: AsyncEngine) -> AsyncIterator[BellekNesneDepo]:
    """KVKK arka plan görevini test motoruna + bellek deposuna bağlar (es-zamanlı)."""
    sm = async_sessionmaker(test_engine, expire_on_commit=False)  # type: ignore[var-annotated]
    uyum_service.oturum_fabrikasi_ayarla(sm)
    uyum_service.es_zamanli_ayarla(True)
    depo = BellekNesneDepo()
    nesne_depo_ayarla(depo)
    try:
        yield depo
    finally:
        uyum_service.oturum_fabrikasi_ayarla(None)
        uyum_service.es_zamanli_ayarla(False)
        nesne_depo_ayarla(None)


async def test_denetim_listele_filtre_rbac_ve_izolasyon(
    test_db: str, kurulu_istemci: AsyncClient
) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    kod = f"S23-DEN-{uuid.uuid4().hex[:6].upper()}"
    r = await kurulu_istemci.post(
        "/api/v1/makineler", json={"kod": kod, "ad": "denetim izi"}, headers=h
    )
    assert r.status_code == 201

    r = await kurulu_istemci.get("/api/v1/denetim-kayitlari?adet=50", headers=h)
    assert r.status_code == 200, r.text
    kayitlar = r.json()["data"]
    assert any(k["eylem"] == "olustur" for k in kayitlar)
    assert all("olusturma_tarihi" in k for k in kayitlar)

    # Filtre: eylem + kullanıcı e-postası birlikte daraltır.
    r = await kurulu_istemci.get(
        f"/api/v1/denetim-kayitlari?eylem=olustur&kullanici_eposta={ALFA['eposta']}", headers=h
    )
    assert r.status_code == 200
    assert all(k["eylem"] == "olustur" for k in r.json()["data"])

    # Kaynak seçenekleri ucu dolu döner.
    r = await kurulu_istemci.get("/api/v1/denetim-kayitlari/kaynaklar", headers=h)
    assert r.status_code == 200 and len(r.json()["data"]) >= 1

    # RBAC: izleyici rolü denetim okuyamaz (hassas adli iz — S23 kuralı).
    r = await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={
            "eposta": "s23-izleyici@alfa.test",
            "parola": "Deneme12345!",
            "ad_soyad": "İzleyici",
            "roller": ["izleyici"],
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    izleyici_h = await _giris(
        kurulu_istemci,
        {"slug": "alfa", "eposta": "s23-izleyici@alfa.test", "parola": "Deneme12345!"},
    )
    r = await kurulu_istemci.get("/api/v1/denetim-kayitlari", headers=izleyici_h)
    assert r.status_code == 403

    # İzolasyon: beta'nın denetiminde alfa admin'inin izi yoktur.
    beta_h = await _giris(kurulu_istemci, BETA)
    r = await kurulu_istemci.get(
        f"/api/v1/denetim-kayitlari?kullanici_eposta={ALFA['eposta']}", headers=beta_h
    )
    assert r.status_code == 200 and r.json()["data"] == []


async def test_denetim_append_only_trigger(test_db: str, test_engine: AsyncEngine) -> None:
    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    # En az bir denetim kaydı olsun (test_db kurulumundan kalmış olabilir; garantiye al).
    async with sm() as db:
        await db.execute(
            text(
                "INSERT INTO tenant_alfa.denetim_izi (eylem, kaynak, olusturma_tarihi,"
                " guncelleme_tarihi) VALUES ('test', 'trigger', now(), now())"
            )
        )
        await db.commit()

    # Adli çekirdek (eylem) değiştirilemez.
    async with sm() as db:
        with pytest.raises(DBAPIError, match="append-only"):
            await db.execute(text("UPDATE tenant_alfa.denetim_izi SET eylem = 'degisti'"))
        await db.rollback()

    # DELETE her zaman yasak.
    async with sm() as db:
        with pytest.raises(DBAPIError, match="append-only"):
            await db.execute(text("DELETE FROM tenant_alfa.denetim_izi"))
        await db.rollback()

    # Kişisel veri maskesi (kullanici_eposta / ip_adresi) serbesttir.
    async with sm() as db:
        await db.execute(
            text(
                "UPDATE tenant_alfa.denetim_izi SET kullanici_eposta = 'anonim@kvkk.yerel',"
                " ip_adresi = NULL WHERE eylem = 'test'"
            )
        )
        await db.commit()


async def test_kvkk_ihrac_uctan_uca(
    test_db: str, kurulu_istemci: AsyncClient, kvkk_ortami: BellekNesneDepo
) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    ben = (await kurulu_istemci.get("/api/v1/kimlik/ben", headers=h)).json()["data"]

    # Var olmayan kişi erken 404.
    r = await kurulu_istemci.post(
        "/api/v1/kvkk/ihrac",
        json={"kisi_turu": "kullanici", "kisi_id": 999999},
        headers=h,
    )
    assert r.status_code == 404

    r = await kurulu_istemci.post(
        "/api/v1/kvkk/ihrac",
        json={"kisi_turu": "kullanici", "kisi_id": ben["id"]},
        headers=h,
    )
    assert r.status_code == 202, r.text
    ihrac_id = r.json()["data"]["id"]
    assert r.json()["data"]["kod"].startswith("KV-")

    r = await kurulu_istemci.get("/api/v1/kvkk/ihraclar", headers=h)
    kayit = next(k for k in r.json()["data"] if k["id"] == ihrac_id)
    assert kayit["durum"] == "hazir", kayit
    assert kayit["kayit_sayisi"] >= 1

    r = await kurulu_istemci.get(f"/api/v1/kvkk/ihraclar/{ihrac_id}/indir", headers=h)
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    z = zipfile.ZipFile(io.BytesIO(r.content))
    adlar = set(z.namelist())
    assert "kullanici.json" in adlar and "manifest.json" in adlar

    ana = json.loads(z.read("kullanici.json"))
    assert ana[0]["eposta"] == ALFA["eposta"]  # bilinen veri bayt düzeyinde içeride
    assert "parola_ozet" not in ana[0]  # güvenlik sırrı ihraca girmez
    manifest = json.loads(z.read("manifest.json"))
    assert manifest["kisi_turu"] == "kullanici" and manifest["toplam_kayit"] >= 1
    # İlişkili keşif: giriş denetim izi kullanıcıya bağlı dosyada.
    iliskili = [a for a in adlar if a.startswith("iliskili/denetim_izi")]
    assert iliskili, adlar


async def test_kvkk_anonimlestir_zinciri(test_db: str, kurulu_istemci: AsyncClient) -> None:
    admin_h = await _giris(kurulu_istemci, ALFA)
    eposta = f"s23-kurban-{uuid.uuid4().hex[:6]}@alfa.test"
    r = await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": eposta, "parola": "Deneme12345!", "ad_soyad": "Kurban Kişi"},
        headers=admin_h,
    )
    assert r.status_code == 201, r.text
    kurban_id = r.json()["data"]["id"]
    # Kurban giriş yapar → denetim izi + oturum kaydı oluşur (zincirleme maskeleme kapsamı).
    await _giris(kurulu_istemci, {"slug": "alfa", "eposta": eposta, "parola": "Deneme12345!"})

    # Yanlış onay metni 422; kendi hesabı 409.
    r = await kurulu_istemci.post(
        "/api/v1/kvkk/anonimlestir",
        json={"kisi_turu": "kullanici", "kisi_id": kurban_id, "onay": "EVET"},
        headers=admin_h,
    )
    assert r.status_code == 422
    ben = (await kurulu_istemci.get("/api/v1/kimlik/ben", headers=admin_h)).json()["data"]
    r = await kurulu_istemci.post(
        "/api/v1/kvkk/anonimlestir",
        json={"kisi_turu": "kullanici", "kisi_id": ben["id"], "onay": "ANONIM"},
        headers=admin_h,
    )
    assert r.status_code == 409

    r = await kurulu_istemci.post(
        "/api/v1/kvkk/anonimlestir",
        json={"kisi_turu": "kullanici", "kisi_id": kurban_id, "onay": "ANONIM"},
        headers=admin_h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["denetim_maskelendi"] >= 1

    # Eski kimlikle giriş imkânsız; e-posta anonimleşti.
    r = await kurulu_istemci.post(
        "/api/v1/kimlik/token",
        data={"username": eposta, "password": "Deneme12345!"},
        headers={"X-Tenant": "alfa"},
    )
    assert r.status_code == 401
    r = await kurulu_istemci.get(
        f"/api/v1/denetim-kayitlari?kullanici_eposta={eposta}", headers=admin_h
    )
    assert r.json()["data"] == []  # eski e-posta denetim izinde de kalmadı
    r = await kurulu_istemci.get(
        f"/api/v1/denetim-kayitlari?kullanici_eposta=anonim-{kurban_id}", headers=admin_h
    )
    assert len(r.json()["data"]) >= 1  # kayıtlar durur, kimlik maskelidir


async def test_consent_kayit_ve_gecmisi(test_db: str, kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.post(
        "/api/v1/consent",
        json={"tur": "aydinlatma", "metin_surumu": "v1", "kabul": True},
        headers=h,
    )
    assert r.status_code == 201, r.text
    r = await kurulu_istemci.post(
        "/api/v1/consent",
        json={"tur": "aydinlatma", "metin_surumu": "v1", "kabul": False},  # geri çekme
        headers=h,
    )
    assert r.status_code == 201
    r = await kurulu_istemci.post(
        "/api/v1/consent",
        json={"tur": "gecersiz", "metin_surumu": "v1", "kabul": True},
        headers=h,
    )
    assert r.status_code == 422

    r = await kurulu_istemci.get("/api/v1/consent", headers=h)
    kayitlar = r.json()["data"]
    assert len(kayitlar) >= 2
    assert kayitlar[0]["kabul"] is False  # en yeni: geri çekme (append-only geçmiş)


async def test_kvkk_rbac_403(test_db: str, kurulu_istemci: AsyncClient) -> None:
    admin_h = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={
            "eposta": "s23-rolsuz@alfa.test",
            "parola": "Deneme12345!",
            "ad_soyad": "R",
            "roller": ["izleyici"],
        },
        headers=admin_h,
    )
    assert r.status_code == 201, r.text
    h = await _giris(
        kurulu_istemci, {"slug": "alfa", "eposta": "s23-rolsuz@alfa.test", "parola": "Deneme12345!"}
    )
    r = await kurulu_istemci.get("/api/v1/kvkk/ihraclar", headers=h)
    assert r.status_code == 403
    r = await kurulu_istemci.post(
        "/api/v1/kvkk/anonimlestir",
        json={"kisi_turu": "kullanici", "kisi_id": 1, "onay": "ANONIM"},
        headers=h,
    )
    assert r.status_code == 403
