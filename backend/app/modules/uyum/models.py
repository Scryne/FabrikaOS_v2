"""Uyum modülü modelleri (tenant şeması) — KVKK ihraç kaydı + aydınlatma/consent.

- ``KvkkIhraci`` — kişi bazlı veri ihracı (S14 rapor deseni: 202 async → MinIO
  ``tenant_<slug>/kvkk/...`` → indirme 409-korumalı). Dosya DB'de değil nesne deposunda.
- ``ConsentKaydi`` — aydınlatma/açık rıza kaydı (kim, hangi metin sürümü, ne zaman);
  geri çekme yeni satırdır (``kabul=False``) — geçmiş silinmez (ispat yükü).
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin

IHRAC_DURUMLARI = {"kuyrukta", "hazirlaniyor", "hazir", "basarisiz"}
KISI_TURLERI = {"kullanici", "personel"}
CONSENT_TURLERI = {"aydinlatma", "acik_riza"}


class KvkkIhraci(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Kişi bazlı KVKK veri ihracı kaydı — durum + artefakt üst verisi."""

    __tablename__ = "kvkk_ihraclari"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    # Kişi: 'kullanici' (kimlik yüzeyi) veya 'personel' (İK yüzeyi) + kaynak id.
    kisi_turu: Mapped[str] = mapped_column(String(20), nullable=False)
    kisi_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    durum: Mapped[str] = mapped_column(String(20), default="kuyrukta", index=True, nullable=False)
    nesne_anahtari: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    dosya_adi: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    boyut: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    kayit_sayisi: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    hata: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    olusturan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )


class ConsentKaydi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Aydınlatma/açık rıza kaydı — append-only (geri çekme yeni satır)."""

    __tablename__ = "consent_kayitlari"

    kullanici_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="CASCADE"), index=True, nullable=False
    )
    tur: Mapped[str] = mapped_column(String(20), nullable=False)  # CONSENT_TURLERI
    metin_surumu: Mapped[str] = mapped_column(String(20), nullable=False)  # ör. "v1"
    kabul: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ip_adresi: Mapped[str | None] = mapped_column(String(64), nullable=True)
