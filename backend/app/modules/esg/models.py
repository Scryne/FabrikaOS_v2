"""ESG modeli (tenant şeması, S32 / ADR-0051).

``EmisyonFaktoru`` — tenant'ın kendi emisyon faktörü (enerji türü + birim + geçerlilik başlangıcı
tekil). Satır yoksa kod içindeki kaynaklı varsayılan faktör kullanılır (``service.VARSAYILAN``);
tenant'ın girdiği faktör aynı tarihten itibaren varsayılanı ezer. Emisyonun kendisi saklanmaz: her
istekte enerji tüketiminden hesaplanır (faktör düzeltilince geçmiş dönemler de düzelir).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin


class EmisyonFaktoru(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    __tablename__ = "emisyon_faktorleri"
    __table_args__ = (
        UniqueConstraint("enerji_turu", "birim", "gecerlilik", name="uq_emisyon_faktorleri_tur"),
        CheckConstraint("deger >= 0", name="deger"),
        CheckConstraint("kapsam IN ('kapsam1', 'kapsam2')", name="kapsam"),
    )

    enerji_turu: Mapped[str] = mapped_column(String(20), nullable=False)
    birim: Mapped[str] = mapped_column(String(20), nullable=False)  # normalleştirilmiş: kwh, m3
    deger: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)  # kg CO2e / birim
    kapsam: Mapped[str] = mapped_column(String(10), nullable=False)
    gecerlilik: Mapped[date] = mapped_column(Date, nullable=False)
    kaynak: Mapped[str] = mapped_column(String(300), default="", nullable=False)
