"""S15 dijital ikiz testleri — yerleşim (replace-all) + canlı durum ucu.

Kesin sayısal doğrulama için testler kendi izole ``ikiz`` tenant'ını provizyonlar
(alfa/beta diğer test dosyalarının verisiyle kirlenebilir). Bilinen sentetik veri
ekilir; durum yanıtı elle hesaplanan değerlerle birebir karşılaştırılır.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.control_plane.provizyon import tenant_provizyonla
from app.core.db.tenancy import search_path_ayarla
from app.modules.analitik.hesap import donem_oee
from app.modules.uretim.models import ArizaKaydi, Makine, UretimVerisi
from tests.conftest import TEST_URL

pytestmark = pytest.mark.asyncio

IKIZ = {"slug": "ikiz", "ad": "İkiz Fabrika", "eposta": "admin@ikiz.test", "parola": "Ikiz1234!"}


async def _ikiz_seed(sm: async_sessionmaker[AsyncSession]) -> dict[str, int]:
    """ikiz tenant'ına bilinen veri eker (idempotent); makine kod→id döndürür."""
    async with sm() as db:
        await search_path_ayarla(db, "ikiz")
        mevcut = await db.execute(select(Makine).where(Makine.kod.like("IKZ-%")))
        makineler = {m.kod: m for m in mevcut.scalars().all()}
        if not makineler:
            m1 = Makine(kod="IKZ-MAK-1", ad="Pres Hattı 1", durum="calisiyor")
            m2 = Makine(kod="IKZ-MAK-2", ad="Kaynak Robotu", durum="ariza")
            m3 = Makine(kod="IKZ-MAK-3", ad="Paketleme", durum="durdu")
            db.add_all([m1, m2, m3])
            await db.flush()
            simdi = datetime.now(UTC)
            # m1: pencere içinde (2 saat önce) — OEE elle doğrulanır.
            db.add(
                UretimVerisi(
                    zaman=simdi - timedelta(hours=2),
                    makine_id=m1.id,
                    planlanan_sure_dk=480.0,
                    durus_sure_dk=60.0,
                    toplam_adet=400,
                    saglam_adet=380,
                    ideal_cevrim_sn=60.0,
                )
            )
            # m2: 24 saatlik pencerenin DIŞINDA (30 saat önce) — saat=48'de görünür.
            db.add(
                UretimVerisi(
                    zaman=simdi - timedelta(hours=30),
                    makine_id=m2.id,
                    planlanan_sure_dk=480.0,
                    durus_sure_dk=0.0,
                    toplam_adet=200,
                    saglam_adet=200,
                    ideal_cevrim_sn=60.0,
                )
            )
            # Arıza: 1 açık + 1 çözülmüş → acik_ariza = 1.
            db.add(ArizaKaydi(makine_id=m2.id, baslangic=simdi - timedelta(hours=1), cozuldu=False))
            db.add(
                ArizaKaydi(
                    makine_id=m1.id,
                    baslangic=simdi - timedelta(days=2),
                    bitis=simdi - timedelta(days=1),
                    cozuldu=True,
                )
            )
            await db.commit()
            makineler = {"IKZ-MAK-1": m1, "IKZ-MAK-2": m2, "IKZ-MAK-3": m3}
        return {kod: m.id for kod, m in makineler.items()}


@pytest_asyncio.fixture
async def ikiz_ortam(
    kurulu_istemci: AsyncClient, test_engine: AsyncEngine
) -> AsyncIterator[tuple[AsyncClient, dict[str, int]]]:
    await tenant_provizyonla(
        slug=IKIZ["slug"],
        ad=IKIZ["ad"],
        admin_eposta=IKIZ["eposta"],
        admin_parola=IKIZ["parola"],
        db_url=TEST_URL,
    )
    sm = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)
    idler = await _ikiz_seed(sm)
    yield kurulu_istemci, idler


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


