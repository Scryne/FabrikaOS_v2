"""DYS modülü modelleri (tenant şeması) — belge + sürüm.

- ``Belge`` — mantıksal doküman. ``guncel_surum`` en son yüklenen sürüm numarasıdır
  (henüz sürüm yoksa 0).
- ``BelgeSurumu`` — append-only sürüm kaydı. Dosya içeriği **nesne depolamadadır**
  (``nesne_anahtari``); DB yalnız üstveriyi tutar. ``(belge_id, surum_no)`` tekildir.

FK'ler şema önekiyle yazılmaz; ``search_path`` çözer.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin


class Belge(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Mantıksal doküman (sürümleri ``belge_surumleri``'nde)."""

    __tablename__ = "belgeler"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    ad: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    kategori: Mapped[str] = mapped_column(String(100), default="", index=True, nullable=False)
    aciklama: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    guncel_surum: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    olusturan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )


class BelgeSurumu(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Belgenin bir sürümü (append-only); içerik nesne depolamada."""

    __tablename__ = "belge_surumleri"
    __table_args__ = (
        UniqueConstraint("belge_id", "surum_no", name="uq_belge_surumleri_belge_id_surum_no"),
    )

    belge_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("belgeler.id", ondelete="CASCADE"), index=True, nullable=False
    )
    surum_no: Mapped[int] = mapped_column(Integer, nullable=False)
    dosya_adi: Mapped[str] = mapped_column(String(255), nullable=False)
    icerik_tipi: Mapped[str] = mapped_column(
        String(150), default="application/octet-stream", nullable=False
    )
    boyut: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    nesne_anahtari: Mapped[str] = mapped_column(String(500), nullable=False)
    yukleyen_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    aciklama: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
