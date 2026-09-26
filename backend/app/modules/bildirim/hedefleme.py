"""Olay → hedef kullanıcı yönlendirme kuralları (saf, DB'siz, tablo-testli).

Sistem olayları gövdede kullanıcı taşımaz; hedef **izne göre** belirlenir (rol-tabanlı).
Kişi-hedefli olaylar (``rapor.hazir``, ``sla.asildi`` sorumlusu) gövdedeki kullanıcıya
gider. Kural tablosu tek doğruluk kaynağıdır; yeni olay eklemek = tabloya satır.

``bildirim_metni`` bildirimin TR referans başlık/gövdesini üretir (FE kendi i18n
etiketini ``olay_turu`` üzerinden de kurabilir; saklanan metin denetim içindir).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class HedefKurali:
    """Bir olay türünün bildirim yönlendirme kuralı.

    - ``izin_kodu``: bu izne sahip tüm aktif kullanıcılar hedeftir (None = izin hedefi yok).
    - ``kisi_alanlari``: gövdeden okunacak kullanıcı-id alanları (kişi-hedefli olaylar).
    - ``herkese``: tüm aktif kullanıcılar (duyuru).
    - ``onem``: üretilen bildirimin önem düzeyi.
    """

    onem: str = "bilgi"
    izin_kodu: str | None = None
    kisi_alanlari: tuple[str, ...] = field(default_factory=tuple)
    herkese: bool = False


# Olay türü -> yönlendirme kuralı. ``sla.asildi`` kaynak modüle göre dinamiktir
# (bkz. ``bildirim_hedef_kurali``); tabloda temel kuralı durur.
BILDIRIM_OLAYLARI: dict[str, HedefKurali] = {
    "stok.kritik": HedefKurali(onem="uyari", izin_kodu="stok:oku"),
    "sozlesme.yaklasiyor": HedefKurali(onem="uyari", izin_kodu="crm:oku"),
    "anomali.tespit": HedefKurali(onem="kritik", izin_kodu="ai:oku"),
    "rapor.hazir": HedefKurali(onem="bilgi", kisi_alanlari=("olusturan_kullanici_id",)),
    "ariza.olustu": HedefKurali(onem="kritik", izin_kodu="uretim:oku"),
    "oee.dustu": HedefKurali(onem="uyari", izin_kodu="uretim:oku"),
    "sla.asildi": HedefKurali(onem="uyari", kisi_alanlari=("sorumlu_kullanici_id",)),
    "duyuru.yeni": HedefKurali(onem="bilgi", herkese=True),
}

# ``sla.asildi`` kaynak türü -> ilgili modülün okuma izni (sorumluya ek hedef kümesi).
_SLA_KAYNAK_IZNI: dict[str, str] = {
    "is_emri": "isemri:oku",
    "talep": "talep:oku",
}


def bildirim_hedef_kurali(olay_turu: str, govde: dict[str, Any]) -> HedefKurali | None:
    """Olayın etkin yönlendirme kuralını döner (bildirim üretmeyen tür → ``None``).

    ``sla.asildi`` için kaynak modülün okuma izni gövdedeki ``kaynak_tur``'dan
    türetilir; sorumlu kullanıcı (varsa) her durumda hedeftir.
    """
    kural = BILDIRIM_OLAYLARI.get(olay_turu)
    if kural is None:
        return None
    if olay_turu == "sla.asildi":
        izin = _SLA_KAYNAK_IZNI.get(str(govde.get("kaynak_tur", "")))
        return HedefKurali(onem=kural.onem, izin_kodu=izin, kisi_alanlari=kural.kisi_alanlari)
    return kural


def _kod(govde: dict[str, Any]) -> str:
    """Gövdeden insan-okur kaynak kodu (yoksa id, o da yoksa boş)."""
    for alan in ("kod", "makine_kodu", "malzeme_kodu"):
        deger = govde.get(alan)
        if deger:
            return str(deger)
    kaynak_id = govde.get("kaynak_id") or govde.get("id")
    return f"#{kaynak_id}" if kaynak_id is not None else ""


def _anomali_ozeti(govde: dict[str, Any]) -> str:
    """Anomali olayında ``kod`` yok; makine kodları (yoksa bulgu sayısı) özetlenir.

    Eski olaylar yalnız ``anomali_sayisi`` taşır — başlık "AI anomali tespiti: " diye boş
    bitiyordu.
    """
    kodlar = [str(k) for k in govde.get("makine_kodlari") or []]
    if kodlar:
        ek = f" +{len(kodlar) - 3}" if len(kodlar) > 3 else ""
        return ", ".join(kodlar[:3]) + ek
    sayi = govde.get("anomali_sayisi")
    return f"{sayi} bulgu" if sayi else "yeni bulgu"


def bildirim_metni(olay_turu: str, govde: dict[str, Any]) -> tuple[str, str]:
    """Olay için (başlık, gövde) TR referans metnini üretir — deterministik."""
    kod = _kod(govde)
    metinler: dict[str, tuple[str, str]] = {
        "stok.kritik": (
            f"Stok kritik eşiğin altında: {kod}",
            "Malzeme bakiyesi kritik stok seviyesinin altına indi.",
        ),
        "sozlesme.yaklasiyor": (
            f"Sözleşme bitişi yaklaşıyor: {kod}",
            "Sözleşmenin bitiş tarihine 30 günden az kaldı.",
        ),
        "anomali.tespit": (
            f"AI anomali tespiti: {_anomali_ozeti(govde)}",
            "Makine verisinde anormal örüntü tespit edildi.",
        ),
        "rapor.hazir": (
            f"Raporunuz hazır: {kod}",
            "Talep ettiğiniz rapor üretildi ve indirilebilir.",
        ),
        "ariza.olustu": (
            f"Arıza kaydı oluştu: {kod}",
            "Bir makine için yeni arıza kaydı açıldı.",
        ),
        "oee.dustu": (
            f"OEE hedefin altında: {kod}",
            "Makinenin OEE değeri hedefin altına düştü.",
        ),
        "sla.asildi": (
            f"SLA hedef tarihi aşıldı: {kod}",
            "Kayıt hedef tarihini geçtiği hâlde hâlâ açık.",
        ),
        "duyuru.yeni": (
            str(govde.get("baslik") or "Yeni duyuru"),
            "Yeni bir kurumsal duyuru yayınlandı.",
        ),
    }
    return metinler.get(olay_turu, (olay_turu, ""))


def bildirim_verisi(olay_turu: str, govde: dict[str, Any]) -> dict[str, Any]:
    """FE derin-bağlantısı için {kaynak_tur, kaynak_id} verisi (saf)."""
    varsayilan_kaynak: dict[str, str] = {
        "stok.kritik": "malzeme",
        "sozlesme.yaklasiyor": "sozlesme",
        "anomali.tespit": "makine",
        "rapor.hazir": "rapor",
        "ariza.olustu": "ariza",
        "oee.dustu": "makine",
        "duyuru.yeni": "duyuru",
    }
    kaynak_tur = str(govde.get("kaynak_tur") or varsayilan_kaynak.get(olay_turu, ""))
    kaynak_id = govde.get("kaynak_id") or govde.get("id")
    veri: dict[str, Any] = {}
    if kaynak_tur:
        veri["kaynak_tur"] = kaynak_tur
    if kaynak_id is not None:
        veri["kaynak_id"] = kaynak_id
    return veri