async def test_yerlesim_roundtrip_replace_all(
    ikiz_ortam: tuple[AsyncClient, dict[str, int]],
) -> None:
    istemci, idler = ikiz_ortam
    h = _h("ikiz", await _giris(istemci, IKIZ))

    govde = {
        "dugumler": [
            {"makine_id": idler["IKZ-MAK-1"], "x": 10.0, "y": 20.0, "bolge": "Hat A"},
            {"makine_id": idler["IKZ-MAK-2"], "x": 55.5, "y": 40.0, "bolge": "Hat B"},
        ]
    }
    r = await istemci.put("/api/v1/ikiz/yerlesim", json=govde, headers=h)
    assert r.status_code == 200, r.text

    r = await istemci.get("/api/v1/ikiz/yerlesim", headers=h)
    assert r.status_code == 200, r.text
    dugumler = r.json()["data"]
    assert len(dugumler) == 2
    ilk = next(d for d in dugumler if d["makine_id"] == idler["IKZ-MAK-1"])
    assert (ilk["x"], ilk["y"], ilk["bolge"]) == (10.0, 20.0, "Hat A")

    # replace-all: tek düğümlü PUT öncekileri siler.
    r = await istemci.put(
        "/api/v1/ikiz/yerlesim",
        json={"dugumler": [{"makine_id": idler["IKZ-MAK-3"], "x": 90.0, "y": 90.0}]},
        headers=h,
    )
    assert r.status_code == 200, r.text
    r = await istemci.get("/api/v1/ikiz/yerlesim", headers=h)
    dugumler = r.json()["data"]
    assert len(dugumler) == 1
    assert dugumler[0]["makine_id"] == idler["IKZ-MAK-3"]
    assert dugumler[0]["bolge"] == ""


async def test_yerlesim_dogrulama_422(ikiz_ortam: tuple[AsyncClient, dict[str, int]]) -> None:
    istemci, idler = ikiz_ortam
    h = _h("ikiz", await _giris(istemci, IKIZ))
    m1 = idler["IKZ-MAK-1"]

    # Koordinat sınır dışı (Pydantic).
    r = await istemci.put(
        "/api/v1/ikiz/yerlesim",
        json={"dugumler": [{"makine_id": m1, "x": 101.0, "y": 0.0}]},
        headers=h,
    )
    assert r.status_code == 422, r.text

    # Mükerrer makine_id.
    r = await istemci.put(
        "/api/v1/ikiz/yerlesim",
        json={
            "dugumler": [
                {"makine_id": m1, "x": 1.0, "y": 1.0},
                {"makine_id": m1, "x": 2.0, "y": 2.0},
            ]
        },
        headers=h,
    )
    assert r.status_code == 422, r.text

    # Var olmayan makine.
    r = await istemci.put(
        "/api/v1/ikiz/yerlesim",
        json={"dugumler": [{"makine_id": 999999, "x": 1.0, "y": 1.0}]},
        headers=h,
    )
    assert r.status_code == 422, r.text
    assert "999999" in r.text


