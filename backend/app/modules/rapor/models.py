"""Rapor modülü modeli (tenant şeması).

``Rapor`` — async üretilen rapor kaydı. Dosyanın kendisi DB'de değil nesne deposundadır
(``nesne_anahtari``; yanıt DTO'sunda gizli). Yaşam döngüsü ``birimler.RAPOR_DURUMLARI``:
``kuyrukta → hazirlaniyor → hazir | basarisiz``. ``kod`` servis tarafından
``RP-{yıl}-{id:06d}`` üretilir.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import BigInteger, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin
from app.modules.rapor.birimler import RAPOR_DURUMLARI

ILK_DURUM = "kuyrukta"
assert ILK_DURUM in RAPOR_DURUMLARI


class Rapor(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Async üretilen rapor kaydı — durum + parametreler + artefakt üst verisi."""

    __tablename__ = "raporlar"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    tur: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    bicim: Mapped[str] = mapped_column(String(10), nullable=False)
    durum: Mapped[str] = mapped_column(String(20), default=ILK_DURUM, index=True, nullable=False)
    parametreler: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    nesne_anahtari: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    dosya_adi: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    icerik_tipi: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    boyut: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    satir_sayisi: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hata: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    uretim_suresi_sn: Mapped[float | None] = mapped_column(Float, nullable=True)
    olusturan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
