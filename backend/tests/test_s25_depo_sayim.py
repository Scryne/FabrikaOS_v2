"""S25-A: depo/lokasyon, lokasyon bakiyesi, transfer ve delta sayım (ADR-0024 kabul testleri).

- Lokasyonlu hareket: bakiye lokasyonda tutulur, malzeme toplamı korunur, lokasyonda yetersiz
  stok 422'dir (toplam yetse bile).
- Transfer: iki bacak, toplam değişmez, idempotent; ters yönlü eşzamanlı transferler kilit
  sırası sayesinde deadlock'sız biter ve son bakiyeler doğrudur.
- Sayım: sistem miktarı satır açılırken anlık görüntülenir; onayda fark DELTA uygulanır ve
  aradaki hareket korunur. Onay ``stok:duzeltme`` ister ve sayımı açan onaylayamaz.
- Göç: mevcut bakiye varsayılan ANA/GENEL lokasyonuna geri doldurulur.
"""

from __future__ import annotations

import asyncio
import uuid

import asyncpg
from httpx import AsyncClient

from app.core.db import fanout
from tests.conftest import ALFA, ASYNCPG_URL, BETA, TEST_URL
from tests.test_s16_entitlement import _giris

API = "/api/v1"


async def _malzeme(istemci: AsyncClient, h: dict[str, str], **ek: object) -> int:
    r = await istemci.post(
        f"{API}/malzemeler",
        json={"kod": f"S25-{uuid.uuid4().hex[:8]}", "ad": "S25 testi", "birim": "adet", **ek},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return int(r.json()["data"]["id"])


async def _depolar(istemci: AsyncClient, h: dict[str, str]) -> list[dict]:
    r = await istemci.get(f"{API}/depolar", headers=h)
    assert r.status_code == 200, r.text
    return r.json()["data"]


async def _genel(istemci: AsyncClient, h: dict[str, str]) -> int:
    ana = next(d for d in await _depolar(istemci, h) if d["kod"] == "ANA")
    return int(next(lok["id"] for lok in ana["lokasyonlar"] if lok["kod"] == "GENEL"))


async def _lokasyon(istemci: AsyncClient, h: dict[str, str], kod: str | None = None) -> int:
    ana = next(d for d in await _depolar(istemci, h) if d["kod"] == "ANA")
    r = await istemci.post(
        f"{API}/lokasyonlar",
        json={"depo_id": ana["id"], "kod": kod or f"RAF-{uuid.uuid4().hex[:6]}", "ad": "Raf"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return int(r.json()["data"]["id"])


async def _hareket(istemci, h, mid, tur, miktar, **ek):
    return await istemci.post(
        f"{API}/stok-hareketleri",
        json={"malzeme_id": mid, "tur": tur, "miktar": miktar, **ek},
        headers=h,
    )


async def _bakiye(istemci, h, mid) -> dict[int, float]:
    r = await istemci.get(f"{API}/stok-bakiyeleri", params={"malzeme_id": mid}, headers=h)
    assert r.status_code == 200, r.text
    return {row["lokasyon_id"]: row["miktar"] for row in r.json()["data"]}


async def _toplam(istemci, h, mid) -> float:
    r = await istemci.get(f"{API}/malzemeler/{mid}", headers=h)
    return float(r.json()["data"]["mevcut_miktar"])


async def _kullanici(istemci: AsyncClient, h: dict[str, str], roller: list[str]) -> dict[str, str]:
    eposta = f"s25-{uuid.uuid4().hex[:8]}@alfa.test"
    r = await istemci.post(
        f"{API}/kullanicilar",
        json={"eposta": eposta, "parola": "Sayim12345!", "ad_soyad": "S25", "roller": roller},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return await _giris(istemci, {"slug": "alfa", "eposta": eposta, "parola": "Sayim12345!"})


async def test_lokasyonlu_hareket_ve_lokasyon_yetersizligi(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    genel = await _genel(kurulu_istemci, h)
    raf = await _lokasyon(kurulu_istemci, h)
    mid = await _malzeme(kurulu_istemci, h)

    assert (await _hareket(kurulu_istemci, h, mid, "giris", 10)).status_code == 201
    r = await _hareket(kurulu_istemci, h, mid, "giris", 5, lokasyon_id=raf)
    assert r.status_code == 201 and r.json()["data"]["lokasyon_id"] == raf
    assert await _bakiye(kurulu_istemci, h, mid) == {genel: 10, raf: 5}
    assert await _toplam(kurulu_istemci, h, mid) == 15

    # Toplam (15) yetse de raftaki 5 yetmez → 422; bakiyeler değişmez.
    yetersiz = await _hareket(kurulu_istemci, h, mid, "cikis", 8, lokasyon_id=raf)
    assert yetersiz.status_code == 422
    assert await _bakiye(kurulu_istemci, h, mid) == {genel: 10, raf: 5}
    assert (await _hareket(kurulu_istemci, h, mid, "cikis", 3, lokasyon_id=raf)).status_code == 201
    assert await _bakiye(kurulu_istemci, h, mid) == {genel: 10, raf: 2}
    assert await _toplam(kurulu_istemci, h, mid) == 12


async def test_lot_takipli_giris_lot_ister(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    mid = await _malzeme(kurulu_istemci, h)
    c = await asyncpg.connect(ASYNCPG_URL)
    try:
        await c.execute('UPDATE "tenant_alfa".malzemeler SET lot_takipli = true WHERE id = $1', mid)
    finally:
        await c.close()
    assert (await _hareket(kurulu_istemci, h, mid, "giris", 5)).status_code == 422
    r = await _hareket(kurulu_istemci, h, mid, "giris", 5, lot_no="DKM-2026-001")
    assert r.status_code == 201 and r.json()["data"]["lot_no"] == "DKM-2026-001"


async def test_transfer_iki_bacak_idempotent_ve_dogrulama(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    genel = await _genel(kurulu_istemci, h)
    raf = await _lokasyon(kurulu_istemci, h)
    mid = await _malzeme(kurulu_istemci, h)
    await _hareket(kurulu_istemci, h, mid, "giris", 20)

    govde = {"malzeme_id": mid, "kaynak_lokasyon_id": genel, "hedef_lokasyon_id": raf, "miktar": 6}
    bh = {**h, "Idempotency-Key": f"tr-{uuid.uuid4().hex}"}
    r = await kurulu_istemci.post(f"{API}/stok-transferleri", json=govde, headers=bh)
    assert r.status_code == 201, r.text
    d = r.json()["data"]
    assert (d["cikis"]["tur"], d["giris"]["tur"]) == ("transfer_cikis", "transfer_giris")
    assert d["cikis"]["transfer_grubu"] == d["giris"]["transfer_grubu"]
    tekrar = await kurulu_istemci.post(f"{API}/stok-transferleri", json=govde, headers=bh)
    assert tekrar.status_code in (200, 201) and "zaten" in tekrar.json()["message"]
    assert await _bakiye(kurulu_istemci, h, mid) == {genel: 14, raf: 6}
    assert await _toplam(kurulu_istemci, h, mid) == 20

    fazla = await kurulu_istemci.post(
        f"{API}/stok-transferleri", json={**govde, "miktar": 15}, headers=h
    )
    assert fazla.status_code == 422
    ayni = await kurulu_istemci.post(
        f"{API}/stok-transferleri", json={**govde, "hedef_lokasyon_id": genel}, headers=h
    )
    assert ayni.status_code == 422


async def test_ters_yonlu_eszamanli_transferler_deadlocksuz(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    a = await _lokasyon(kurulu_istemci, h)
    b = await _lokasyon(kurulu_istemci, h)
    mid = await _malzeme(kurulu_istemci, h)
    await _hareket(kurulu_istemci, h, mid, "giris", 30, lokasyon_id=a)
    await _hareket(kurulu_istemci, h, mid, "giris", 30, lokasyon_id=b)

    async def tasi(kaynak: int, hedef: int) -> int:
        r = await kurulu_istemci.post(
            f"{API}/stok-transferleri",
            json={
                "malzeme_id": mid,
                "kaynak_lokasyon_id": kaynak,
                "hedef_lokasyon_id": hedef,
                "miktar": 1,
            },
            headers=h,
        )
        return r.status_code

    sonuc = await asyncio.wait_for(
        asyncio.gather(*[tasi(a, b) for _ in range(10)], *[tasi(b, a) for _ in range(10)]),
        timeout=60,
    )
    assert sonuc == [201] * 20
    assert await _bakiye(kurulu_istemci, h, mid) == {a: 30, b: 30}


async def test_sayim_delta_aradaki_hareketi_korur_ve_gorev_ayrimi(
    kurulu_istemci: AsyncClient,
) -> None:
    admin = await _giris(kurulu_istemci, ALFA)
    sayan = await _kullanici(kurulu_istemci, admin, ["depo"])
    onaylayan = await _kullanici(kurulu_istemci, admin, ["admin"])
    lok = await _lokasyon(kurulu_istemci, admin)
    mid = await _malzeme(kurulu_istemci, admin)
    await _hareket(kurulu_istemci, admin, mid, "giris", 100, lokasyon_id=lok)

    acik = await kurulu_istemci.post(f"{API}/sayimlar", json={"lokasyon_id": lok}, headers=sayan)
    assert acik.status_code == 201, acik.text
    sid = acik.json()["data"]["id"]
    assert acik.json()["data"]["kod"].startswith("SAY-")
    satir = await kurulu_istemci.put(
        f"{API}/sayimlar/{sid}/satirlar",
        json={"malzeme_id": mid, "sayilan_miktar": 95},
        headers=sayan,
    )
    (s,) = satir.json()["data"]["satirlar"]
    assert (s["sistem_miktari"], s["sayilan_miktar"], s["fark"]) == (100, 95, -5)

    # Sayım sürerken üretimden 50 giriş: sayım bunu EZMEMELİ.
    await _hareket(kurulu_istemci, admin, mid, "giris", 50, lokasyon_id=lok)
    assert (
        await kurulu_istemci.post(f"{API}/sayimlar/{sid}/gonder", headers=sayan)
    ).status_code == 200

    # Depo rolünde stok:duzeltme yok → 403.
    yetkisiz = await kurulu_istemci.post(f"{API}/sayimlar/{sid}/onayla", headers=sayan)
    assert yetkisiz.status_code == 403

    onay = await kurulu_istemci.post(f"{API}/sayimlar/{sid}/onayla", headers=onaylayan)
    assert onay.status_code == 200, onay.text
    assert onay.json()["data"]["durum"] == "onaylandi"
    assert await _bakiye(kurulu_istemci, admin, mid) == {lok: 145}  # 150 + (−5), mutlak 95 değil
    assert await _toplam(kurulu_istemci, admin, mid) == 145

    hareketler = await kurulu_istemci.get(
        f"{API}/stok-hareketleri", params={"malzeme_id": mid}, headers=admin
    )
    turler = [(x["tur"], x["miktar"]) for x in hareketler.json()["data"]]
    assert ("sayim_duzeltme", -5) in turler

    tekrar = await kurulu_istemci.post(f"{API}/sayimlar/{sid}/onayla", headers=onaylayan)
    assert tekrar.status_code == 409  # onaylanmış sayım ikinci kez uygulanmaz


async def test_sayimi_acan_kendi_sayimini_onaylayamaz(kurulu_istemci: AsyncClient) -> None:
    admin = await _giris(kurulu_istemci, ALFA)
    lok = await _lokasyon(kurulu_istemci, admin)
    mid = await _malzeme(kurulu_istemci, admin)
    await _hareket(kurulu_istemci, admin, mid, "giris", 10, lokasyon_id=lok)
    sid = (
        await kurulu_istemci.post(f"{API}/sayimlar", json={"lokasyon_id": lok}, headers=admin)
    ).json()["data"]["id"]
    await kurulu_istemci.put(
        f"{API}/sayimlar/{sid}/satirlar",
        json={"malzeme_id": mid, "sayilan_miktar": 9},
        headers=admin,
    )
    await kurulu_istemci.post(f"{API}/sayimlar/{sid}/gonder", headers=admin)
    r = await kurulu_istemci.post(f"{API}/sayimlar/{sid}/onayla", headers=admin)
    assert r.status_code == 403
    assert await _bakiye(kurulu_istemci, admin, mid) == {lok: 10}


async def test_gocun_geri_doldurmasi_ve_up_down(kurulu_istemci: AsyncClient) -> None:
    """Beta şemasında S25 göçünü geri al, eski düzende bakiye yaz, yeniden uygula."""
    await asyncio.to_thread(fanout.tenant_indir_tek, "beta", "f4c8a2e6b791", db_url=TEST_URL)
    c = await asyncpg.connect(ASYNCPG_URL)
    try:
        mid = await c.fetchval(
            'INSERT INTO "tenant_beta".malzemeler (kod, ad, birim, kategori, mevcut_miktar, '
            "min_stok, kritik_stok, aktif) VALUES ('GECMIS-1', 'Eski', 'adet', '', 7, 0, 0, true) "
            "RETURNING id"
        )
        await c.execute(
            'INSERT INTO "tenant_beta".stok_hareketleri (malzeme_id, tur, miktar, bakiye_sonrasi, '
            "aciklama) VALUES ($1, 'giris', 7, 7, 'eski')",
            mid,
        )
    finally:
        await c.close()
    await asyncio.to_thread(fanout.tenant_yukselt_tek, "beta", "head", db_url=TEST_URL)

    h = await _giris(kurulu_istemci, BETA)
    genel = await _genel(kurulu_istemci, h)
    assert await _bakiye(kurulu_istemci, h, mid) == {genel: 7}
    c = await asyncpg.connect(ASYNCPG_URL)
    try:
        lok = await c.fetchval(
            'SELECT lokasyon_id FROM "tenant_beta".stok_hareketleri WHERE malzeme_id = $1', mid
        )
    finally:
        await c.close()
    assert lok == genel
