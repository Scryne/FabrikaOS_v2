"""Entegrasyon modülü modelleri (tenant şeması) — webhook + API anahtarı (S18 / ADR-0020).

- ``WebhookAboneligi``: hedef URL + olay türü seçimi + HMAC imza gizli anahtarı.
  ``gizli_anahtar`` imzalama için düz saklanır (her teslimatta gerekir); API yanıtlarında
  maskelenir, yalnız oluşturma/yenilemede tam döner.
- ``WebhookTeslimati``: olay × abonelik başına teslimat günlüğü. Outbox (``giden_olaylar``)
  fan-out ile buraya açılır; retry durumu satır başına burada yaşar.
- ``ApiAnahtari``: 3. taraf erişim anahtarı — düz anahtar ASLA saklanmaz, SHA-256 özet
  eşleşmesiyle doğrulanır; ``izinler`` kapsam alt kümesidir (en az ayrıcalık).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin

# Teslimat yaşam döngüsü: beklemede → basarili | yeniden_denenecek → ... → basarisiz.
TESLIMAT_DURUMLARI = frozenset({"beklemede", "basarili", "yeniden_denenecek", "basarisiz"})


class WebhookAboneligi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Webhook aboneliği — hangi olaylar hangi URL'ye hangi anahtarla imzalanıp gider."""

    __tablename__ = "webhook_abonelikleri"

    ad: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    gizli_anahtar: Mapped[str] = mapped_column(String(120), nullable=False)
    # Katalogdan alt küme; boş liste = tüm olay türleri.
    olay_turleri: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class WebhookTeslimati(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Bir olayın bir aboneliğe teslimat kaydı (deneme günlüğü + retry durumu)."""

    __tablename__ = "webhook_teslimatlari"

    dis_anahtar: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True, nullable=False
    )
    abonelik_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("webhook_abonelikleri.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    olay_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("giden_olaylar.id", ondelete="CASCADE"), index=True, nullable=False
    )
    olay_turu: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    # Gönderilen zarfın anlık görüntüsü (v1) — günlükte "ne gitti" sorusunun cevabı.
    govde: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    durum: Mapped[str] = mapped_column(String(20), default="beklemede", index=True, nullable=False)
    deneme_sayisi: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Vade taraması bu kolonu okur; oluşturulduğunda now() → hemen teslim edilebilir.
    sonraki_deneme_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )
    son_deneme_tarihi: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    yanit_kodu: Mapped[int | None] = mapped_column(Integer, nullable=True)
    yanit_ozeti: Mapped[str] = mapped_column(String(500), default="", nullable=False)


class ApiAnahtari(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """3. taraf (ERP/muhasebe) erişim anahtarı — SHA-256 özetle doğrulanır."""

    __tablename__ = "api_anahtarlari"

    ad: Mapped[str] = mapped_column(String(120), nullable=False)
    # Görüntü kimliği (anahtarın ilk 12 karakteri) — listede tam anahtar asla dönmez.
    onek: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    anahtar_ozet: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    # ENTEGRASYON_IZIN_KAPSAMLARI alt kümesi (ör. ["stok:oku"]).
    izinler: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    gecerlilik_tarihi: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    son_kullanim_tarihi: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    olusturan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
