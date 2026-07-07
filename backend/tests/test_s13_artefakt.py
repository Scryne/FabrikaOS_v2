"""S13 artefakt deposu testleri — joblib round-trip + tenant-izole anahtar + önbellek."""

from __future__ import annotations

from collections.abc import Iterator

import pandas as pd
import pytest

from app.modules.ai import artefakt, modeller
from app.modules.dys.depolama import BellekNesneDepo, nesne_depo_ayarla


@pytest.fixture(autouse=True)
def bellek_depo() -> Iterator[BellekNesneDepo]:
    depo = BellekNesneDepo()
    nesne_depo_ayarla(depo)
    artefakt.onbellek_temizle()
    yield depo
    nesne_depo_ayarla(None)
    artefakt.onbellek_temizle()


def test_anahtar_tenant_izole() -> None:
    assert artefakt.model_nesne_anahtari("alfa", "oee", 3) == "tenant_alfa/model/oee/3/model.joblib"


def test_kaydet_yukle_roundtrip(bellek_depo: BellekNesneDepo) -> None:
    tuketim = pd.DataFrame(
        [
            {
                "malzeme_id": 5,
                "gun": pd.Timestamp("2026-06-01") + pd.Timedelta(days=g),
                "miktar": 4.0,
            }
            for g in range(6)
        ]
    )
    egitilen = modeller.stok_egit(tuketim)
    anahtar = artefakt.model_nesne_anahtari("alfa", "stok", 1)
    boyut = artefakt.artefakt_kaydet(anahtar, egitilen.nesne)
    assert boyut > 0
    assert bellek_depo.var_mi(anahtar)

    geri = artefakt.artefakt_yukle(anahtar)
    assert geri["hizlar"] == egitilen.nesne["hizlar"]


def test_onbellek_ayni_nesneyi_dondurur() -> None:
    anahtar = artefakt.model_nesne_anahtari("alfa", "stok", 2)
    artefakt.artefakt_kaydet(anahtar, {"hizlar": {5: 4.0}})
    a = artefakt.artefakt_yukle_onbellekli(anahtar)
    b = artefakt.artefakt_yukle_onbellekli(anahtar)
    assert a is b  # ikinci çağrı depoya inmez


def test_farkli_tenant_anahtari_ayrisir(bellek_depo: BellekNesneDepo) -> None:
    a1 = artefakt.model_nesne_anahtari("alfa", "oee", 1)
    b1 = artefakt.model_nesne_anahtari("beta", "oee", 1)
    artefakt.artefakt_kaydet(a1, {"kaynak": "alfa"})
    assert not bellek_depo.var_mi(b1)
    assert artefakt.artefakt_yukle(a1)["kaynak"] == "alfa"
