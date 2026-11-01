"""Satış servisi (S31, ADR-0050): sipariş, MRP girdileri, onay → iş emri + satınalma tetiği.

Tetik zinciri **idempotent**: her tetik ``MrpTetigi.kaynak`` tekil anahtarıyla yazılır
(``ie:<kalem_id>``, ``st:<siparis_id>``). Aynı sipariş için tetik ikinci kez çalışırsa (yeniden
deneme, eşzamanlı iki onay isteği) var olan tetik bulunur, yeni iş emri/talep açılmaz.
Sipariş satırı
``FOR UPDATE`` ile kilitlenir; iki eşzamanlı onaydan biri 409 alır. Olay (outbox) yalnız yeni tetik
oluştuğunda yayınlanır (kenar-tetikli).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi, YetkiHatasi
from app.core.olaylar import olay_yayinla
from app.core.zaman import is_saat_dilimi
from app.kimlik.models import Kullanici
from app.modules.crm.models import Firma
from app.modules.isemri import service as isemri_service
from app.modules.isemri.durum import ILK_DURUM as IE_ILK_DURUM
from app.modules.isemri.models import IsEmri
from app.modules.satis import durum, mrp
from app.modules.satis.models import MrpTetigi, SatisSiparisi, SatisSiparisiKalemi
from app.modules.stok import service as stok_service
from app.modules.stok.models import (
    Malzeme,
    SatinalmaSiparisi,
    SatinalmaSiparisiKalemi,
    SatinalmaTalebi,
    SatinalmaTalebiKalemi,
)
from app.modules.talep.models import Talep
from app.modules.uretim.models import Makine
from app.modules.urun.models import Recete, ReceteKalemi, Urun

OLAY_ONAYLANDI = "satis.siparis_onaylandi"
OLAY_MRP = "mrp.tetiklendi"

# Siparişe dönmemiş, hâlâ gelebilecek talepler (reddedilen/iptal olan gelmez).
_ACIK_TALEP = ("taslak", "onay_bekliyor", "onaylandi")
_ACIK_SATINALMA_SIPARISI = ("acik", "kismi_teslim")
_ACIK_IS_EMRI = ("acik", "atandi", "devam_ediyor")


def gecici_kod() -> str:
    return f"GECICI-{uuid.uuid4().hex}"


def kalici_kod(s: SatisSiparisi) -> str:
    return f"SP-{datetime.now(UTC).year}-{s.id:06d}"


@dataclass(frozen=True)
class KalemGirdisi:
    urun_id: int
    miktar: Decimal
    birim_fiyat: Decimal | None = None


async def firma_dogrula(db: AsyncSession, firma_id: int) -> Firma:
    firma = await db.get(Firma, firma_id)
    if firma is None:
        raise KaynakBulunamadi("Firma bulunamadı")
    if firma.tip not in ("musteri", "her_ikisi"):
        raise DogrulamaHatasi(
            "Satış siparişi yalnız müşteri firmaya açılır",
            detaylar=[{"alan": "firma_id", "mesaj": f"firma tipi: {firma.tip}"}],
        )
    return firma


async def makine_dogrula(db: AsyncSession, makine_id: int | None) -> None:
    if makine_id is not None and await db.get(Makine, makine_id) is None:
        raise KaynakBulunamadi("Makine bulunamadı")


async def urunleri_dogrula(db: AsyncSession, kalemler: list[KalemGirdisi]) -> None:
    if not kalemler:
        raise DogrulamaHatasi("Sipariş en az bir kalem içermeli")
    ids = {k.urun_id for k in kalemler}
    var = set((await db.execute(select(Urun.id).where(Urun.id.in_(ids)))).scalars())
    eksik = sorted(ids - var)
    if eksik:
        raise KaynakBulunamadi(f"Ürün bulunamadı: {', '.join(map(str, eksik))}")


async def talep_dogrula(db: AsyncSession, talep_id: int, firma_id: int) -> Talep:
    talep = await db.get(Talep, talep_id)
    if talep is None:
        raise KaynakBulunamadi("Talep bulunamadı")
    if talep.firma_id is not None and talep.firma_id != firma_id:
        raise DogrulamaHatasi(
            "Talep başka bir firmaya ait",
            detaylar=[{"alan": "talep_id", "mesaj": "talebin firması siparişinkiyle aynı olmalı"}],
        )
    mevcut = await db.scalar(select(SatisSiparisi.id).where(SatisSiparisi.talep_id == talep_id))
    if mevcut is not None:
        raise CakismaHatasi("Bu talep zaten bir siparişe dönüştürülmüş")
    return talep


def kalemleri_kur(s: SatisSiparisi, kalemler: list[KalemGirdisi]) -> None:
    s.kalemler = [
        SatisSiparisiKalemi(sira=i, urun_id=k.urun_id, miktar=k.miktar, birim_fiyat=k.birim_fiyat)
        for i, k in enumerate(kalemler, start=1)
    ]


def gecis_dogrula(s: SatisSiparisi, hedef: str) -> None:
    if hedef not in durum.DURUMLAR:
        raise DogrulamaHatasi("Geçersiz hedef durum", detaylar=[{"alan": "durum", "mesaj": hedef}])
    if not durum.gecis_gecerli_mi(s.durum, hedef):
        raise CakismaHatasi(f"Geçersiz durum geçişi: {s.durum} → {hedef}")


async def siparis_kilitle(db: AsyncSession, siparis_id: int) -> SatisSiparisi:
    s = await db.scalar(
        select(SatisSiparisi).where(SatisSiparisi.id == siparis_id).with_for_update()
    )
    if s is None:
        raise KaynakBulunamadi("Sipariş bulunamadı")
    return s


# --- MRP girdileri ----------------------------------------------------------------------------


async def _receteler(
    db: AsyncSession, urun_idler: set[int]
) -> dict[int, list[tuple[int, Decimal]]]:
    rows = (
        await db.execute(
            select(Recete.urun_id, ReceteKalemi.malzeme_id, ReceteKalemi.miktar)
            .join(ReceteKalemi, ReceteKalemi.recete_id == Recete.id)
            .where(Recete.urun_id.in_(urun_idler), Recete.aktif)
        )
    ).all()
    sonuc: dict[int, list[tuple[int, Decimal]]] = {}
    for urun_id, malzeme_id, miktar in rows:
        sonuc.setdefault(urun_id, []).append((malzeme_id, Decimal(miktar)))
    return sonuc


async def _eldeki(db: AsyncSession, malzemeler: set[int]) -> dict[int, Decimal]:
    rows = (
        await db.execute(
            select(Malzeme.id, Malzeme.mevcut_miktar).where(Malzeme.id.in_(malzemeler))
        )
    ).all()
    return {m: Decimal(q or 0) for m, q in rows}


def _kendi_tetikleri(siparis_id: int, tur: str) -> Any:
    """Siparişin kendi açtığı iş emirleri/talepler. Kendi ihtiyacına "ayrılmış" ya da "gelecek
    tedarik" sayılırsa onaydan sonraki hesap ihtiyacı iki kez düşer."""
    return select(MrpTetigi.hedef_id).where(
        MrpTetigi.siparis_id == siparis_id, MrpTetigi.tur == tur
    )


