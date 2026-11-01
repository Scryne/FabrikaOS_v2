"""ESG servisi (S32, ADR-0051): enerji tüketiminden dönemsel emisyon ve yoğunluk.

Tüketim ham ``enerji_tuketim`` tablosundan okunur (saatlik toplam görünümünde birim yok; emisyon
birim ister). Dönem sınırı İstanbul saatine göredir. Üretim yoğunluğu aynı dönemlerin sağlam
adedine bölünür.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.zaman import is_saat_dilimi
from app.modules.enerji.models import EnerjiTuketim
from app.modules.esg import hesap
from app.modules.esg.models import EmisyonFaktoru
from app.modules.uretim.models import UretimVerisi

Donem = Literal["gun", "ay"]

# Kaynaklı varsayılan faktörler (ADR-0051 §2): tenant kendi faktörünü girene dek kullanılır.
# Basınçlı hava, su, buhar bilerek yok: enerjileri elektrik/yakıt tüketiminin içinde (çift sayım).
# Değerler 2026-11-01'de birincil kaynaktan alındı; ETKB yılda bir (≈2 yıl gecikmeli) yayımlar.
VARSAYILAN_GECERLILIK = date(2000, 1, 1)
VARSAYILAN: tuple[hesap.Faktor, ...] = (
    hesap.Faktor(
        "elektrik",
        "kwh",
        Decimal("0.469"),
        "kapsam2",
        VARSAYILAN_GECERLILIK,
        "ETKB 2023 tüketim noktası emisyon faktörü, dağıtım hattına bağlı tüketim (tCO2e/MWh). "
        "İletim hattına bağlı tesis 0,436 girmeli. Dağıtım kaybını içerir: Kapsam 3'te ayrıca "
        "sayılmaz. enerji.gov.tr/evced-cevre-ve-iklim-elektrik-uretim-tuketim-emisyon-faktorleri",
    ),
    hesap.Faktor(
        "dogalgaz",
        "m3",
        Decimal("1.928"),
        "kapsam1",
        VARSAYILAN_GECERLILIK,
        "IPCC 2006 sabit yakma CO2 56.100 kg/TJ × alt ısıl değer 8.200 kcal/Sm3 (ETKB) = 1,926 kg "
        "CO2; CH4/N2O varsayılanı (+0,002) birincil kaynaktan doğrulanmadı. "
        "Sm3: 15 °C, 1,01325 bar.",
    ),
)


@dataclass(frozen=True)
class EsgSonucu:
    sonuc: hesap.Sonuc
    adet: dict[date, int]  # dönem → sağlam adet
    faktorler: list[tuple[hesap.Faktor, str, int | None]]  # (faktör, köken, tenant satır id)

    @property
    def toplam_adet(self) -> int:
        return sum(self.adet.values())


def _kesim(donem: Donem) -> str:
    return "day" if donem == "gun" else "month"


def donem_basi(gun: date, donem: Donem) -> date:
    return gun if donem == "gun" else gun.replace(day=1)


async def faktorler(db: AsyncSession) -> list[tuple[hesap.Faktor, str, int | None]]:
    """Etkin faktörler: tenant satırları + tenant'ın aynı tür/birim için satırı yoksa varsayılan."""
    satirlar = (
        await db.execute(
            select(EmisyonFaktoru).order_by(
                EmisyonFaktoru.enerji_turu, EmisyonFaktoru.birim, EmisyonFaktoru.gecerlilik
            )
        )
    ).scalars()
    sonuc: list[tuple[hesap.Faktor, str, int | None]] = []
    kendi: set[tuple[str, str]] = set()
    for r in satirlar:
        kendi.add((r.enerji_turu, r.birim))
        sonuc.append(
            (
                hesap.Faktor(
                    r.enerji_turu, r.birim, Decimal(r.deger), r.kapsam, r.gecerlilik, r.kaynak
                ),
                "tenant",
                r.id,
            )
        )
    for f in VARSAYILAN:
        if (f.enerji_turu, f.birim) not in kendi:
            sonuc.append((f, "varsayilan", None))
    return sonuc


async def hesapla(db: AsyncSession, *, baslangic: date, bitis: date, donem: Donem) -> EsgSonucu:
    """``[baslangic, bitis]`` (dahil) aralığının dönemsel emisyonu ve üretim yoğunluğu."""
    tz = is_saat_dilimi()
    bas = datetime.combine(baslangic, time(0), tz)
    bit = datetime.combine(bitis + timedelta(days=1), time(0), tz)
    yerel = func.timezone("Europe/Istanbul", EnerjiTuketim.zaman)
    kova = func.date_trunc(_kesim(donem), yerel).label("kova")
    tuketim_rows = (
        await db.execute(
            select(
                kova,
                EnerjiTuketim.enerji_turu,
                EnerjiTuketim.birim,
                func.sum(EnerjiTuketim.tuketim),
            )
            .where(EnerjiTuketim.zaman >= bas, EnerjiTuketim.zaman < bit)
            .group_by(kova, EnerjiTuketim.enerji_turu, EnerjiTuketim.birim)
        )
    ).all()
    tuketimler = [
        hesap.Tuketim(k.date(), tur, birim, Decimal(toplam or 0))
        for k, tur, birim, toplam in tuketim_rows
    ]
    uyerel = func.timezone("Europe/Istanbul", UretimVerisi.zaman)
    ukova = func.date_trunc(_kesim(donem), uyerel).label("kova")
    adet_rows = (
        await db.execute(
            select(ukova, func.sum(UretimVerisi.saglam_adet))
            .where(UretimVerisi.zaman >= bas, UretimVerisi.zaman < bit)
            .group_by(ukova)
        )
    ).all()
    adet = {k.date(): int(a or 0) for k, a in adet_rows}
    etkin = await faktorler(db)
    sonuc = hesap.hesapla(tuketimler, [f for f, _, _ in etkin])
    return EsgSonucu(sonuc=sonuc, adet=adet, faktorler=etkin)


def kg_ton(kg: Decimal) -> float:
    return round(float(kg) / 1000, 3)


def ozet_satirlari(r: EsgSonucu) -> list[dict[str, Any]]:
    """Dönem satırları (rapor ve uç ortak): emisyon kg, sağlam adet, yoğunluklar."""
    donemler = {d.donem for d in r.sonuc.donemler} | set(r.adet)
    bul = {d.donem: d for d in r.sonuc.donemler}
    satirlar = []
    for g in sorted(donemler):
        d = bul.get(g, hesap.DonemSonucu(g))
        adet = r.adet.get(g, 0)
        kg_adet = hesap.yogunluk(d.toplam, adet)
        kwh_adet = hesap.yogunluk(d.elektrik_kwh, adet)
        satirlar.append(
            {
                "donem": g,
                "kapsam1_kg": round(float(d.kapsam1), 3),
                "kapsam2_kg": round(float(d.kapsam2), 3),
                "toplam_kg": round(float(d.toplam), 3),
                "elektrik_kwh": round(float(d.elektrik_kwh), 3),
                "saglam_adet": adet,
                "kg_adet": round(float(kg_adet), 4) if kg_adet is not None else None,
                "kwh_adet": round(float(kwh_adet), 4) if kwh_adet is not None else None,
            }
        )
    return satirlar
