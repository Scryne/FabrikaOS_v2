"""S16 API testleri — GET /moduller (oturum) + GET /abonelik (abonelik:oku)."""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import ALFA
from tests.test_s16_entitlement import GAMMA, _giris, gamma_db  # noqa: F401  (fixture)

MODULLER = "/api/v1/moduller"
ABONELIK = "/api/v1/abonelik"


async def test_moduller_temel_planda_dogru_harita(
    gamma_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
) -> None:
    h = await _giris(kurulu_istemci, GAMMA)
    r = await kurulu_istemci.get(MODULLER, headers=h)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]

    durum = {m["kod"]: m for m in veri["moduller"]}
    assert durum["uretim"]["acik"] is True
    assert durum["uretim"]["kaynak"] == "plan"
    assert durum["ai"]["acik"] is False  # temel planda kapalı
    assert durum["ai"]["kaynak"] == "plan"
    assert len(durum) == 17

    ozellik = {o["kod"]: o for o in veri["ozellikler"]}
    assert ozellik["mobil-api"]["acik"] is False  # temel planda özellik yok
    assert ozellik["mobil-api"]["deneysel"] is True


async def test_moduller_izinsiz_rol_bile_gorur_abonelik_403(
    gamma_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
) -> None:
    # saha-cihaz rolü yalnız `edge` iznine sahiptir (abonelik:oku yok).
    admin = await _giris(kurulu_istemci, ALFA)
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={
            "eposta": "edge16@alfa.test",
            "parola": "Edge12345!",
            "roller": ["saha-cihaz"],
        },
        headers=admin,
    )
    edge = await _giris(
        kurulu_istemci, {"slug": "alfa", "eposta": "edge16@alfa.test", "parola": "Edge12345!"}
    )

    r = await kurulu_istemci.get(MODULLER, headers=edge)
    assert r.status_code == 200, r.text  # menü süzgeci: oturum yeter

    r = await kurulu_istemci.get(ABONELIK, headers=edge)
    assert r.status_code == 403, r.text  # plan/koltuk ayrıntısı izin ister


async def test_abonelik_ozeti_plan_koltuk_ve_matris(
    gamma_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
) -> None:
    h = await _giris(kurulu_istemci, GAMMA)
    r = await kurulu_istemci.get(ABONELIK, headers=h)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]

    assert veri["plan"]["kod"] == "temel"
    assert veri["plan"]["koltuk_limiti"] == 10
    assert veri["durum"] == "deneme"
    assert veri["koltuk"]["limit"] == 10
    assert veri["koltuk"]["kullanilan"] >= 1  # en az provizyon admini
    assert len(veri["moduller"]) == 17
    assert any(o["deneysel"] for o in veri["ozellikler"])


async def test_abonelik_sinirsiz_planda_limit_null(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)  # alfa test fixture'ı kurumsal planda
    r = await kurulu_istemci.get(ABONELIK, headers=h)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert veri["plan"]["kod"] == "kurumsal"
    assert veri["koltuk"]["limit"] is None
    assert all(m["acik"] for m in veri["moduller"])
