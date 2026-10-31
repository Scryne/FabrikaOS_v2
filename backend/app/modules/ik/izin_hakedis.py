"""Yıllık izin hakedişi ve bakiyesi (S26-B, ADR-0044) — saf fonksiyonlar, veritabanı bilmez.

Hakediş 4857 sayılı İş Kanunu md. 53'ün tablosuyla hesaplanır; işletme daha cömert bir sözleşme
uyguluyorsa ``Personel.yillik_izin_hakki`` alt sınır olarak devreye girer (az olan değil, çok olan
geçerlidir)::

    hizmet yılı 1–5  (5 dahil)  → 14 gün
    hizmet yılı 6–14            → 20 gün
    hizmet yılı 15 ve üstü      → 26 gün
    18 yaş ve altı, 50 yaş ve üstü → en az 20 gün

Hak, her **tamamlanan** hizmet yılının sonunda (işe giriş yıldönümü) doğar; ilk yıl dolmadan yıllık
izin hakkı yoktur. Kullanılmayan izin yanmaz, sonraki yıla devreder: bakiye kümülatiftir.

    bakiye = Σ (tamamlanan her yıl için o yılın hakkı) − Σ onaylı yıllık izin günleri

Yaş eşiği hakkın doğduğu gündeki yaşa göre değerlendirilir.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

KANUNI_GENC_YASLI_ALT_SINIR = 20


def _yil_ekle(d: date, yil: int) -> date:
    try:
        return d.replace(year=d.year + yil)
    except ValueError:  # 29 Şubat → 28 Şubat
        return d.replace(year=d.year + yil, day=28)


def tam_yil(baslangic: date, bugun: date) -> int:
    """``baslangic`` ile ``bugun`` arasındaki tamamlanmış yıl sayısı (yıldönümü dahil)."""
    if bugun < baslangic:
        return 0
    yil = bugun.year - baslangic.year
    if _yil_ekle(baslangic, yil) > bugun:
        yil -= 1
    return max(yil, 0)


def yillik_hak(hizmet_yili: int, yas: int | None, sozlesme_hakki: int = 0) -> int:
    """``hizmet_yili``. yılın sonunda doğan yıllık izin günü (``hizmet_yili`` ≥ 1)."""
    if hizmet_yili < 1:
        return 0
    if hizmet_yili <= 5:
        gun = 14
    elif hizmet_yili < 15:
        gun = 20
    else:
        gun = 26
    if yas is not None and (yas <= 18 or yas >= 50):
        gun = max(gun, KANUNI_GENC_YASLI_ALT_SINIR)
    return max(gun, sozlesme_hakki)


@dataclass(frozen=True)
class HakedisSatiri:
    hizmet_yili: int
    dogdugu_tarih: date
    gun: int


@dataclass(frozen=True)
class IzinBakiyesi:
    hakedilen: int
    kullanilan: int
    bakiye: int
    kidem_yili: int
    sonraki_hak_tarihi: date | None
    sonraki_hak_gun: int
    satirlar: tuple[HakedisSatiri, ...]


def izin_bakiyesi(
    *,
    ise_giris: date | None,
    dogum: date | None,
    bugun: date,
    kullanilan: int,
    sozlesme_hakki: int = 0,
) -> IzinBakiyesi:
    """Kümülatif hakediş, kullanılan ve kalan gün. İşe giriş tarihi yoksa hak doğmaz."""
    if ise_giris is None:
        return IzinBakiyesi(0, kullanilan, -kullanilan, 0, None, 0, ())
    kidem = tam_yil(ise_giris, bugun)
    satirlar: list[HakedisSatiri] = []
    for y in range(1, kidem + 1):
        dogdu = _yil_ekle(ise_giris, y)
        yas = tam_yil(dogum, dogdu) if dogum else None
        satirlar.append(HakedisSatiri(y, dogdu, yillik_hak(y, yas, sozlesme_hakki)))
    sonraki = _yil_ekle(ise_giris, kidem + 1)
    sonraki_yas = tam_yil(dogum, sonraki) if dogum else None
    hakedilen = sum(s.gun for s in satirlar)
    return IzinBakiyesi(
        hakedilen=hakedilen,
        kullanilan=kullanilan,
        bakiye=hakedilen - kullanilan,
        kidem_yili=kidem,
        sonraki_hak_tarihi=sonraki,
        sonraki_hak_gun=yillik_hak(kidem + 1, sonraki_yas, sozlesme_hakki),
        satirlar=tuple(satirlar),
    )
