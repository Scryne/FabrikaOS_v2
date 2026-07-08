"""Rapor iş kuralları — async üretim orkestrasyonu (S13 süreç-içi görev deseni).

Akış (ADR-0016; ADR-0015 deseninin yeniden kullanımı):

1. ``rapor_olustur`` istek oturumunda ``kuyrukta`` durumlu bir ``Rapor`` açar (oto kod
   ``RP-{yıl}-{id:06d}``, parametre penceresi kayda dondurulur). Router kaydı commit
   ettikten sonra ``uretim_planla`` ile arka plan görevini başlatır ve 202 döner.
2. ``rapor_uret_calistir`` **kendi oturumunu** açar, ``search_path``'i tenant'a bağlar,
   tür-bazlı satırları çeker, PDF/XLSX baytlarını ``asyncio.to_thread``'de üretir,
   ``NesneDepo``'ya ``tenant_<slug>/rapor/<id>/<dosya>`` anahtarıyla yazar ve kaydı
   ``hazir`` yapar. Hata → ``basarisiz`` + ``hata`` mesajı.
3. Her iki sonda da ``rapor.hazir`` gerçek-zaman olayı yayınlanır (best-effort).

Testler ``oturum_fabrikasi_ayarla`` ile test motorunu, ``es_zamanli_ayarla(True)`` ile
görevi bekleyerek koşmayı enjekte eder (S13 ``ai.service`` ile aynı imzalar).
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db.session import get_sessionmaker
from app.core.db.tenancy import search_path_ayarla
from app.core.exceptions import DogrulamaHatasi
from app.core.gercekzaman import yayinla
from app.modules.analitik.hesap import donem_oee, fire_orani
from app.modules.dys.depolama import nesne_depo_al
from app.modules.rapor import repository
from app.modules.rapor.birimler import (
    ICERIK_TIPLERI,
    RAPOR_BICIMLERI,
    RAPOR_TURLERI,
    rapor_dosya_adi,
)
from app.modules.rapor.models import Rapor
from app.modules.rapor.uretici import RaporIcerik, pdf_uret, xlsx_uret

logger = logging.getLogger("app.rapor")

# Rapor başlıkları (belge içeriği TR üretilir; UI metinleri i18n'dedir).
_TUR_BASLIKLARI: dict[str, str] = {
    "uretim": "Üretim Raporu",
    "stok": "Stok Raporu",
    "kalite": "Kalite Raporu",
    "enerji": "Enerji Raporu",
    "isemri": "İş Emri Raporu",
}

_oturum_fabrikasi: async_sessionmaker[AsyncSession] | None = None
_es_zamanli = False
_gorevler: set[asyncio.Task[None]] = set()


def oturum_fabrikasi_ayarla(fabrika: async_sessionmaker[AsyncSession] | None) -> None:
    """Arka plan görevlerinin oturum fabrikasını enjekte eder (testler için)."""
    global _oturum_fabrikasi
    _oturum_fabrikasi = fabrika


def es_zamanli_ayarla(deger: bool) -> None:
    """``True`` iken üretim görevi beklenerek koşar (deterministik testler için)."""
    global _es_zamanli
    _es_zamanli = deger


def _fabrika() -> async_sessionmaker[AsyncSession]:
    return _oturum_fabrikasi if _oturum_fabrikasi is not None else get_sessionmaker()


def tur_dogrula(tur: str) -> None:
    if tur not in RAPOR_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz rapor türü",
            detaylar=[{"alan": "tur", "mesaj": f"şunlardan biri olmalı: {sorted(RAPOR_TURLERI)}"}],
        )


def bicim_dogrula(bicim: str) -> None:
    if bicim not in RAPOR_BICIMLERI:
        raise DogrulamaHatasi(
            "Geçersiz rapor biçimi",
            detaylar=[
                {"alan": "bicim", "mesaj": f"şunlardan biri olmalı: {sorted(RAPOR_BICIMLERI)}"}
            ],
        )


def rapor_kalici_kod(rapor_id: int) -> str:
    """İnsan-okur rapor numarası: ``RP-{yıl}-{id:06d}``."""
    return f"RP-{datetime.now(UTC).year}-{rapor_id:06d}"


def rapor_nesne_anahtari(slug: str, rapor_id: int, dosya_adi: str) -> str:
    """Tenant-izole artefakt anahtarı: ``tenant_<slug>/rapor/<id>/<dosya>``."""
    return f"tenant_{slug}/rapor/{rapor_id}/{dosya_adi}"


async def rapor_olustur(
    db: AsyncSession, *, tur: str, bicim: str, gun: int, kullanici_id: int | None
) -> Rapor:
    """``kuyrukta`` durumlu rapor kaydı açar; pencere parametreleri kayda dondurulur."""
    tur_dogrula(tur)
    bicim_dogrula(bicim)
    bitis = datetime.now(UTC)
    baslangic = bitis - timedelta(days=gun)
    kayit = Rapor(
        kod="",  # id flush'tan sonra belli olur; kalıcı kod aşağıda
        tur=tur,
        bicim=bicim,
        parametreler={"gun": gun, "baslangic": baslangic.isoformat(), "bitis": bitis.isoformat()},
        icerik_tipi=ICERIK_TIPLERI[bicim],
        olusturan_kullanici_id=kullanici_id,
    )
    db.add(kayit)
    await db.flush()
    kayit.kod = rapor_kalici_kod(kayit.id)
    kayit.dosya_adi = rapor_dosya_adi(kayit.kod, bicim)
    await db.flush()
    return kayit


async def uretim_planla(rapor_id: int, slug: str) -> None:
    """Rapor üretimini arka plana atar (test modunda bekler)."""
    if _es_zamanli:
        await rapor_uret_calistir(rapor_id, slug)
        return
    gorev = asyncio.create_task(rapor_uret_calistir(rapor_id, slug))
    _gorevler.add(gorev)
    gorev.add_done_callback(_gorevler.discard)


async def rapor_uret_calistir(rapor_id: int, slug: str) -> None:
    """Arka plan rapor üretimi — kendi oturumu; asla exception sızdırmaz."""
    baslangic = time.monotonic()
    try:
        await _uret_dene(rapor_id, slug, baslangic)
        durum = "hazir"
    except Exception as exc:  # noqa: BLE001 — arka plan görevi süreci düşürmemeli
        logger.warning("rapor üretimi başarısız (kayit=%s): %s", rapor_id, exc)
        durum = "basarisiz"
        await _basarisiz_isaretle(rapor_id, slug, exc, baslangic)
    await yayinla(slug, {"tur": "rapor.hazir", "id": rapor_id, "durum": durum})


async def _uret_dene(rapor_id: int, slug: str, baslangic: float) -> None:
    async with _fabrika()() as db:
        await search_path_ayarla(db, slug)
        kayit = await repository.rapor_getir(db, rapor_id)
        if kayit is None:
            raise RuntimeError(f"Rapor kaydı bulunamadı: {rapor_id}")
        kayit.durum = "hazirlaniyor"
        await db.commit()
        # search_path işlem-yerel (set_config is_local): commit sıfırladı → yeniden bağla.
        await search_path_ayarla(db, slug)

        icerik = await _icerik_hazirla(db, slug, kayit)
        veri = await asyncio.to_thread(_uret, kayit.bicim, icerik)
        anahtar = rapor_nesne_anahtari(slug, kayit.id, kayit.dosya_adi)
        depo = nesne_depo_al()
        await asyncio.to_thread(depo.yukle, anahtar, veri, kayit.icerik_tipi)

        kayit.durum = "hazir"
        kayit.nesne_anahtari = anahtar
        kayit.boyut = len(veri)
        kayit.satir_sayisi = len(icerik.satirlar)
        kayit.uretim_suresi_sn = round(time.monotonic() - baslangic, 3)
        await db.commit()
    logger.info("rapor üretildi (kod=%s, tenant=%s, bayt=%s)", kayit.kod, slug, len(veri))


async def _basarisiz_isaretle(rapor_id: int, slug: str, hata: Exception, baslangic: float) -> None:
    try:
        async with _fabrika()() as db:
            await search_path_ayarla(db, slug)
            kayit = await repository.rapor_getir(db, rapor_id)
            if kayit is None:
                return
            kayit.durum = "basarisiz"
            kayit.hata = str(hata)[:1000]
            kayit.uretim_suresi_sn = round(time.monotonic() - baslangic, 3)
            await db.commit()
    except Exception:  # noqa: BLE001 — işaretleme de düşerse yalnız logla
        logger.exception("başarısız rapor kaydı işaretlenemedi (kayit=%s)", rapor_id)


def _pencere(kayit: Rapor) -> datetime:
    """Kayda dondurulan pencere başlangıcı (parametresizse 30 gün geriye düşer)."""
    parametreler = kayit.parametreler or {}
    ham = parametreler.get("baslangic")
    if isinstance(ham, str):
        return datetime.fromisoformat(ham)
    return datetime.now(UTC) - timedelta(days=30)


def _d(deger: datetime | None) -> str:
    return deger.strftime("%Y-%m-%d %H:%M") if deger is not None else ""


async def _icerik_hazirla(db: AsyncSession, slug: str, kayit: Rapor) -> RaporIcerik:
    """Tür-bazlı satırları çekip biçimden bağımsız ``RaporIcerik`` kurar."""
    esik = _pencere(kayit)
    alt_baslik = f"{kayit.kod} • {slug} • {esik:%Y-%m-%d} → {datetime.now(UTC):%Y-%m-%d}"
    baslik = _TUR_BASLIKLARI[kayit.tur]

    if kayit.tur == "uretim":
        ham = await repository.uretim_satirlari(db, esik=esik)
        satirlar: list[list[Any]] = []
        for s in ham:
            oee = donem_oee(
                planlanan_sure_dk=float(s["planlanan"]),
                durus_sure_dk=float(s["durus"]),
                toplam_adet=int(s["toplam_adet"]),
                saglam_adet=int(s["saglam_adet"]),
                ideal_toplam_sn=float(s["ideal_toplam_sn"]),
            )
            satirlar.append(
                [
                    f"{s['gun']:%Y-%m-%d}",
                    s["makine_kod"],
                    int(s["toplam_adet"]),
                    int(s["saglam_adet"]),
                    round(fire_orani(int(s["toplam_adet"]), int(s["saglam_adet"])) * 100, 2),
                    round(oee.oee * 100, 2),
                ]
            )
        toplam = sum(int(s["toplam_adet"]) for s in ham)
        saglam = sum(int(s["saglam_adet"]) for s in ham)
        return RaporIcerik(
            baslik=baslik,
            alt_baslik=alt_baslik,
            kolonlar=["Gün", "Makine", "Toplam Adet", "Sağlam Adet", "Fire %", "OEE %"],
            satirlar=satirlar,
            ozet=[f"Toplam üretim: {toplam}", f"Sağlam: {saglam}", f"Fire: {toplam - saglam}"],
        )

    if kayit.tur == "stok":
        ham = await repository.stok_satirlari(db)
        satirlar = [
            [
                s["kod"],
                s["ad"],
                s["kategori"],
                s["birim"],
                s["mevcut"],
                s["kritik_stok"],
                "KRİTİK" if 0 < s["kritik_stok"] >= s["mevcut"] else "",
            ]
            for s in ham
        ]
        kritik_sayisi = sum(1 for s in satirlar if s[-1] == "KRİTİK")
        return RaporIcerik(
            baslik=baslik,
            alt_baslik=alt_baslik,
            kolonlar=["Kod", "Ad", "Kategori", "Birim", "Mevcut", "Kritik Eşik", "Durum"],
            satirlar=satirlar,
            ozet=[f"Aktif malzeme: {len(satirlar)}", f"Kritik altında: {kritik_sayisi}"],
        )

    if kayit.tur == "kalite":
        ham = await repository.kalite_satirlari(db, esik=esik)
        satirlar = [
            [
                s["kod"],
                _d(s["zaman"]),
                s["kontrol_turu"],
                s["sonuc"],
                int(s["numune_adedi"]),
                int(s["uygunsuz_adet"]),
            ]
            for s in ham
        ]
        gecti = sum(1 for s in ham if s["sonuc"] == "gecti")
        return RaporIcerik(
            baslik=baslik,
            alt_baslik=alt_baslik,
            kolonlar=["Kod", "Zaman", "Tür", "Sonuç", "Numune", "Uygunsuz"],
            satirlar=satirlar,
            ozet=[f"Kontrol: {len(satirlar)}", f"Geçti: {gecti}"],
        )

    if kayit.tur == "enerji":
        ham = await repository.enerji_satirlari(db, esik=esik)
        satirlar = [
            [f"{s['gun']:%Y-%m-%d}", s["enerji_turu"], round(float(s["toplam"]), 3), s["birim"]]
            for s in ham
        ]
        return RaporIcerik(
            baslik=baslik,
            alt_baslik=alt_baslik,
            kolonlar=["Gün", "Enerji Türü", "Tüketim", "Birim"],
            satirlar=satirlar,
            ozet=[f"Gün×tür kaydı: {len(satirlar)}"],
        )

    # isemri (tur_dogrula'dan geçmiş olmalı)
    ham = await repository.isemri_satirlari(db, esik=esik)
    satirlar = [
        [
            s["kod"],
            s["baslik"],
            s["makine_kod"],
            s["durum"],
            s["oncelik"],
            _d(s["olusturma_tarihi"]),
            _d(s["kapanis_tarihi"]),
        ]
        for s in ham
    ]
    kapanan = sum(1 for s in ham if s["durum"] == "kapandi")
    return RaporIcerik(
        baslik=baslik,
        alt_baslik=alt_baslik,
        kolonlar=["Kod", "Başlık", "Makine", "Durum", "Öncelik", "Açılış", "Kapanış"],
        satirlar=satirlar,
        ozet=[f"İş emri: {len(satirlar)}", f"Kapanan: {kapanan}"],
    )


def _uret(bicim: str, icerik: RaporIcerik) -> bytes:
    """Saf üretim dispatcher'ı (thread'de koşar)."""
    if bicim == "pdf":
        return pdf_uret(icerik)
    return xlsx_uret(icerik)


async def rapor_icerik_indir(kayit: Rapor) -> bytes:
    """Hazır raporun baytlarını nesne deposundan okur."""
    depo = nesne_depo_al()
    return await asyncio.to_thread(depo.indir, kayit.nesne_anahtari)
