"""S23 sertleştirme turu — PII log penceresi + KVKK artefakt saklama süresi.

İki risk kapatılır:
1. ``debug_claim_log`` ham ID token claim'lerini (e-posta/ad/grup = kişisel veri) log
   akışına yazar. Kalıcı açık kalırsa PII sürekli birikir → süreli + denetim izli.
2. Hazır KVKK ihracı, kişinin tüm modüllerdeki verisinin dökümüdür. Süresiz saklanması
   veri minimizasyonuna aykırı → saklama süresi + otomatik imha + indirme denetimi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.security import oidc
from app.modules.dys.depolama import nesne_depo_al
from app.modules.uyum import service
from app.modules.uyum.models import IHRAC_SAKLAMA_GUN, KvkkIhraci
from app.platform.guvenlik_ayar import (
    DEBUG_OMRU_DK,
    debug_suresini_damgala,
)
from tests.test_s16_entitlement import _giris
from tests.test_s17_platform_kimlik import (  # noqa: F401 (fixture zinciri)
    oturum,
    platform_db,
    platform_giris,
)

PLATFORM = "/api/v1/platform"
UYUM = "/api/v1"


def _oidc(debug: bool = False, bitis: str | None = None) -> dict[str, Any]:
    oidc_ayar: dict[str, Any] = {
        "aktif": True,
        "issuer": "https://idp.test",
        "istemci_id": "fos",
        "istemci_sirri": "sir",
        "donus_url": "https://app.test/sso/donus",
        "debug_claim_log": debug,
    }
    if bitis is not None:
        oidc_ayar["debug_claim_log_bitis"] = bitis
    return {"oidc": oidc_ayar}


# --------------------------------------------------------------------------------------
# 1) Debug claim logu — süreli pencere (saf)
# --------------------------------------------------------------------------------------
def test_debug_acilinca_bitis_damgalanir() -> None:
    an = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
    yeni, gecis = debug_suresini_damgala(_oidc(debug=True), None, simdi=an)

    assert gecis.acildi is True and gecis.kapandi is False
    assert yeni is not None
    beklenen = an + timedelta(minutes=DEBUG_OMRU_DK)
    assert yeni["oidc"]["debug_claim_log_bitis"] == beklenen.isoformat()


def test_debug_acikken_ilgisiz_duzenleme_pencereyi_UZATMAZ() -> None:
    """IP listesi gibi başka bir ayarı kaydetmek PII penceresini sessizce uzatmamalı."""
    an = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
    ilk_bitis = an + timedelta(minutes=30)
    mevcut = _oidc(debug=True, bitis=ilk_bitis.isoformat())

    yeni, gecis = debug_suresini_damgala(_oidc(debug=True), mevcut, simdi=an)

    assert gecis.acildi is False and gecis.kapandi is False
    assert yeni is not None
    assert yeni["oidc"]["debug_claim_log_bitis"] == ilk_bitis.isoformat()


def test_debug_kapatilinca_damga_silinir_ve_gecis_bildirilir() -> None:
    an = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
    mevcut = _oidc(debug=True, bitis=(an + timedelta(minutes=30)).isoformat())

    yeni, gecis = debug_suresini_damgala(_oidc(debug=False), mevcut, simdi=an)

    assert gecis.kapandi is True and gecis.acildi is False
    assert yeni is not None
    assert "debug_claim_log_bitis" not in yeni["oidc"]


def test_debug_suresi_gecmisse_yeniden_acilir() -> None:
    an = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
    mevcut = _oidc(debug=True, bitis=(an - timedelta(minutes=1)).isoformat())

    yeni, gecis = debug_suresini_damgala(_oidc(debug=True), mevcut, simdi=an)

    assert gecis.acildi is True  # süresi dolmuş pencere "kapalı" sayılır
    assert yeni is not None
    assert (
        yeni["oidc"]["debug_claim_log_bitis"] == (an + timedelta(minutes=DEBUG_OMRU_DK)).isoformat()
    )


def test_ayarlar_sifirlanirsa_debug_kapanmis_sayilir() -> None:
    an = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
    mevcut = _oidc(debug=True, bitis=(an + timedelta(minutes=30)).isoformat())
    yeni, gecis = debug_suresini_damgala(None, mevcut, simdi=an)
    assert yeni is None and gecis.kapandi is True


def test_debug_aktif_mi_damgasiz_bayragi_kabul_ETMEZ() -> None:
    """Elle JSONB düzenleyip kalıcı PII loglaması açılamaz: damga şart."""
    ayar = oidc.ayar_coz(_oidc(debug=True))
    assert ayar is not None and ayar.debug_claim_log is True
    assert oidc.debug_aktif_mi(ayar) is False  # bitiş damgası yok → yazma

    an = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
    ayar2 = oidc.ayar_coz(_oidc(debug=True, bitis=(an + timedelta(minutes=5)).isoformat()))
    assert ayar2 is not None
    assert oidc.debug_aktif_mi(ayar2, simdi=an) is True
    assert oidc.debug_aktif_mi(ayar2, simdi=an + timedelta(minutes=6)) is False


async def test_platform_debug_acma_kapama_denetim_izine_yazilir(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
    test_engine: AsyncEngine,
) -> None:
    """Ham PII loglamasını kimin, ne zaman, ne kadar süreyle açtığı denetlenebilmeli."""
    h = await platform_giris(kurulu_istemci)
    tenantlar = await kurulu_istemci.get(f"{PLATFORM}/tenantlar", headers=h)
    alfa = next(t for t in tenantlar.json()["data"] if t["slug"] == "alfa")
    yol = f"{PLATFORM}/tenantlar/{alfa['id']}/guvenlik-ayarlari"

    ac = await kurulu_istemci.put(yol, json={"ayarlar": _oidc(debug=True)}, headers=h)
    assert ac.status_code == 200, ac.text
    # Sunucu bitiş damgasını kendisi basar (istemci veremez).
    assert ac.json()["data"]["oidc"]["debug_claim_log_bitis"]

    kapat = await kurulu_istemci.put(yol, json={"ayarlar": _oidc(debug=False)}, headers=h)
    assert kapat.status_code == 200

    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm() as db:
        eylemler = (
            (
                await db.execute(
                    text(
                        "SELECT eylem FROM public.platform_denetim_izi "
                        "WHERE eylem IN ('sso_debug_ac', 'sso_debug_kapat') ORDER BY id"
                    )
                )
            )
            .scalars()
            .all()
        )
    assert "sso_debug_ac" in eylemler
    assert "sso_debug_kapat" in eylemler

    await kurulu_istemci.put(yol, json={"ayarlar": None}, headers=h)


# --------------------------------------------------------------------------------------
# 2) KVKK artefakt saklama süresi
# --------------------------------------------------------------------------------------
async def _ihrac_uret(kurulu_istemci: AsyncClient, h: dict[str, str]) -> int:
    ben = await kurulu_istemci.get("/api/v1/kimlik/ben", headers=h)
    kisi_id = ben.json()["data"]["id"]
    r = await kurulu_istemci.post(
        f"{UYUM}/kvkk/ihrac", json={"kisi_turu": "kullanici", "kisi_id": kisi_id}, headers=h
    )
    assert r.status_code == 202, r.text
    return int(r.json()["data"]["id"])


async def test_hazir_ihraca_gecerlilik_bitisi_damgalanir(
    test_db: str, kurulu_istemci: AsyncClient, test_engine: AsyncEngine
) -> None:
    service.es_zamanli_ayarla(True)
    service.oturum_fabrikasi_ayarla(async_sessionmaker(test_engine, expire_on_commit=False))
    try:
        h = await _giris(
            kurulu_istemci, {"slug": "alfa", "eposta": "admin@alfa.test", "parola": "Alfa12345!"}
        )
        ihrac_id = await _ihrac_uret(kurulu_istemci, h)
    finally:
        service.es_zamanli_ayarla(False)
        service.oturum_fabrikasi_ayarla(None)

    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm() as db:
        await db.execute(text("SET search_path TO tenant_alfa, public"))
        kayit = (await db.execute(select(KvkkIhraci).where(KvkkIhraci.id == ihrac_id))).scalar_one()
        assert kayit.durum == "hazir"
        assert kayit.gecerlilik_bitisi is not None
        kalan = kayit.gecerlilik_bitisi - datetime.now(UTC)
        assert timedelta(days=IHRAC_SAKLAMA_GUN - 1) < kalan <= timedelta(days=IHRAC_SAKLAMA_GUN)


async def test_suresi_dolan_ihrac_410_doner_ve_artefakt_silinir(
    test_db: str, kurulu_istemci: AsyncClient, test_engine: AsyncEngine
) -> None:
    """Süre dolduğunda: 410 (404 değil — "vardı, süresi doldu") + nesne deposundan silme."""
    service.es_zamanli_ayarla(True)
    service.oturum_fabrikasi_ayarla(async_sessionmaker(test_engine, expire_on_commit=False))
    try:
        h = await _giris(
            kurulu_istemci, {"slug": "alfa", "eposta": "admin@alfa.test", "parola": "Alfa12345!"}
        )
        ihrac_id = await _ihrac_uret(kurulu_istemci, h)
    finally:
        service.es_zamanli_ayarla(False)
        service.oturum_fabrikasi_ayarla(None)

    # Önce indirilebiliyor olmalı.
    ilk = await kurulu_istemci.get(f"{UYUM}/kvkk/ihraclar/{ihrac_id}/indir", headers=h)
    assert ilk.status_code == 200

    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm() as db:
        await db.execute(text("SET search_path TO tenant_alfa, public"))
        kayit = (await db.execute(select(KvkkIhraci).where(KvkkIhraci.id == ihrac_id))).scalar_one()
        anahtar = kayit.nesne_anahtari
        await db.execute(
            text("UPDATE kvkk_ihraclari SET gecerlilik_bitisi = :g WHERE id = :i"),
            {"g": datetime.now(UTC) - timedelta(minutes=1), "i": ihrac_id},
        )
        await db.commit()
    assert nesne_depo_al().var_mi(anahtar)

    cevap = await kurulu_istemci.get(f"{UYUM}/kvkk/ihraclar/{ihrac_id}/indir", headers=h)
    assert cevap.status_code == 410, cevap.text
    assert cevap.json()["hata_kodu"] == "SURE_DOLDU"
    assert not nesne_depo_al().var_mi(anahtar), "süresi dolan artefakt depodan silinmedi"

    # Kayıt satırı denetim için DURUR (kim kimin verisini ihraç etmişti sorusu cevaplanabilir).
    liste = await kurulu_istemci.get(f"{UYUM}/kvkk/ihraclar?adet=50", headers=h)
    kalan = next(k for k in liste.json()["data"] if k["id"] == ihrac_id)
    assert kalan["durum"] == "suresi_doldu"


async def test_temizleme_taramasi_idempotent(
    test_db: str, kurulu_istemci: AsyncClient, test_engine: AsyncEngine
) -> None:
    service.es_zamanli_ayarla(True)
    service.oturum_fabrikasi_ayarla(async_sessionmaker(test_engine, expire_on_commit=False))
    try:
        h = await _giris(
            kurulu_istemci, {"slug": "alfa", "eposta": "admin@alfa.test", "parola": "Alfa12345!"}
        )
        ihrac_id = await _ihrac_uret(kurulu_istemci, h)
    finally:
        service.es_zamanli_ayarla(False)
        service.oturum_fabrikasi_ayarla(None)

    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm() as db:
        await db.execute(text("SET search_path TO tenant_alfa, public"))
        await db.execute(
            text("UPDATE kvkk_ihraclari SET gecerlilik_bitisi = :g WHERE id = :i"),
            {"g": datetime.now(UTC) - timedelta(minutes=1), "i": ihrac_id},
        )
        await db.commit()

    ilk = await kurulu_istemci.post(f"{UYUM}/kvkk/ihraclar/temizle", headers=h)
    assert ilk.status_code == 200 and ilk.json()["data"]["silinen"] >= 1

    ikinci = await kurulu_istemci.post(f"{UYUM}/kvkk/ihraclar/temizle", headers=h)
    assert ikinci.json()["data"]["silinen"] == 0, "tarama idempotent degil"


async def test_ihrac_indirme_denetim_izine_yazilir(
    test_db: str, kurulu_istemci: AsyncClient, test_engine: AsyncEngine
) -> None:
    """Her indirme "kim + kimin verisi" ile kayda geçer (artefaktın kendisi denetlenir)."""
    service.es_zamanli_ayarla(True)
    service.oturum_fabrikasi_ayarla(async_sessionmaker(test_engine, expire_on_commit=False))
    try:
        h = await _giris(
            kurulu_istemci, {"slug": "alfa", "eposta": "admin@alfa.test", "parola": "Alfa12345!"}
        )
        ihrac_id = await _ihrac_uret(kurulu_istemci, h)
    finally:
        service.es_zamanli_ayarla(False)
        service.oturum_fabrikasi_ayarla(None)

    assert (
        await kurulu_istemci.get(f"{UYUM}/kvkk/ihraclar/{ihrac_id}/indir", headers=h)
    ).status_code == 200

    kayitlar = await kurulu_istemci.get(
        f"{UYUM}/denetim-kayitlari?eylem=kvkk_ihrac_indir&adet=5", headers=h
    )
    assert kayitlar.status_code == 200
    veri = kayitlar.json()["data"]
    assert veri, "indirme denetim izine yazilmadi"
    assert veri[0]["kullanici_eposta"] == "admin@alfa.test"
    assert veri[0]["detay"]["kisi_turu"] == "kullanici"
    assert veri[0]["detay"]["indirme_sayisi"] >= 1


def test_nesne_depo_imzali_url_uretmiyor() -> None:
    """SÖZLEŞME: nesne deposunda paylaşılabilir (presigned) URL üreten bir yüzey YOK.

    KVKK artefaktı yalnız kimlik doğrulamalı uçtan akar. Depoya imzalı URL yeteneği
    eklenirse bu test kırılır ve KVKK yolunun gözden geçirilmesi gerektiğini hatırlatır.
    """
    depo = nesne_depo_al()
    yasak = {"presigned_url", "imzali_url", "get_presigned_url", "paylas"}
    mevcut = {ad for ad in dir(depo) if not ad.startswith("_")}
    assert not (yasak & mevcut), f"nesne deposunda imzali URL yuzeyi belirdi: {yasak & mevcut}"
