"""S18 katalog/izin/rol testleri — entegrasyon + dis-portal modülleri, dis-panel rolü.

Kapı davranışı (temel planda 403 MODUL_KAPALI, `webhook-onizleme` bayrağı override'ı)
webhook uçlarıyla birlikte `test_s18_webhook_ucler.py`'de; burada katalog/seed sözleşmesi.
"""

from __future__ import annotations

from httpx import AsyncClient

from app.control_plane.moduller import MODUL_KATALOGU, OZELLIK_KATALOGU, PLAN_KATALOGU
from app.kimlik.izinler import IZIN_KATALOGU, VARSAYILAN_ROLLER
from tests.conftest import ALFA


def test_katalogda_s18_modulleri_var() -> None:
    assert "entegrasyon" in MODUL_KATALOGU
    assert "dis-portal" in MODUL_KATALOGU
    # webhook-onizleme bayrağı S16'dan beri katalogda — S18 tüketicisi buna güvenir.
    assert "webhook-onizleme" in OZELLIK_KATALOGU


def test_s18_modulleri_yalniz_ust_segment_planlarda() -> None:
    for kod in ("entegrasyon", "dis-portal"):
        assert kod in PLAN_KATALOGU["deneme"].moduller, kod
        assert kod in PLAN_KATALOGU["kurumsal"].moduller, kod
        assert kod not in PLAN_KATALOGU["temel"].moduller, kod
        assert kod not in PLAN_KATALOGU["profesyonel"].moduller, kod


def test_izin_katalogu_s18_kodlari() -> None:
    for kod in ("entegrasyon:oku", "entegrasyon:yaz", "dis:erisim"):
        assert kod in IZIN_KATALOGU, kod


def test_dis_panel_rolu_yalniz_dis_erisim() -> None:
    # Skill sözleşmesi: dış panel rolü iç modül izinleriyle KARIŞMAZ.
    assert VARSAYILAN_ROLLER["dis-panel"] == frozenset({"dis:erisim"})


def test_entegrasyon_rolu_yalniz_kendi_kapsami() -> None:
    assert VARSAYILAN_ROLLER["entegrasyon"] == frozenset({"entegrasyon:oku", "entegrasyon:yaz"})


async def test_seed_yeni_roller_provizyonda(kurulu_istemci: AsyncClient) -> None:
    r = await kurulu_istemci.post(
        "/api/v1/kimlik/token",
        data={"username": ALFA["eposta"], "password": ALFA["parola"]},
        headers={"X-Tenant": "alfa"},
    )
    assert r.status_code == 200, r.text
    h = {"X-Tenant": "alfa", "Authorization": f"Bearer {r.json()['data']['access_token']}"}

    r = await kurulu_istemci.get("/api/v1/roller", headers=h)
    assert r.status_code == 200, r.text
    adlar = {rol["ad"] for rol in r.json()["data"]}
    assert {"entegrasyon", "dis-panel"} <= adlar
