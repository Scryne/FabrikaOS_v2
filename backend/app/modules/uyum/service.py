"""KVKK iş kuralları (S23 / ADR-0022) — kişi bazlı ihraç + anonimleştirme.

**İhraç** S14/S17 async desenini izler: ``kuyrukta`` kayıt + arka plan görevi →
JSON dosyaları ZIP'lenir → MinIO ``tenant_<slug>/kvkk/...`` → indirme 409-korumalı.
"Eksiksizlik" garantisi KEŞFE bağlıdır: tenant şemasında ``kullanici_id`` /
``personel_id`` desenli TÜM kolonlar ``information_schema``'dan bulunur ve kişiye ait
satırlar dökülür — gelecekte eklenen modüller otomatik kapsanır (S17 dersi).

**Anonimleştirme** istek içinde, tek transaction'da koşar: kimlik alanları maskelenir,
denetim izinin adli çekirdeği (eylem/kaynak/zaman) korunur — yalnız kişisel veri
kolonları güncellenir (migration'daki trigger başka kolonu zaten kilitler).
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import secrets
import zipfile
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.audit import DenetimIzi, denetim_yaz
from app.core.db.session import get_sessionmaker
from app.core.db.tenancy import search_path_ayarla, sema_adi
from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.security.parola import parola_ozetle
from app.kimlik.models import Kullanici, Oturum
from app.modules.dys.depolama import nesne_depo_al
from app.modules.ik.models import Personel
from app.modules.uyum.models import IHRAC_SAKLAMA_GUN, KISI_TURLERI, KvkkIhraci

logger = logging.getLogger("app.modules.uyum")

_oturum_fabrikasi: async_sessionmaker[AsyncSession] | None = None
_es_zamanli = False
_gorevler: set[asyncio.Task[None]] = set()

# Kişi türü → referans kolon deseni (information_schema keşfi).
_KOLON_DESENI = {"kullanici": "%kullanici_id", "personel": "%personel_id"}
_ANA_TABLO = {"kullanici": "kullanici", "personel": "personel"}


def oturum_fabrikasi_ayarla(fabrika: async_sessionmaker[AsyncSession] | None) -> None:
    """Arka plan görevlerinin oturum fabrikasını enjekte eder (testler için)."""
    global _oturum_fabrikasi
    _oturum_fabrikasi = fabrika


def es_zamanli_ayarla(deger: bool) -> None:
    """``True`` iken ihraç görevi beklenerek koşar (deterministik testler için)."""
    global _es_zamanli
    _es_zamanli = deger


def _fabrika() -> async_sessionmaker[AsyncSession]:
    return _oturum_fabrikasi if _oturum_fabrikasi is not None else get_sessionmaker()


def kvkk_nesne_anahtari(slug: str, ihrac: KvkkIhraci) -> str:
    """Tenant-izole artefakt anahtarı: ``tenant_<slug>/kvkk/<id>/<dosya>``."""
    return f"tenant_{slug}/kvkk/{ihrac.id}/{ihrac.kod.lower()}.zip"


def _json_bayt(veri: Any) -> bytes:
    return json.dumps(veri, ensure_ascii=False, default=str, indent=1).encode("utf-8")


def _zip_uret(dosyalar: dict[str, bytes]) -> bytes:
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        for ad, icerik in dosyalar.items():
            z.writestr(ad, icerik)
    return tampon.getvalue()


def kisi_turu_dogrula(tur: str) -> None:
    if tur not in KISI_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz kişi türü",
            detaylar=[
                {"alan": "kisi_turu", "mesaj": f"Geçerli: {', '.join(sorted(KISI_TURLERI))}"}
            ],
        )


async def uretim_planla(ihrac_id: int, slug: str) -> None:
    """İhraç üretimini arka plana atar (test modunda bekler)."""
    if _es_zamanli:
        await ihrac_calistir(ihrac_id, slug)
        return
    gorev = asyncio.create_task(ihrac_calistir(ihrac_id, slug))
    _gorevler.add(gorev)
    gorev.add_done_callback(_gorevler.discard)


async def ihrac_calistir(ihrac_id: int, slug: str) -> None:
    """Arka plan ihraç üretimi — kendi oturumu; asla exception sızdırmaz."""
    try:
        await _uret_dene(ihrac_id, slug)
    except Exception as exc:  # noqa: BLE001 — arka plan görevi süreci düşürmemeli
        logger.warning("kvkk ihracı başarısız (kayit=%s): %s", ihrac_id, exc)
        await _basarisiz_isaretle(ihrac_id, slug, exc)


async def _satirlar(db: AsyncSession, sql: str, /, **params: Any) -> list[dict[str, Any]]:
    sonuc = await db.execute(text(sql), params)
    return [dict(m) for m in sonuc.mappings().all()]


async def _kisi_tablolari(db: AsyncSession, sema: str, kisi_turu: str) -> list[tuple[str, str]]:
    """Kişiye referans veren (tablo, kolon) çiftleri — information_schema keşfi."""
    desen = _KOLON_DESENI[kisi_turu]
    satirlar = await _satirlar(
        db,
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = :sema AND (column_name = :tam OR column_name LIKE :desen) "
        "ORDER BY table_name, column_name",
        sema=sema,
        tam=f"{kisi_turu}_id",
        desen=desen,
    )
    return [(str(s["table_name"]), str(s["column_name"])) for s in satirlar]


async def _uret_dene(ihrac_id: int, slug: str) -> None:
    sema = sema_adi(slug)
    async with _fabrika()() as db:
        # Arka plan oturumunda search_path yok — sorgular şema-nitelikli koşar
        # (adlar sema_adi doğrulamalı; platform ihraç deseniyle aynı istisna).
        satir = await _satirlar(
            db, f'SELECT * FROM "{sema}"."kvkk_ihraclari" WHERE id = :i', i=ihrac_id
        )
        if not satir:
            raise RuntimeError(f"KVKK ihraç kaydı bulunamadı: {ihrac_id}")
        kisi_turu = str(satir[0]["kisi_turu"])
        kisi_id = int(satir[0]["kisi_id"])
        kod = str(satir[0]["kod"])
        await db.execute(
            text(f'UPDATE "{sema}"."kvkk_ihraclari" SET durum = :d WHERE id = :i'),
            {"d": "hazirlaniyor", "i": ihrac_id},
        )
        await db.commit()

        dosyalar: dict[str, bytes] = {}
        kayit_sayisi = 0

        # 1) Ana kayıt.
        ana_tablo = _ANA_TABLO[kisi_turu]
        ana = await _satirlar(db, f'SELECT * FROM "{sema}"."{ana_tablo}" WHERE id = :i', i=kisi_id)
        if not ana:
            raise RuntimeError(f"Kişi bulunamadı: {kisi_turu} #{kisi_id}")
        # Parola özeti/totp sırrı kişisel veri ihracına girmez (güvenlik sırrıdır).
        for hassas in ("parola_ozet", "totp_sirri"):
            for satir_ in ana:
                satir_.pop(hassas, None)
        dosyalar[f"{ana_tablo}.json"] = _json_bayt(ana)
        kayit_sayisi += len(ana)

        # 2) Keşif: kişiye referans veren tüm tablo/kolonlar.
        iliskiler: dict[str, int] = {}
        for tablo, kolon in await _kisi_tablolari(db, sema, kisi_turu):
            if tablo == ana_tablo:
                continue
            veriler = await _satirlar(
                db, f'SELECT * FROM "{sema}"."{tablo}" WHERE "{kolon}" = :i', i=kisi_id
            )
            if not veriler:
                continue
            dosyalar[f"iliskili/{tablo}.{kolon}.json"] = _json_bayt(veriler)
            iliskiler[f"{tablo}.{kolon}"] = len(veriler)
            kayit_sayisi += len(veriler)

        dosyalar["manifest.json"] = _json_bayt(
            {
                "kod": kod,
                "kisi_turu": kisi_turu,
                "kisi_id": kisi_id,
                "uretim_tarihi": datetime.now(UTC),
                "iliskili_tablolar": iliskiler,
                "toplam_kayit": kayit_sayisi,
            }
        )

        veri = await asyncio.to_thread(_zip_uret, dosyalar)
        anahtar = f"tenant_{slug}/kvkk/{ihrac_id}/{kod.lower()}.zip"
        depo = nesne_depo_al()
        await asyncio.to_thread(depo.yukle, anahtar, veri, "application/zip")

        await db.execute(
            text(
                f'UPDATE "{sema}"."kvkk_ihraclari" SET durum = :d, nesne_anahtari = :a, '
                f"dosya_adi = :ad, boyut = :b, kayit_sayisi = :k, gecerlilik_bitisi = :g "
                f"WHERE id = :i"
            ),
            {
                "d": "hazir",
                "a": anahtar,
                "ad": f"{kod.lower()}.zip",
                "b": len(veri),
                "k": kayit_sayisi,
                # Saklama süresi üretim anından işler (talep anından değil): kuyrukta
                # uzun bekleyen bir ihraç, indirilebilir ömrünü kaybetmiş olmasın.
                "g": datetime.now(UTC) + timedelta(days=IHRAC_SAKLAMA_GUN),
                "i": ihrac_id,
            },
        )
        await db.commit()
    logger.info("kvkk ihracı üretildi (slug=%s, kod=%s, kayit=%s)", slug, kod, kayit_sayisi)


async def _basarisiz_isaretle(ihrac_id: int, slug: str, hata: Exception) -> None:
    try:
        sema = sema_adi(slug)
        async with _fabrika()() as db:
            await db.execute(
                text(f'UPDATE "{sema}"."kvkk_ihraclari" SET durum = :d, hata = :h WHERE id = :i'),
                {"d": "basarisiz", "h": str(hata)[:1000], "i": ihrac_id},
            )
            await db.commit()
    except Exception:  # noqa: BLE001 — işaretleme de düşerse yalnız logla
        logger.exception("başarısız kvkk ihracı işaretlenemedi (kayit=%s)", ihrac_id)


async def ihrac_icerik_indir(kayit: KvkkIhraci) -> bytes:
    """Hazır ihracın ZIP baytlarını nesne deposundan okur."""
    depo = nesne_depo_al()
    return await asyncio.to_thread(depo.indir, kayit.nesne_anahtari)


def suresi_doldu_mu(kayit: KvkkIhraci, *, simdi: datetime | None = None) -> bool:
    """Artefaktın saklama süresi doldu mu (damga yoksa dolmamış sayılır)?"""
    if kayit.gecerlilik_bitisi is None:
        return False
    return (simdi or datetime.now(UTC)) >= kayit.gecerlilik_bitisi


def artefakti_isaretle(kayit: KvkkIhraci) -> str | None:
    """Kaydı ``suresi_doldu`` işaretler; silinecek nesne anahtarını döner (I/O YOK).

    **Sıra kritiktir:** önce DB işaretlenip COMMIT edilir, nesne SONRA silinir. Ters sıra
    (önce nesne, sonra commit) araya düşen bir çökmede dosyayı yok eder ama kaydı ``hazir``
    bırakır — depo ile DB kalıcı olarak tutarsızlaşır.

    Bu yüzden ``nesne_anahtari`` burada TEMİZLENMEZ: commit ile silme arasında çökme
    olursa anahtar kayıtta durduğu için yetim nesne bulunabilir kalır ve
    ``suresi_dolanlari_temizle`` onu bir sonraki koşuda toplar.
    """
    if kayit.durum == "suresi_doldu" and not kayit.nesne_anahtari:
        return None
    kayit.durum = "suresi_doldu"
    kayit.boyut = 0
    return kayit.nesne_anahtari or None


async def nesneyi_sil(anahtar: str) -> bool:
    """Nesneyi depodan siler (best-effort). Başarısızlık kaydı kilitlemez."""
    try:
        await asyncio.to_thread(nesne_depo_al().sil, anahtar)
        return True
    except Exception as exc:  # noqa: BLE001 — yetim nesneyi sonraki tarama toplar
        logger.warning("kvkk artefaktı silinemedi (%s): %s", anahtar, exc)
        return False


async def suresi_dolanlari_temizle(db: AsyncSession, *, slug: str) -> int:
    """Süresi dolan artefaktları imha eder + önceki koşulardan kalan yetimleri toplar.

    İki aşamalı, çökmeye dayanıklı sıra:
    1. Süresi dolan ``hazir`` kayıtlar ``suresi_doldu`` işaretlenir ve **commit edilir**.
    2. Nesneler depodan silinir; silme başarılıysa ``nesne_anahtari`` temizlenir.

    Ayrıca ``suresi_doldu`` olup anahtarı hâlâ dolu olan kayıtlar (1. ile 2. arasında
    çökülmüş) bu koşuda toplanır — bu yüzden tarama idempotent VE kendi kendini onarır.

    ``slug`` şart: ``search_path`` ``SET LOCAL`` ile kurulur, yani **transaction
    kapsamlıdır**. Aradaki commit onu düşürür; sonraki sorgular tenant şemasını
    göremez. Commit sonrası yeniden kurulur.
    """
    simdi = datetime.now(UTC)
    # (1) Süresi dolanları işaretle.
    dolanlar = (
        (
            await db.execute(
                select(KvkkIhraci).where(
                    KvkkIhraci.durum == "hazir",
                    KvkkIhraci.gecerlilik_bitisi.is_not(None),
                    KvkkIhraci.gecerlilik_bitisi <= simdi,
                )
            )
        )
        .scalars()
        .all()
    )
    sayi = 0
    for kayit in dolanlar:
        if artefakti_isaretle(kayit) is not None or kayit.durum == "suresi_doldu":
            sayi += 1
    await db.flush()
    await db.commit()  # ÖNCE kalıcı işaret, SONRA nesne imhası
    await search_path_ayarla(db, slug)  # commit SET LOCAL'i düşürdü — yeniden kur

    # (2) İşaretli ama nesnesi hâlâ duran kayıtları (bu koşudakiler + eski yetimler) temizle.
    yetimler = (
        (
            await db.execute(
                select(KvkkIhraci).where(
                    KvkkIhraci.durum == "suresi_doldu",
                    KvkkIhraci.nesne_anahtari != "",
                )
            )
        )
        .scalars()
        .all()
    )
    for kayit in yetimler:
        if await nesneyi_sil(kayit.nesne_anahtari):
            kayit.nesne_anahtari = ""
    await db.flush()
    return sayi


# --- Anonimleştirme (zincirleme maskeleme, denetim izli) ---
async def anonimlestir(
    db: AsyncSession, *, kisi_turu: str, kisi_id: int, yapan: Kullanici
) -> dict[str, Any]:
    """Kişisel veriyi maskeler; adli çekirdek (denetim eylem/kaynak/zaman) korunur.

    - ``kullanici``: e-posta/ad maskelenir, hesap pasifleştirilir, parola ve 2FA sırrı
      geçersiz kılınır; denetim izindeki e-posta/IP + oturum IP/istemci maskelenir.
    - ``personel``: ad/soyad/TC/telefon/e-posta/doğum tarihi maskelenir, pasifleştirilir.
    Kendi hesabını anonimleştirmek engellenir (kilitlenme koruması, 409).
    """
    kisi_turu_dogrula(kisi_turu)
    ozet: dict[str, Any] = {"kisi_turu": kisi_turu, "kisi_id": kisi_id}

    if kisi_turu == "kullanici":
        if kisi_id == yapan.id:
            raise CakismaHatasi("Kendi hesabınızı anonimleştiremezsiniz")
        hedef = (
            await db.execute(select(Kullanici).where(Kullanici.id == kisi_id))
        ).scalar_one_or_none()
        if hedef is None:
            raise KaynakBulunamadi("Kullanıcı bulunamadı")
        hedef.eposta = f"anonim-{kisi_id}@kvkk.yerel"
        hedef.ad_soyad = "ANONİMLEŞTİRİLDİ"
        hedef.aktif = False
        hedef.parola_ozet = parola_ozetle(secrets.token_urlsafe(24))
        hedef.totp_sirri = None
        hedef.iki_asama_aktif = False

        # Denetim izi: yalnız kişisel veri kolonları (trigger adli çekirdeği kilitler).
        denetimler = (
            (await db.execute(select(DenetimIzi).where(DenetimIzi.kullanici_id == kisi_id)))
            .scalars()
            .all()
        )
        for d in denetimler:
            d.kullanici_eposta = hedef.eposta
            d.ip_adresi = None
        ozet["denetim_maskelendi"] = len(denetimler)

        oturumlar = (
            (await db.execute(select(Oturum).where(Oturum.kullanici_id == kisi_id))).scalars().all()
        )
        for o in oturumlar:
            o.ip_adresi = None
            o.istemci = ""
            o.iptal = True
        ozet["oturum_maskelendi"] = len(oturumlar)
    else:
        hedef_p = (
            await db.execute(select(Personel).where(Personel.id == kisi_id))
        ).scalar_one_or_none()
        if hedef_p is None:
            raise KaynakBulunamadi("Personel bulunamadı")
        hedef_p.ad = "ANONİM"
        hedef_p.soyad = f"#{kisi_id}"
        hedef_p.tc_kimlik_no = ""
        hedef_p.telefon = ""
        hedef_p.eposta = ""
        hedef_p.dogum_tarihi = None
        hedef_p.aktif = False

    await db.flush()
    await denetim_yaz(
        db,
        eylem="kvkk_anonimlestir",
        kaynak="uyum",
        kaynak_id=f"{kisi_turu}:{kisi_id}",
        kullanici=yapan,
        detay=ozet,
    )
    return ozet
