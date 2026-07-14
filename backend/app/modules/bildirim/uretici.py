"""Bildirim üretici — outbox → kişi-hedefli bildirim fan-out'u (S-VB / ADR-0021).

Webhook relay'den **bağımsız** ikinci outbox tüketicisidir: relay ``giden_olaylar.durum``
alanını koordinasyon için kullanır; üretici kendi ``bildirim_imleci`` yüksek-su-işaretiyle
``id`` sırasında okur. İki tüketici tek outbox'ı çakışmasız paylaşır (decoupled).

İdempotency iki katmanlıdır: imleç tarama penceresini daraltır; ``UNIQUE(kullanici_id,
giden_olay_id)`` kısıtı (ON CONFLICT DO NOTHING) tekrar taramada çift bildirimi yapısal
olarak önler. Kanal gönderimi (e-posta) best-effort'tur — uygulama-içi satır otoritedir.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db.tenancy import search_path_ayarla
from app.core.gercekzaman import yayinla
from app.core.olaylar import GidenOlay
from app.kimlik.models import Izin, Kullanici, kullanici_rol, rol_izin
from app.modules.bildirim.hedefleme import (
    BILDIRIM_OLAYLARI,
    bildirim_hedef_kurali,
    bildirim_metni,
    bildirim_verisi,
)
from app.modules.bildirim.kanallar import EPostaKanali
from app.modules.bildirim.models import Bildirim, BildirimImleci, BildirimTercihi

logger = logging.getLogger("app.bildirim.uretici")

PARTI_BOYU = 200  # tur başına işlenecek olay sınırı; kalan sonraki tura devreder


async def _imlec_getir(db: AsyncSession) -> BildirimImleci:
    """Tek satırlık imleci getirir; yoksa 0'dan oluşturur."""
    imlec = (await db.execute(select(BildirimImleci).limit(1))).scalar_one_or_none()
    if imlec is None:
        imlec = BildirimImleci(son_islenen_olay_id=0)
        db.add(imlec)
        await db.flush()
    return imlec


async def _izinli_kullanicilar(db: AsyncSession, izin_kodu: str) -> list[int]:
    """``izin_kodu`` iznine sahip aktif kullanıcı id'leri (tek sorgu)."""
    sorgu = (
        select(Kullanici.id)
        .distinct()
        .join(kullanici_rol, kullanici_rol.c.kullanici_id == Kullanici.id)
        .join(rol_izin, rol_izin.c.rol_id == kullanici_rol.c.rol_id)
        .join(Izin, Izin.id == rol_izin.c.izin_id)
        .where(Kullanici.aktif, Izin.kod == izin_kodu)
    )
    return list((await db.execute(sorgu)).scalars().all())


async def _tum_aktif_kullanicilar(db: AsyncSession) -> list[int]:
    return list((await db.execute(select(Kullanici.id).where(Kullanici.aktif))).scalars().all())


async def olay_hedefleri(db: AsyncSession, olay: GidenOlay) -> tuple[list[int], str]:
    """Olayın hedef kullanıcı id kümesini ve önemini çözer (kural + izin sorgusu)."""
    kural = bildirim_hedef_kurali(olay.olay_turu, olay.govde)
    if kural is None:
        return [], "bilgi"
    hedefler: set[int] = set()
    if kural.herkese:
        hedefler.update(await _tum_aktif_kullanicilar(db))
    if kural.izin_kodu:
        hedefler.update(await _izinli_kullanicilar(db, kural.izin_kodu))
    for alan in kural.kisi_alanlari:
        deger = olay.govde.get(alan)
        if isinstance(deger, int):
            hedefler.add(deger)
    return sorted(hedefler), kural.onem


async def _tercihler(
    db: AsyncSession, kullanici_idler: list[int], olay_turu: str
) -> dict[int, BildirimTercihi]:
    if not kullanici_idler:
        return {}
    kayitlar = (
        (
            await db.execute(
                select(BildirimTercihi).where(
                    BildirimTercihi.kullanici_id.in_(kullanici_idler),
                    BildirimTercihi.olay_turu == olay_turu,
                )
            )
        )
        .scalars()
        .all()
    )
    return {t.kullanici_id: t for t in kayitlar}


