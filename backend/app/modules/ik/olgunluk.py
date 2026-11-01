"""S26-B İK servisleri (ADR-0044): izin bakiyesi, org şeması, işe giriş/çıkış kontrol listesi.

**Bakiye onayda zorlanır, talepte değil** (işe giriş tarihi girilmiş personelde; tarih yoksa kıdem
bilinmez, kapı uygulanmaz ve ekran bunu söyler). Talepte bakiye yalnız uyarıdır; asıl
kapı onaydır, çünkü iki talep aynı bakiyeyi ayrı ayrı "yeterli" görebilir. Onay, personel satırı
``FOR UPDATE`` ile kilitlenip bakiye yeniden hesaplanarak verilir: eşzamanlı iki onaydan ikincisi
güncel kullanılanı görür ve 409 ``IZIN_BAKIYE_YETERSIZ`` alır.

**Org şeması döngü kabul etmez.** Yönetici zinciri yukarı yürünür; atanan kişi zincirde
görünürse 409 ``ORG_DONGU``.

**Çıkış listesi açık zimmetle kapanmaz.** "Zimmet iadesi" maddesi, personelin ``zimmetli``
durumda kaydı varken işaretlenemez (409 ``ACIK_ZIMMET``); liste tamamlanınca personel pasifleşir.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.zaman import is_gunu
from app.kimlik.models import Kullanici
from app.modules.ik.izin_hakedis import IzinBakiyesi, izin_bakiyesi
from app.modules.ik.models import IzinTalebi, Personel, PersonelKontrolListesi, Zimmet

KONTROL_SABLONLARI: dict[str, list[tuple[str, str]]] = {
    "giris": [
        ("is_sozlesmesi", "İş sözleşmesi imzalandı"),
        ("sgk_giris", "SGK işe giriş bildirgesi verildi"),
        ("ozluk_dosyasi", "Özlük dosyası belgeleri tamamlandı"),
        ("isg_temel_egitim", "Temel İSG eğitimi verildi"),
        ("kkd_teslim", "Gerekli KKD teslim edildi"),
        ("sistem_hesabi", "Sistem hesabı ve yetkileri açıldı"),
    ],
    "cikis": [
        ("zimmet_iade", "Zimmetler iade alındı"),
        ("sistem_hesabi_kapat", "Sistem hesabı kapatıldı"),
        ("sgk_cikis", "SGK işten ayrılış bildirgesi verildi"),
        ("son_bordro", "Son bordro ve ödemeler yapıldı"),
        ("ibraname", "İbraname / çıkış belgeleri imzalandı"),
    ],
}


class BakiyeYetersiz(CakismaHatasi):
    hata_kodu = "IZIN_BAKIYE_YETERSIZ"


class OrgDongu(CakismaHatasi):
    hata_kodu = "ORG_DONGU"


class AcikZimmet(CakismaHatasi):
    hata_kodu = "ACIK_ZIMMET"


# ── İzin bakiyesi ────────────────────────────────────────────────────────────


async def kullanilan_yillik(db: AsyncSession, personel_id: int) -> int:
    toplam = await db.scalar(
        select(func.coalesce(func.sum(IzinTalebi.gun_sayisi), 0)).where(
            IzinTalebi.personel_id == personel_id,
            IzinTalebi.izin_turu == "yillik",
            IzinTalebi.durum == "onaylandi",
        )
    )
    return int(toplam or 0)


async def bakiye_hesapla(
    db: AsyncSession, personel: Personel, bugun: date | None = None
) -> IzinBakiyesi:
    return izin_bakiyesi(
        ise_giris=personel.ise_giris_tarihi,
        dogum=personel.dogum_tarihi,
        bugun=bugun or is_gunu(),
        kullanilan=await kullanilan_yillik(db, personel.id),
        sozlesme_hakki=personel.yillik_izin_hakki,
    )


async def onay_oncesi_bakiye_kontrol(db: AsyncSession, izin: IzinTalebi) -> None:
    """Yıllık izin onayından hemen önce: personeli kilitle, bakiyeyi taze hesapla."""
    if izin.izin_turu != "yillik":
        return
    personel = (
        await db.execute(select(Personel).where(Personel.id == izin.personel_id).with_for_update())
    ).scalar_one()
    if personel.ise_giris_tarihi is None:
        return  # kıdem bilinmiyor → bakiye hesaplanamaz; ekran bunu söyler, kapı uygulanmaz
    b = await bakiye_hesapla(db, personel)
    if izin.gun_sayisi > b.bakiye:
        raise BakiyeYetersiz(
            f"Yıllık izin bakiyesi yetersiz: talep {izin.gun_sayisi} gün, kalan {b.bakiye} gün",
            detaylar=[
                {"alan": "gun_sayisi", "mesaj": f"kalan {b.bakiye}, talep {izin.gun_sayisi}"}
            ],
        )


# ── Org şeması ───────────────────────────────────────────────────────────────


async def yonetici_ata(db: AsyncSession, personel: Personel, yonetici_id: int | None) -> None:
    if yonetici_id is None:
        personel.yonetici_id = None
        await db.flush()
        return
    if yonetici_id == personel.id:
        raise DogrulamaHatasi(
            "Personel kendi yöneticisi olamaz",
            detaylar=[{"alan": "yonetici_id", "mesaj": "kendisi"}],
        )
    yonetici = await db.get(Personel, yonetici_id)
    if yonetici is None:
        raise KaynakBulunamadi("Yönetici personel bulunamadı")
    # Zinciri yukarı yürü: atanacak yöneticinin üstlerinde personel varsa döngü olur.
    gorulen: set[int] = set()
    ust: int | None = yonetici.id
    while ust is not None and ust not in gorulen:
        if ust == personel.id:
            raise OrgDongu(
                "Bu atama org şemasında döngü oluşturur",
                detaylar=[{"alan": "yonetici_id", "mesaj": "yönetici, personelin astı"}],
            )
        gorulen.add(ust)
        ust = await db.scalar(select(Personel.yonetici_id).where(Personel.id == ust))
    personel.yonetici_id = yonetici_id
    await db.flush()


async def org_semasi(db: AsyncSession, departman: str | None = None) -> list[dict[str, Any]]:
    """Aktif personel düz listesi (yönetici kimliğiyle); ağacı istemci kurar."""
    sorgu = select(Personel).where(Personel.aktif.is_(True)).order_by(Personel.ad, Personel.soyad)
    if departman:
        sorgu = sorgu.where(Personel.departman == departman)
    kisiler = (await db.execute(sorgu)).scalars().all()
    kimlikler = {p.id for p in kisiler}
    ast_sayisi: dict[int, int] = {}
    for p in kisiler:
        if p.yonetici_id is not None:
            ast_sayisi[p.yonetici_id] = ast_sayisi.get(p.yonetici_id, 0) + 1
    return [
        {
            "id": p.id,
            "ad_soyad": f"{p.ad} {p.soyad}",
            "unvan": p.unvan,
            "departman": p.departman,
            # Süzülmüş görünümde yöneticisi dışarıda kalan kişi kök olur.
            "yonetici_id": p.yonetici_id if p.yonetici_id in kimlikler else None,
            "ast_sayisi": ast_sayisi.get(p.id, 0),
        }
        for p in kisiler
    ]


# ── Kontrol listesi ──────────────────────────────────────────────────────────


async def liste_ac(db: AsyncSession, personel: Personel, tur: str) -> PersonelKontrolListesi:
    """Listeyi şablondan açar; varsa olanı döner (idempotent)."""
    if tur not in KONTROL_SABLONLARI:
        raise DogrulamaHatasi(
            "Geçersiz liste türü", detaylar=[{"alan": "tur", "mesaj": "giris | cikis"}]
        )
    mevcut = await db.scalar(
        select(PersonelKontrolListesi).where(
            PersonelKontrolListesi.personel_id == personel.id, PersonelKontrolListesi.tur == tur
        )
    )
    if mevcut is not None:
        return mevcut
    liste = PersonelKontrolListesi(
        personel_id=personel.id,
        tur=tur,
        maddeler=[
            {
                "anahtar": a,
                "ad": ad,
                "tamam": False,
                "tamamlayan_kullanici_id": None,
                "zaman": None,
            }
            for a, ad in KONTROL_SABLONLARI[tur]
        ],
    )
    db.add(liste)
    await db.flush()
    return liste


async def acik_zimmet_sayisi(db: AsyncSession, personel_id: int) -> int:
    return int(
        await db.scalar(
            select(func.count())
            .select_from(Zimmet)
            .where(Zimmet.personel_id == personel_id, Zimmet.durum == "zimmetli")
        )
        or 0
    )


async def madde_isaretle(
    db: AsyncSession,
    liste: PersonelKontrolListesi,
    anahtar: str,
    tamam: bool,
    kullanici: Kullanici,
) -> PersonelKontrolListesi:
    if liste.durum == "tamamlandi":
        raise CakismaHatasi("Tamamlanmış liste değiştirilemez")
    maddeler = [dict(m) for m in liste.maddeler]
    madde = next((m for m in maddeler if m["anahtar"] == anahtar), None)
    if madde is None:
        raise KaynakBulunamadi("Kontrol maddesi bulunamadı")
    if tamam and liste.tur == "cikis" and anahtar == "zimmet_iade":
        adet = await acik_zimmet_sayisi(db, liste.personel_id)
        if adet:
            raise AcikZimmet(
                f"Personelde {adet} açık zimmet var; önce iade alın",
                detaylar=[{"alan": "zimmet_iade", "mesaj": f"{adet} açık zimmet"}],
            )
    madde["tamam"] = tamam
    madde["tamamlayan_kullanici_id"] = kullanici.id if tamam else None
    madde["zaman"] = datetime.now(UTC).isoformat() if tamam else None
    liste.maddeler = maddeler  # JSONB değişimi yeni liste ataması ile izlenir
    if all(m["tamam"] for m in maddeler):
        liste.durum = "tamamlandi"
        liste.tamamlanma_tarihi = datetime.now(UTC)
        if liste.tur == "cikis":
            personel = await db.get(Personel, liste.personel_id)
            if personel is not None:
                personel.aktif = False
    await db.flush()
    return liste