async def _acik_tedarik(
    db: AsyncSession, malzemeler: set[int], siparis_id: int
) -> dict[int, Decimal]:
    """Siparişe dönmemiş açık talepler + açık satınalma siparişlerinin teslim alınmamış kısmı."""
    sonuc: dict[int, Decimal] = {}
    siparise_donmus = select(SatinalmaSiparisi.talep_id).where(
        SatinalmaSiparisi.talep_id.is_not(None)
    )
    talep_rows = (
        await db.execute(
            select(SatinalmaTalebiKalemi.malzeme_id, func.sum(SatinalmaTalebiKalemi.miktar))
            .join(SatinalmaTalebi, SatinalmaTalebi.id == SatinalmaTalebiKalemi.talep_id)
            .where(
                SatinalmaTalebiKalemi.malzeme_id.in_(malzemeler),
                SatinalmaTalebi.durum.in_(_ACIK_TALEP),
                SatinalmaTalebi.id.not_in(siparise_donmus),
                SatinalmaTalebi.id.not_in(_kendi_tetikleri(siparis_id, "satinalma_talebi")),
            )
            .group_by(SatinalmaTalebiKalemi.malzeme_id)
        )
    ).all()
    for m, q in talep_rows:
        sonuc[m] = sonuc.get(m, Decimal(0)) + Decimal(q or 0)
    siparis_rows = (
        await db.execute(
            select(
                SatinalmaSiparisiKalemi.malzeme_id,
                func.sum(
                    SatinalmaSiparisiKalemi.miktar - SatinalmaSiparisiKalemi.teslim_alinan_miktar
                ),
            )
            .join(SatinalmaSiparisi, SatinalmaSiparisi.id == SatinalmaSiparisiKalemi.siparis_id)
            .where(
                SatinalmaSiparisiKalemi.malzeme_id.in_(malzemeler),
                SatinalmaSiparisi.durum.in_(_ACIK_SATINALMA_SIPARISI),
            )
            .group_by(SatinalmaSiparisiKalemi.malzeme_id)
        )
    ).all()
    for m, q in siparis_rows:
        kalan = max(Decimal(q or 0), Decimal(0))
        sonuc[m] = sonuc.get(m, Decimal(0)) + kalan
    return sonuc


