"""AI iş kuralları — tenant-aware model eğitimi (arka plan görevi) ve orkestrasyon.

Eğitim akışı (🔧 ADR-0015: Celery yerine süreç-içi asyncio görevi):

1. ``egitim_baslat`` istek oturumunda ``egitiliyor`` durumlu bir ``ModelKaydi`` açar
   (tur başına artan sürüm). Router kaydı **commit ettikten sonra** ``egitim_planla``
   ile arka plan görevini başlatır ve 202 döner.
2. ``egitim_calistir`` **kendi oturumunu** açar, ``search_path``'i tenant'a bağlar,
   tenant verisinden feature çerçevelerini çeker, sklearn eğitimini ``asyncio.to_thread``
   ile koşar (event loop bloklanmaz), artefaktı nesne deposuna sürümlü yazar ve kaydı
   ``hazir`` + ``aktif`` yapar (aynı türün önceki aktifleri pasiflenir).
3. Hata/az veri → kayıt ``basarisiz`` + ``hata`` mesajı. Her iki sonda da ``ai.model``
   gerçek-zaman olayı yayınlanır (best-effort).

Testler ``oturum_fabrikasi_ayarla`` ile test motorunu, ``es_zamanli_ayarla(True)`` ile
görevi bekleyerek (create_task yerine await) koşmayı enjekte eder.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db.session import get_sessionmaker
from app.core.db.tenancy import search_path_ayarla
from app.core.exceptions import DogrulamaHatasi, KaynakBulunamadi
from app.core.gercekzaman import yayinla
from app.core.olaylar import GidenOlay, olay_yayinla
from app.modules.ai import artefakt, modeller, ozellikler, repository
from app.modules.ai.birimler import MODEL_TURLERI
from app.modules.ai.models import ModelKaydi, Tahmin

logger = logging.getLogger("app.ai")

# Feature pencereleri (gün).
URETIM_PENCERE_GUN = 90
ARIZA_PENCERE_GUN = 365
STOK_PENCERE_GUN = 90
BAKIM_PENCERE = 7
BAKIM_UFUK = 7
OEE_GECIKME = 7
OEE_UFUK = 7
ANOMALI_SON_GUN = 14  # çıkarımda taranan güncel gözlem penceresi

_oturum_fabrikasi: async_sessionmaker[AsyncSession] | None = None
_es_zamanli = False
_gorevler: set[asyncio.Task[None]] = set()


def oturum_fabrikasi_ayarla(fabrika: async_sessionmaker[AsyncSession] | None) -> None:
    """Arka plan görevlerinin oturum fabrikasını enjekte eder (testler için)."""
    global _oturum_fabrikasi
    _oturum_fabrikasi = fabrika


def es_zamanli_ayarla(deger: bool) -> None:
    """``True`` iken eğitim görevi beklenerek koşar (deterministik testler için)."""
    global _es_zamanli
    _es_zamanli = deger


def _fabrika() -> async_sessionmaker[AsyncSession]:
    return _oturum_fabrikasi if _oturum_fabrikasi is not None else get_sessionmaker()


def tur_dogrula(tur: str) -> None:
    if tur not in MODEL_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz model türü",
            detaylar=[{"alan": "tur", "mesaj": f"şunlardan biri olmalı: {sorted(MODEL_TURLERI)}"}],
        )


async def egitim_baslat(db: AsyncSession, *, tur: str, kullanici_id: int | None) -> ModelKaydi:
    """Yeni bir ``egitiliyor`` model kaydı açar (tur başına artan sürüm)."""
    tur_dogrula(tur)
    surum = await repository.sonraki_surum(db, tur)
    kayit = ModelKaydi(tur=tur, surum=surum, olusturan_kullanici_id=kullanici_id)
    db.add(kayit)
    await db.flush()
    return kayit


async def egitim_planla(kayit_id: int, slug: str, tur: str) -> None:
    """Eğitimi arka plana atar (test modunda bekler)."""
    if _es_zamanli:
        await egitim_calistir(kayit_id, slug, tur)
        return
    gorev = asyncio.create_task(egitim_calistir(kayit_id, slug, tur))
    _gorevler.add(gorev)
    gorev.add_done_callback(_gorevler.discard)


async def egitim_calistir(kayit_id: int, slug: str, tur: str) -> None:
    """Arka plan eğitimi — kendi oturumu; asla exception sızdırmaz."""
    baslangic = time.monotonic()
    try:
        await _egitim_dene(kayit_id, slug, tur, baslangic)
        durum = "hazir"
    except Exception as exc:  # noqa: BLE001 — arka plan görevi süreci düşürmemeli
        logger.warning("model eğitimi başarısız (tur=%s, kayit=%s): %s", tur, kayit_id, exc)
        durum = "basarisiz"
        await _basarisiz_isaretle(kayit_id, slug, exc, baslangic)
    await yayinla(slug, {"tur": "ai.model", "id": kayit_id, "model_turu": tur, "durum": durum})


async def _egitim_dene(kayit_id: int, slug: str, tur: str, baslangic: float) -> None:
    async with _fabrika()() as db:
        await search_path_ayarla(db, slug)
        kayit = await repository.kayit_getir(db, kayit_id)
        if kayit is None:
            raise RuntimeError(f"Model kaydı bulunamadı: {kayit_id}")
        cerceveler = await _veri_hazirla(db, tur)
        sonuc, veri_ozeti = await asyncio.to_thread(_egit, tur, cerceveler)
        anahtar = artefakt.model_nesne_anahtari(slug, tur, kayit.surum)
        boyut = await asyncio.to_thread(artefakt.artefakt_kaydet, anahtar, sonuc.nesne)
        kayit.durum = "hazir"
        kayit.aktif = True
        kayit.nesne_anahtari = anahtar
        kayit.metrikler = dict(sonuc.metrikler)
        kayit.veri_ozeti = {**veri_ozeti, "artefakt_bayt": boyut}
        kayit.egitim_suresi_sn = round(time.monotonic() - baslangic, 3)
        await repository.aktifleri_pasifle(db, tur, haric_id=kayit.id)
        await db.commit()
    logger.info("model eğitimi tamam (tur=%s, surum=%s, tenant=%s)", tur, kayit.surum, slug)


async def _basarisiz_isaretle(kayit_id: int, slug: str, hata: Exception, baslangic: float) -> None:
    try:
        async with _fabrika()() as db:
            await search_path_ayarla(db, slug)
            kayit = await repository.kayit_getir(db, kayit_id)
            if kayit is None:
                return
            kayit.durum = "basarisiz"
            kayit.hata = str(hata)[:1000]
            kayit.egitim_suresi_sn = round(time.monotonic() - baslangic, 3)
            await db.commit()
    except Exception:  # noqa: BLE001 — işaretleme de düşerse yalnız logla
        logger.exception("başarısız eğitim kaydı işaretlenemedi (kayit=%s)", kayit_id)


async def _veri_hazirla(db: AsyncSession, tur: str) -> dict[str, pd.DataFrame]:
    """Model türüne göre ham tenant çerçevelerini çeker."""
    if tur == "stok":
        return {"hareket": await repository.stok_hareket_cercevesi(db, gun=STOK_PENCERE_GUN)}
    cerceveler = {"uretim": await repository.uretim_cercevesi(db, gun=URETIM_PENCERE_GUN)}
    if tur == "kestirimci_bakim":
        cerceveler["ariza"] = await repository.ariza_cercevesi(db, gun=ARIZA_PENCERE_GUN)
    return cerceveler


def _egit(
    tur: str, cerceveler: dict[str, pd.DataFrame]
) -> tuple[modeller.EgitimSonucu, dict[str, Any]]:
    """Saf eğitim dispatcher'ı (thread'de koşar): feature pipeline + sklearn fit."""
    if tur == "stok":
        tuketim = ozellikler.stok_tuketim_gunluk(cerceveler["hareket"])
        sonuc = modeller.stok_egit(tuketim)
        ozet = {"pencere_gun": STOK_PENCERE_GUN, "ham_satir": int(len(cerceveler["hareket"]))}
        return sonuc, ozet

    gunluk = ozellikler.gunluk_makine_ozeti(cerceveler["uretim"])
    ozet = {
        "pencere_gun": URETIM_PENCERE_GUN,
        "ham_satir": int(len(cerceveler["uretim"])),
        "makine_gun": int(len(gunluk)),
    }
    if tur == "kestirimci_bakim":
        egitim = ozellikler.bakim_ozellikleri(
            gunluk, cerceveler["ariza"], pencere=BAKIM_PENCERE, ufuk=BAKIM_UFUK
        )
        return modeller.kestirimci_bakim_egit(egitim), ozet
    if tur == "anomali":
        return modeller.anomali_egit(gunluk), ozet
    if tur == "oee":
        lagli = ozellikler.oee_gecikme_ozellikleri(gunluk, gecikme=OEE_GECIKME)
        return modeller.oee_egit(lagli, gecikme=OEE_GECIKME), ozet
    raise DogrulamaHatasi("Geçersiz model türü")  # tur_dogrula'dan geçmiş olmalı


# --- Çıkarım (istek anında) ---
@dataclass(frozen=True, slots=True)
class CikarimSonucu:
    """Bir çıkarım koşusunun sonucu: kullanılan model + geçmiş satırı + çıktı listesi."""

    kayit: ModelKaydi
    tahmin: Tahmin
    sonuclar: list[dict[str, Any]]


async def tahmin_calistir(
    db: AsyncSession, *, slug: str, tur: str, kullanici_id: int | None
) -> CikarimSonucu:
    """Aktif modelle güncel tenant verisi üzerinde çıkarım yapar; geçmişe satır yazar.

    Anomali türünde ≥1 bulgu varsa aynı transaction'da ``anomali.tespit`` outbox olayı
    yazılır (S18 webhook teslimatına hazır) ve gerçek-zaman yayını yapılır.
    """
    tur_dogrula(tur)
    kayit = await repository.aktif_kayit(db, tur)
    if kayit is None:
        raise KaynakBulunamadi("Bu tür için hazır model yok; önce eğitim başlatın")
    nesne = await asyncio.to_thread(artefakt.artefakt_yukle_onbellekli, kayit.nesne_anahtari)
    cerceveler = await _cikarim_veri_hazirla(db, tur)
    sonuclar, veri_ozeti = await asyncio.to_thread(_tahmin, tur, nesne, cerceveler)
    if tur != "stok":  # makine-bazlı çıktılar insan-okur kodla zenginleşir
        kodlar = await repository.makine_kod_haritasi(db)
        for s in sonuclar:
            s["makine_kod"] = kodlar.get(int(s["makine_id"]), "")
    tahmin = Tahmin(
        tur=tur,
        model_id=kayit.id,
        cikti=sonuclar,
        veri_ozeti=veri_ozeti,
        olusturan_kullanici_id=kullanici_id,
    )
    await repository.tahmin_ekle(db, tahmin)
    makineler = sorted({int(s["makine_id"]) for s in sonuclar}) if tur == "anomali" else []
    if tur == "anomali" and sonuclar and not await _anomali_yakin_zamanda_bildirildi(db, makineler):
        await olay_yayinla(
            db,
            olay_turu="anomali.tespit",
            govde={
                "tahmin_id": tahmin.id,
                "model_surum": kayit.surum,
                "anomali_sayisi": len(sonuclar),
                "makineler": makineler,
                # İnsan-okur özet: bildirim başlığı ve webhook alıcısı için (id listesi yetmiyor).
                "makine_kodlari": sorted(
                    {s["makine_kod"] for s in sonuclar if s.get("makine_kod")}
                ),
            },
        )
        await yayinla(slug, {"tur": "anomali.tespit", "id": tahmin.id})
    return CikarimSonucu(kayit=kayit, tahmin=tahmin, sonuclar=sonuclar)


# Anomali ekranı GET ile çıkarım yapar; her görüntüleme (ve odakta yeniden çekme) yeni bir
# outbox olayı → yetkili HER kullanıcıya bildirim üretiyordu (09-23'te bir saatte 49 olay).
# Aynı makine kümesi bu pencere içinde zaten bildirildiyse olay tekrar yazılmaz; tahmin
# kaydı (geçmiş ekranı) yine yazılır.
ANOMALI_TEKRAR_PENCERESI = timedelta(hours=24)


async def _anomali_yakin_zamanda_bildirildi(db: AsyncSession, makineler: list[int]) -> bool:
    son = (
        await db.execute(
            select(GidenOlay)
            .where(
                GidenOlay.olay_turu == "anomali.tespit",
                GidenOlay.olusturma_tarihi >= datetime.now(UTC) - ANOMALI_TEKRAR_PENCERESI,
            )
            .order_by(GidenOlay.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return son is not None and sorted(son.govde.get("makineler") or []) == makineler


async def _cikarim_veri_hazirla(db: AsyncSession, tur: str) -> dict[str, pd.DataFrame]:
    """Model türüne göre çıkarım girdisi çerçevelerini çeker."""
    if tur == "stok":
        return {"malzeme": await repository.malzeme_cercevesi(db)}
    if tur == "anomali":
        return {"uretim": await repository.uretim_cercevesi(db, gun=ANOMALI_SON_GUN)}
    cerceveler = {"uretim": await repository.uretim_cercevesi(db, gun=URETIM_PENCERE_GUN)}
    if tur == "kestirimci_bakim":
        cerceveler["ariza"] = await repository.ariza_cercevesi(db, gun=ARIZA_PENCERE_GUN)
    return cerceveler


def _tahmin(
    tur: str, nesne: Any, cerceveler: dict[str, pd.DataFrame]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Saf çıkarım dispatcher'ı (thread'de koşar): feature pipeline + model tahmini."""
    if tur == "stok":
        sonuclar = modeller.stok_tahmin(nesne, cerceveler["malzeme"])
        return sonuclar, {"malzeme_sayisi": int(len(cerceveler["malzeme"]))}

    gunluk = ozellikler.gunluk_makine_ozeti(cerceveler["uretim"])
    ozet = {"makine_gun": int(len(gunluk))}
    if tur == "kestirimci_bakim":
        guncel = ozellikler.bakim_guncel_ozellikler(
            gunluk, cerceveler["ariza"], pencere=BAKIM_PENCERE
        )
        return modeller.kestirimci_bakim_tahmin(nesne, guncel), ozet
    if tur == "anomali":
        ozet["taranan_gun"] = ANOMALI_SON_GUN
        return modeller.anomali_tahmin(nesne, gunluk), ozet
    if tur == "oee":
        son = ozellikler.oee_son_pencere(gunluk, gecikme=OEE_GECIKME)
        return modeller.oee_tahmin(nesne, son, ufuk=OEE_UFUK), ozet
    raise DogrulamaHatasi("Geçersiz model türü")
