"""Enerji veri erişimi (repository) — ham liste + continuous aggregate trend sorgusu.

Trend, ``enerji_tuketim_saatlik`` CAGG'inden okur. Real-time aggregation açık
(``materialized_only = false``) → materialize edilmemiş son veri de dahil olur.
``aralik`` beyaz-liste (``saat``/``gun``) → SQL enjeksiyonu yok; ``gun`` CAGG üstünde
``time_bucket('1 day', kova)`` ile toplulaştırır.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import TIMESTAMP, BigInteger, String, bindparam, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sorgu import siralama_uygula
from app.modules.enerji.models import EnerjiTuketim

_OLCUM_SIRALAMA = {
    "id": EnerjiTuketim.id,
    "zaman": EnerjiTuketim.zaman,
    "tuketim": EnerjiTuketim.tuketim,
    "enerji_turu": EnerjiTuketim.enerji_turu,
}


async def olcum_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    makine_id: int | None = None,
    enerji_turu: str | None = None,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[EnerjiTuketim], int]:
    filtreler: list[Any] = []
    if makine_id is not None:
        filtreler.append(EnerjiTuketim.makine_id == makine_id)
    if enerji_turu is not None:
        filtreler.append(EnerjiTuketim.enerji_turu == enerji_turu)
    if baslangic is not None:
        filtreler.append(EnerjiTuketim.zaman >= baslangic)
    if bitis is not None:
        filtreler.append(EnerjiTuketim.zaman <= bitis)

    kosul = select(EnerjiTuketim)
    sayim = select(func.count()).select_from(EnerjiTuketim)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul,
        siralama=siralama,
        yon=yon,
        izinli=_OLCUM_SIRALAMA,
        varsayilan=EnerjiTuketim.zaman,
        varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)


async def trend(
    db: AsyncSession,
    *,
    makine_id: int | None = None,
    enerji_turu: str | None = None,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    aralik: str = "saat",
) -> list[dict[str, Any]]:
    # aralik beyaz-liste (server-side) → f-string güvenli.
    zaman_ifade = "time_bucket(INTERVAL '1 day', kova)" if aralik == "gun" else "kova"
    # asyncpg, NULL parametre için tür çıkarımı yapamaz → bindparam ile explicit tür belirt.
    sql = text(
        f"""
        SELECT {zaman_ifade} AS zaman,
               sum(toplam_tuketim) AS toplam,
               sum(olcum_adedi) AS adet
        FROM enerji_tuketim_saatlik
        WHERE (:makine_id IS NULL OR makine_id = :makine_id)
          AND (:enerji_turu IS NULL OR enerji_turu = :enerji_turu)
          AND (:baslangic IS NULL OR kova >= :baslangic)
          AND (:bitis IS NULL OR kova < :bitis)
        GROUP BY 1
        ORDER BY 1
        """
    ).bindparams(
        bindparam("makine_id", type_=BigInteger()),
        bindparam("enerji_turu", type_=String()),
        bindparam("baslangic", type_=TIMESTAMP(timezone=True)),
        bindparam("bitis", type_=TIMESTAMP(timezone=True)),
    )
    sonuc = await db.execute(
        sql,
        {
            "makine_id": makine_id,
            "enerji_turu": enerji_turu,
            "baslangic": baslangic,
            "bitis": bitis,
        },
    )
    return [
        {"zaman": r.zaman, "toplam": float(r.toplam or 0), "adet": int(r.adet or 0)} for r in sonuc
    ]
