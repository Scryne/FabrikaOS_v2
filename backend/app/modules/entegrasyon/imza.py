"""Webhook imza + zarf + backoff çekirdeği (saf fonksiyonlar; S18 / ADR-0020).

İmza şeması (Stripe deseni): ``X-FabrikaOS-Signature: t=<unix>,v1=<hex>`` — imzalanan
içerik ``f"{t}." + govde_bytes``'tır. Zaman damgası imzaya dahil olduğundan alıcı,
``tolerans_sn`` penceresiyle yeniden-oynatmayı (replay) reddedebilir. ``v1`` imza
şeması sürümüdür; zarfın kendi ``surum`` alanı (payload v1) ondan bağımsızdır.

Alıcı tarafın doğrulama reçetesi (ADR-0020'de belgelidir):
1. Başlıktan ``t`` ve ``v1``'i ayır.
2. ``HMAC-SHA256(gizli_anahtar, f"{t}." + ham_govde)`` hesapla.
3. Sabit-zaman karşılaştır ve ``|şimdi - t| <= tolerans`` doğrula.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.core.olaylar import GidenOlay

IMZA_BASLIGI = "X-FabrikaOS-Signature"
OLAY_BASLIGI = "X-FabrikaOS-Olay"
TESLIMAT_BASLIGI = "X-FabrikaOS-Teslimat"

ZARF_SURUMU = "v1"

# Başarısız denemeler arası bekleme: 1dk, 5dk, 30dk, 2sa, 6sa.
DENEME_ARALIKLARI_SN: tuple[int, ...] = (60, 300, 1800, 7200, 21600)
# İlk deneme + her aralık için bir retry = toplam 6 deneme; sonrası terminal `basarisiz`.
MAKS_DENEME = len(DENEME_ARALIKLARI_SN) + 1


def gizli_anahtar_uret() -> str:
    """Yeni abonelik imza anahtarı: ``whs_`` + 43 char urlsafe rastgele."""
    return f"whs_{secrets.token_urlsafe(32)}"


def imza_uret(gizli_anahtar: str, zaman: int, govde: bytes) -> str:
    """``t=<unix>,v1=<hex>`` imza başlık değeri üretir."""
    mac = hmac.new(gizli_anahtar.encode(), f"{zaman}.".encode() + govde, hashlib.sha256)
    return f"t={zaman},v1={mac.hexdigest()}"


def imza_dogrula(
    gizli_anahtar: str, baslik: str, govde: bytes, *, simdi: int, tolerans_sn: int = 300
) -> bool:
    """İmza başlığını doğrular: biçim + sabit-zaman HMAC eşleşmesi + zaman toleransı."""
    try:
        parcalar = dict(p.split("=", 1) for p in baslik.split(","))
        zaman = int(parcalar["t"])
        verilen = parcalar["v1"]
    except (ValueError, KeyError):
        return False
    if abs(simdi - zaman) > tolerans_sn:
        return False
    beklenen = imza_uret(gizli_anahtar, zaman, govde).split("v1=", 1)[1]
    return hmac.compare_digest(beklenen, verilen)


def zarf_olustur(olay: GidenOlay) -> dict[str, Any]:
    """Outbox olayından sürümlü teslimat zarfı (payload v1) üretir."""
    return {
        "surum": ZARF_SURUMU,
        "olay_turu": olay.olay_turu,
        "dis_anahtar": str(olay.dis_anahtar),
        "olusturma_tarihi": olay.olusturma_tarihi.isoformat(),
        "veri": olay.govde,
    }


def zarf_bytelari(zarf: dict[str, Any]) -> bytes:
    """Zarfın gönderilecek (ve imzalanacak) bayt hâli — imza ile gövde AYNI kaynaktan.

    Deterministik serileştirme (ayraçlar sabit, ASCII'ye zorlamadan) — alıcı ham gövdeyi
    olduğu gibi imzalayarak doğrular, yeniden serileştirme gerekmez.
    """
    return json.dumps(zarf, ensure_ascii=False, separators=(",", ":")).encode()


def sonraki_deneme_gecikmesi_sn(deneme_sayisi: int) -> int | None:
    """``deneme_sayisi`` başarısız denemeden sonra bekleme süresi; ``None`` = terminal.

    1. deneme sonrası 60 sn ... 5. deneme sonrası 21600 sn; 6. deneme son şanstır
    (``MAKS_DENEME``) — başarısızsa teslimat ``basarisiz``'a düşer.
    """
    if deneme_sayisi < 1 or deneme_sayisi >= MAKS_DENEME:
        return None
    return DENEME_ARALIKLARI_SN[deneme_sayisi - 1]
