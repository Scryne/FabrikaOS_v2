"""S18 imza/zarf/backoff saf birim testleri (DB'siz)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.entegrasyon.imza import (
    DENEME_ARALIKLARI_SN,
    MAKS_DENEME,
    gizli_anahtar_uret,
    imza_dogrula,
    imza_uret,
    sonraki_deneme_gecikmesi_sn,
    zarf_bytelari,
    zarf_olustur,
)

GIZLI = "whs_test-anahtari"
GOVDE = b'{"surum":"v1","veri":{"x":1}}'


def test_imza_gidis_donus() -> None:
    baslik = imza_uret(GIZLI, 1_700_000_000, GOVDE)
    assert baslik.startswith("t=1700000000,v1=")
    assert imza_dogrula(GIZLI, baslik, GOVDE, simdi=1_700_000_000)
    assert imza_dogrula(GIZLI, baslik, GOVDE, simdi=1_700_000_000 + 299)


def test_imza_yanlis_anahtar_reddedilir() -> None:
    baslik = imza_uret(GIZLI, 1_700_000_000, GOVDE)
    assert not imza_dogrula("whs_baska-anahtar", baslik, GOVDE, simdi=1_700_000_000)


def test_imza_oynanmis_govde_reddedilir() -> None:
    baslik = imza_uret(GIZLI, 1_700_000_000, GOVDE)
    assert not imza_dogrula(GIZLI, baslik, GOVDE + b" ", simdi=1_700_000_000)


def test_imza_tolerans_disi_reddedilir() -> None:
    # Yeniden-oynatma koruması: imza doğru olsa bile eski zaman damgası geçmez.
    baslik = imza_uret(GIZLI, 1_700_000_000, GOVDE)
    assert not imza_dogrula(GIZLI, baslik, GOVDE, simdi=1_700_000_000 + 301)
    assert not imza_dogrula(GIZLI, baslik, GOVDE, simdi=1_700_000_000 - 301)


def test_imza_bozuk_baslik_reddedilir() -> None:
    for bozuk in ("", "v1=abc", "t=abc,v1=def", "t=170,x=1", "sacmalik"):
        assert not imza_dogrula(GIZLI, bozuk, GOVDE, simdi=170), bozuk


def test_gizli_anahtar_uret_onek_ve_benzersizlik() -> None:
    a, b = gizli_anahtar_uret(), gizli_anahtar_uret()
    assert a.startswith("whs_") and b.startswith("whs_")
    assert a != b
    assert len(a) > 30


def test_zarf_olustur_alanlari() -> None:
    dis = uuid.uuid4()
    olay = SimpleNamespace(
        olay_turu="is_emri.kapandi",
        dis_anahtar=dis,
        olusturma_tarihi=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        govde={"is_emri_id": 5},
    )
    zarf = zarf_olustur(olay)  # type: ignore[arg-type]
    assert zarf == {
        "surum": "v1",
        "olay_turu": "is_emri.kapandi",
        "dis_anahtar": str(dis),
        "olusturma_tarihi": "2026-07-10T12:00:00+00:00",
        "veri": {"is_emri_id": 5},
    }


def test_zarf_bytelari_deterministik_ve_json() -> None:
    zarf = {"surum": "v1", "veri": {"ad": "Türkçe ölçüm"}}
    b1, b2 = zarf_bytelari(zarf), zarf_bytelari(zarf)
    assert b1 == b2
    assert json.loads(b1) == zarf
    assert "Türkçe ölçüm".encode() in b1  # ensure_ascii=False — okunur UTF-8


def test_backoff_dizisi() -> None:
    gecikmeler = [sonraki_deneme_gecikmesi_sn(n) for n in range(1, MAKS_DENEME)]
    assert gecikmeler == list(DENEME_ARALIKLARI_SN) == [60, 300, 1800, 7200, 21600]
    assert sonraki_deneme_gecikmesi_sn(MAKS_DENEME) is None  # 6. deneme son şans
    assert sonraki_deneme_gecikmesi_sn(0) is None
    assert sonraki_deneme_gecikmesi_sn(99) is None
