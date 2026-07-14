"""S-VB saf birim testleri — hedefleme kuralları, operatör eşleştirme, tedarikçi skoru."""

from __future__ import annotations

import pytest

from app.modules.ai.operator_eslestir import (
    EslesmeSonucu,
    OperatorAdayi,
    departman_uygunlugu,
    operator_puanla,
)
from app.modules.bildirim.hedefleme import (
    BILDIRIM_OLAYLARI,
    bildirim_hedef_kurali,
    bildirim_metni,
    bildirim_verisi,
)
from app.modules.crm.tedarikci_skoru import SkorSinyalleri, tedarikci_skoru
from app.modules.entegrasyon.birimler import OLAY_TURU_KATALOGU


# --- Bildirim hedefleme (tablo-testli) ---
@pytest.mark.parametrize(
    ("olay_turu", "izin", "kisi_alanlari", "herkese", "onem"),
    [
        ("stok.kritik", "stok:oku", (), False, "uyari"),
        ("sozlesme.yaklasiyor", "crm:oku", (), False, "uyari"),
        ("anomali.tespit", "ai:oku", (), False, "kritik"),
        ("rapor.hazir", None, ("olusturan_kullanici_id",), False, "bilgi"),
        ("ariza.olustu", "uretim:oku", (), False, "kritik"),
        ("oee.dustu", "uretim:oku", (), False, "uyari"),
        ("duyuru.yeni", None, (), True, "bilgi"),
    ],
)
def test_hedef_kurali_tablosu(
    olay_turu: str, izin: str | None, kisi_alanlari: tuple, herkese: bool, onem: str
) -> None:
    kural = bildirim_hedef_kurali(olay_turu, {})
    assert kural is not None
    assert kural.izin_kodu == izin
    assert kural.kisi_alanlari == kisi_alanlari
    assert kural.herkese is herkese
    assert kural.onem == onem


def test_sla_asildi_kaynak_modul_iznine_yonlenir() -> None:
    ie = bildirim_hedef_kurali("sla.asildi", {"kaynak_tur": "is_emri"})
    assert ie is not None and ie.izin_kodu == "isemri:oku"
    assert ie.kisi_alanlari == ("sorumlu_kullanici_id",)
    tl = bildirim_hedef_kurali("sla.asildi", {"kaynak_tur": "talep"})
    assert tl is not None and tl.izin_kodu == "talep:oku"
    bilinmeyen = bildirim_hedef_kurali("sla.asildi", {"kaynak_tur": "yok"})
    assert bilinmeyen is not None and bilinmeyen.izin_kodu is None  # sorumluya yine gider


def test_katalog_disi_olay_bildirim_uretmez() -> None:
    assert bildirim_hedef_kurali("is_emri.kapandi", {}) is None


def test_bildirim_metni_her_olay_icin_dolu() -> None:
    for olay_turu in BILDIRIM_OLAYLARI:
        baslik, govde = bildirim_metni(olay_turu, {"kod": "X-1", "baslik": "Test"})
        assert baslik, olay_turu
        assert govde, olay_turu


def test_bildirim_verisi_derin_baglanti() -> None:
    veri = bildirim_verisi("stok.kritik", {"kaynak_id": 7})
    assert veri == {"kaynak_tur": "malzeme", "kaynak_id": 7}
    veri2 = bildirim_verisi("sla.asildi", {"kaynak_tur": "is_emri", "kaynak_id": 3})
    assert veri2 == {"kaynak_tur": "is_emri", "kaynak_id": 3}


def test_sla_asildi_webhook_katalogunda() -> None:
    assert "sla.asildi" in OLAY_TURU_KATALOGU  # katalog 8 → 9


# --- Operatör eşleştirme ---
def _aday(pid: int, departman: str = "", unvan: str = "", kapanis: int = 0, izinli: bool = False):
    return OperatorAdayi(
        personel_id=pid,
        ad_soyad=f"P{pid}",
        departman=departman,
        unvan=unvan,
        kapatilan_is_emri=kapanis,
        izinli=izinli,
    )


def test_operator_puanla_deterministik_ve_sirali() -> None:
    adaylar = [
        _aday(1, departman="Üretim", kapanis=10),
        _aday(2, departman="Kalite", kapanis=10),
        _aday(3, departman="Üretim", kapanis=10, izinli=True),
    ]
    once = operator_puanla(adaylar, is_turu="uretim")
    sonra = operator_puanla(list(reversed(adaylar)), is_turu="uretim")
    assert [s.personel_id for s in once] == [s.personel_id for s in sonra]  # girdi sırası etkisiz
    assert once[0].personel_id == 1  # departman + müsait en yüksek
    assert once[1].personel_id == 3  # departman uyumlu ama izinli (0.2 kaybı)
    assert once[0].skor > once[1].skor > once[2].skor


def test_operator_puanla_esitlikte_kucuk_id_once() -> None:
    adaylar = [_aday(9, departman="Üretim"), _aday(2, departman="Üretim")]
    sonuc = operator_puanla(adaylar, is_turu="uretim")
    assert [s.personel_id for s in sonuc] == [2, 9]


def test_operator_puanla_bos_girdi_ve_sifir_gecmis() -> None:
    assert operator_puanla([], is_turu="uretim") == []
    # Hiç kapanış yokken bölme hatası olmamalı; performans bileşeni 0.
    sonuc = operator_puanla([_aday(1, departman="Üretim")], is_turu="uretim")
    assert isinstance(sonuc[0], EslesmeSonucu)
    assert sonuc[0].skor == pytest.approx(0.5 * 1.0 + 0.2, abs=1e-6)


def test_departman_uygunlugu_turkce_karakter_ve_unvan() -> None:
    assert departman_uygunlugu(_aday(1, departman="ÜRETİM"), "uretim") == 1.0
    assert departman_uygunlugu(_aday(1, unvan="Bakım Teknisyeni"), "bakim") == 0.8
    assert departman_uygunlugu(_aday(1, departman="İK"), "uretim") == 0.2


# --- Tedarikçi skoru ---
def test_tedarikci_skoru_tam_sinyal() -> None:
    detay = tedarikci_skoru(
        SkorSinyalleri(
            kalite_gecen=8,
            kalite_toplam=10,
            sozlesme_saglikli=3,
            sozlesme_toplam=4,
            talep_cozulen=5,
            talep_toplam=10,
        )
    )
    assert detay.skor == pytest.approx(40 * 0.8 + 30 * 0.75 + 30 * 0.5, abs=0.1)
    assert detay.yetersiz_veri == []
    assert detay.zamaninda_teslim is None  # S25'te dolar


def test_tedarikci_skoru_sinyalsiz_notr_ve_dürüst() -> None:
    detay = tedarikci_skoru(SkorSinyalleri())
    assert detay.skor == pytest.approx(50.0)  # tüm bileşenler nötr 0.5
    assert set(detay.yetersiz_veri) == {"kalite", "sozlesme", "talep"}


def test_tedarikci_skoru_sinirlar() -> None:
    tam = tedarikci_skoru(
        SkorSinyalleri(
            kalite_gecen=5,
            kalite_toplam=5,
            sozlesme_saglikli=2,
            sozlesme_toplam=2,
            talep_cozulen=3,
            talep_toplam=3,
        )
    )
    assert tam.skor == 100.0
    sifir = tedarikci_skoru(
        SkorSinyalleri(
            kalite_gecen=0,
            kalite_toplam=5,
            sozlesme_saglikli=0,
            sozlesme_toplam=2,
            talep_cozulen=0,
            talep_toplam=3,
        )
    )
    assert sifir.skor == 0.0
