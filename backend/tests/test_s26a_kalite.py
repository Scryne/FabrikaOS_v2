"""S26-A kalite olgunluğu (ADR-0025): kalibrasyon, kontrol planı, SPC kartı ve ihlal olayı."""

from __future__ import annotations

import asyncio
import uuid
from datetime import timedelta

import asyncpg
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.zaman import is_gunu
from app.modules.bildirim.zamanli import tenant_zamanli_taramalar
from tests.conftest import ALFA, ASYNCPG_URL
from tests.test_s16_entitlement import _giris
from tests.test_s25_depo_sayim import _kullanici

API = "/api/v1"
BUGUN = is_gunu()
# Kararlı süreç: ortalama 10, küçük ama sıfır olmayan aralık; deterministik.
KARARLI = [
    [10.02, 9.98, 10.01, 9.99, 10.00],
    [9.97, 10.03, 10.00, 10.01, 9.99],
    [10.01, 10.00, 9.98, 10.02, 9.99],
    [9.99, 10.01, 10.02, 9.98, 10.00],
]


def _ek() -> str:
    return uuid.uuid4().hex[:6].upper()


async def _olay_sayisi(tur: str) -> int:
    conn = await asyncpg.connect(ASYNCPG_URL)
    try:
        return int(
            await conn.fetchval(
                "SELECT count(*) FROM tenant_alfa.giden_olaylar WHERE olay_turu = $1", tur
            )
        )
    finally:
        await conn.close()


async def _cihaz(
    istemci: AsyncClient, h: dict[str, str], *, kalibrasyon_gun_once: int | None, periyot: int = 365
) -> dict:
    r = await istemci.post(
        f"{API}/olcum-cihazlari",
        json={"kod": f"OC-{_ek()}", "ad": "Dijital kumpas", "kalibrasyon_periyodu_gun": periyot},
        headers=h,
    )
    assert r.status_code == 201, r.text
    cihaz = r.json()["data"]
    if kalibrasyon_gun_once is not None:
        r = await istemci.post(
            f"{API}/olcum-cihazlari/{cihaz['id']}/kalibrasyonlar",
            json={
                "tarih": (BUGUN - timedelta(days=kalibrasyon_gun_once)).isoformat(),
                "sonuc": "uygun",
                "sertifika_no": "KAL-1",
                "kurum": "Akredite Lab",
            },
            headers=h,
        )
        assert r.status_code == 201, r.text
        cihaz = r.json()["data"]
    return cihaz


