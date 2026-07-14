"""İş emri modülü modelleri (tenant şeması).

- ``IsEmri`` — durum makinesi taşıyan iş emri (bkz. ``durum.py``). Makine'ye n–1 (zorunlu),
  atanan kullanıcıya n–1 (opsiyonel; ``Personel`` modeli S11'de gelecek, şimdilik atama
  giriş yapan ``Kullanici``'ya yapılır). ``kod`` boş bırakılırsa servis ``IE-{yıl}-{id:06d}``
  üretir.
- ``IsEmriYorum`` — iş emri yorum/aktivite akışı (n–1 ``IsEmri``).

FK'ler şema önekiyle yazılmaz; tablo adıyla (``makineler.id``, ``kullanici.id``) verilir ve
aktif ``search_path`` (tenant şeması) çözer (tenant-rbac-conventions).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin
from app.modules.isemri.durum import ILK_DURUM

# İş emri öncelikleri.
ONCELIKLER = frozenset({"dusuk", "orta", "yuksek", "kritik"})


class IsEmri(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """İş emri — yaşam döngüsü ``durum.py`` durum makinesiyle yönetilir."""

    __tablename__ = "is_emirleri"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    baslik: Mapped[str] = mapped_column(String(200), nullable=False)
    aciklama: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    makine_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("makineler.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    atanan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    durum: Mapped[str] = mapped_column(String(20), default=ILK_DURUM, index=True, nullable=False)
    oncelik: Mapped[str] = mapped_column(String(10), default="orta", nullable=False)
    kapanis_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # SLA hedefi (S-VB): boş = SLA takibi yok; aşımı sla-tara kenar-tetikli üretir.
    hedef_tarih: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    yorumlar: Mapped[list[IsEmriYorum]] = relationship(
        back_populates="is_emri",
        cascade="all, delete-orphan",
        order_by="IsEmriYorum.id",
    )


class IsEmriYorum(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """İş emri yorumu/aktivite kaydı."""

    __tablename__ = "is_emri_yorumlari"

    is_emri_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("is_emirleri.id", ondelete="CASCADE"), index=True, nullable=False
    )
    yazan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    yazan_eposta: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metin: Mapped[str] = mapped_column(String(2000), nullable=False)

    is_emri: Mapped[IsEmri] = relationship(back_populates="yorumlar")
