"""Kullanımdan kaldırılmış MUTLAK `duzeltme` stok hareketinin korumaları (ADR-0024).

Bu tür bakiyeyi mutlak yazar: hareketin hazırlanmasıyla uygulanması arasında yapılan
her şeyi sessizce siler. Yayındaki bir uç olduğu için davranışı DEĞİŞTİRİLMEDİ; bunun
yerine üç koruma eklendi ve burada sınanıyor:

1. Erişim `stok:duzeltme` iznine daraltıldı (`stok:yaz` artık yetmez).
2. Her kullanım ayrı bir denetim eylemi bırakır (`stok_mutlak_duzeltme`) — "hareket"
   gürültüsünde kaybolmaz, filtrelenebilir.
3. OpenAPI açıklamasında "kullanımdan kaldırıldı" işaretlidir.

Ayrıca veri kaybı davranışının **hâlâ mevcut olduğu** açıkça belgelenir (regresyon değil,
bilinen borç): düzeltme aradaki hareketi ezer. Bu test, davranış Sprint 9'da delta'ya
çevrildiğinde kırılacak ve backlog #2'nin kapandığını hatırlatacaktır.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from httpx import AsyncClient

from tests.conftest import ALFA
from tests.test_s16_entitlement import _giris

STOK = "/api/v1"


async def _malzeme_ac(istemci: AsyncClient, h: dict[str, str]) -> int:
    r = await istemci.post(
        f"{STOK}/malzemeler",
        json={
            "kod": f"DZ-{uuid.uuid4().hex[:8]}",
            "ad": "Düzeltme testi",
            "birim": "adet",
            "kritik_stok": 0,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    return int(r.json()["data"]["id"])


async def _kullanici_ac(
    istemci: AsyncClient, h: dict[str, str], roller: list[str]
) -> dict[str, str]:
    eposta = f"dz-{uuid.uuid4().hex[:8]}@alfa.test"
    r = await istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": eposta, "parola": "Duzelt12345!", "ad_soyad": "DZ", "roller": roller},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return await _giris(istemci, {"slug": "alfa", "eposta": eposta, "parola": "Duzelt12345!"})


async def test_depo_rolu_mutlak_duzeltme_YAPAMAZ(test_db: str, kurulu_istemci: AsyncClient) -> None:
    """`stok:yaz` yeter DEĞİL: mutlak düzeltme ayrı izin ister (görev ayrımı)."""
    admin_h = await _giris(kurulu_istemci, ALFA)
    malzeme_id = await _malzeme_ac(kurulu_istemci, admin_h)
    depo_h = await _kullanici_ac(kurulu_istemci, admin_h, ["depo"])

    # Normal giriş yapabiliyor (stok:yaz var).
    giris = await kurulu_istemci.post(
        f"{STOK}/stok-hareketleri",
        json={"malzeme_id": malzeme_id, "tur": "giris", "miktar": 100},
        headers=depo_h,
    )
    assert giris.status_code == 201, giris.text

    # Mutlak düzeltme YAPAMIYOR.
    duzeltme = await kurulu_istemci.post(
        f"{STOK}/stok-hareketleri",
        json={"malzeme_id": malzeme_id, "tur": "duzeltme", "miktar": 5},
        headers=depo_h,
    )
    assert duzeltme.status_code == 403, duzeltme.text
    assert "stok:duzeltme" in duzeltme.json()["message"]


async def test_yetkili_kullanimi_AYRI_denetim_eylemi_birakir(
    test_db: str, kurulu_istemci: AsyncClient
) -> None:
    """İzinli kullanıcı yapabilir ama iz bırakır: `stok_mutlak_duzeltme` denetim olayı."""
    admin_h = await _giris(kurulu_istemci, ALFA)  # admin tüm izinlere sahip
    malzeme_id = await _malzeme_ac(kurulu_istemci, admin_h)

    await kurulu_istemci.post(
        f"{STOK}/stok-hareketleri",
        json={"malzeme_id": malzeme_id, "tur": "giris", "miktar": 100},
        headers=admin_h,
    )
    r = await kurulu_istemci.post(
        f"{STOK}/stok-hareketleri",
        json={"malzeme_id": malzeme_id, "tur": "duzeltme", "miktar": 42},
        headers=admin_h,
    )
    assert r.status_code == 201, r.text

    kayitlar = await kurulu_istemci.get(
        "/api/v1/denetim-kayitlari?eylem=stok_mutlak_duzeltme&adet=5", headers=admin_h
    )
    assert kayitlar.status_code == 200
    veri = kayitlar.json()["data"]
    assert veri, "mutlak düzeltme ayrı denetim eylemi bırakmadı"
    assert veri[0]["detay"]["uyari"] == "kullanimdan_kaldirildi_mutlak_yazim"
    assert veri[0]["detay"]["bakiye_sonrasi"] == "42"


async def test_mutlak_yazim_davranisi_HALA_veri_kaybettiriyor(
    test_db: str, kurulu_istemci: AsyncClient
) -> None:
    """BİLİNEN BORÇ (backlog #2): düzeltme, arada yapılan hareketi ezer.

    Bu test mevcut (yanlış) davranışı **kasıtlı olarak** sabitler. Sprint 9'da delta
    semantiğine geçilince kırılacak ve borcun kapandığını işaret edecektir.
    """
    admin_h = await _giris(kurulu_istemci, ALFA)
    malzeme_id = await _malzeme_ac(kurulu_istemci, admin_h)

    await kurulu_istemci.post(
        f"{STOK}/stok-hareketleri",
        json={"malzeme_id": malzeme_id, "tur": "giris", "miktar": 100},
        headers=admin_h,
    )
    # "Sayım 95 buldu" niyeti; arada 50 giriş oluyor (gerçek hayatta üretim/teslimat).
    await kurulu_istemci.post(
        f"{STOK}/stok-hareketleri",
        json={"malzeme_id": malzeme_id, "tur": "giris", "miktar": 50},
        headers=admin_h,
    )
    r = await kurulu_istemci.post(
        f"{STOK}/stok-hareketleri",
        json={"malzeme_id": malzeme_id, "tur": "duzeltme", "miktar": 95},
        headers=admin_h,
    )
    assert r.status_code == 201

    detay = await kurulu_istemci.get(f"{STOK}/malzemeler/{malzeme_id}", headers=admin_h)
    bakiye = Decimal(str(detay.json()["data"]["mevcut_miktar"]))
    # Doğrusu 145 olurdu (150 + (95-100)); mutlak yazım 95 yazıyor → 50 birim kayıp.
    assert bakiye == Decimal("95"), (
        "davranış değişmiş — backlog #2 kapandıysa bu test güncellenmeli"
    )


async def test_openapi_aciklamasi_kullanimdan_kaldirildi_diyor(
    test_db: str, kurulu_istemci: AsyncClient
) -> None:
    """Sözleşme: uç açıklamasında bariz bir kullanımdan kaldırma uyarısı olmalı."""
    from app.main import create_app

    semalar = create_app().openapi()
    uc = semalar["paths"]["/api/v1/stok-hareketleri"]["post"]
    aciklama = uc.get("description", "")
    assert "KULLANIMDAN KALDIRILDI" in aciklama
    assert "duzeltme" in aciklama
