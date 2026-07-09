"""Etkin entitlement hesabı — SAF fonksiyonlar (S16 / ADR-0018).

Kural: tenant-başına **istisna (override)** varsa o kazanır; yoksa "modül planın
listesinde mi" bakılır. Katalogda olmayan kod her koşulda **kapalıdır** (fail-closed):
yazım hatası ya da kaldırılmış bir modül asla yanlışlıkla açılmaz.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping

from app.control_plane.moduller import MODUL_KATALOGU, OZELLIK_KATALOGU


def modul_acik_mi(
    modul_kodu: str,
    plan_moduller: Collection[str],
    hak_haritasi: Mapping[str, bool],
) -> bool:
    """Modül bu tenant için açık mı? (override > plan; bilinmeyen kod kapalı)."""
    if modul_kodu not in MODUL_KATALOGU:
        return False
    if modul_kodu in hak_haritasi:
        return hak_haritasi[modul_kodu]
    return modul_kodu in plan_moduller


def etkin_moduller(
    plan_moduller: Collection[str],
    hak_haritasi: Mapping[str, bool],
) -> dict[str, bool]:
    """Katalogdaki TÜM modüller için kod -> açık/kapalı haritası."""
    return {kod: modul_acik_mi(kod, plan_moduller, hak_haritasi) for kod in MODUL_KATALOGU}


def ozellik_acik_mi(
    kod: str,
    plan_ozellikler: Collection[str],
    bayrak_haritasi: Mapping[str, bool],
) -> bool:
    """Özellik bayrağı bu tenant için açık mı? (override > plan; bilinmeyen kapalı)."""
    if kod not in OZELLIK_KATALOGU:
        return False
    if kod in bayrak_haritasi:
        return bayrak_haritasi[kod]
    return kod in plan_ozellikler


def etkin_ozellikler(
    plan_ozellikler: Collection[str],
    bayrak_haritasi: Mapping[str, bool],
) -> dict[str, bool]:
    """Katalogdaki TÜM özellik bayrakları için kod -> açık/kapalı haritası."""
    return {kod: ozellik_acik_mi(kod, plan_ozellikler, bayrak_haritasi) for kod in OZELLIK_KATALOGU}
