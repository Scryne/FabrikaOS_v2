"""AI operatör eşleştirme (S-VB / ADR-0021) — kural-tabanlı, saf, deterministik.

İş emri gereksinimi ⋈ personel geçmişi → sıralı öneri. Model artefaktı gerekmez
(S13 çıkarım deseninin kural-tabanlı hafif üyesi); "beceri matrisi" (S26) ve vardiya
ataması (S24) geldiğinde skor derinleşir.

Skor bileşenleri (ağırlıklar sabit, toplam 1.0):

    skor = 0.5 * departman_uygunlugu   # iş türü ↔ personel departman/unvan eşleşmesi
         + 0.3 * gecmis_performans      # kapattığı iş emri sayısı (adaylar içinde normalize)
         + 0.2 * musaitlik              # bugün onaylı izinde değil

Girdi yoksa (geçmiş kapanış hiç yok) performans bileşeni 0'a düşer — bölme hatası
imkânsız. Sonuç kesin sıralıdır: (-skor, personel_id) — eşitlikte küçük id önce.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ik.models import IzinTalebi, Personel
from app.modules.isemri.models import IsEmri

# Bilinen iş türleri → departman/unvan anahtar kelimeleri (ascii-lower).
_TUR_ANAHTAR: dict[str, tuple[str, ...]] = {
    "uretim": ("uretim", "operator", "imalat"),
    "bakim": ("bakim", "teknik", "mekanik", "elektrik"),
    "kalite": ("kalite", "muayene"),
}


def _asciilestir(metin: str) -> str:
    """TR karakterleri sadeleştirip küçültür (deterministik eşleşme)."""
    tablo = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosucgiosu")
    return metin.translate(tablo).lower()


@dataclass(frozen=True)
class OperatorAdayi:
    """Skorlamaya giren personel özeti (DB'den toplanır, saf fonksiyona verilir)."""

    personel_id: int
    ad_soyad: str
    departman: str
    unvan: str
    kapatilan_is_emri: int
    izinli: bool


@dataclass(frozen=True)
class EslesmeSonucu:
    personel_id: int
    ad_soyad: str
    departman: str
    unvan: str
    skor: float
    gerekce: str


def departman_uygunlugu(aday: OperatorAdayi, is_turu: str) -> float:
    """İş türü ↔ departman/unvan eşleşmesi: departman 1.0 · unvan 0.8 · aksi 0.2.

    0.2 tabanı "çapraz görevlendirilebilir" varsayımıdır (hiç aday elenmesin);
    eşleşme sözlüğü ``_TUR_ANAHTAR`` tek doğruluk kaynağıdır.
    """
    anahtarlar = _TUR_ANAHTAR.get(_asciilestir(is_turu), (_asciilestir(is_turu),))
    departman = _asciilestir(aday.departman)
    unvan = _asciilestir(aday.unvan)
    if any(a in departman for a in anahtarlar):
        return 1.0
    if any(a in unvan for a in anahtarlar):
        return 0.8
    return 0.2


def operator_puanla(adaylar: list[OperatorAdayi], *, is_turu: str) -> list[EslesmeSonucu]:
    """Adayları skorlar ve kesin sıralı öneri listesi döner (saf, deterministik)."""
    en_cok_kapanis = max((a.kapatilan_is_emri for a in adaylar), default=0)
    sonuclar: list[EslesmeSonucu] = []
    for aday in adaylar:
        d = departman_uygunlugu(aday, is_turu)
        g = aday.kapatilan_is_emri / en_cok_kapanis if en_cok_kapanis > 0 else 0.0
        m = 0.0 if aday.izinli else 1.0
        skor = round(0.5 * d + 0.3 * g + 0.2 * m, 4)
        gerekce_parcalari = [
            f"departman uygunluğu {d:.1f}",
            f"geçmiş performans {g:.2f} ({aday.kapatilan_is_emri} kapanış)",
            "bugün izinli" if aday.izinli else "müsait",
        ]
        sonuclar.append(
            EslesmeSonucu(
                personel_id=aday.personel_id,
                ad_soyad=aday.ad_soyad,
                departman=aday.departman,
                unvan=aday.unvan,
                skor=skor,
                gerekce=" · ".join(gerekce_parcalari),
            )
        )
    return sorted(sonuclar, key=lambda s: (-s.skor, s.personel_id))


async def aday_topla(db: AsyncSession) -> list[OperatorAdayi]:
    """Aktif + kullanıcı hesabı bağlı personeli skorlama girdisiyle toplar.

    Tüm sorgular aktif ``search_path`` üzerinde koşar (tenant izole).
    """
    personeller = (
        (
            await db.execute(
                select(Personel).where(Personel.aktif, Personel.kullanici_id.isnot(None))
            )
        )
        .scalars()
        .all()
    )
    if not personeller:
        return []
    kullanici_idler = [p.kullanici_id for p in personeller if p.kullanici_id is not None]

    # Geçmiş performans: kullanıcı başına kapatılan iş emri sayısı (tek sorgu).
    kapanis_sayilari = dict(
        (
            await db.execute(
                select(IsEmri.atanan_kullanici_id, func.count())
                .where(
                    IsEmri.durum == "kapandi",
                    IsEmri.atanan_kullanici_id.in_(kullanici_idler),
                )
                .group_by(IsEmri.atanan_kullanici_id)
            )
        )
        .tuples()
        .all()
    )

    # Müsaitlik: bugün onaylı izin kapsamında olan personel kümesi (tek sorgu).
    bugun = func.current_date()
    izinli_personel = set(
        (
            await db.execute(
                select(IzinTalebi.personel_id).where(
                    IzinTalebi.durum == "onaylandi",
                    IzinTalebi.baslangic_tarihi <= bugun,
                    IzinTalebi.bitis_tarihi >= bugun,
                )
            )
        )
        .scalars()
        .all()
    )

    return [
        OperatorAdayi(
            personel_id=p.id,
            ad_soyad=f"{p.ad} {p.soyad}",
            departman=p.departman,
            unvan=p.unvan,
            kapatilan_is_emri=int(kapanis_sayilari.get(p.kullanici_id, 0)),
            izinli=p.id in izinli_personel,
        )
        for p in personeller
    ]
