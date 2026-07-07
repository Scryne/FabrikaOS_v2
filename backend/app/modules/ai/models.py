"""AI modülü modelleri (tenant şeması).

- ``ModelKaydi`` — sürümlü model kayıt defteri. Artefaktın kendisi DB'de değil nesne
  deposundadır (``nesne_anahtari``); ``tur`` başına ``surum`` artar (uq) ve en fazla bir
  kayıt ``aktif`` olur (servis rotasyonu). Yaşam döngüsü: ``egitiliyor → hazir | basarisiz``.
- ``Tahmin`` — çıkarım geçmişi (append-only): hangi model sürümüyle, hangi girdiyle,
  ne üretildi.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin
from app.modules.ai.birimler import MODEL_DURUMLARI

ILK_DURUM = "egitiliyor"
assert ILK_DURUM in MODEL_DURUMLARI


class ModelKaydi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Sürümlü model kaydı — eğitim durumu + metrikler + artefakt anahtarı."""

    __tablename__ = "model_kayitlari"

    tur: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    surum: Mapped[int] = mapped_column(Integer, nullable=False)
    durum: Mapped[str] = mapped_column(String(20), default=ILK_DURUM, index=True, nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    nesne_anahtari: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    metrikler: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    veri_ozeti: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    hata: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    egitim_suresi_sn: Mapped[float | None] = mapped_column(Float, nullable=True)
    olusturan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )

    __table_args__ = (UniqueConstraint("tur", "surum", name="uq_model_kayitlari_tur_surum"),)


class Tahmin(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Çıkarım geçmişi satırı (append-only)."""

    __tablename__ = "tahminler"

    tur: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    model_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("model_kayitlari.id", ondelete="CASCADE"), index=True, nullable=False
    )
    cikti: Mapped[Any] = mapped_column(JSONB, nullable=False)
    veri_ozeti: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    olusturan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
