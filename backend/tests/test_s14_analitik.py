"""S14 analitik testleri — saf dönem OEE + /analitik/kpi + /analitik/trend.

Kesin sayısal doğrulama için testler kendi izole ``kpi`` tenant'ını provizyonlar
(alfa/beta diğer test dosyalarının verisiyle kirlenebilir). Bilinen sentetik veri
ekilir; KPI/trend yanıtı elle hesaplanan değerlerle birebir karşılaştırılır.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.control_plane.provizyon import tenant_provizyonla
from app.core.db.tenancy import search_path_ayarla
from app.modules.analitik.hesap import donem_oee, fire_orani
from app.modules.bakim.models import BakimPlani
from app.modules.enerji.models import EnerjiTuketim
from app.modules.isemri.models import IsEmri
from app.modules.isg.models import IsKazasi
from app.modules.kalite.models import KaliteKontrol, Uygunsuzluk
from app.modules.stok.models import Malzeme
from app.modules.uretim.models import Makine, UretimVerisi
from tests.conftest import TEST_URL

KPI = {"slug": "kpi", "ad": "KPI Fabrika", "eposta": "admin@kpi.test", "parola": "Kpi12345!"}


# --- Saf dönem OEE (birim) ---
def test_donem_oee_bilesenler() -> None:
    # 2 kayıt toplamı: planlanan 960, duruş 60, 600/580 adet, ideal toplam 36000 sn.
    sonuc = donem_oee(
        planlanan_sure_dk=960.0,
        durus_sure_dk=60.0,
        toplam_adet=600,
        saglam_adet=580,
        ideal_toplam_sn=36000.0,
    )
    assert sonuc.kullanilabilirlik == pytest.approx(0.9375)
    assert sonuc.performans == pytest.approx(600.0 / 900.0)
    assert sonuc.kalite == pytest.approx(580.0 / 600.0)
    assert sonuc.oee == pytest.approx(0.9375 * (600.0 / 900.0) * (580.0 / 600.0))


def test_donem_oee_sifir_veri() -> None:
    sonuc = donem_oee(
        planlanan_sure_dk=0.0, durus_sure_dk=0.0, toplam_adet=0, saglam_adet=0, ideal_toplam_sn=0.0
    )
    assert sonuc.oee == 0.0


def test_fire_orani() -> None:
    assert fire_orani(600, 580) == pytest.approx(20.0 / 600.0)
    assert fire_orani(0, 0) == 0.0


# --- Entegrasyon: izole kpi tenant'ı + bilinen veri ---
def _ogle(gun_once: int) -> datetime:
    """Gün sınırı sorunlarına karşı öğlene sabitlenmiş geçmiş zaman damgası."""
    simdi = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0)
    return simdi - timedelta(days=gun_once)


async def _kpi_seed(sm: async_sessionmaker[AsyncSession]) -> None:
    """kpi tenant'ına bilinen analitik verisi eker (idempotent: KP-MAK-1 varsa atlar)."""
    async with sm() as db:
        await search_path_ayarla(db, "kpi")
        mevcut = await db.execute(select(Makine).where(Makine.kod == "KP-MAK-1"))
        if mevcut.scalar_one_or_none() is not None:
            return
        m1 = Makine(kod="KP-MAK-1", ad="KPI Makine 1", durum="calisiyor")
        m2 = Makine(kod="KP-MAK-2", ad="KPI Makine 2", durum="ariza")
        db.add_all([m1, m2])
        await db.flush()
        # Üretim: 2 kayıt, 2 ayrı gün (dönem OEE + trend elle doğrulanır).
        db.add(
            UretimVerisi(
                zaman=_ogle(2),
                makine_id=m1.id,
                planlanan_sure_dk=480.0,
                durus_sure_dk=60.0,
                toplam_adet=400,
                saglam_adet=380,
                ideal_cevrim_sn=60.0,
            )
        )
        db.add(
            UretimVerisi(
                zaman=_ogle(1),
                makine_id=m2.id,
                planlanan_sure_dk=480.0,
                durus_sure_dk=0.0,
                toplam_adet=200,
                saglam_adet=200,
                ideal_cevrim_sn=60.0,
            )
        )
        # İş emri: 1 açık + 1 kapanmış (2 saatte).
        acilis = _ogle(3)
        db.add(IsEmri(kod="KP-IE-1", baslik="Açık iş", makine_id=m1.id, durum="acik"))
        db.add(
            IsEmri(
                kod="KP-IE-2",
                baslik="Kapanan iş",
                makine_id=m1.id,
                durum="kapandi",
                olusturma_tarihi=acilis,
                kapanis_tarihi=acilis + timedelta(hours=2),
            )
        )
        # Stok: 1 kritik altında + 1 normal.
        db.add(
            Malzeme(
                kod="KP-MLZ-1",
                ad="Kritik Malzeme",
                birim="adet",
                mevcut_miktar=Decimal(5),
                kritik_stok=Decimal(10),
            )
        )
        db.add(
            Malzeme(
                kod="KP-MLZ-2",
                ad="Normal Malzeme",
                birim="adet",
                mevcut_miktar=Decimal(100),
                kritik_stok=Decimal(10),
            )
        )
        # Kalite: 3 kontrol (2 gecti, 1 kaldi) + 1 açık uygunsuzluk.
        for i, sonuc in enumerate(("gecti", "gecti", "kaldi"), start=1):
            db.add(KaliteKontrol(kod=f"KP-KK-{i}", sonuc=sonuc, zaman=_ogle(1)))
        db.add(Uygunsuzluk(kod="KP-UY-1", baslik="Açık uygunsuzluk", durum="acik"))
        # Enerji: elektrik 100.5 + 50.5 kWh, dogalgaz 10 m3.
        db.add(
            EnerjiTuketim(
                zaman=_ogle(2), enerji_turu="elektrik", tuketim=Decimal("100.5"), birim="kWh"
            )
        )
        db.add(
            EnerjiTuketim(
                zaman=_ogle(1), enerji_turu="elektrik", tuketim=Decimal("50.5"), birim="kWh"
            )
        )
        db.add(
            EnerjiTuketim(zaman=_ogle(1), enerji_turu="dogalgaz", tuketim=Decimal(10), birim="m3")
        )
        # İSG: 1 kaza + 1 ramak kala.
        db.add(IsKazasi(kod="KP-KZ-1", tur="kaza", olay_tarihi=_ogle(2)))
        db.add(IsKazasi(kod="KP-KZ-2", tur="ramak_kala", olay_tarihi=_ogle(1)))
        # Bakım: 1 geciken (dün geçmiş) + 1 ileride.
        db.add(BakimPlani(makine_id=m1.id, ad="Geciken bakım", sonraki_bakim_tarihi=_ogle(1)))
        db.add(
            BakimPlani(
                makine_id=m2.id,
                ad="Planlı bakım",
                sonraki_bakim_tarihi=_ogle(0) + timedelta(days=10),
            )
        )
        await db.commit()


