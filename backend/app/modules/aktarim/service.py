"""İçe aktarma: önizleme (hiçbir şey yazmaz) ve uygulama (hepsi ya da hiçbiri) — S21, ADR-0042.

Önizleme her satır için ``yeni`` / ``guncelle`` / ``ayni`` / ``hata`` döner; uygulama aynı
dosyayı yeniden doğrular ve tek bir hata bile varsa hiçbir şey yazmaz. Anahtar eşleşmesi
idempotenttir: aynı dosyayı ikinci kez uygulamak her satırı ``ayni`` bulur.

Güncellemede **yalnız dosyadaki dolu hücreler** yazılır: boş hücre "değiştirme" demektir,
mevcut değeri silmez (kısmi bir tabloyla güncelleme yapılabilsin diye).
Önizleme yanıtı değer taşımaz (anahtar, işlem, değişen alan adları, hata): personel
dosyasındaki T.C. kimlik no ve iletişim bilgisi yanıta, dolayısıyla tarayıcı belleğine girmez.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import denetim_yaz
from app.core.exceptions import DogrulamaHatasi
from app.kimlik.models import Kullanici
from app.modules.aktarim.tanimlar import AlanHatasi, Tur
from app.modules.crm.models import Firma
from app.modules.ik.models import Personel
from app.modules.stok import depo_service
from app.modules.stok.models import Depo, Lokasyon, Malzeme, StokHareketi
from app.modules.stok.service import stok_hareketi_uygula
from app.modules.uretim.models import Makine

ONIZLEME_SATIR_SINIRI = 500  # yanıtta satır ayrıntısı; sayılar her zaman tam

_MODELLER: dict[str, Any] = {
    "firma": Firma,
    "makine": Makine,
    "malzeme": Malzeme,
    "personel": Personel,
}
# Dosya kolonu → model alanı (yalnız adı farklı olanlar).
_MODEL_ALANI = {"tedarikci_vergi_no": "tedarikci_firma_id"}


@dataclass
class SatirSonucu:
    satir: int
    anahtar: str
    islem: str  # yeni | guncelle | ayni | hata
    hatalar: list[dict[str, str]] = field(default_factory=list)
    degisen: list[str] = field(default_factory=list)


@dataclass
class _Hazir:
    sonuc: SatirSonucu
    degerler: dict[str, Any]
    mevcut: Any = None
    ek: dict[str, Any] = field(default_factory=dict)


@dataclass
class Onizleme:
    tur: str
    toplam: int
    yeni: int
    guncelle: int
    ayni: int
    hatali: int
    eksik_kolonlar: list[str]
    bilinmeyen_kolonlar: list[str]
    satirlar: list[SatirSonucu]


def _anahtar_metni(tur: Tur, d: dict[str, Any]) -> str:
    if tur.kod == "firma":
        return str(d.get("vergi_no") or d.get("ad", ""))
    return " / ".join(str(d.get(a) or "") for a in tur.anahtar).strip(" /")


def _firma_anahtari(d: dict[str, Any]) -> tuple[str, str]:
    return ("v", d["vergi_no"]) if d.get("vergi_no") else ("a", str(d.get("ad", "")).casefold())


async def _hazirla(
    db: AsyncSession, tur: Tur, satirlar: list[dict[str, str]]
) -> tuple[list[_Hazir], list[str], list[str]]:
    kolonlar = set(satirlar[0]) if satirlar else set()
    bilinen = {a.ad for a in tur.alanlar}
    eksik = [a.ad for a in tur.alanlar if a.zorunlu and a.ad not in kolonlar]
    bilinmeyen = sorted(kolonlar - bilinen)

    hazir: list[_Hazir] = []
    gorulen: dict[Any, int] = {}
    for i, ham in enumerate(satirlar, start=2):  # 1. satır başlık
        hatalar: list[dict[str, str]] = []
        degerler: dict[str, Any] = {}
        for alan in tur.alanlar:
            hucre = (ham.get(alan.ad) or "").strip()
            if not hucre:
                if alan.zorunlu:
                    hatalar.append({"alan": alan.ad, "mesaj": "Zorunlu"})
                continue
            try:
                degerler[alan.ad] = alan.donustur(hucre)
            except AlanHatasi as exc:
                hatalar.append({"alan": alan.ad, "mesaj": str(exc)})
        sonuc = SatirSonucu(
            satir=i, anahtar=_anahtar_metni(tur, degerler), islem="hata", hatalar=hatalar
        )
        if not hatalar:
            k = (
                _firma_anahtari(degerler)
                if tur.kod == "firma"
                else tuple(degerler.get(a) or "" for a in tur.anahtar)
            )
            if k in gorulen:
                hatalar.append(
                    {"alan": tur.anahtar[0], "mesaj": f"Dosyada {gorulen[k]}. satırla aynı kayıt"}
                )
            else:
                gorulen[k] = i
        hazir.append(_Hazir(sonuc=sonuc, degerler=degerler))

    if eksik:
        for h in hazir:
            h.sonuc.hatalar.insert(
                0, {"alan": ", ".join(eksik), "mesaj": "Dosyada zorunlu kolon yok"}
            )
        return hazir, eksik, bilinmeyen

    gecerli = [h for h in hazir if not h.sonuc.hatalar]
    if tur.kod == "acilis_stogu":
        await _acilis_esle(db, gecerli)
    else:
        await _kayit_esle(db, tur, gecerli)
    for h in hazir:
        if h.sonuc.hatalar:
            h.sonuc.islem = "hata"
    return hazir, eksik, bilinmeyen


async def _kayit_esle(db: AsyncSession, tur: Tur, hazir: list[_Hazir]) -> None:
    model = _MODELLER[tur.kod]
    if tur.kod == "firma":
        vergiler = [h.degerler["vergi_no"] for h in hazir if h.degerler.get("vergi_no")]
        adlar = [str(h.degerler["ad"]).casefold() for h in hazir if not h.degerler.get("vergi_no")]
        mevcutlar: dict[Any, Any] = {}
        if vergiler:
            for f in (
                await db.execute(select(Firma).where(Firma.vergi_no.in_(vergiler)))
            ).scalars():
                mevcutlar[("v", f.vergi_no)] = f
        if adlar:
            for f in (
                await db.execute(select(Firma).where(func.lower(Firma.ad).in_(adlar)))
            ).scalars():
                mevcutlar.setdefault(("a", f.ad.casefold()), f)
        for h in hazir:
            h.mevcut = mevcutlar.get(_firma_anahtari(h.degerler))
    else:
        alan = tur.anahtar[0]
        degerler = [h.degerler[alan] for h in hazir]
        kolon = getattr(model, alan)
        kayitlar: list[Any] = (
            list((await db.execute(select(model).where(kolon.in_(degerler)))).scalars())
            if degerler
            else []
        )
        mevcutlar = {getattr(m, alan): m for m in kayitlar}
        for h in hazir:
            h.mevcut = mevcutlar.get(h.degerler[alan])

    if tur.kod == "malzeme":
        tedarikci_vergileri = {
            h.degerler["tedarikci_vergi_no"] for h in hazir if "tedarikci_vergi_no" in h.degerler
        }
        firmalar = (
            {
                f.vergi_no: f.id
                for f in (
                    await db.execute(select(Firma).where(Firma.vergi_no.in_(tedarikci_vergileri)))
                ).scalars()
            }
            if tedarikci_vergileri
            else {}
        )
        for h in hazir:
            vn = h.degerler.pop("tedarikci_vergi_no", None)
            if vn is None:
                continue
            if vn not in firmalar:
                h.sonuc.hatalar.append(
                    {
                        "alan": "tedarikci_vergi_no",
                        "mesaj": "Bu vergi numarasıyla firma yok (önce firmaları yükleyin)",
                    }
                )
            else:
                h.degerler["tedarikci_firma_id"] = firmalar[vn]

    for h in hazir:
        if h.sonuc.hatalar:
            continue
        if h.mevcut is None:
            h.sonuc.islem = "yeni"
            continue
        degisen = [
            a for a, v in h.degerler.items() if getattr(h.mevcut, _MODEL_ALANI.get(a, a)) != v
        ]
        h.sonuc.degisen = [next((k for k, m in _MODEL_ALANI.items() if m == a), a) for a in degisen]
        h.sonuc.islem = "guncelle" if degisen else "ayni"


async def _lokasyon_id(db: AsyncSession, yol: str | None) -> int | None:
    if not yol:
        return await depo_service.varsayilan_lokasyon_id(db)
    depo_kod, _, lok_kod = yol.partition("/")
    return (
        await db.execute(
            select(Lokasyon.id)
            .join(Depo, Depo.id == Lokasyon.depo_id)
            .where(Depo.kod == depo_kod.strip(), Lokasyon.kod == lok_kod.strip())
        )
    ).scalar_one_or_none()


def acilis_anahtari(malzeme_id: int, lokasyon_id: int, lot_no: str) -> str:
    return f"acilis:{malzeme_id}:{lokasyon_id}:{lot_no}"[:64]


async def _acilis_esle(db: AsyncSession, hazir: list[_Hazir]) -> None:
    kodlar = list({h.degerler["malzeme_kod"] for h in hazir})
    malzemeler = (
        {
            m.kod: m
            for m in (await db.execute(select(Malzeme).where(Malzeme.kod.in_(kodlar)))).scalars()
        }
        if kodlar
        else {}
    )
    for h in hazir:
        d = h.degerler
        malzeme = malzemeler.get(d["malzeme_kod"])
        if malzeme is None:
            h.sonuc.hatalar.append(
                {
                    "alan": "malzeme_kod",
                    "mesaj": "Böyle bir malzeme yok (önce malzemeleri yükleyin)",
                }
            )
            continue
        lokasyon_id = await _lokasyon_id(db, d.get("lokasyon"))
        if lokasyon_id is None:
            h.sonuc.hatalar.append(
                {"alan": "lokasyon", "mesaj": "Lokasyon bulunamadı (DEPO/LOKASYON kodu)"}
            )
            continue
        lot = d.get("lot_no", "")
        if malzeme.lot_takipli and not lot:
            h.sonuc.hatalar.append(
                {"alan": "lot_no", "mesaj": "Lot takipli malzemede lot no zorunlu"}
            )
            continue
        anahtar = acilis_anahtari(malzeme.id, lokasyon_id, lot)
        onceki = (
            await db.execute(
                select(StokHareketi).where(StokHareketi.idempotency_anahtari == anahtar)
            )
        ).scalar_one_or_none()
        h.ek = {"malzeme": malzeme, "lokasyon_id": lokasyon_id, "lot_no": lot, "anahtar": anahtar}
        if onceki is None:
            h.sonuc.islem = "yeni"
        elif Decimal(onceki.miktar) == d["miktar"]:
            h.sonuc.islem = "ayni"
        else:
            h.sonuc.hatalar.append(
                {
                    "alan": "miktar",
                    "mesaj": f"Açılış stoğu zaten {onceki.miktar} girilmiş; "
                    "fark için sayım kullanın",
                }
            )


def _ozet(tur: Tur, hazir: list[_Hazir], eksik: list[str], bilinmeyen: list[str]) -> Onizleme:
    say = {
        k: sum(1 for h in hazir if h.sonuc.islem == k) for k in ("yeni", "guncelle", "ayni", "hata")
    }
    return Onizleme(
        tur=tur.kod,
        toplam=len(hazir),
        yeni=say["yeni"],
        guncelle=say["guncelle"],
        ayni=say["ayni"],
        hatali=say["hata"],
        eksik_kolonlar=eksik,
        bilinmeyen_kolonlar=bilinmeyen,
        satirlar=[h.sonuc for h in hazir][:ONIZLEME_SATIR_SINIRI],
    )


async def onizle(db: AsyncSession, tur: Tur, satirlar: list[dict[str, str]]) -> Onizleme:
    hazir, eksik, bilinmeyen = await _hazirla(db, tur, satirlar)
    return _ozet(tur, hazir, eksik, bilinmeyen)


async def uygula(
    db: AsyncSession, tur: Tur, satirlar: list[dict[str, str]], kullanici: Kullanici, dosya_adi: str
) -> Onizleme:
    hazir, eksik, bilinmeyen = await _hazirla(db, tur, satirlar)
    ozet = _ozet(tur, hazir, eksik, bilinmeyen)
    if ozet.hatali or ozet.toplam == 0:
        hatalar = [
            {"alan": f"satır {h.sonuc.satir} · {e['alan']}", "mesaj": e["mesaj"]}
            for h in hazir
            for e in h.sonuc.hatalar
        ][:50]
        raise DogrulamaHatasi(
            f"{ozet.hatali} satırda hata var; hiçbir kayıt yazılmadı"
            if ozet.hatali
            else "Dosyada satır yok",
            hata_kodu="ICE_AKTARMA_HATALI",
            detaylar=hatalar,
        )

    for h in hazir:
        if h.sonuc.islem == "ayni":
            continue
        if tur.kod == "acilis_stogu":
            await stok_hareketi_uygula(
                db,
                h.ek["malzeme"],
                tur="giris",
                miktar=h.degerler["miktar"],
                aciklama="Açılış stoğu (içe aktarma)",
                kaynak="acilis",
                kullanici=kullanici,
                idempotency_anahtari=h.ek["anahtar"],
                lokasyon_id=h.ek["lokasyon_id"],
                lot_no=h.ek["lot_no"],
            )
        elif h.mevcut is None:
            db.add(_MODELLER[tur.kod](**h.degerler))
        else:
            for alan, deger in h.degerler.items():
                setattr(h.mevcut, alan, deger)
    await db.flush()
    await denetim_yaz(
        db,
        eylem="ice_aktar",
        kaynak=tur.kod,
        kullanici=kullanici,
        detay={"dosya": dosya_adi, "yeni": ozet.yeni, "guncelle": ozet.guncelle, "ayni": ozet.ayni},
    )
    return ozet
