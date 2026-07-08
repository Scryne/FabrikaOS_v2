"""Dijital ikiz modülü modeli (tenant şeması).

``IkizDugum`` — tesis/hat şemasında bir makinenin konumu. Koordinatlar **yüzde**
(0–100) tabanlıdır; şema çözünürlükten bağımsız ölçeklenir. Bir makine şemada en
fazla bir kez yer alır (``makine_id`` unique). Canlı durum bu tabloda tutulmaz —
``makineler.durum`` + ``uretim_verileri``'nden okunur (S15 / ADR-0017).
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin

# Yüzde koordinat sınırları (şema alanı).
KOORDINAT_MIN = 0.0
KOORDINAT_MAX = 100.0


class IkizDugum(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Tesis şemasında bir makine düğümü (yüzde koordinat + opsiyonel bölge etiketi)."""

    __tablename__ = "ikiz_dugumleri"

    makine_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("makineler.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    bolge: Mapped[str] = mapped_column(String(100), default="", nullable=False)