@pytest_asyncio.fixture
async def kpi_istemci(
    kurulu_istemci: AsyncClient, test_engine: AsyncEngine
) -> AsyncIterator[AsyncClient]:
    await tenant_provizyonla(
        slug=KPI["slug"],
        ad=KPI["ad"],
        admin_eposta=KPI["eposta"],
        admin_parola=KPI["parola"],
        db_url=TEST_URL,
    )
    sm = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)
    await _kpi_seed(sm)
    yield kurulu_istemci


async def _giris(istemci: AsyncClient, t: dict) -> str:
    r = await istemci.post(
        "/api/v1/kimlik/token",
        data={"username": t["eposta"], "password": t["parola"]},
        headers={"X-Tenant": t["slug"]},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["access_token"]


def _h(slug: str, access: str) -> dict[str, str]:
    return {"X-Tenant": slug, "Authorization": f"Bearer {access}"}


async def test_kpi_dogru_hesaplar(kpi_istemci: AsyncClient) -> None:
    h = _h("kpi", await _giris(kpi_istemci, KPI))
    r = await kpi_istemci.get("/api/v1/analitik/kpi?gun=30", headers=h)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert veri["gun"] == 30

    u = veri["uretim"]
    assert u["kayit_sayisi"] == 2
    assert u["toplam_adet"] == 600
    assert u["saglam_adet"] == 580
    assert u["fire_orani"] == pytest.approx(20.0 / 600.0, abs=1e-6)
    assert u["oee"] == pytest.approx(0.9375 * (600.0 / 900.0) * (580.0 / 600.0), abs=1e-6)

    assert veri["makine"] == {"toplam": 2, "durumlar": {"ariza": 1, "calisiyor": 1}}
    ie = veri["isemri"]
    assert ie["acik"] == 1
    assert ie["kapanan"] == 1
    assert ie["ortalama_kapanma_saat"] == pytest.approx(2.0, abs=0.01)
    assert veri["stok"] == {"toplam_malzeme": 2, "kritik_sayisi": 1}
    k = veri["kalite"]
    assert k["kontrol_sayisi"] == 3
    assert k["gecme_orani"] == pytest.approx(2.0 / 3.0, abs=1e-6)
    assert k["acik_uygunsuzluk"] == 1
    assert veri["enerji"]["kirilim"] == [
        {"enerji_turu": "dogalgaz", "birim": "m3", "toplam": 10.0},
        {"enerji_turu": "elektrik", "birim": "kWh", "toplam": 151.0},
    ]
    assert veri["isg"] == {"olay_sayisi": 2, "kaza_sayisi": 1}
    assert veri["bakim"] == {"aktif_plan": 2, "geciken": 1}


async def test_trend_gunluk_seri(kpi_istemci: AsyncClient) -> None:
    h = _h("kpi", await _giris(kpi_istemci, KPI))
    r = await kpi_istemci.get("/api/v1/analitik/trend?gun=30", headers=h)
    assert r.status_code == 200, r.text
    noktalar = r.json()["data"]
    assert len(noktalar) == 2  # iki ayrı günde üretim var
    ilk, son = noktalar[0], noktalar[1]
    assert ilk["gun"] < son["gun"]  # artan tarih sırası
    # 1. gün: 480/60 dk, 400/380 adet, çevrim 60 sn.
    assert ilk["toplam_adet"] == 400
    assert ilk["oee"] == pytest.approx((420 / 480) * (400 / 420) * (380 / 400), abs=1e-6)
    # 2. gün: 480/0 dk, 200/200 adet.
    assert son["toplam_adet"] == 200
    assert son["oee"] == pytest.approx(200.0 / 480.0, abs=1e-6)


async def test_gun_siniri_dogrulanir(kpi_istemci: AsyncClient) -> None:
    h = _h("kpi", await _giris(kpi_istemci, KPI))
    for gun in (0, 366):
        r = await kpi_istemci.get(f"/api/v1/analitik/kpi?gun={gun}", headers=h)
        assert r.status_code == 422, r.text


async def test_rbac_analitik_izni_olmayan_403(kpi_istemci: AsyncClient) -> None:
    admin = _h("kpi", await _giris(kpi_istemci, KPI))
    r = await kpi_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "depo@kpi.test", "parola": "Depo12345!", "roller": ["depo"]},
        headers=admin,
    )
    assert r.status_code in (200, 201, 409), r.text  # idempotent (tekrar koşuda 409)
    depo = _h(
        "kpi",
        await _giris(
            kpi_istemci, {"slug": "kpi", "eposta": "depo@kpi.test", "parola": "Depo12345!"}
        ),
    )
    for yol in ("kpi", "trend"):
        r = await kpi_istemci.get(f"/api/v1/analitik/{yol}", headers=depo)
        assert r.status_code == 403, r.text


async def test_izolasyon_beta_kpi_verisi_gormez(kpi_istemci: AsyncClient) -> None:
    from tests.conftest import BETA

    beta = _h("beta", await _giris(kpi_istemci, BETA))
    r = await kpi_istemci.get("/api/v1/analitik/kpi", headers=beta)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    # beta şeması kpi tenant'ının verisini görmez (kendi verisi de yok → sıfırlar).
    assert veri["uretim"]["kayit_sayisi"] == 0
    assert veri["stok"]["toplam_malzeme"] == 0
    assert veri["enerji"]["kirilim"] == []
