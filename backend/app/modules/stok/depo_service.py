"""S25-A depo/lokasyon iş kuralları: lokasyon bakiyesi, transfer, sayım (ADR-0024).

Kilit sırası (deadlock'a karşı, ADR-0024 §2): önce **malzeme** satırı (``malzeme_getir_kilitli``,
çağıran alır), sonra bakiye satırları **(malzeme_id, lokasyon_id, lot_no) artan sırada**.
Transferin yönü ne olursa olsun aynı sıra kullanıldığı için döngüsel bekleme oluşmaz.

Negatif bakiye katı biçimde engellenir (ADR-0024 §5): transfer, sayım düzeltmesi ve lokasyonlu
çıkış dahil. ``Malzeme.mevcut_miktar`` her hareketle lokasyon bakiyelerinin toplamı olarak
güncellenir (geriye uyumluluk).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, YetkiHatasi
from app.kimlik.models import Kullanici
from app.modules.stok.models import (
    Depo,
    Lokasyon,
    Malzeme,
    SayimOturumu,
    SayimSatiri,
    StokBakiyesi,
    StokHareketi,
)

VARSAYILAN_DEPO = "ANA"
VARSAYILAN_LOKASYON = "GENEL"

SAYIM_GECISLER: dict[str, set[str]] = {
    "acik": {"onay_bekliyor", "iptal"},
    "onay_bekliyor": {"onaylandi", "acik", "iptal"},
    "onaylandi": set(),
    "iptal": set(),
}


async def varsayilan_lokasyon_id(db: AsyncSession) -> int:
    lok_id = (
        await db.execute(
            select(Lokasyon.id)
            .join(Depo, Depo.id == Lokasyon.depo_id)
            .where(Depo.kod == VARSAYILAN_DEPO, Lokasyon.kod == VARSAYILAN_LOKASYON)
        )
    ).scalar_one_or_none()
    if lok_id is None:  # pragma: no cover — migration her şemaya açar
        raise CakismaHatasi("Varsayılan lokasyon (ANA/GENEL) bulunamadı.")
    return int(lok_id)


async def lokasyon_getir(db: AsyncSession, lokasyon_id: int) -> Lokasyon:
    lok = await db.get(Lokasyon, lokasyon_id)
    if lok is None or not lok.aktif:
        raise DogrulamaHatasi(
            "Lokasyon bulunamadı ya da pasif",
            detaylar=[{"alan": "lokasyon_id", "mesaj": str(lokasyon_id)}],
        )
    return lok


async def bakiye_kilitle(
    db: AsyncSession, malzeme_id: int, lokasyon_id: int, lot_no: str
) -> StokBakiyesi:
    """Bakiye satırını (yoksa sıfırla açıp) ``FOR UPDATE`` ile kilitli döndürür."""
    await db.execute(
        insert(StokBakiyesi)
        .values(malzeme_id=malzeme_id, lokasyon_id=lokasyon_id, lot_no=lot_no, miktar=0)
        .on_conflict_do_nothing(constraint="uq_stok_bakiyeleri_malzeme_id")
    )
    return (
        await db.execute(
            select(StokBakiyesi)
            .where(
                StokBakiyesi.malzeme_id == malzeme_id,
                StokBakiyesi.lokasyon_id == lokasyon_id,
                StokBakiyesi.lot_no == lot_no,
            )
            .with_for_update()
        )
    ).scalar_one()


def _lokasyon_yetersiz(bakiye: Decimal, istenen: Decimal) -> DogrulamaHatasi:
    return DogrulamaHatasi(
        "Lokasyonda yetersiz stok",
        detaylar=[{"alan": "miktar", "mesaj": f"Lokasyon bakiyesi {bakiye}, istenen {istenen}"}],
    )


async def lokasyon_bakiyesine_uygula(
    db: AsyncSession,
    malzeme: Malzeme,
    *,
    lokasyon_id: int | None,
    lot_no: str,
    delta: Decimal,
) -> int:
    """``stok_hareketi_uygula`` tarafından çağrılır: toplam değişimi lokasyona yansıtır."""
    lok_id = lokasyon_id if lokasyon_id is not None else await varsayilan_lokasyon_id(db)
    if lokasyon_id is not None:
        await lokasyon_getir(db, lok_id)
    bakiye = await bakiye_kilitle(db, malzeme.id, lok_id, lot_no)
    yeni = bakiye.miktar + delta
    if yeni < 0:
        raise _lokasyon_yetersiz(bakiye.miktar, -delta)
    bakiye.miktar = yeni
    return lok_id


async def transfer_uygula(
    db: AsyncSession,
    malzeme: Malzeme,
    *,
    kaynak_lokasyon_id: int,
    hedef_lokasyon_id: int,
    miktar: Decimal,
    lot_no: str,
    aciklama: str,
    kullanici: Kullanici,
    idempotency_anahtari: str | None,
) -> tuple[StokHareketi, StokHareketi]:
    """İki bacaklı transfer, tek transaction (çağıran commit eder). Toplam bakiye değişmez."""
    if kaynak_lokasyon_id == hedef_lokasyon_id:
        raise DogrulamaHatasi("Kaynak ve hedef lokasyon aynı olamaz")
    if miktar <= 0:
        raise DogrulamaHatasi("Transfer miktarı pozitif olmalı")
    await lokasyon_getir(db, kaynak_lokasyon_id)
    await lokasyon_getir(db, hedef_lokasyon_id)

    # Deterministik kilit sırası: (malzeme_id, lokasyon_id, lot_no) artan.
    anahtarlar = sorted(
        [(malzeme.id, kaynak_lokasyon_id, lot_no), (malzeme.id, hedef_lokasyon_id, lot_no)]
    )
    kilitli = {k[1]: await bakiye_kilitle(db, *k) for k in anahtarlar}
    kaynak, hedef = kilitli[kaynak_lokasyon_id], kilitli[hedef_lokasyon_id]
    if kaynak.miktar < miktar:
        raise _lokasyon_yetersiz(kaynak.miktar, miktar)
    kaynak.miktar -= miktar
    hedef.miktar += miktar

    grup = str(uuid.uuid4())
    ortak = {
        "malzeme_id": malzeme.id,
        "miktar": miktar,
        "bakiye_sonrasi": malzeme.mevcut_miktar,  # toplam değişmez
        "aciklama": aciklama,
        "kaynak": "transfer",
        "olusturan_kullanici_id": kullanici.id,
        "lot_no": lot_no,
        "transfer_grubu": grup,
    }
    cikis = StokHareketi(
        tur="transfer_cikis",
        lokasyon_id=kaynak_lokasyon_id,
        idempotency_anahtari=idempotency_anahtari,
        **ortak,
    )
    giris = StokHareketi(tur="transfer_giris", lokasyon_id=hedef_lokasyon_id, **ortak)
    db.add_all([cikis, giris])
    await db.flush()
    return cikis, giris


# ── Sayım ────────────────────────────────────────────────────────────────────


def sayim_gecici_kod() -> str:
    return f"GECICI-{uuid.uuid4().hex[:30]}"


def sayim_kalici_kod(oturum_id: int) -> str:
    return f"SAY-{datetime.now(UTC).year}-{oturum_id:06d}"


def sayim_gecisi(oturum: SayimOturumu, hedef: str) -> None:
    if hedef not in SAYIM_GECISLER:
        raise DogrulamaHatasi(f"Geçersiz sayım durumu: {hedef}")
    if hedef not in SAYIM_GECISLER[oturum.durum]:
        raise CakismaHatasi(f"Sayım '{oturum.durum}' durumundan '{hedef}' durumuna geçemez")
    oturum.durum = hedef


async def sayim_satiri_yaz(
    db: AsyncSession,
    oturum: SayimOturumu,
    malzeme: Malzeme,
    *,
    lot_no: str,
    sayilan_miktar: Decimal,
) -> SayimSatiri:
    """Satır ilk açıldığında sistem miktarını anlık görüntüler; sonraki yazımlar yalnız
    sayılan miktarı günceller (anlık görüntü değişmez — delta onun üzerinden hesaplanır)."""
    if oturum.durum != "acik":
        raise CakismaHatasi("Yalnız açık sayıma satır yazılır")
    if sayilan_miktar < 0:
        raise DogrulamaHatasi("Sayılan miktar negatif olamaz")
    satir = (
        await db.execute(
            select(SayimSatiri).where(
                SayimSatiri.oturum_id == oturum.id,
                SayimSatiri.malzeme_id == malzeme.id,
                SayimSatiri.lot_no == lot_no,
            )
        )
    ).scalar_one_or_none()
    if satir is None:
        sistem = (
            await db.execute(
                select(StokBakiyesi.miktar).where(
                    StokBakiyesi.malzeme_id == malzeme.id,
                    StokBakiyesi.lokasyon_id == oturum.lokasyon_id,
                    StokBakiyesi.lot_no == lot_no,
                )
            )
        ).scalar_one_or_none()
        satir = SayimSatiri(
            oturum_id=oturum.id,
            malzeme_id=malzeme.id,
            lot_no=lot_no,
            sistem_miktari=sistem if sistem is not None else Decimal(0),
            sayilan_miktar=sayilan_miktar,
        )
        db.add(satir)
    else:
        satir.sayilan_miktar = sayilan_miktar
    await db.flush()
    return satir


async def sayim_onayla(
    db: AsyncSession, oturum: SayimOturumu, *, onaylayan: Kullanici
) -> list[StokHareketi]:
    """Farkları DELTA olarak uygular (ADR-0024 §1). Sayanla onaylayan aynı kişi olamaz."""
    if oturum.olusturan_kullanici_id is not None and oturum.olusturan_kullanici_id == onaylayan.id:
        raise YetkiHatasi("Sayımı açan kullanıcı kendi sayımını onaylayamaz (görev ayrımı)")
    sayim_gecisi(oturum, "onaylandi")
    satirlar = list(
        (
            await db.execute(
                select(SayimSatiri)
                .where(SayimSatiri.oturum_id == oturum.id)
                .order_by(SayimSatiri.malzeme_id, SayimSatiri.lot_no)
            )
        ).scalars()
    )
    hareketler: list[StokHareketi] = []
    for satir in satirlar:
        fark = satir.fark
        if fark == 0:
            continue
        malzeme = (
            await db.execute(
                select(Malzeme).where(Malzeme.id == satir.malzeme_id).with_for_update()
            )
        ).scalar_one()
        bakiye = await bakiye_kilitle(db, satir.malzeme_id, oturum.lokasyon_id, satir.lot_no)
        yeni_lok = bakiye.miktar + fark
        if yeni_lok < 0:
            raise _lokasyon_yetersiz(bakiye.miktar, -fark)
        bakiye.miktar = yeni_lok
        malzeme.mevcut_miktar = malzeme.mevcut_miktar + fark
        hareket = StokHareketi(
            malzeme_id=satir.malzeme_id,
            tur="sayim_duzeltme",
            miktar=fark,
            bakiye_sonrasi=malzeme.mevcut_miktar,
            aciklama=(
                f"Sayım {oturum.kod}: sistem {satir.sistem_miktari}, sayılan {satir.sayilan_miktar}"
            ),
            kaynak=oturum.kod[:50],
            olusturan_kullanici_id=onaylayan.id,
            idempotency_anahtari=f"sayim-{satir.id}",
            lokasyon_id=oturum.lokasyon_id,
            lot_no=satir.lot_no,
        )
        db.add(hareket)
        await db.flush()
        satir.uygulanan_hareket_id = hareket.id
        hareketler.append(hareket)
    oturum.onaylayan_kullanici_id = onaylayan.id
    oturum.onay_tarihi = datetime.now(UTC)
    await db.flush()
    return hareketler
