"""Liste sorguları için güvenli sıralama yardımcısı.

Sıralama kolonu adı **beyaz-listeden** çözülür; istemciden gelen ham metin asla
ORDER BY'a doğrudan girmez (SQL enjeksiyonu / geçersiz kolon koruması). Tanımsız
kolon veya yön sessizce varsayılana düşer (hata fırlatmaz) — liste uçları sağlamdır.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Select


def siralama_uygula[S: Select[Any]](
    sorgu: S,
    *,
    siralama: str | None,
    yon: str | None,
    izinli: dict[str, Any],
    varsayilan: Any,
    varsayilan_yon: str = "asc",
) -> S:
    """``sorgu``ya ``ORDER BY`` ekler.

    ``izinli`` = {istemci kolon adı -> SQLAlchemy kolonu}. ``siralama`` bu sözlükte
    yoksa ``varsayilan`` kolonu kullanılır. ``yon`` 'desc' (büyük/küçük harf duyarsız)
    ise azalan, aksi hâlde artan sıralanır.
    """
    kolon = izinli.get(siralama or "", varsayilan)
    artan = (yon or varsayilan_yon).lower() != "desc"
    return sorgu.order_by(kolon.asc() if artan else kolon.desc())
