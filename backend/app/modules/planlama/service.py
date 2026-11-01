"""Planlama servisi (S30, ADR-0049): açık iş emirlerinden makine bazlı sonlu kapasite çizelgesi.

Süre önceliği: plandaki elle süre → tahmin (miktar × makinenin son ideal çevrim süresi ÷ OEE
hedefi) → varsayılan (60 dk, uyarılı). Vardiya tanımı yoksa 08:00–16:00 varsayılır ve yanıt
bunu söyler. Çizelge saklanmaz; her istekte yeniden hesaplanır.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.zaman import is_gunu, is_saat_dilimi
from app.modules.isemri.models import IsEmri
from app.modules.planlama import cizelge
from app.modules.planlama.models import IsEmriPlani
from app.modules.uretim.models import Makine, UretimVerisi
from app.modules.vardiya.models import Vardiya

ACIK_DURUMLAR = ("acik", "atandi", "devam_ediyor")
VARSAYILAN_SURE_DK = 60.0
VARSAYILAN_VARDIYA = ((time(8), time(16)),)
VARSAYILAN_VERIM = 0.85


@dataclass(frozen=True)
class SureTahmini:
    dakika: float
    kaynak: str  # elle | tahmin | varsayilan


def sure_tahmin_et(
    elle: float | None,
    miktar: float | None,
    ideal_cevrim_sn: float | None,
    oee_hedefi: float | None,
) -> SureTahmini:
    """Saf: elle süre > çevrim tahmini > varsayılan."""
    if elle is not None and elle > 0:
        return SureTahmini(float(elle), "elle")
    if miktar and miktar > 0 and ideal_cevrim_sn and ideal_cevrim_sn > 0:
        verim = oee_hedefi if oee_hedefi and 0 < oee_hedefi <= 1 else VARSAYILAN_VERIM
        return SureTahmini(round(miktar * ideal_cevrim_sn / 60 / verim, 1), "tahmin")
    return SureTahmini(VARSAYILAN_SURE_DK, "varsayilan")


async def _son_cevrimler(db: AsyncSession, makine_idler: list[int]) -> dict[int, float]:
    if not makine_idler:
        return {}
    son = (
        select(UretimVerisi.makine_id, func.max(UretimVerisi.zaman).label("z"))
        .where(UretimVerisi.makine_id.in_(makine_idler), UretimVerisi.ideal_cevrim_sn > 0)
        .group_by(UretimVerisi.makine_id)
        .subquery()
    )
    satirlar = (
        await db.execute(
            select(UretimVerisi.makine_id, UretimVerisi.ideal_cevrim_sn).join(
                son,
                (son.c.makine_id == UretimVerisi.makine_id) & (son.c.z == UretimVerisi.zaman),
            )
        )
    ).all()
    return {mid: float(c) for mid, c in satirlar}


async def cizelge_hesapla(
    db: AsyncSession, *, ilk_gun: date, gun_sayisi: int, makine_id: int | None = None
) -> dict[str, Any]:
    tz = is_saat_dilimi()
    vardiyalar = [
        (v.baslangic_saat, v.bitis_saat)
        for v in (await db.execute(select(Vardiya).where(Vardiya.aktif))).scalars()
    ]
    varsayilan_vardiya = not vardiyalar
    pencereler = cizelge.vardiya_pencereleri(
        vardiyalar or VARSAYILAN_VARDIYA, ilk_gun, gun_sayisi, tz
    )
    simdi = datetime.now(tz).replace(second=0, microsecond=0)
    gun_basi = datetime.combine(ilk_gun, time(0), tz)
    baslangic = max(simdi, gun_basi) if ilk_gun <= is_gunu() else gun_basi

    sorgu = (
        select(IsEmri, Makine, IsEmriPlani)
        .join(Makine, Makine.id == IsEmri.makine_id)
        .outerjoin(IsEmriPlani, IsEmriPlani.is_emri_id == IsEmri.id)
        .where(IsEmri.durum.in_(ACIK_DURUMLAR))
    )
    if makine_id is not None:
        sorgu = sorgu.where(IsEmri.makine_id == makine_id)
    satirlar = (await db.execute(sorgu)).all()
    cevrimler = await _son_cevrimler(db, sorted({m.id for _, m, _ in satirlar}))

    makineler: dict[int, dict[str, Any]] = {}
    girdiler: dict[int, list[tuple[cizelge.Is, IsEmri, SureTahmini, IsEmriPlani | None]]] = {}
    for ie, m, plan in satirlar:
        tahmin = sure_tahmin_et(
            float(plan.sure_dk) if plan and plan.sure_dk is not None else None,
            float(ie.miktar) if ie.miktar is not None else None,
            cevrimler.get(m.id),
            m.oee_hedefi,
        )
        is_ = cizelge.Is(
            id=ie.id,
            sure_dk=tahmin.dakika,
            hedef=ie.hedef_tarih,
            oncelik=ie.oncelik,
            devam_ediyor=ie.durum == "devam_ediyor",
            elle_sira=plan.elle_sira if plan else None,
        )
        makineler.setdefault(m.id, {"makine_id": m.id, "kod": m.kod, "ad": m.ad})
        girdiler.setdefault(m.id, []).append((is_, ie, tahmin, plan))

    sonuc: list[dict[str, Any]] = []
    toplam_geciken = toplam_asim = 0
    for mid in sorted(makineler, key=lambda x: makineler[x]["kod"]):
        liste = girdiler[mid]
        isler = [x[0] for x in liste]
        c = cizelge.cizelgele(isler, pencereler, baslangic)
        # Kapasite aşımı elle sırasız (saf EDD) çizelgeden: sıra kaynaklı gecikmeyi ayırır.
        edd = cizelge.cizelgele(
            [cizelge.Is(i.id, i.sure_dk, i.hedef, i.oncelik, i.devam_ediyor) for i in isler],
            pencereler,
            baslangic,
        )
        asim = set(cizelge.kapasite_asimi(isler, edd))
        bilgi = {i.id: (ie_, t_, p_) for i, ie_, t_, p_ in liste}
        isler_cikti = []
        for y in c.yerlesimler:
            ie, tahmin, plan_ = bilgi[y.is_id]
            geciken = y.gecikme_dk > 0 or y.is_id in c.sigmayan
            toplam_geciken += geciken
            toplam_asim += y.is_id in asim
            isler_cikti.append(
                {
                    "is_emri_id": ie.id,
                    "kod": ie.kod,
                    "baslik": ie.baslik,
                    "durum": ie.durum,
                    "oncelik": ie.oncelik,
                    "hedef_tarih": ie.hedef_tarih,
                    "sure_dk": tahmin.dakika,
                    "sure_kaynagi": tahmin.kaynak,
                    "elle_sira": plan_.elle_sira if plan_ else None,
                    "baslangic": y.baslangic,
                    "bitis": y.bitis,
                    "parcalar": [{"baslangic": b, "bitis": e} for b, e in y.parcalar],
                    "gecikme_dk": round(y.gecikme_dk, 1),
                    "sigmadi": y.is_id in c.sigmayan,
                    "kapasite_asimi": y.is_id in asim,
                    "sira_kaynakli_gecikme": geciken and y.is_id not in asim,
                }
            )
        yuk = cizelge.gunluk_yuk(c, pencereler, tz)
        sonuc.append(
            {
                **makineler[mid],
                "isler": isler_cikti,
                "gunluk_yuk": [
                    {"gun": g, "plan_dk": p, "kapasite_dk": k} for g, (p, k) in yuk.items()
                ],
            }
        )
    return {
        "baslangic": baslangic.astimezone(UTC),
        "bitis": datetime.combine(ilk_gun + timedelta(days=gun_sayisi), time(0), tz).astimezone(
            UTC
        ),
        "varsayilan_vardiya": varsayilan_vardiya,
        "pencereler": [{"baslangic": p.baslangic, "bitis": p.bitis} for p in pencereler],
        "makineler": sonuc,
        "ozet": {
            "is_sayisi": sum(len(m["isler"]) for m in sonuc),
            "geciken": toplam_geciken,
            "kapasite_asimi": toplam_asim,
            "varsayilan_sure": sum(
                1 for m in sonuc for i in m["isler"] if i["sure_kaynagi"] == "varsayilan"
            ),
        },
    }
