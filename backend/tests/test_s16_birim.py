"""S16 birim testleri — katalog tutarlılığı + saf entitlement fonksiyonları."""

from __future__ import annotations

from app.control_plane.entitlement import (
    etkin_moduller,
    etkin_ozellikler,
    modul_acik_mi,
    ozellik_acik_mi,
)
from app.control_plane.moduller import (
    MODUL_KATALOGU,
    OZELLIK_KATALOGU,
    PLAN_KATALOGU,
)

# --- Katalog tutarlılığı ---


def test_plan_kataloglari_modul_katalogu_ile_tutarli() -> None:
    for plan in PLAN_KATALOGU.values():
        assert plan.moduller <= set(MODUL_KATALOGU), plan.kod
        assert plan.ozellikler <= set(OZELLIK_KATALOGU), plan.kod
        assert plan.kod in PLAN_KATALOGU


def test_plan_katalogu_beklenen_planlar_ve_koltuklar() -> None:
    assert set(PLAN_KATALOGU) == {"deneme", "temel", "profesyonel", "kurumsal"}
    assert PLAN_KATALOGU["deneme"].koltuk_limiti == 5
    assert PLAN_KATALOGU["temel"].koltuk_limiti == 10
    assert PLAN_KATALOGU["profesyonel"].koltuk_limiti == 50
    assert PLAN_KATALOGU["kurumsal"].koltuk_limiti is None  # sınırsız


def test_deneme_ve_kurumsal_tum_modulleri_kapsar() -> None:
    assert PLAN_KATALOGU["deneme"].moduller == set(MODUL_KATALOGU)
    assert PLAN_KATALOGU["kurumsal"].moduller == set(MODUL_KATALOGU)
    # temel gerçek bir alt kümedir (kapalı modül senaryosu var olabilsin diye)
    assert PLAN_KATALOGU["temel"].moduller < set(MODUL_KATALOGU)
    assert "ai" not in PLAN_KATALOGU["temel"].moduller


# --- modul_acik_mi ---


def test_modul_planda_varsa_acik_yoksa_kapali() -> None:
    plan = PLAN_KATALOGU["temel"].moduller
    assert modul_acik_mi("uretim", plan, {}) is True
    assert modul_acik_mi("ai", plan, {}) is False


def test_override_plani_ezer_iki_yonde() -> None:
    plan = PLAN_KATALOGU["temel"].moduller
    assert modul_acik_mi("ai", plan, {"ai": True}) is True  # planda yok, hak açtı
    assert modul_acik_mi("uretim", plan, {"uretim": False}) is False  # planda var, hak kapattı


def test_bilinmeyen_modul_kodu_daima_kapali() -> None:
    # Fail-closed: katalog dışı kod, override True olsa bile açılmaz.
    assert modul_acik_mi("olmayan-modul", set(MODUL_KATALOGU), {"olmayan-modul": True}) is False


def test_etkin_moduller_tum_katalogu_dondurur() -> None:
    sonuc = etkin_moduller(PLAN_KATALOGU["temel"].moduller, {"kalite": True})
    assert set(sonuc) == set(MODUL_KATALOGU)
    assert sonuc["uretim"] is True
    assert sonuc["kalite"] is True  # override ile açıldı
    assert sonuc["ai"] is False


# --- ozellik_acik_mi ---


def test_ozellik_plan_ve_override_davranisi() -> None:
    plan = PLAN_KATALOGU["kurumsal"].ozellikler
    kod = next(iter(OZELLIK_KATALOGU))
    assert ozellik_acik_mi(kod, plan, {}) is True
    assert ozellik_acik_mi(kod, frozenset(), {}) is False
    assert ozellik_acik_mi(kod, frozenset(), {kod: True}) is True
    assert ozellik_acik_mi("olmayan-ozellik", plan, {"olmayan-ozellik": True}) is False


def test_etkin_ozellikler_tum_katalogu_dondurur() -> None:
    sonuc = etkin_ozellikler(frozenset(), {})
    assert set(sonuc) == set(OZELLIK_KATALOGU)
    assert all(v is False for v in sonuc.values())
