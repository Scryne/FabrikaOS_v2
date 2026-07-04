"""S12 seed: CRM/sözleşme/talep/DYS/duyuru izin kataloğu + rol izin kümeleri."""

from __future__ import annotations

from app.kimlik.izinler import IZIN_KATALOGU, VARSAYILAN_ROLLER


def test_s12_izinleri_katalogda() -> None:
    for kod in (
        "crm:oku",
        "crm:yaz",
        "sozlesme:oku",
        "sozlesme:yaz",
        "talep:oku",
        "talep:yaz",
        "dys:oku",
        "dys:yaz",
        "duyuru:oku",
        "duyuru:yaz",
    ):
        assert kod in IZIN_KATALOGU


def test_crm_rolu() -> None:
    crm = VARSAYILAN_ROLLER["crm"]
    assert crm == frozenset(
        {"crm:oku", "crm:yaz", "sozlesme:oku", "sozlesme:yaz", "talep:oku", "talep:yaz"}
    )
    # CRM sorumlusu belge yükleyemez / duyuru yayınlayamaz (görev ayrımı).
    assert "dys:yaz" not in crm
    assert "duyuru:yaz" not in crm


def test_dokuman_rolu() -> None:
    assert VARSAYILAN_ROLLER["dokuman"] == frozenset({"dys:oku", "dys:yaz"})


def test_duyuru_rolu() -> None:
    assert VARSAYILAN_ROLLER["duyuru"] == frozenset({"duyuru:oku", "duyuru:yaz"})


def test_izleyici_oku_izinlerini_alir() -> None:
    # *:oku otomatik olarak izleyici rolüne düşer.
    izleyici = VARSAYILAN_ROLLER["izleyici"]
    for kod in ("crm:oku", "sozlesme:oku", "talep:oku", "dys:oku", "duyuru:oku"):
        assert kod in izleyici
    assert "crm:yaz" not in izleyici


def test_admin_tum_s12_izinlerini_alir() -> None:
    admin = VARSAYILAN_ROLLER["admin"]
    for kod in ("crm:yaz", "sozlesme:yaz", "talep:yaz", "dys:yaz", "duyuru:yaz"):
        assert kod in admin
