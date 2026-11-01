"""S26-B İSG + İK (ADR-0044): izin bakiyesi kapısı, org şeması, kontrol listesi, eğitim matrisi,
KKD eksikleri, tatbikat, kaza → CAPA köprüsü."""

from __future__ import annotations

import asyncio
import uuid
from datetime import timedelta

from httpx import AsyncClient

from app.core.zaman import is_gunu
from tests.conftest import ALFA, BETA
from tests.test_s16_entitlement import _giris
from tests.test_s25_depo_sayim import _kullanici

API = "/api/v1"
BUGUN = is_gunu()


def _ek() -> str:
    return uuid.uuid4().hex[:6].upper()


async def _personel(
    istemci: AsyncClient, h: dict[str, str], *, gun_once: int | None = None, departman: str = ""
) -> int:
    govde: dict[str, object] = {
        "sicil_no": f"S26B-{_ek()}",
        "ad": "Ayşe",
        "soyad": f"Test{_ek()}",
        "departman": departman,
        "dogum_tarihi": "1990-01-01",
    }
    if gun_once is not None:
        govde["ise_giris_tarihi"] = (BUGUN - timedelta(days=gun_once)).isoformat()
    r = await istemci.post(f"{API}/personeller", json=govde, headers=h)
    assert r.status_code == 201, r.text
    return int(r.json()["data"]["id"])


