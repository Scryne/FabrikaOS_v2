"""Bildirim modülü modelleri (tenant şeması).

- ``Bildirim`` — kişi-hedefli uygulama-içi bildirim; kaynağı (varsa) bir outbox olayıdır.
  ``UNIQUE(kullanici_id, giden_olay_id)`` üretici idempotency'sidir: tüketici aynı olayı
  tekrar tarasa da aynı kullanıcıya ikinci bildirim yazamaz (``giden_olay_id IS NULL``
  sistem bildirimleri kısıta girmez — PostgreSQL NULL semantiği).
- ``BildirimTercihi`` — kullanıcı × olay türü kanal tercihi. Kayıt yoksa varsayılan:
  uygulama-içi açık, e-posta kapalı.
- ``BildirimImleci`` — tüketicinin işlediği son ``giden_olaylar.id`` (yüksek-su-işareti).
  Kısıt zaten çift-yazımı önler; imleç yalnız tarama penceresini daraltır.

FK'ler şema önekiyle yazılmaz; ``search_path`` çözer (tenant-rbac-conventions).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin

# Bildirim önem düzeyleri (duyuru ile aynı sözlük).
BILDIRIM_ONEMLERI = frozenset({"bilgi", "uyari", "kritik"})


class Bildirim(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Kişi-hedefli uygulama-içi bildirim (kaynak = bir outbox olayı)."""

    __tablename__ = "bildirimler"
    __table_args__ = (UniqueConstraint("kullanici_id", "giden_olay_id"),)

    kullanici_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="CASCADE"), index=True, nullable=False
    )
    giden_olay_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("giden_olaylar.id", ondelete="CASCADE"), index=True, nullable=True
    )
    olay_turu: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    baslik: Mapped[str] = mapped_column(String(200), nullable=False)
    govde: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    # Derin-bağlantı verisi: {"kaynak_tur": "...", "kaynak_id": ...} — FE yönlendirmesi.
    veri: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    onem: Mapped[str] = mapped_column(String(20), default="bilgi", nullable=False)
    okundu: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    okundu_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BildirimTercihi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Kullanıcı × olay türü bildirim kanal tercihi (yoksa varsayılan geçerli)."""

    __tablename__ = "bildirim_tercihleri"
    __table_args__ = (UniqueConstraint("kullanici_id", "olay_turu"),)

    kullanici_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="CASCADE"), index=True, nullable=False
    )
    olay_turu: Mapped[str] = mapped_column(String(80), nullable=False)
    uygulama_ici: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    eposta: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class BildirimImleci(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Bildirim üreticisinin tek satırlık outbox yüksek-su-işareti."""

    __tablename__ = "bildirim_imleci"

    son_islenen_olay_id: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
