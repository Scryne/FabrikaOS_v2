"""S26-B İSG servisleri (ADR-0044): eğitim matrisi, KKD eksikleri, tatbikat, kaza → CAPA.

**KKD eksikleri zimmetten okunur.** KKD teslimi ayrı bir kayıt değil, ``kategori='kkd'`` zimmettir
(S11 zimmet yeniden kullanılır): iade edilince eksik listesine geri düşer. Eşleme ad üzerinden,
büyük/küçük harf ve baştaki/sondaki boşluk duyarsızdır.

**Kaza başına tek CAPA.** ``uygunsuzluklar.kaynak_kaza_id`` UNIQUE; ikinci istek 409
``CAPA_ZATEN_VAR`` ve mevcut vakanın kimliğini döner. Önem kaza ağırlığından türetilir.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import denetim_yaz
from app.core.exceptions import CakismaHatasi
from app.core.olaylar import olay_yayinla
from app.core.zaman import is_gunu
from app.kimlik.models import Kullanici
from app.modules.ik.models import Personel, Zimmet
from app.modules.isg.egitim_matrisi import Katilim, matris
from app.modules.isg.models import (
    EgitimGereksinimi,
    EgitimKatilimi,
    IsgEgitimi,
    IsKazasi,
    KkdGereksinimi,
)
from app.modules.kalite import service as kalite_service
from app.modules.kalite.models import Uygunsuzluk

TATBIKAT_TURLERI: frozenset[str] = frozenset(
    {"yangin", "deprem", "tahliye", "kimyasal", "ilk_yardim", "diger"}
)
AGIRLIK_ONEM: dict[str, str] = {
    "hafif": "orta",
    "orta": "yuksek",
    "agir": "kritik",
    "olumcul": "kritik",
}


def yillik_kod(onek: str, kimlik: int) -> str:
    return f"{onek}-{datetime.now(UTC).year}-{kimlik:05d}"


def _norm(s: str) -> str:
    return " ".join(s.split()).casefold()


async def gereksinim_haritasi(db: AsyncSession, model: Any, alan: str) -> dict[str, frozenset[str]]:
    harita: dict[str, set[str]] = defaultdict(set)
    g: Any
    for g in (await db.execute(select(model))).scalars():
        harita[g.departman].add(getattr(g, alan))
    return {d: frozenset(v) for d, v in harita.items()}


async def egitim_matrisi(
    db: AsyncSession, *, departman: str | None, bugun: date | None = None
) -> dict[str, Any]:
    bugun = bugun or is_gunu()
    sorgu = select(Personel).where(Personel.aktif.is_(True)).order_by(Personel.ad, Personel.soyad)
    if departman:
        sorgu = sorgu.where(Personel.departman == departman)
    kisiler = (await db.execute(sorgu)).scalars().all()
    ids = [p.id for p in kisiler]
    satirlar = (
        await db.execute(
            select(
                EgitimKatilimi.personel_id,
                IsgEgitimi.konu,
                IsgEgitimi.tarih,
                IsgEgitimi.gecerlilik_ay,
            )
            .join(IsgEgitimi, IsgEgitimi.id == EgitimKatilimi.egitim_id)
            .where(EgitimKatilimi.personel_id.in_(ids))
        )
        if ids
        else None
    )
    katilimlar = [Katilim(*r) for r in satirlar.all()] if satirlar is not None else []
    gereksinim = await gereksinim_haritasi(db, EgitimGereksinimi, "konu")
    sutunlar, hucreler = matris(
        [(p.id, p.departman) for p in kisiler], katilimlar, gereksinim, bugun=bugun
    )
    ozet: dict[str, int] = defaultdict(int)
    personeller = []
    for p in kisiler:
        h = hucreler[p.id]
        for c in h.values():
            ozet[c.durum] += 1
        personeller.append(
            {
                "personel_id": p.id,
                "ad_soyad": f"{p.ad} {p.soyad}",
                "departman": p.departman,
                "hucreler": {
                    k: {
                        "durum": c.durum,
                        "son_tarih": c.son_tarih,
                        "gecerlilik_sonu": c.gecerlilik_sonu,
                    }
                    for k, c in h.items()
                },
            }
        )
    return {"konular": sutunlar, "personeller": personeller, "ozet": dict(ozet)}


async def kkd_eksikleri(db: AsyncSession, *, departman: str | None) -> list[dict[str, Any]]:
    gereksinim = await gereksinim_haritasi(db, KkdGereksinimi, "kkd")
    genel = gereksinim.get("", frozenset())
    sorgu = select(Personel).where(Personel.aktif.is_(True)).order_by(Personel.ad, Personel.soyad)
    if departman:
        sorgu = sorgu.where(Personel.departman == departman)
    kisiler = (await db.execute(sorgu)).scalars().all()
    teslim: dict[int, set[str]] = defaultdict(set)
    for pid, ad in await db.execute(
        select(Zimmet.personel_id, Zimmet.demirbas).where(
            Zimmet.kategori == "kkd", Zimmet.durum == "zimmetli"
        )
    ):
        teslim[pid].add(_norm(ad))
    sonuc = []
    for p in kisiler:
        gerekli = sorted(genel | gereksinim.get(p.departman, frozenset()))
        if not gerekli:
            continue
        eksik = [k for k in gerekli if _norm(k) not in teslim[p.id]]
        sonuc.append(
            {
                "personel_id": p.id,
                "ad_soyad": f"{p.ad} {p.soyad}",
                "departman": p.departman,
                "gerekli": gerekli,
                "eksik": eksik,
            }
        )
    return sonuc


class CapaZatenVar(CakismaHatasi):
    hata_kodu = "CAPA_ZATEN_VAR"


async def kaza_capa(db: AsyncSession, kaza_id: int) -> Uygunsuzluk | None:
    return await db.scalar(select(Uygunsuzluk).where(Uygunsuzluk.kaynak_kaza_id == kaza_id))


async def kazadan_capa_ac(
    db: AsyncSession, kaza: IsKazasi, kullanici: Kullanici, sorumlu_kullanici_id: int | None
) -> Uygunsuzluk:
    mevcut = await kaza_capa(db, kaza.id)
    if mevcut is not None:
        raise CapaZatenVar(
            f"Bu kaza için CAPA vakası zaten açık: {mevcut.kod}",
            detaylar=[{"alan": "uygunsuzluk_id", "mesaj": str(mevcut.id)}],
        )
    tur = {"kaza": "İş kazası", "ramak_kala": "Ramak kala", "meslek_hastaligi": "Meslek hastalığı"}
    baslik = f"{tur.get(kaza.tur, 'İSG olayı')}: {kaza.kod}"
    if kaza.yer:
        baslik += f" — {kaza.yer}"
    u = Uygunsuzluk(
        kod=kalite_service.uygunsuzluk_gecici_kod(),
        baslik=baslik[:200],
        aciklama=kaza.aciklama[:2000],
        onem=AGIRLIK_ONEM.get(kaza.agirlik, "orta"),
        makine_id=kaza.makine_id,
        kaynak_kaza_id=kaza.id,
        sorumlu_kullanici_id=sorumlu_kullanici_id,
        acan_kullanici_id=kullanici.id,
    )
    db.add(u)
    await db.flush()
    u.kod = kalite_service.uygunsuzluk_kalici_kod(u.id)
    await db.flush()
    await denetim_yaz(
        db,
        eylem="olustur",
        kaynak="uygunsuzluk",
        kaynak_id=str(u.id),
        kullanici=kullanici,
        detay={"kaynak_kaza_id": kaza.id},
    )
    await olay_yayinla(
        db,
        olay_turu="kalite.uygunsuzluk",
        govde={
            "uygunsuzluk_id": u.id,
            "kod": u.kod,
            "baslik": u.baslik,
            "onem": u.onem,
            "durum": u.durum,
            "kaynak_kaza_id": kaza.id,
        },
    )
    return u
