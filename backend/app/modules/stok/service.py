"""Stok & Satınalma iş kuralları — bakiye güncelleme + kenar-tetikli kritik olay.

``stok_hareketi_uygula`` malzemeyi (çağıran ``FOR UPDATE`` ile kilitli getirir) günceller;
bakiye **kritik eşiğin üstünden altına ilk geçtiğinde** (kenar tetik) ``stok.kritik`` olayını
hareketi yazan iş ile **aynı transaction'da** outbox'a yazar (transactional outbox / ADR-0007).
``govde`` JSON-native olmalı → Decimal'ler ``float`` olarak verilir.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CakismaHatasi, DogrulamaHatasi
from app.core.olaylar import olay_yayinla
from app.kimlik.models import Kullanici
from app.modules.stok import talep_durum
from app.modules.stok.models import Malzeme, SatinalmaTalebi, StokHareketi

OLAY_KRITIK = "stok.kritik"


def _yeni_bakiye(eski: Decimal, *, tur: str, miktar: Decimal) -> Decimal:
    if tur == "giris":
        return eski + miktar
    if tur == "cikis":
        yeni = eski - miktar
        if yeni < 0:
            raise DogrulamaHatasi(
                "Yetersiz stok",
                detaylar=[{"alan": "miktar", "mesaj": f"Mevcut bakiye {eski}, çıkış {miktar}"}],
            )
        return yeni
    # duzeltme: mutlak sayım sonucu (miktar = yeni bakiye).
    return miktar


async def stok_hareketi_uygula(
    db: AsyncSession,
    malzeme: Malzeme,
    *,
    tur: str,
    miktar: Decimal,
    aciklama: str = "",
    kaynak: str | None = None,
    kullanici: Kullanici,
    idempotency_anahtari: str | None = None,
) -> tuple[StokHareketi, bool]:
    """Bakiyeyi günceller, hareketi yazar, gerekirse kenar-tetikli ``stok.kritik`` yayınlar."""
    eski = malzeme.mevcut_miktar
    yeni = _yeni_bakiye(eski, tur=tur, miktar=miktar)

    kritik = malzeme.kritik_stok
    ustteydi = kritik > 0 and eski > kritik
    simdi_altinda = kritik > 0 and yeni <= kritik
    kritige_dustu = ustteydi and simdi_altinda

    malzeme.mevcut_miktar = yeni
    hareket = StokHareketi(
        malzeme_id=malzeme.id,
        tur=tur,
        miktar=miktar,
        bakiye_sonrasi=yeni,
        aciklama=aciklama,
        kaynak=kaynak,
        olusturan_kullanici_id=kullanici.id,
        idempotency_anahtari=idempotency_anahtari,
    )
    db.add(hareket)

    if kritige_dustu:
        await olay_yayinla(
            db,
            olay_turu=OLAY_KRITIK,
            govde={
                "malzeme_id": malzeme.id,
                "kod": malzeme.kod,
                "ad": malzeme.ad,
                "mevcut_miktar": float(yeni),
                "kritik_stok": float(kritik),
            },
        )
    await db.flush()
    return hareket, kritige_dustu


def talep_gecici_kod() -> str:
    """Kalıcı kod üretilene dek (id bilinene dek) kullanılan geçici tekil değer."""
    return f"GECICI-{uuid.uuid4().hex}"


def talep_kalici_kod(talep_id: int) -> str:
    """İnsan-okur satınalma talebi numarası: ``ST-{yıl}-{id:06d}``."""
    return f"ST-{datetime.now(UTC).year}-{talep_id:06d}"


async def talep_durum_gecisi(
    db: AsyncSession,
    talep: SatinalmaTalebi,
    *,
    hedef: str,
    onaylayan: Kullanici | None = None,
    red_nedeni: str | None = None,
) -> SatinalmaTalebi:
    """Talebi ``hedef`` duruma geçirir; durum makinesi + onay/red alanlarını uygular.

    - Tanımsız hedef → 422; makineye aykırı geçiş → 409.
    - ``reddedildi`` ``red_nedeni`` gerektirir → 422.
    - ``onaylandi``/``reddedildi`` onaylayan + onay tarihini yazar.
    """
    if hedef not in talep_durum.DURUMLAR:
        raise DogrulamaHatasi(
            "Geçersiz durum",
            detaylar=[
                {"alan": "durum", "mesaj": f"Geçerli: {', '.join(sorted(talep_durum.DURUMLAR))}"}
            ],
        )
    if not talep_durum.gecis_gecerli_mi(talep.durum, hedef):
        raise CakismaHatasi(f"Geçersiz durum geçişi: {talep.durum} → {hedef}")

    if hedef == "reddedildi" and not (red_nedeni and red_nedeni.strip()):
        raise DogrulamaHatasi(
            "Red nedeni gerekli",
            detaylar=[{"alan": "red_nedeni", "mesaj": "'reddedildi' için zorunlu"}],
        )

    talep.durum = hedef
    if hedef in ("onaylandi", "reddedildi"):
        talep.onaylayan_kullanici_id = onaylayan.id if onaylayan is not None else None
        talep.onay_tarihi = datetime.now(UTC)
    if hedef == "reddedildi":
        talep.red_nedeni = red_nedeni
    await db.flush()
    return talep