async def _ayrilmis(db: AsyncSession, malzemeler: set[int], siparis_id: int) -> dict[int, Decimal]:
    """Açık iş emirlerinin henüz stoktan düşülmemiş reçete tüketimi (kapanışta düşer, S24)."""
    rows = (
        await db.execute(
            select(ReceteKalemi.malzeme_id, func.sum(IsEmri.miktar * ReceteKalemi.miktar))
            .join(Recete, Recete.id == ReceteKalemi.recete_id)
            .join(IsEmri, IsEmri.urun_id == Recete.urun_id)
            .where(
                ReceteKalemi.malzeme_id.in_(malzemeler),
                Recete.aktif,
                IsEmri.durum.in_(_ACIK_IS_EMRI),
                IsEmri.miktar.is_not(None),
                IsEmri.id.not_in(_kendi_tetikleri(siparis_id, "is_emri")),
            )
            .group_by(ReceteKalemi.malzeme_id)
        )
    ).all()
    return {m: Decimal(q or 0) for m, q in rows}


async def mrp_hesapla(db: AsyncSession, s: SatisSiparisi) -> mrp.MrpSonucu:
    kalemler = [mrp.Kalem(k.urun_id, Decimal(k.miktar)) for k in s.kalemler]
    receteler = await _receteler(db, {k.urun_id for k in kalemler})
    brut, _ = mrp.brut_ihtiyac(kalemler, receteler)
    m = set(brut)
    if not m:
        return mrp.hesapla(kalemler, receteler, {}, {}, {})
    return mrp.hesapla(
        kalemler,
        receteler,
        await _eldeki(db, m),
        await _acik_tedarik(db, m, s.id),
        await _ayrilmis(db, m, s.id),
    )


async def malzeme_bilgisi(db: AsyncSession, idler: set[int]) -> dict[int, Malzeme]:
    if not idler:
        return {}
    return {
        m.id: m for m in (await db.execute(select(Malzeme).where(Malzeme.id.in_(idler)))).scalars()
    }


# --- Onay ve tetik ----------------------------------------------------------------------------


@dataclass
class TetikSonucu:
    is_emirleri: list[IsEmri]
    satinalma_talebi: SatinalmaTalebi | None
    yeni: int  # bu çağrıda oluşan tetik sayısı (0 → hepsi zaten vardı)


async def _tetik(db: AsyncSession, kaynak: str) -> MrpTetigi | None:
    return await db.scalar(select(MrpTetigi).where(MrpTetigi.kaynak == kaynak))


async def mrp_tetikle(
    db: AsyncSession, s: SatisSiparisi, kullanici: Kullanici, makine_id: int
) -> TetikSonucu:
    """Kalem başına üretim iş emri + eksik malzemeler için tek satınalma talebi (idempotent)."""
    yeni = 0
    urunler = {
        u.id: u
        for u in (
            await db.execute(select(Urun).where(Urun.id.in_({k.urun_id for k in s.kalemler})))
        ).scalars()
    }
    teslim = datetime.combine(s.teslim_tarihi, time(17, 0), is_saat_dilimi())
    is_emirleri: list[IsEmri] = []
    for k in s.kalemler:
        kaynak = f"ie:{k.id}"
        var = await _tetik(db, kaynak)
        if var is not None:
            ie = await db.get(IsEmri, var.hedef_id)
            if ie is not None:
                is_emirleri.append(ie)
            continue
        urun = urunler[k.urun_id]
        ie = IsEmri(
            kod=isemri_service.gecici_kod(),
            baslik=f"Sipariş {s.kod}: {urun.ad} × {k.miktar.normalize():f}",
            aciklama=f"Satış siparişi {s.kod}, kalem {k.sira}.",
            makine_id=makine_id,
            durum=IE_ILK_DURUM,
            oncelik="yuksek",
            hedef_tarih=teslim,
            urun_id=k.urun_id,
            miktar=k.miktar,
            lot_no=f"{s.kod}-{k.sira}",
        )
        db.add(ie)
        await db.flush()
        ie.kod = isemri_service.kalici_kod(ie.id)
        db.add(MrpTetigi(siparis_id=s.id, kaynak=kaynak, tur="is_emri", hedef_id=ie.id))
        await db.flush()
        is_emirleri.append(ie)
        yeni += 1

    talep: SatinalmaTalebi | None = None
    kaynak = f"st:{s.id}"
    var = await _tetik(db, kaynak)
    if var is not None:
        talep = await db.get(SatinalmaTalebi, var.hedef_id)
    else:
        sonuc = await mrp_hesapla(db, s)
        eksikler = sonuc.eksikler
        if eksikler:
            malzemeler = await malzeme_bilgisi(db, {e.malzeme_id for e in eksikler})
            talep = SatinalmaTalebi(
                kod=stok_service.talep_gecici_kod(),
                baslik=f"MRP: {s.kod} için eksik malzeme",
                aciklama=(
                    f"Satış siparişi {s.kod} onayında MRP'nin açtığı talep. Net ihtiyaç = brüt − "
                    "(stok + açık tedarik − açık iş emri tüketimi)."
                ),
                para_birimi=s.para_birimi,
                # Talebi açan siparişi onaylayan kişidir: satınalma onayı başka biri olmalı (S9).
                talep_eden_kullanici_id=kullanici.id,
                durum="onay_bekliyor",
                kalemler=[
                    SatinalmaTalebiKalemi(
                        malzeme_id=e.malzeme_id,
                        miktar=e.net,
                        birim=malzemeler[e.malzeme_id].birim,
                        aciklama=f"brüt {e.brut:f}, kullanılabilir {e.kullanilabilir:f}",
                    )
                    for e in eksikler
                ],
            )
            db.add(talep)
            await db.flush()
            talep.kod = stok_service.talep_kalici_kod(talep.id)
            db.add(
                MrpTetigi(siparis_id=s.id, kaynak=kaynak, tur="satinalma_talebi", hedef_id=talep.id)
            )
            await db.flush()
            yeni += 1
    return TetikSonucu(is_emirleri=is_emirleri, satinalma_talebi=talep, yeni=yeni)