async def _plan(istemci: AsyncClient, h: dict[str, str], cihaz_id: int | None) -> tuple[int, int]:
    r = await istemci.post(
        f"{API}/kontrol-planlari",
        json={
            "ad": "Mil işleme",
            "operasyon": "Tornalama",
            "karakteristikler": [
                {
                    "ad": "Mil çapı",
                    "birim": "mm",
                    "nominal": 10,
                    "alt_tolerans": 9.9,
                    "ust_tolerans": 10.1,
                    "alt_grup_boyutu": 5,
                    "cihaz_id": cihaz_id,
                }
            ],
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    plan = r.json()["data"]
    assert plan["kod"].startswith("KP-")
    return plan["id"], plan["karakteristikler"][0]["id"]


async def _olc(
    istemci: AsyncClient, h: dict[str, str], kid: int, degerler: list[float], **ek: object
):  # type: ignore[no-untyped-def]
    return await istemci.post(
        f"{API}/karakteristikler/{kid}/olcumler", json={"degerler": degerler, **ek}, headers=h
    )


async def test_kalibrasyon_gecerliligi_ve_kullanim_disi(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    c = await _cihaz(kurulu_istemci, h, kalibrasyon_gun_once=10)
    assert c["gecerlilik"] == "gecerli"
    assert c["sonraki_kalibrasyon_tarihi"] == (BUGUN + timedelta(days=355)).isoformat()

    eski = await _cihaz(kurulu_istemci, h, kalibrasyon_gun_once=400)
    assert eski["gecerlilik"] == "gecmis"

    r = await kurulu_istemci.post(
        f"{API}/olcum-cihazlari/{c['id']}/kalibrasyonlar",
        json={"tarih": BUGUN.isoformat(), "sonuc": "uygunsuz"},
        headers=h,
    )
    assert r.json()["data"]["durum"] == "kullanim_disi"
    # Kullanım dışı cihaz elle aktif edilemez; yeni kalibrasyon gerekir.
    r = await kurulu_istemci.patch(
        f"{API}/olcum-cihazlari/{c['id']}", json={"durum": "aktif"}, headers=h
    )
    assert r.status_code == 409
    assert r.json()["hata_kodu"] == "KALIBRASYON_GEREKLI"
    # Gelecek tarihli ve eskiye dönük kayıt reddedilir.
    for gun in (1, -30):
        r = await kurulu_istemci.post(
            f"{API}/olcum-cihazlari/{c['id']}/kalibrasyonlar",
            json={"tarih": (BUGUN + timedelta(days=gun)).isoformat(), "sonuc": "uygun"},
            headers=h,
        )
        assert r.status_code == 422, gun


async def test_spc_faz1_kayma_tek_olay_ve_yetenek(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    c = await _cihaz(kurulu_istemci, h, kalibrasyon_gun_once=5)
    _pid, kid = await _plan(kurulu_istemci, h, c["id"])

    for i in range(20):
        r = await _olc(kurulu_istemci, h, kid, KARARLI[i % 4])
        assert r.status_code == 201, r.text
    r = await kurulu_istemci.post(
        f"{API}/karakteristikler/{kid}/limitleri-sabitle", json={"ilk": 20}, headers=h
    )
    assert r.status_code == 200, r.text
    kart = r.json()["data"]
    assert kart["limitler_sabit"] is True
    assert kart["limitler"]["alt_grup_sayisi"] == 20
    assert kart["ihlaller"] == []
    assert kart["yetenek"]["cp"] > 1  # tolerans ±0,1, süreç çok daha dar

    once = await _olay_sayisi("kalite.spc_ihlal")
    r = await _olc(kurulu_istemci, h, kid, [10.4, 10.5, 10.45, 10.42, 10.48])  # 3σ'nın çok dışında
    assert r.status_code == 201
    assert {i["kural"] for i in r.json()["data"]["ihlaller"]} == {1}
    assert await _olay_sayisi("kalite.spc_ihlal") == once + 1

    r = await _olc(kurulu_istemci, h, kid, KARARLI[0])  # kararlıya dönüş: yeni olay yok
    assert r.json()["data"]["ihlaller"] == []
    assert await _olay_sayisi("kalite.spc_ihlal") == once + 1

    kart = (await kurulu_istemci.get(f"{API}/karakteristikler/{kid}/kart", headers=h)).json()[
        "data"
    ]
    assert len(kart["noktalar"]) == 22
    assert [i["indeks"] for i in kart["ihlaller"] if i["kart"] == "xbar"] == [20]
    assert kart["noktalar"][20]["kayitli_ihlaller"][0]["kural"] == 1
    # Sabit limitler yeni noktalarla değişmez.
    assert kart["limitler"]["alt_grup_sayisi"] == 20


async def test_olcum_dogrulamalari(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    eski = await _cihaz(kurulu_istemci, h, kalibrasyon_gun_once=400)
    _pid, kid = await _plan(kurulu_istemci, h, eski["id"])
    r = await _olc(kurulu_istemci, h, kid, KARARLI[0])
    assert r.status_code == 422
    assert r.json()["hata_kodu"] == "KALIBRASYON_GECERSIZ"

    gecerli = await _cihaz(kurulu_istemci, h, kalibrasyon_gun_once=1)
    r = await _olc(
        kurulu_istemci, h, kid, KARARLI[0], cihaz_id=gecerli["id"]
    )  # cihaz geçersiz kılınabilir
    assert r.status_code == 201, r.text
    r = await _olc(kurulu_istemci, h, kid, [10.0, 10.1, 9.9], cihaz_id=gecerli["id"])
    assert r.status_code == 422  # n = 5
    r = await kurulu_istemci.post(
        f"{API}/karakteristikler/{kid}/limitleri-sabitle", json={}, headers=h
    )
    assert r.status_code == 409  # tek alt grupla limit yok
    r = await kurulu_istemci.post(
        f"{API}/kontrol-planlari",
        json={
            "ad": "Hatalı",
            "karakteristikler": [{"ad": "X", "alt_tolerans": 5, "ust_tolerans": 4}],
        },
        headers=h,
    )
    assert r.status_code == 422


async def test_esanli_olcumler_sira_benzersiz(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    _pid, kid = await _plan(kurulu_istemci, h, None)
    sonuc = await asyncio.gather(*[_olc(kurulu_istemci, h, kid, KARARLI[i % 4]) for i in range(6)])
    assert all(r.status_code == 201 for r in sonuc), [r.text for r in sonuc]
    assert sorted(r.json()["data"]["sira"] for r in sonuc) == [1, 2, 3, 4, 5, 6]


async def test_kalibrasyon_taramasi_kenar_tetikli(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    yakin = await _cihaz(kurulu_istemci, h, kalibrasyon_gun_once=350)  # 15 gün kaldı
    once = await _olay_sayisi("kalibrasyon.yaklasiyor")
    r = await kurulu_istemci.post(
        f"{API}/olcum-cihazlari/kalibrasyon-tara", json={"esik_gun": 30}, headers=h
    )
    assert r.json()["data"]["bildirilen"] >= 1
    sonra = await _olay_sayisi("kalibrasyon.yaklasiyor")
    assert sonra > once
    r = await kurulu_istemci.post(
        f"{API}/olcum-cihazlari/kalibrasyon-tara", json={"esik_gun": 30}, headers=h
    )
    assert r.json()["data"]["bildirilen"] == 0  # ikinci tarama aynı cihaz için yeni olay üretmez
    detay = (await kurulu_istemci.get(f"{API}/olcum-cihazlari/{yakin['id']}", headers=h)).json()[
        "data"
    ]
    assert detay["gecerlilik"] == "yaklasiyor"
    assert detay["kalibrasyonlar"][0]["sertifika_no"] == "KAL-1"


async def test_yetki(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    _pid, kid = await _plan(kurulu_istemci, h, None)
    izleyici = await _kullanici(kurulu_istemci, h, ["izleyici"])
    assert (
        await kurulu_istemci.get(f"{API}/karakteristikler/{kid}/kart", headers=izleyici)
    ).status_code in (200, 403)
    assert (await _olc(kurulu_istemci, izleyici, kid, KARARLI[0])).status_code == 403
    kaliteci = await _kullanici(kurulu_istemci, h, ["kalite"])
    assert (await _olc(kurulu_istemci, kaliteci, kid, KARARLI[0])).status_code == 201


async def test_zamanli_taramalar_isciden_bir_kez(
    kurulu_istemci: AsyncClient, test_engine: AsyncEngine
) -> None:
    """Bildirim işçisinin zamanlı turu: yaklaşan kalibrasyon bir kez olay olur, hata izoledir."""
    h = await _giris(kurulu_istemci, ALFA)
    await _cihaz(kurulu_istemci, h, kalibrasyon_gun_once=355)  # 10 gün kaldı
    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    once = await _olay_sayisi("kalibrasyon.yaklasiyor")
    ilk = await tenant_zamanli_taramalar(sm, "alfa")
    assert set(ilk) == {"sozlesme.yaklasiyor", "sla.asildi", "kalibrasyon.yaklasiyor"}
    assert all(v is not None for v in ilk.values()), ilk
    assert (ilk["kalibrasyon.yaklasiyor"] or 0) >= 1
    assert await _olay_sayisi("kalibrasyon.yaklasiyor") > once
    ikinci = await tenant_zamanli_taramalar(sm, "alfa")
    assert ikinci["kalibrasyon.yaklasiyor"] == 0  # kenar tetikli: ikinci turda yeni olay yok


async def test_uygunsuzluk_tedarikci_baglantisi(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)

    async def firma(tip: str) -> int:
        r = await kurulu_istemci.post(
            f"{API}/firmalar", json={"ad": f"Firma {_ek()}", "tip": tip}, headers=h
        )
        assert r.status_code == 201, r.text
        return int(r.json()["data"]["id"])

    tedarikci, musteri = await firma("tedarikci"), await firma("musteri")
    govde = {"baslik": "Giriş muayenesinde ölçü dışı sac", "onem": "yuksek"}
    r = await kurulu_istemci.post(
        f"{API}/uygunsuzluklar", json={**govde, "tedarikci_firma_id": musteri}, headers=h
    )
    assert r.status_code == 422, r.text  # müşteri firması tedarikçi kaynağı olamaz
    r = await kurulu_istemci.post(
        f"{API}/uygunsuzluklar", json={**govde, "tedarikci_firma_id": 987654}, headers=h
    )
    assert r.status_code == 404, r.text
    r = await kurulu_istemci.post(
        f"{API}/uygunsuzluklar", json={**govde, "tedarikci_firma_id": tedarikci}, headers=h
    )
    assert r.status_code == 201, r.text
    assert r.json()["data"]["tedarikci_firma_id"] == tedarikci
    liste = (
        await kurulu_istemci.get(f"{API}/uygunsuzluklar?tedarikci_firma_id={tedarikci}", headers=h)
    ).json()["data"]
    assert [u["tedarikci_firma_id"] for u in liste] == [tedarikci]
