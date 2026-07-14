"""Bildirim modülü (S-VB / ADR-0021) — kişi-hedefli, tenant içi uygulama-içi bildirim.

Çapraz-kesen özelliktir: ``modul_gerekli`` kapısı almaz (duyuru gibi); uçlar oturum
yeterli, kişisel süzgeç dependency'de zorlanır. Üretim outbox'tan ayrı süreçle yapılır
(``uretici.py`` + ``scripts/bildirim_uretici.py``).
"""
