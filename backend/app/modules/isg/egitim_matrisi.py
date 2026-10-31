"""İSG eğitim matrisi (S26-B, ADR-0044) — saf fonksiyon, veritabanı bilmez.

Satır personel, sütun eğitim konusu. Bir hücre, personelin o konuda katıldığı **en yeni** eğitimin
geçerlilik sonuna göre etiketlenir::

    gecerli     geçerlilik sonu > bugün + eşik
    yaklasiyor  bugün ≤ geçerlilik sonu ≤ bugün + eşik
    gecmis      geçerlilik sonu < bugün
    eksik       konu personelin departmanı için zorunlu ama hiç katılım yok
    gerekmez    zorunlu değil ve katılım yok

Geçerlilik süresi eğitim kaydında ay olarak tutulur; tekrar sıklığı işyerinin tehlike sınıfına
bağlıdır (çok tehlikeli 12, tehlikeli 24, az tehlikeli 36 ay) ve kaydı açan bunu seçer.
``gecerlilik_ay = 0`` süresiz eğitimdir (ör. işe giriş oryantasyonu).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, timedelta

YAKLASMA_ESIGI_GUN = 30


def ay_ekle(d: date, ay: int) -> date:
    """Takvim ayı ekler; hedef ayda gün yoksa ayın son günü (31 Ocak + 1 ay → 28/29 Şubat)."""
    toplam = d.month - 1 + ay
    yil, ay0 = d.year + toplam // 12, toplam % 12 + 1
    for gun in (d.day, 30, 29, 28):
        try:
            return date(yil, ay0, gun)
        except ValueError:
            continue
    raise ValueError(d)  # pragma: no cover — 28 her ayda vardır


@dataclass(frozen=True)
class Katilim:
    personel_id: int
    konu: str
    tarih: date
    gecerlilik_ay: int


@dataclass(frozen=True)
class Hucre:
    durum: str
    son_tarih: date | None
    gecerlilik_sonu: date | None


def hucre(
    katilimlar: Iterable[Katilim], *, zorunlu: bool, bugun: date, esik: int = YAKLASMA_ESIGI_GUN
) -> Hucre:
    """Bir personel × konu hücresi (``katilimlar`` yalnız o personel ve konuya ait olmalı)."""
    son = max(katilimlar, key=lambda k: k.tarih, default=None)
    if son is None:
        return Hucre("eksik" if zorunlu else "gerekmez", None, None)
    if son.gecerlilik_ay <= 0:
        return Hucre("gecerli", son.tarih, None)
    bitis = ay_ekle(son.tarih, son.gecerlilik_ay)
    if bitis < bugun:
        durum = "gecmis"
    elif bitis <= bugun + timedelta(days=esik):
        durum = "yaklasiyor"
    else:
        durum = "gecerli"
    return Hucre(durum, son.tarih, bitis)


def matris(
    personeller: Iterable[tuple[int, str]],
    katilimlar: Iterable[Katilim],
    gereksinimler: Mapping[str, frozenset[str]],
    *,
    bugun: date,
) -> tuple[list[str], dict[int, dict[str, Hucre]]]:
    """``personeller`` (id, departman); ``gereksinimler`` departman → zorunlu konular.

    ``""`` anahtarlı gereksinim tüm departmanlara uygulanır. Sütunlar: zorunlu konuların ve
    katılım görülen konuların birleşimi, alfabetik. Dönüş: (sütunlar, personel_id → konu → hücre).
    """
    kayitlar = list(katilimlar)
    personel_listesi = list(personeller)
    genel = gereksinimler.get("", frozenset())
    konular = set(genel)
    for dep, ks in gereksinimler.items():
        if dep:
            konular |= ks
    konular |= {k.konu for k in kayitlar}
    sutunlar = sorted(konular)

    gruplu: dict[tuple[int, str], list[Katilim]] = {}
    for k in kayitlar:
        gruplu.setdefault((k.personel_id, k.konu), []).append(k)

    sonuc: dict[int, dict[str, Hucre]] = {}
    for pid, dep in personel_listesi:
        zorunlular = genel | gereksinimler.get(dep, frozenset())
        sonuc[pid] = {
            konu: hucre(gruplu.get((pid, konu), []), zorunlu=konu in zorunlular, bugun=bugun)
            for konu in sutunlar
        }
    return sutunlar, sonuc
