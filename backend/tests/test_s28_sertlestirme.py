"""S28 (ADR-0047): schemathesis sertleştirme taramasının bulduğu 500'lerin geri dönmemesi.

Tarama (``docs/operasyon/sertlestirme.md``) GET'te 76, yazmada 12 uçta 500 buldu. Hepsi istemci
girdisinden doğuyordu ve tek tek uçlarda değil merkezi hata işleyicide kapandı; bu testler her
sınıftan bir temsilciyi sabitler.
"""

from __future__ import annotations

import uuid
from typing import Any

from httpx import AsyncClient

from tests.conftest import ALFA

API = "/api/v1"
INT64_ASIRI = 2**63


async def _h(istemci: AsyncClient) -> dict[str, str]:
    r = await istemci.post(
        f"{API}/kimlik/token",
        data={"username": ALFA["eposta"], "password": ALFA["parola"]},
        headers={"X-Tenant": ALFA["slug"]},
    )
    assert r.status_code == 200, r.text
    return {"X-Tenant": ALFA["slug"], "Authorization": f"Bearer {r.json()['data']['access_token']}"}


def _hata(r: Any, durum: int, kod: str) -> None:
    assert r.status_code == durum, r.text
    assert r.json()["hata_kodu"] == kod


async def test_int64_disi_yol_ve_sorgu_parametresi_422(kurulu_istemci: AsyncClient) -> None:
    h = await _h(kurulu_istemci)
    _hata(
        await kurulu_istemci.get(f"{API}/makineler/{INT64_ASIRI}", headers=h), 422, "GECERSIZ_DEGER"
    )
    _hata(
        await kurulu_istemci.get(f"{API}/zimmetler?personel_id={INT64_ASIRI}", headers=h),
        422,
        "GECERSIZ_DEGER",
    )


async def test_metinde_nul_bayti_422(kurulu_istemci: AsyncClient) -> None:
    h = await _h(kurulu_istemci)
    r = await kurulu_istemci.post(f"{API}/uygunsuzluklar", json={"baslik": "a\x00b"}, headers=h)
    _hata(r, 422, "GECERSIZ_DEGER")


async def test_olmayan_kayda_referans_422(kurulu_istemci: AsyncClient) -> None:
    h = await _h(kurulu_istemci)
    r = await kurulu_istemci.post(
        f"{API}/uygunsuzluklar", json={"baslik": "Referans", "makine_id": 987_654_321}, headers=h
    )
    _hata(r, 422, "GECERSIZ_REFERANS")


async def test_patch_ile_var_olan_ada_yeniden_adlandirma_409(kurulu_istemci: AsyncClient) -> None:
    h = await _h(kurulu_istemci)
    ek = uuid.uuid4().hex[:6]
    ids = []
    for ad in (f"V1-{ek}", f"V2-{ek}"):
        r = await kurulu_istemci.post(
            f"{API}/vardiyalar",
            json={"ad": ad, "baslangic_saat": "08:00", "bitis_saat": "16:00"},
            headers=h,
        )
        assert r.status_code == 201, r.text
        ids.append(r.json()["data"]["id"])
    r = await kurulu_istemci.patch(f"{API}/vardiyalar/{ids[1]}", json={"ad": f"V1-{ek}"}, headers=h)
    _hata(r, 409, "CAKISMA")


async def test_patch_zorunlu_alana_null_422(kurulu_istemci: AsyncClient) -> None:
    h = await _h(kurulu_istemci)
    r = await kurulu_istemci.post(
        f"{API}/makineler", json={"kod": f"SRT-{uuid.uuid4().hex[:5]}", "ad": "Pres"}, headers=h
    )
    assert r.status_code == 201, r.text
    mid = r.json()["data"]["id"]
    r = await kurulu_istemci.patch(f"{API}/makineler/{mid}", json={"ad": None}, headers=h)
    _hata(r, 422, "DOGRULAMA")
    assert r.json()["detaylar"][0]["alan"] == "ad"
    detay = (await kurulu_istemci.get(f"{API}/makineler/{mid}", headers=h)).json()["data"]
    assert detay["ad"] == "Pres"  # işlem geri alındı, kayıt bozulmadı


async def test_bozuk_ve_utf8_olmayan_csv_422(kurulu_istemci: AsyncClient) -> None:
    h = await _h(kurulu_istemci)
    for icerik in (
        b'makine_kod,zaman\n"MAK\rX,2026-01-01\n',  # tırnaksız alanda satır sonu (csv.Error)
        "makine_kod,zaman\nÇAPAK-ŞİŞ,2026-01-01\n".encode("cp1254"),  # Excel'in yerel kodlaması
    ):
        r = await kurulu_istemci.post(
            f"{API}/saha/olcumler/csv?cihaz_kod=GW-1",
            files={"dosya": ("o.csv", icerik, "text/csv")},
            headers=h,
        )
        _hata(r, 422, "DOGRULAMA")
