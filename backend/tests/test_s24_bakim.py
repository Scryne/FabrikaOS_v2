"""S24 bakım olgunluğu testleri — vade taraması (bir-kez) + arıza otomasyonu + MTBF/MTTR ucu."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from tests.conftest import ALFA
from tests.test_s16_entitlement import _giris

pytestmark = pytest.mark.asyncio


async def _makine(istemci: AsyncClient, h: dict[str, str], kod: str) -> int:
    r = await istemci.post("/api/v1/makineler", json={"kod": kod, "ad": f"{kod} m."}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


async def test_vade_taramasi_bir_kez_is_emri_uretir(
    test_db: str, kurulu_istemci: AsyncClient
) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    mid = await _makine(kurulu_istemci, h, "S24-VDE")
    gecmis = (datetime.now(UTC) - timedelta(days=1)).isoformat()

    r = await kurulu_istemci.post(
        "/api/v1/bakim-planlari",
        json={
            "makine_id": mid,
            "ad": "S24 Aylık bakım",
            "tip": "periyodik",
            "periyot_gun": 30,
            "sonraki_bakim_tarihi": gecmis,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    plan_id = r.json()["data"]["id"]

    # İlk tarama: 1 iş emri üretilir; plan vadesi periyot kadar ileri atılır.
    r = await kurulu_istemci.post("/api/v1/bakim-planlari/vade-tara", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["uretilen_is_emri"] == 1
    r = await kurulu_istemci.get(f"/api/v1/is-emirleri?makine_id={mid}", headers=h)
    otomatikler = [ie for ie in r.json()["data"] if ie["bakim_plani_id"] == plan_id]
    assert len(otomatikler) == 1
    assert otomatikler[0]["baslik"].startswith("Bakım — ")
    ie_id = otomatikler[0]["id"]

    r = await kurulu_istemci.get(f"/api/v1/bakim-planlari/{plan_id}", headers=h)
    yeni_vade = r.json()["data"]["sonraki_bakim_tarihi"]
    assert yeni_vade is not None and yeni_vade > datetime.now(UTC).isoformat()

    # İkinci tarama: vade ileride → üretmez.
    r = await kurulu_istemci.post("/api/v1/bakim-planlari/vade-tara", headers=h)
    assert r.json()["data"]["uretilen_is_emri"] == 0

    # Vade tekrar geçmişe çekilse bile AÇIK otomatik iş emri varken üretmez (dedup katmanı 2).
    r = await kurulu_istemci.patch(
        f"/api/v1/bakim-planlari/{plan_id}", json={"sonraki_bakim_tarihi": gecmis}, headers=h
    )
    assert r.status_code == 200
    r = await kurulu_istemci.post("/api/v1/bakim-planlari/vade-tara", headers=h)
    assert r.json()["data"]["uretilen_is_emri"] == 0

    # İş emri kapatılınca (iptal) yeni tarama tekrar üretebilir.
    r = await kurulu_istemci.patch(
        f"/api/v1/is-emirleri/{ie_id}/durum", json={"durum": "iptal"}, headers=h
    )
    assert r.status_code == 200
    r = await kurulu_istemci.post("/api/v1/bakim-planlari/vade-tara", headers=h)
    assert r.json()["data"]["uretilen_is_emri"] == 1


async def test_ariza_otomasyonu_ve_mtbf_mttr_ucu(test_db: str, kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    mid = await _makine(kurulu_istemci, h, "S24-MTB")

    # Arızaya geçiş: açık arıza kaydı otomatik açılır.
    r = await kurulu_istemci.patch(
        f"/api/v1/makineler/{mid}/durum", json={"durum": "ariza"}, headers=h
    )
    assert r.status_code == 200, r.text
    r = await kurulu_istemci.get(f"/api/v1/bakim/metrikler?makine_id={mid}&gun=30", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["ariza_sayisi"] == 1
    assert data["kapanan_ariza"] == 0
    assert data["mttr_saat"] is None  # açık arıza — onarım süresi bilinmiyor

    # Arızadan çıkış: kayıt kapanır → MTTR hesaplanabilir.
    r = await kurulu_istemci.patch(
        f"/api/v1/makineler/{mid}/durum", json={"durum": "calisiyor"}, headers=h
    )
    assert r.status_code == 200
    r = await kurulu_istemci.get(f"/api/v1/bakim/metrikler?makine_id={mid}&gun=30", headers=h)
    data = r.json()["data"]
    assert data["kapanan_ariza"] == 1
    assert data["mttr_saat"] is not None
    assert data["mtbf_saat"] is not None

    # Var olmayan makine 404.
    r = await kurulu_istemci.get("/api/v1/bakim/metrikler?makine_id=999999", headers=h)
    assert r.status_code == 404
