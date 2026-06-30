"""Dayanıklı store-and-forward kuyruğu (stdlib sqlite3).

Broker erişilemezken ölçümler burada birikir; reconnect'te ekleme sırasıyla yayınlanır
ve PUBACK alınınca ``onayla`` ile silinir. Süreç yeniden başlasa veriler dosyada kalır.
İdempotency uçta (çift ``ekle`` yok sayılır) ve bulutta (``olcum_id`` defteri) iki kat güvencede.
"""

from __future__ import annotations

import sqlite3


class Tampon:
    def __init__(self, yol: str) -> None:
        self._conn = sqlite3.connect(yol)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS bekleyen ("
            "  sira INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  olcum_id TEXT NOT NULL UNIQUE,"
            "  paket_json TEXT NOT NULL"
            ")"
        )
        self._conn.commit()

    def ekle(self, olcum_id: str, paket_json: str) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO bekleyen (olcum_id, paket_json) VALUES (?, ?)",
            (olcum_id, paket_json),
        )
        self._conn.commit()

    def bekleyenler(self) -> list[tuple[str, str]]:
        cur = self._conn.execute("SELECT olcum_id, paket_json FROM bekleyen ORDER BY sira ASC")
        return [(r[0], r[1]) for r in cur.fetchall()]

    def onayla(self, olcum_id: str) -> None:
        self._conn.execute("DELETE FROM bekleyen WHERE olcum_id = ?", (olcum_id,))
        self._conn.commit()

    def bekleyen_sayisi(self) -> int:
        cur = self._conn.execute("SELECT COUNT(*) FROM bekleyen")
        return int(cur.fetchone()[0])

    def kapat(self) -> None:
        self._conn.close()
