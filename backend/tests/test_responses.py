"""Yanıt zarfı yardımcıları (birim testleri)."""

from __future__ import annotations

from app.core.responses import SayfaMeta, basari, sayfalama_meta, sayfali


def test_basari_zarfi_meta_yok() -> None:
    z = basari({"a": 1})
    assert z["success"] is True
    assert z["data"] == {"a": 1}
    assert "meta" not in z


def test_basari_zarfi_mesaj() -> None:
    z = basari(None, mesaj="Oldu")
    assert z["message"] == "Oldu"
    assert z["data"] is None


def test_sayfalama_meta() -> None:
    assert sayfalama_meta(2, 50, 137) == {"sayfa": 2, "adet": 50, "toplam": 137}


def test_sayfali_liste() -> None:
    z = sayfali([1, 2, 3], sayfa=1, adet=20, toplam=3)
    assert z["data"] == [1, 2, 3]
    assert z["meta"] == {"sayfa": 1, "adet": 20, "toplam": 3}


def test_sayfa_meta_modeli() -> None:
    m = SayfaMeta(sayfa=2, adet=50, toplam=137)
    assert m.model_dump() == {"sayfa": 2, "adet": 50, "toplam": 137}
