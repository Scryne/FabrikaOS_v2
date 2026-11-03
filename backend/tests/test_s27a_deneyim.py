"""S27-A (ADR-0045): birleşik onay kutusu ve içerik araması — izin, modül, görev ayrımı."""

from __future__ import annotations

import uuid
from datetime import timedelta

from httpx import AsyncClient

from app.core.zaman import is_gunu
from tests.conftest import ALFA, BETA
from tests.test_s16_entitlement import _giris
from tests.test_s25_depo_sayim import _hareket, _kullanici, _lokasyon, _malzeme

API = "/api/v1"


def _ek() -> str:
    return uuid.uuid4().hex[:6].upper()


async def _bekleyen_talep(istemci: AsyncClient, h: dict[str, str], mid: int) -> int:
    r = await istemci.post(
        f"{API}/satinalma-talepleri",
        json={
            "baslik": f"Rulman alımı {_ek()}",
            "kalemler": [{"malzeme_id": mid, "miktar": 3, "birim": "adet"}],
        },
        headers=h,
    )
    tid = r.json()["data"]["id"]
    assert (
        await istemci.post(f"{API}/satinalma-talepleri/{tid}/gonder", headers=h)
    ).status_code == 200
    return int(tid)


async def _bekleyen_izin(istemci: AsyncClient, h: dict[str, str]) -> int:
    p = await istemci.post(
        f"{API}/personeller",
        json={"sicil_no": f"S27-{_ek()}", "ad": "Kaan", "soyad": "Ateş"},
        headers=h,
    )
    bas = is_gunu() + timedelta(days=20)
    r = await istemci.post(
        f"{API}/izin-talepleri",
        json={
            "personel_id": p.json()["data"]["id"],
            "izin_turu": "mazeret",
            "baslangic_tarihi": bas.isoformat(),
            "bitis_tarihi": bas.isoformat(),
        },
        headers=h,
    )
    iid = r.json()["data"]["id"]
    await istemci.post(f"{API}/izin-talepleri/{iid}/gonder", headers=h)
    return int(iid)


async def _bekleyen_sayim(
    istemci: AsyncClient, admin: dict[str, str], sayan: dict[str, str]
) -> int:
    lok = await _lokasyon(istemci, admin)
    mid = await _malzeme(istemci, admin)
    await _hareket(istemci, admin, mid, "giris", 10, lokasyon_id=lok)
    sid = (await istemci.post(f"{API}/sayimlar", json={"lokasyon_id": lok}, headers=sayan)).json()[
        "data"
    ]["id"]
    await istemci.put(
        f"{API}/sayimlar/{sid}/satirlar",
        json={"malzeme_id": mid, "sayilan_miktar": 9},
        headers=sayan,
    )
    await istemci.post(f"{API}/sayimlar/{sid}/gonder", headers=sayan)
    return int(sid)


