"""Tablolarda/çekmecelerde ham id yerine okunur ad (2026-11-03).

İzin talebi personeli ``#6`` diye gösteriyordu; enerji tablosu makineyi çıplak id ile.
Yanıtlar artık okunur adı taşır. Korunan üç şey ayrıca sınanır:

- **N+1 yok:** liste uçlarının SQL sayısı satır sayısından bağımsızdır (adlar tek sorguda).
- **KVKK:** izin yanıtı yalnız ad/soyad taşır; TC kimlik no hiçbir biçimde dönmez.
- **RBAC:** ad, kaydın kendi okuma izniyle gelir; izinsiz rol yine 403 alır.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.conftest import ALFA, onayci_basliklari

API = "/api/v1"


async def _admin(istemci: AsyncClient) -> dict[str, str]:
    r = await istemci.post(
        f"{API}/kimlik/token",
        data={"username": ALFA["eposta"], "password": ALFA["parola"]},
        headers={"X-Tenant": ALFA["slug"]},
    )
    assert r.status_code == 200, r.text
    return {"X-Tenant": "alfa", "Authorization": f"Bearer {r.json()['data']['access_token']}"}


@contextmanager
def _sorgu_sayaci(engine: AsyncEngine) -> Iterator[list[str]]:
    """Blok içinde çalışan SELECT'leri toplar (N+1 tespiti için)."""
    sorgular: list[str] = []

    def _dinle(_c: Any, _cur: Any, ifade: str, *_a: Any, **_k: Any) -> None:
        if ifade.lstrip().upper().startswith("SELECT"):
            sorgular.append(ifade)

    event.listen(engine.sync_engine, "before_cursor_execute", _dinle)
    try:
        yield sorgular
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", _dinle)


async def _personel(istemci: AsyncClient, h: dict[str, str], ad: str, soyad: str) -> int:
    r = await istemci.post(
        f"{API}/personeller",
        json={
            "sicil_no": f"OA-{uuid4().hex[:8]}",
            "ad": ad,
            "soyad": soyad,
            "tc_kimlik_no": "12345678950",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    return int(r.json()["data"]["id"])


async def _izin(istemci: AsyncClient, h: dict[str, str], pid: int) -> dict[str, Any]:
    r = await istemci.post(
        f"{API}/izin-talepleri",
        json={
            "personel_id": pid,
            "izin_turu": "yillik",
            "baslangic_tarihi": "2026-12-07",
            "bitis_tarihi": "2026-12-08",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    return dict(r.json()["data"])


async def test_izin_yaniti_personel_adini_tasir_tc_tasimaz(kurulu_istemci: AsyncClient) -> None:
    h = await _admin(kurulu_istemci)
    pid = await _personel(kurulu_istemci, h, "Selin", "Kaya")
    olusan = await _izin(kurulu_istemci, h, pid)
    assert olusan["personel_ad"] == "Selin Kaya"

    detay = (await kurulu_istemci.get(f"{API}/izin-talepleri/{olusan['id']}", headers=h)).json()
    assert detay["data"]["personel_ad"] == "Selin Kaya"

    liste = await kurulu_istemci.get(f"{API}/izin-talepleri?personel_id={pid}", headers=h)
    assert [x["personel_ad"] for x in liste.json()["data"]] == ["Selin Kaya"]

    # Durum geçişi yanıtı da adı taşır (çekmece onay sonrası tazelenir).
    gonder = await kurulu_istemci.post(f"{API}/izin-talepleri/{olusan['id']}/gonder", headers=h)
    assert gonder.json()["data"]["personel_ad"] == "Selin Kaya"

    # KVKK: TC ne alan olarak ne de değer olarak izin yanıtına sızmaz.
    for govde in (detay, liste.json(), gonder.json()):
        assert "tc_kimlik_no" not in str(govde)
        assert "12345678950" not in str(govde)


async def test_izin_listesi_n_arti_1_yok(
    kurulu_istemci: AsyncClient, test_engine: AsyncEngine
) -> None:
    h = await _admin(kurulu_istemci)
    pidler = [await _personel(kurulu_istemci, h, f"Ad{i}", "Soyad") for i in range(5)]
    await _izin(kurulu_istemci, h, pidler[0])
    yol = f"{API}/izin-talepleri?siralama=id&yon=desc"

    with _sorgu_sayaci(test_engine) as tek:
        r1 = await kurulu_istemci.get(f"{yol}&adet=1", headers=h)
    for pid in pidler[1:]:
        await _izin(kurulu_istemci, h, pid)
    with _sorgu_sayaci(test_engine) as bes:
        r5 = await kurulu_istemci.get(f"{yol}&adet=5", headers=h)

    assert len(r1.json()["data"]) == 1
    assert len(r5.json()["data"]) == 5
    assert all(x["personel_ad"] for x in r5.json()["data"])
    # Satır sayısı 5 katına çıktı; sorgu sayısı değişmedi (adlar tek IN sorgusunda).
    assert len(bes) == len(tek), (tek, bes)


async def test_izin_adi_rbac_gevsetmez(kurulu_istemci: AsyncClient) -> None:
    h = await _admin(kurulu_istemci)
    pid = await _personel(kurulu_istemci, h, "Gizli", "Personel")
    izin = await _izin(kurulu_istemci, h, pid)
    # ik:oku taşımayan rol (enerji) izin talebini — dolayısıyla personel adını — göremez.
    enerjici = await onayci_basliklari(kurulu_istemci, h, roller=("enerji",))
    r = await kurulu_istemci.get(f"{API}/izin-talepleri/{izin['id']}", headers=enerjici)
    assert r.status_code == 403, r.text
    r = await kurulu_istemci.get(f"{API}/izin-talepleri", headers=enerjici)
    assert r.status_code == 403, r.text


async def test_enerji_listesi_makine_kodu_tek_sorguda(
    kurulu_istemci: AsyncClient, test_engine: AsyncEngine
) -> None:
    h = await _admin(kurulu_istemci)
    kodlar = [f"EN-{uuid4().hex[:6].upper()}" for _ in range(4)]
    mids = []
    for kod in kodlar:
        r = await kurulu_istemci.post(
            f"{API}/makineler", json={"kod": kod, "ad": f"Makine {kod}"}, headers=h
        )
        assert r.status_code == 201, r.text
        mids.append(int(r.json()["data"]["id"]))

    def olcum(mid: int | None) -> dict[str, Any]:
        g: dict[str, Any] = {"enerji_turu": "elektrik", "tuketim": 3, "birim": "kWh"}
        g["zaman"] = "2026-05-02T08:00:00Z"
        if mid is not None:
            g["makine_id"] = mid
        return g

    r = await kurulu_istemci.post(f"{API}/enerji-tuketimleri", json=olcum(mids[0]), headers=h)
    assert r.json()["data"]["makine_kod"] == kodlar[0]
    yol = f"{API}/enerji-tuketimleri?siralama=id&yon=desc"
    with _sorgu_sayaci(test_engine) as tek:
        await kurulu_istemci.get(f"{yol}&adet=1", headers=h)

    for mid in [*mids[1:], None]:
        await kurulu_istemci.post(f"{API}/enerji-tuketimleri", json=olcum(mid), headers=h)
    with _sorgu_sayaci(test_engine) as bes:
        r5 = await kurulu_istemci.get(f"{yol}&adet=5", headers=h)

    satirlar = r5.json()["data"]
    assert [x["makine_kod"] for x in satirlar] == [None, *reversed(kodlar)]
    assert len(bes) == len(tek), (tek, bes)