async def _yillik(istemci: AsyncClient, h: dict[str, str], pid: int, gun: int) -> int:
    bas = BUGUN + timedelta(days=30)
    r = await istemci.post(
        f"{API}/izin-talepleri",
        json={
            "personel_id": pid,
            "izin_turu": "yillik",
            "baslangic_tarihi": bas.isoformat(),
            "bitis_tarihi": (bas + timedelta(days=gun - 1)).isoformat(),
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    iid = int(r.json()["data"]["id"])
    assert (await istemci.post(f"{API}/izin-talepleri/{iid}/gonder", headers=h)).status_code == 200
    return iid


async def test_izin_bakiyesi_onayda_dusulur_asim_409(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    pid = await _personel(kurulu_istemci, h, gun_once=400)  # 1 tam yıl → 14 gün
    b = (await kurulu_istemci.get(f"{API}/personeller/{pid}/izin-bakiyesi", headers=h)).json()
    assert (b["data"]["hakedilen"], b["data"]["bakiye"], b["data"]["kidem_yili"]) == (14, 14, 1)

    ilk = await _yillik(kurulu_istemci, h, pid, 10)
    assert (
        await kurulu_istemci.post(f"{API}/izin-talepleri/{ilk}/onayla", headers=h)
    ).status_code == 200
    ikinci = await _yillik(kurulu_istemci, h, pid, 5)  # kalan 4 < 5
    r = await kurulu_istemci.post(f"{API}/izin-talepleri/{ikinci}/onayla", headers=h)
    assert r.status_code == 409, r.text
    assert r.json()["hata_kodu"] == "IZIN_BAKIYE_YETERSIZ"
    b = (await kurulu_istemci.get(f"{API}/personeller/{pid}/izin-bakiyesi", headers=h)).json()
    assert (b["data"]["kullanilan"], b["data"]["bakiye"]) == (10, 4)

    # Mazeret izni bakiyeden düşmez; işe giriş tarihi olmayan personelde kapı yok.
    tarihsiz = await _personel(kurulu_istemci, h)
    iid = await _yillik(kurulu_istemci, h, tarihsiz, 3)
    assert (
        await kurulu_istemci.post(f"{API}/izin-talepleri/{iid}/onayla", headers=h)
    ).status_code == 200


async def test_esanli_onaylar_bakiyeyi_asamaz(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    pid = await _personel(kurulu_istemci, h, gun_once=400)
    a, b = await _yillik(kurulu_istemci, h, pid, 8), await _yillik(kurulu_istemci, h, pid, 8)
    sonuc = await asyncio.gather(
        kurulu_istemci.post(f"{API}/izin-talepleri/{a}/onayla", headers=h),
        kurulu_istemci.post(f"{API}/izin-talepleri/{b}/onayla", headers=h),
    )
    assert sorted(r.status_code for r in sonuc) == [200, 409]


async def test_org_semasi_dongu_409(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    dep = f"ORG-{_ek()}"
    mudur, sef, usta = [await _personel(kurulu_istemci, h, departman=dep) for _ in range(3)]

    async def ata(p: int, y: int | None) -> int:
        r = await kurulu_istemci.put(
            f"{API}/personeller/{p}/yonetici", json={"yonetici_id": y}, headers=h
        )
        return r.status_code

    assert await ata(sef, mudur) == 200
    assert await ata(usta, sef) == 200
    assert await ata(mudur, usta) == 409  # müdür → usta → şef → müdür döngüsü
    assert await ata(mudur, mudur) == 422
    org = (await kurulu_istemci.get(f"{API}/ik/org-semasi?departman={dep}", headers=h)).json()
    dugum = {d["id"]: d for d in org["data"]}
    assert dugum[mudur]["yonetici_id"] is None and dugum[mudur]["ast_sayisi"] == 1
    assert dugum[usta]["yonetici_id"] == sef
    assert await ata(usta, None) == 200


async def test_cikis_listesi_acik_zimmetle_kapanmaz(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    pid = await _personel(kurulu_istemci, h, gun_once=800)
    r = await kurulu_istemci.post(
        f"{API}/zimmetler",
        json={
            "personel_id": pid,
            "demirbas": "Dizüstü bilgisayar",
            "zimmet_tarihi": BUGUN.isoformat(),
        },
        headers=h,
    )
    zid = r.json()["data"]["id"]
    r = await kurulu_istemci.post(
        f"{API}/personeller/{pid}/kontrol-listeleri", json={"tur": "cikis"}, headers=h
    )
    liste = r.json()["data"]
    tekrar = await kurulu_istemci.post(
        f"{API}/personeller/{pid}/kontrol-listeleri", json={"tur": "cikis"}, headers=h
    )
    assert tekrar.json()["data"]["id"] == liste["id"]  # idempotent
    assert liste["acik_zimmet"] == 1

    async def isaretle(anahtar: str) -> object:
        return await kurulu_istemci.put(
            f"{API}/kontrol-listeleri/{liste['id']}/maddeler/{anahtar}",
            json={"tamam": True},
            headers=h,
        )

    r = await isaretle("zimmet_iade")
    assert r.status_code == 409 and r.json()["hata_kodu"] == "ACIK_ZIMMET"  # type: ignore[attr-defined]
    await kurulu_istemci.post(f"{API}/zimmetler/{zid}/iade", headers=h)
    for m in liste["maddeler"]:
        r = await isaretle(m["anahtar"])
        assert r.status_code == 200, r.text  # type: ignore[attr-defined]
    son = r.json()["data"]  # type: ignore[attr-defined]
    assert son["durum"] == "tamamlandi" and son["tamamlanan"] == son["toplam"]
    p = (await kurulu_istemci.get(f"{API}/personeller/{pid}", headers=h)).json()["data"]
    assert p["aktif"] is False


async def test_egitim_matrisi_ve_kkd_eksikleri(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    dep = f"URT-{_ek()}"
    a, b = (
        await _personel(kurulu_istemci, h, departman=dep),
        await _personel(kurulu_istemci, h, departman=dep),
    )
    konu = f"yuksekte_calisma_{_ek()}"
    r = await kurulu_istemci.post(
        f"{API}/isg/gereksinimler/egitim", json={"departman": dep, "ad": konu}, headers=h
    )
    assert r.status_code == 201, r.text
    assert (
        await kurulu_istemci.post(
            f"{API}/isg/gereksinimler/egitim", json={"departman": dep, "ad": konu}, headers=h
        )
    ).status_code == 409
    r = await kurulu_istemci.post(
        f"{API}/isg/egitimler",
        json={
            "konu": konu,
            "baslik": "Yüksekte çalışma",
            "tarih": (BUGUN - timedelta(days=350)).isoformat(),
            "gecerlilik_ay": 12,
            "personel_idler": [a],
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["data"]["kod"].startswith("EGT-")
    m = (await kurulu_istemci.get(f"{API}/isg/egitim-matrisi?departman={dep}", headers=h)).json()
    satir = {s["personel_id"]: s["hucreler"][konu]["durum"] for s in m["data"]["personeller"]}
    assert satir == {a: "yaklasiyor", b: "eksik"}

    kkd = f"Baret {_ek()}"
    await kurulu_istemci.post(
        f"{API}/isg/gereksinimler/kkd", json={"departman": dep, "ad": kkd}, headers=h
    )
    await kurulu_istemci.post(
        f"{API}/zimmetler",
        json={
            "personel_id": a,
            "demirbas": f"  {kkd.lower()} ",
            "kategori": "kkd",
            "zimmet_tarihi": BUGUN.isoformat(),
        },
        headers=h,
    )
    e = (await kurulu_istemci.get(f"{API}/isg/kkd-eksikleri?departman={dep}", headers=h)).json()
    eksik = {s["personel_id"]: s["eksik"] for s in e["data"]}
    assert eksik == {a: [], b: [kkd]}


async def test_tatbikat_ve_kazadan_capa(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.post(
        f"{API}/isg/tatbikatlar",
        json={"tur": "yangin", "tarih": BUGUN.isoformat(), "sonraki_tarih": BUGUN.isoformat()},
        headers=h,
    )
    assert r.status_code == 422  # sonraki tarih bu tatbikattan sonra olmalı
    r = await kurulu_istemci.post(
        f"{API}/isg/tatbikatlar",
        json={
            "tur": "yangin",
            "tarih": BUGUN.isoformat(),
            "katilimci_sayisi": 42,
            "tahliye_suresi_sn": 185,
        },
        headers=h,
    )
    assert r.status_code == 201 and r.json()["data"]["kod"].startswith("TAT-")

    r = await kurulu_istemci.post(
        f"{API}/is-kazalari",
        json={"tur": "kaza", "agirlik": "agir", "yer": "Pres hattı", "aciklama": "El sıkışması"},
        headers=h,
    )
    kid = r.json()["data"]["id"]
    assert (await kurulu_istemci.get(f"{API}/is-kazalari/{kid}/capa", headers=h)).json()[
        "data"
    ] is None
    sonuc = await asyncio.gather(
        *[
            kurulu_istemci.post(f"{API}/is-kazalari/{kid}/capa", json={}, headers=h)
            for _ in range(2)
        ]
    )
    assert sorted(r.status_code for r in sonuc) == [201, 409]
    capa = next(r for r in sonuc if r.status_code == 201).json()["data"]
    assert capa["onem"] == "kritik" and capa["kod"].startswith("UY-")
    u = (
        await kurulu_istemci.get(f"{API}/uygunsuzluklar/{capa['uygunsuzluk_id']}", headers=h)
    ).json()
    assert u["data"]["baslik"].startswith("İş kazası:")


async def test_yetki_ve_izolasyon(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.post(
        f"{API}/is-kazalari", json={"tur": "ramak_kala", "agirlik": "hafif"}, headers=h
    )
    kid = r.json()["data"]["id"]
    isgci = await _kullanici(kurulu_istemci, h, ["isg"])  # kalite:yaz yok
    assert (
        await kurulu_istemci.post(f"{API}/is-kazalari/{kid}/capa", json={}, headers=isgci)
    ).status_code == 403
    pid = await _personel(kurulu_istemci, h, gun_once=400)
    izleyici = await _kullanici(kurulu_istemci, h, ["izleyici"])
    assert (
        await kurulu_istemci.put(
            f"{API}/personeller/{pid}/yonetici", json={"yonetici_id": None}, headers=izleyici
        )
    ).status_code == 403
    beta = await _giris(kurulu_istemci, BETA)
    assert (
        await kurulu_istemci.get(f"{API}/personeller/{pid}/izin-bakiyesi", headers=beta)
    ).status_code == 404
    assert (
        await kurulu_istemci.get(f"{API}/is-kazalari/{kid}/capa", headers=beta)
    ).status_code == 404