async def test_onay_kutusu_izin_ve_gorev_ayrimi(kurulu_istemci: AsyncClient) -> None:
    admin = await _giris(kurulu_istemci, ALFA)
    mid = await _malzeme(kurulu_istemci, admin)
    depocu = await _kullanici(kurulu_istemci, admin, ["depo"])
    ik_girisci = await _kullanici(kurulu_istemci, admin, ["ik"])
    tid = await _bekleyen_talep(kurulu_istemci, depocu, mid)
    iid = await _bekleyen_izin(kurulu_istemci, ik_girisci)
    kendi_talep = await _bekleyen_talep(kurulu_istemci, admin, mid)
    baskasinin = await _bekleyen_sayim(kurulu_istemci, admin, depocu)
    kendi = await _bekleyen_sayim(kurulu_istemci, admin, admin)

    kutu = (await kurulu_istemci.get(f"{API}/onaylarim", headers=admin)).json()["data"]
    anahtarlar = {(k["tur"], k["id"]) for k in kutu["kalemler"]}
    assert ("satinalma_talebi", tid) in anahtarlar
    assert ("izin_talebi", iid) in anahtarlar
    assert ("sayim", baskasinin) in anahtarlar
    assert ("sayim", kendi) not in anahtarlar  # kendi sayımını onaylayamaz
    assert ("satinalma_talebi", kendi_talep) not in anahtarlar  # kendi talebi de (S28)
    assert kutu["kendi_kayitlarim"] >= 2
    izin = next(k for k in kutu["kalemler"] if k["tur"] == "izin_talebi" and k["id"] == iid)
    assert izin["red_gerekce_zorunlu"] is True
    # Başlık okunur: personel adı + izin türü etiketi (ham enum ``mazeret`` değil).
    assert izin["baslik"] == "Kaan Ateş · mazeret izni"
    assert izin["onay_yolu"] == f"/izin-talepleri/{iid}/onayla"

    # Kalemin gösterdiği uç gerçekten çalışır ve onaylanan kalem kutudan düşer.
    assert (await kurulu_istemci.post(API + izin["onay_yolu"], headers=admin)).status_code == 200
    kutu = (await kurulu_istemci.get(f"{API}/onaylarim", headers=admin)).json()["data"]
    assert ("izin_talebi", iid) not in {(k["tur"], k["id"]) for k in kutu["kalemler"]}

    # Yalnız İK onaycısı: satınalma ve sayım görmez.
    ikci = await _kullanici(kurulu_istemci, admin, ["ik-onaylayan"])
    turler = {
        k["tur"]
        for k in (await kurulu_istemci.get(f"{API}/onaylarim", headers=ikci)).json()["data"][
            "kalemler"
        ]
    }
    assert turler <= {"izin_talebi", "fazla_mesai"}
    # Onay izni olmayan kullanıcıda kutu boş.
    izleyici = await _kullanici(kurulu_istemci, admin, ["izleyici"])
    bos = (await kurulu_istemci.get(f"{API}/onaylarim", headers=izleyici)).json()["data"]
    assert bos == {"kalemler": [], "kendi_kayitlarim": 0}


async def test_arama_rbac_ve_kiraci_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    admin = await _giris(kurulu_istemci, ALFA)
    iz = f"ZQ{_ek()}"
    await kurulu_istemci.post(
        f"{API}/makineler", json={"kod": f"{iz}-M", "ad": "Arama makinesi"}, headers=admin
    )
    await _malzeme(kurulu_istemci, admin, kod=f"{iz}-MLZ", ad=f"{iz} rulman")
    await kurulu_istemci.post(
        f"{API}/personeller",
        json={"sicil_no": f"{iz}-P", "ad": "Arama", "soyad": "Kişi"},
        headers=admin,
    )

    gruplar = (await kurulu_istemci.get(f"{API}/ara", params={"q": iz}, headers=admin)).json()[
        "data"
    ]
    turler = {g["tur"] for g in gruplar}
    assert {"makine", "malzeme", "personel"} <= turler
    malzeme = next(g for g in gruplar if g["tur"] == "malzeme")["kayitlar"][0]
    assert malzeme["yol"].startswith("/malzemeler/")

    # İK rolü yalnız personeli görür: RBAC dışı kayıt sonuçta hiç yok.
    ikci = await _kullanici(kurulu_istemci, admin, ["ik"])
    ik_gruplar = (await kurulu_istemci.get(f"{API}/ara", params={"q": iz}, headers=ikci)).json()[
        "data"
    ]
    assert {g["tur"] for g in ik_gruplar} == {"personel"}

    # Başka kiracı aynı terimle hiçbir şey bulmaz; % joker değil düz karakterdir.
    beta = await _giris(kurulu_istemci, BETA)
    assert (await kurulu_istemci.get(f"{API}/ara", params={"q": iz}, headers=beta)).json()[
        "data"
    ] == []
    joker = (await kurulu_istemci.get(f"{API}/ara", params={"q": "%%"}, headers=admin)).json()[
        "data"
    ]
    assert joker == []
    assert (
        await kurulu_istemci.get(f"{API}/ara", params={"q": "a"}, headers=admin)
    ).status_code == 422