async def test_durum_dogru_hesaplar(ikiz_ortam: tuple[AsyncClient, dict[str, int]]) -> None:
    istemci, idler = ikiz_ortam
    h = _h("ikiz", await _giris(istemci, IKIZ))

    r = await istemci.put(
        "/api/v1/ikiz/yerlesim",
        json={
            "dugumler": [
                {"makine_id": idler["IKZ-MAK-1"], "x": 10.0, "y": 20.0, "bolge": "Hat A"},
                {"makine_id": idler["IKZ-MAK-2"], "x": 55.0, "y": 40.0, "bolge": "Hat B"},
            ]
        },
        headers=h,
    )
    assert r.status_code == 200, r.text

    # saat=24 → yalnız m1'in kaydı pencerede.
    r = await istemci.get("/api/v1/ikiz/durum", headers=h)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert veri["saat"] == 24

    ozet = veri["ozet"]
    assert ozet["toplam_makine"] == 3
    assert ozet["durumlar"] == {"calisiyor": 1, "ariza": 1, "durdu": 1}
    assert ozet["kayit_sayisi"] == 1
    assert ozet["toplam_adet"] == 400
    assert ozet["saglam_adet"] == 380
    assert ozet["acik_ariza"] == 1
    beklenen_oee = donem_oee(
        planlanan_sure_dk=480.0,
        durus_sure_dk=60.0,
        toplam_adet=400,
        saglam_adet=380,
        ideal_toplam_sn=60.0 * 400,
    ).oee
    assert ozet["oee"] == pytest.approx(beklenen_oee, abs=1e-6)
    assert ozet["fire_orani"] == pytest.approx(20.0 / 400.0, abs=1e-6)

    dugumler = {d["makine_kod"]: d for d in veri["dugumler"]}
    assert set(dugumler) == {"IKZ-MAK-1", "IKZ-MAK-2"}
    d1 = dugumler["IKZ-MAK-1"]
    assert d1["durum"] == "calisiyor"
    assert d1["bolge"] == "Hat A"
    assert d1["oee"] == pytest.approx(beklenen_oee, abs=1e-6)
    assert d1["toplam_adet"] == 400
    assert d1["son_veri_zamani"] is not None
    # m2 pencere dışı → üretim özeti boş ama durum canlı.
    d2 = dugumler["IKZ-MAK-2"]
    assert d2["durum"] == "ariza"
    assert d2["oee"] is None
    assert d2["toplam_adet"] == 0

    yerlesmemis = veri["yerlesmemis"]
    assert [m["makine_kod"] for m in yerlesmemis] == ["IKZ-MAK-3"]

    # saat=48 → m2'nin 30 saat önceki kaydı da pencereye girer.
    r = await istemci.get("/api/v1/ikiz/durum?saat=48", headers=h)
    veri = r.json()["data"]
    assert veri["ozet"]["kayit_sayisi"] == 2
    assert veri["ozet"]["toplam_adet"] == 600
    d2 = next(d for d in veri["dugumler"] if d["makine_kod"] == "IKZ-MAK-2")
    assert d2["oee"] == pytest.approx(200.0 / 480.0, abs=1e-6)

    # saat sınırları.
    for saat in (0, 169):
        r = await istemci.get(f"/api/v1/ikiz/durum?saat={saat}", headers=h)
        assert r.status_code == 422, r.text


async def test_rbac_izleyici_yerlesim_yazamaz(
    ikiz_ortam: tuple[AsyncClient, dict[str, int]],
) -> None:
    istemci, idler = ikiz_ortam
    admin = _h("ikiz", await _giris(istemci, IKIZ))
    r = await istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "izleyici@ikiz.test", "parola": "Izle1234!", "roller": ["izleyici"]},
        headers=admin,
    )
    assert r.status_code in (200, 201, 409), r.text  # idempotent (tekrar koşuda 409)
    izleyici = _h(
        "ikiz",
        await _giris(
            istemci, {"slug": "ikiz", "eposta": "izleyici@ikiz.test", "parola": "Izle1234!"}
        ),
    )
    # Okur…
    r = await istemci.get("/api/v1/ikiz/durum", headers=izleyici)
    assert r.status_code == 200, r.text
    # …ama yazamaz.
    r = await istemci.put(
        "/api/v1/ikiz/yerlesim",
        json={"dugumler": [{"makine_id": idler["IKZ-MAK-1"], "x": 1.0, "y": 1.0}]},
        headers=izleyici,
    )
    assert r.status_code == 403, r.text


async def test_izolasyon_beta_ikiz_verisi_gormez(
    ikiz_ortam: tuple[AsyncClient, dict[str, int]],
) -> None:
    from tests.conftest import BETA

    istemci, _ = ikiz_ortam
    beta = _h("beta", await _giris(istemci, BETA))
    r = await istemci.get("/api/v1/ikiz/durum", headers=beta)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    kodlar = {d["makine_kod"] for d in veri["dugumler"]} | {
        m["makine_kod"] for m in veri["yerlesmemis"]
    }
    assert not any(k.startswith("IKZ-") for k in kodlar)