async def siparis_onayla(
    db: AsyncSession, siparis_id: int, kullanici: Kullanici, makine_id: int | None
) -> tuple[SatisSiparisi, TetikSonucu]:
    s = await siparis_kilitle(db, siparis_id)
    gecis_dogrula(s, "onaylandi")
    if s.olusturan_kullanici_id == kullanici.id:
        raise YetkiHatasi("Kendi açtığınız siparişi onaylayamazsınız (görev ayrımı)")
    hat = makine_id or s.makine_id
    if hat is None:
        raise DogrulamaHatasi(
            "Üretim emirlerinin açılacağı makine seçilmeli",
            detaylar=[{"alan": "makine_id", "mesaj": "siparişte ya da onayda makine gerekli"}],
        )
    await makine_dogrula(db, hat)
    s.makine_id = hat
    sonuc = await mrp_hesapla(db, s)
    if sonuc.recetesiz:
        raise DogrulamaHatasi(
            "Reçetesi olmayan ürün MRP'den geçemez",
            detaylar=[{"alan": "kalemler", "mesaj": f"ürün id: {sonuc.recetesiz}"}],
        )
    s.durum = "onaylandi"
    s.onaylayan_kullanici_id = kullanici.id
    tetik = await mrp_tetikle(db, s, kullanici, hat)
    await olay_yayinla(
        db,
        olay_turu=OLAY_ONAYLANDI,
        govde={"id": s.id, "kod": s.kod, "firma_id": s.firma_id, "kaynak_tur": "satis_siparisi"},
    )
    if tetik.yeni:
        await olay_yayinla(db, olay_turu=OLAY_MRP, govde=tetik_govdesi(s, tetik))
    return s, tetik


def tetik_govdesi(s: SatisSiparisi, t: TetikSonucu) -> dict[str, Any]:
    return {
        "id": s.id,
        "kod": s.kod,
        "kaynak_tur": "satis_siparisi",
        "is_emirleri": [ie.kod for ie in t.is_emirleri],
        "satinalma_talebi": t.satinalma_talebi.kod if t.satinalma_talebi else None,
    }


async def tetikler(db: AsyncSession, siparis_id: int) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(MrpTetigi).where(MrpTetigi.siparis_id == siparis_id).order_by(MrpTetigi.id)
        )
    ).scalars()
    sonuc: list[dict[str, Any]] = []
    for t in rows:
        if t.tur == "is_emri":
            ie = await db.get(IsEmri, t.hedef_id)
            sonuc.append(
                {
                    "tur": t.tur,
                    "id": t.hedef_id,
                    "kod": ie.kod if ie else None,
                    "durum": ie.durum if ie else None,
                }
            )
        else:
            st = await db.get(SatinalmaTalebi, t.hedef_id)
            sonuc.append(
                {
                    "tur": t.tur,
                    "id": t.hedef_id,
                    "kod": st.kod if st else None,
                    "durum": st.durum if st else None,
                }
            )
    return sonuc
