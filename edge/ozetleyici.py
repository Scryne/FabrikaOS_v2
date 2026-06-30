"""Aralık özetleme: iki ham sayaç görüntüsü arasındaki farktan UretimVerisi-şekilli paket.

Saf fonksiyon (yan etkisiz, ``olcum_id`` hariç deterministik). Negatif delta'lar 0'a
kırpılır (sayaç sıfırlama/taşma koruması).
"""

from __future__ import annotations

from edge.paket import HamOkuma, OlcumPaketi, yeni_olcum_id


def _poz(x: float) -> float:
    return x if x > 0 else 0.0


def ozetle(onceki: HamOkuma, simdiki: HamOkuma, *, vardiya: str | None = None) -> OlcumPaketi:
    aralik_dk = _poz((simdiki.zaman - onceki.zaman).total_seconds() / 60.0)
    toplam = int(_poz(simdiki.toplam_sayac - onceki.toplam_sayac))
    saglam = int(_poz(simdiki.saglam_sayac - onceki.saglam_sayac))
    durus = _poz(simdiki.durus_dk_sayac - onceki.durus_dk_sayac)
    return OlcumPaketi(
        olcum_id=yeni_olcum_id(),
        makine_kod=simdiki.makine_kod,
        zaman=simdiki.zaman,
        vardiya=vardiya,
        planlanan_sure_dk=aralik_dk,
        durus_sure_dk=durus,
        toplam_adet=toplam,
        saglam_adet=min(saglam, toplam),
        ideal_cevrim_sn=simdiki.ideal_cevrim_sn,
    )