async def bildirim_uret(
    db: AsyncSession, *, tenant_slug: str, eposta_kanali: EPostaKanali | None = None
) -> int:
    """Bir tenant şemasında bir üretim turu koşar; üretilen bildirim sayısını döner.

    Çağıran ``search_path``'i ayarlamış olmalıdır (tenant-rbac-conventions). Commit
    çağırana aittir; fonksiyon yalnız flush eder.
    """
    imlec = await _imlec_getir(db)
    olaylar = (
        (
            await db.execute(
                select(GidenOlay)
                .where(
                    GidenOlay.id > imlec.son_islenen_olay_id,
                    GidenOlay.olay_turu.in_(BILDIRIM_OLAYLARI),
                )
                .order_by(GidenOlay.id)
                .limit(PARTI_BOYU)
            )
        )
        .scalars()
        .all()
    )
    if not olaylar:
        return 0

    uretilen = 0
    eposta_gorevleri: list[tuple[int, str, str]] = []  # (kullanici_id, baslik, govde)
    for olay in olaylar:
        hedefler, onem = await olay_hedefleri(db, olay)
        if hedefler:
            baslik, govde_metin = bildirim_metni(olay.olay_turu, olay.govde)
            veri = bildirim_verisi(olay.olay_turu, olay.govde)
            tercihler = await _tercihler(db, hedefler, olay.olay_turu)
            for kullanici_id in hedefler:
                tercih = tercihler.get(kullanici_id)
                if tercih is not None and not tercih.uygulama_ici:
                    continue  # kullanıcı bu olay türünü kapatmış
                sonuc = await db.execute(
                    pg_insert(Bildirim)
                    .values(
                        kullanici_id=kullanici_id,
                        giden_olay_id=olay.id,
                        olay_turu=olay.olay_turu,
                        baslik=baslik,
                        govde=govde_metin,
                        veri=veri,
                        onem=onem,
                    )
                    .on_conflict_do_nothing()
                    .returning(Bildirim.id)
                )
                yeni_id = sonuc.scalar_one_or_none()
                if yeni_id is None:
                    continue  # kısıt: bu olay bu kullanıcıya zaten düşmüş
                uretilen += 1
                # Canlı zil güncellemesi: tenant kanalı + FE kendi kullanıcısına süzer.
                await yayinla(
                    tenant_slug,
                    {
                        "tur": "bildirim.yeni",
                        "id": yeni_id,
                        "kullanici_id": kullanici_id,
                        "onem": onem,
                    },
                )
                if tercih is not None and tercih.eposta:
                    eposta_gorevleri.append((kullanici_id, baslik, govde_metin))
        imlec.son_islenen_olay_id = olay.id
    await db.flush()

    # Kanal gönderimi (best-effort): DB durumu kesinleşti, hata bildirimi düşürmez.
    if eposta_gorevleri and eposta_kanali is not None:
        idler = [k for k, _, _ in eposta_gorevleri]
        sorgu = select(Kullanici.id, Kullanici.eposta).where(Kullanici.id.in_(idler))
        epostalar = dict((await db.execute(sorgu)).tuples().all())
        for kullanici_id, baslik, govde_metin in eposta_gorevleri:
            alici = epostalar.get(kullanici_id)
            if alici:
                await eposta_kanali.gonder(alici_eposta=alici, baslik=baslik, govde=govde_metin)
    return uretilen


async def tenant_uretici_turu(
    sm: async_sessionmaker[AsyncSession],
    slug: str,
    *,
    eposta_kanali: EPostaKanali | None = None,
) -> int:
    """Tek tenant için bir üretim turu (kendi transaction'ında); üretilen sayıyı döner."""
    async with sm() as session, session.begin():
        await search_path_ayarla(session, slug)
        uretilen = await bildirim_uret(session, tenant_slug=slug, eposta_kanali=eposta_kanali)
    if uretilen:
        logger.info("bildirim turu: tenant=%s uretilen=%d", slug, uretilen)
    return uretilen
