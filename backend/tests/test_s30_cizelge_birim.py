"""S30 (ADR-0049) saf çizelgeleme: pencereler, sıralama, ileri yerleştirme, yük, kapasite aşımı."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.modules.planlama.cizelge import (
    Is,
    Pencere,
    cizelgele,
    gunluk_yuk,
    kapasite_asimi,
    sirala,
    vardiya_pencereleri,
)

TR = ZoneInfo("Europe/Istanbul")
GUN = date(2026, 11, 2)  # pazartesi


def _an(gun: int, saat: int, dakika: int = 0) -> datetime:
    return datetime.combine(GUN + timedelta(days=gun), time(saat, dakika), TR)


def test_pencereler_gece_vardiyasi_ve_birlesme() -> None:
    p = vardiya_pencereleri([(time(8), time(16)), (time(16), time(0))], GUN, 2, TR)
    # 08–16 ve 16–24 bitişik: tek pencere 08:00–24:00, iki gün
    assert p == [Pencere(_an(0, 8), _an(1, 0)), Pencere(_an(1, 8), _an(2, 0))]
    gece = vardiya_pencereleri([(time(22), time(6))], GUN, 1, TR)
    assert gece == [Pencere(_an(0, 22), _an(1, 6))]
    assert gece[0].dakika == 480


def test_siralama_devam_elle_edd_oncelik_id() -> None:
    isler = [
        Is(5, 60, hedef=_an(3, 12), oncelik="dusuk"),
        Is(4, 60, hedef=_an(1, 12), oncelik="dusuk"),
        Is(3, 60, hedef=_an(1, 12), oncelik="kritik"),
        Is(2, 60, hedef=None),
        Is(9, 60, hedef=_an(5, 0), elle_sira=1),
        Is(1, 60, hedef=_an(9, 0), devam_ediyor=True),
    ]
    assert [i.id for i in sirala(isler)] == [1, 9, 3, 4, 5, 2]
    # Tekrarlanabilir: girdi sırası sonucu değiştirmez.
    assert [i.id for i in sirala(reversed(isler))] == [1, 9, 3, 4, 5, 2]


def test_ileri_cizelgeleme_pencere_sonunda_boler() -> None:
    p = vardiya_pencereleri([(time(8), time(16))], GUN, 3, TR)
    c = cizelgele([Is(1, 300), Is(2, 300, hedef=_an(0, 15))], p, _an(0, 9))
    a, b = c.yerlesimler  # 2'nin hedefi var → önce
    assert a.is_id == 2 and a.parcalar == [(_an(0, 9), _an(0, 14))]
    assert a.gecikme_dk == 0
    # 14:00'te başlar, 16:00'da kesilir, ertesi gün 08:00'de 180 dk sürer.
    assert b.parcalar == [(_an(0, 14), _an(0, 16)), (_an(1, 8), _an(1, 11))]
    assert c.sigmayan == []


def test_gecikme_kapasite_asimi_ve_sigmayan() -> None:
    p = vardiya_pencereleri([(time(8), time(16))], GUN, 2, TR)  # 2 × 480 dk
    isler = [
        Is(1, 400, hedef=_an(0, 16)),
        Is(2, 200, hedef=_an(0, 16)),  # ilk gün 600 dk iş, 480 kapasite → biri gecikir
        Is(3, 600),  # ufukta sığmaz
    ]
    c = cizelgele(isler, p, _an(0, 8))
    y = {x.is_id: x for x in c.yerlesimler}
    # Gecikme duvar saatiyle: hedef 16:00, bitiş ertesi gün 10:00 → 18 saat.
    assert y[1].gecikme_dk == 0 and y[2].gecikme_dk == 1080
    assert c.sigmayan == [3]
    assert kapasite_asimi(isler, c) == [2, 3]


def test_gunluk_yuk_gun_sinirinda_bolunur() -> None:
    p = vardiya_pencereleri([(time(20), time(4))], GUN, 1, TR)
    c = cizelgele([Is(1, 360)], p, _an(0, 20))  # 20:00–02:00
    yuk = gunluk_yuk(c, p, TR)
    assert yuk[GUN] == (240.0, 240.0)
    assert yuk[GUN + timedelta(days=1)] == (120.0, 240.0)


def test_baslangic_pencere_ortasinda_ve_gecmis_pencereler_atlanir() -> None:
    p = vardiya_pencereleri([(time(8), time(16))], GUN, 2, TR)
    c = cizelgele([Is(1, 120)], p, _an(0, 15))
    assert c.yerlesimler[0].parcalar == [(_an(0, 15), _an(0, 16)), (_an(1, 8), _an(1, 9))]
    c2 = cizelgele([Is(1, 60)], p, _an(0, 17))
    assert c2.yerlesimler[0].parcalar == [(_an(1, 8), _an(1, 9))]
    bos = cizelgele([Is(1, 0)], p, _an(0, 8))
    assert bos.yerlesimler[0].parcalar == [] and bos.sigmayan == []


def test_oncelik_dort_seviye_ve_bilinmeyen_orta_sayilir() -> None:
    hedef = _an(2, 12)
    # Id'ler önceliğin tersine: eşitlik id'ye kalsaydı sıra bozulurdu.
    isler = [
        Is(1, 60, hedef=hedef, oncelik="dusuk"),
        Is(2, 60, hedef=hedef, oncelik="bilinmeyen"),
        Is(3, 60, hedef=hedef, oncelik="orta"),
        Is(4, 60, hedef=hedef, oncelik="yuksek"),
        Is(5, 60, hedef=hedef, oncelik="kritik"),
    ]
    # Bilinmeyen öncelik "orta" ile eşit (id ile kırılır), düşükten önce.
    assert [i.id for i in sirala(isler)] == [5, 4, 2, 3, 1]


def test_elle_sira_tum_hedeflerin_onunde_devam_edenin_arkasinda() -> None:
    isler = [
        Is(1, 60, hedef=_an(0, 9)),
        Is(2, 60, hedef=None, elle_sira=2),
        Is(3, 60, hedef=_an(9, 9), elle_sira=1),
        Is(4, 60, hedef=_an(5, 9), devam_ediyor=True),
    ]
    assert [i.id for i in sirala(isler)] == [4, 3, 2, 1]


def test_yerlesim_ozellikleri_ve_hedefsiz_iste_gecikme_yok() -> None:
    p = vardiya_pencereleri([(time(8), time(16))], GUN, 3, TR)
    c = cizelgele([Is(1, 600)], p, _an(0, 8))  # hedefsiz, iki güne bölünür
    y = c.yerlesimler[0]
    assert y.baslangic == _an(0, 8) and y.bitis == _an(1, 10)
    assert y.gecikme_dk == 0.0
    bos = cizelgele([Is(2, 60)], [], _an(0, 8)).yerlesimler[0]
    assert bos.baslangic is None and bos.bitis is None


def test_tam_gun_vardiyasi_ve_pencere_sonunda_baslangic() -> None:
    # 08:00–08:00: başlangıç = bitiş → 24 saatlik vardiya (ertesi güne taşar).
    tam = vardiya_pencereleri([(time(8), time(8))], GUN, 1, TR)
    assert tam == [Pencere(_an(0, 8), _an(1, 8))] and tam[0].dakika == 1440
    # Başlangıç tam pencere sonunda: sıfır uzunlukta parça yazılmaz, ertesi pencereye geçilir.
    p = vardiya_pencereleri([(time(8), time(16))], GUN, 2, TR)
    c = cizelgele([Is(1, 60)], p, _an(0, 16))
    assert c.yerlesimler[0].parcalar == [(_an(1, 8), _an(1, 9))]


def test_tam_zamanda_biten_is_gecikmez_ve_asim_sayilmaz() -> None:
    p = vardiya_pencereleri([(time(8), time(16))], GUN, 1, TR)
    isler = [Is(1, 480, hedef=_an(0, 16)), Is(2, 1, hedef=_an(0, 16))]
    c = cizelgele(isler, p, _an(0, 8))
    y = {x.is_id: x for x in c.yerlesimler}
    assert y[1].gecikme_dk == 0.0  # tam 16:00'da biter: geç değil
    assert c.sigmayan == [2]  # 1 dk bile kalmadı
    assert kapasite_asimi(isler, c) == [2]


def test_gunluk_yuk_bos_gun_sifir_ve_yuvarlama() -> None:
    p = vardiya_pencereleri([(time(8), time(16))], GUN, 2, TR)
    c = cizelgele([Is(1, 100.04)], p, _an(0, 8))
    yuk = gunluk_yuk(c, p, TR)
    assert yuk == {GUN: (100.0, 480.0), GUN + timedelta(days=1): (0.0, 480.0)}


def test_dakikanin_altindaki_gecikme_de_asimdir() -> None:
    p = vardiya_pencereleri([(time(8), time(16))], GUN, 2, TR)
    isler = [Is(1, 480.5, hedef=_an(0, 16))]  # 30 sn geç biter (ertesi sabah 08:00:30)
    c = cizelgele(isler, p, _an(0, 8))
    assert c.yerlesimler[0].gecikme_dk > 0
    assert kapasite_asimi(isler, c) == [1]
