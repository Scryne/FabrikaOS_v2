"""Talep modülü modeli (tenant şeması).

``Talep`` — müşteri veya iç talep (teklif/destek/şikayet/bilgi). Yaşam döngüsü ``talep.durum``
makinesiyle; opsiyonel ``firma_id`` bir cariye, ``atanan_kullanici_id`` bir çözümleyiciye
bağlar. Dış self-servis portal (S18) da bu kayda talep yazar. FK'ler şema önekiyle yazılmaz.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin
from app.modules.talep.durum import ILK_DURUM


class Talep(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Müşteri/iç talep — yaşam döngüsü ``talep.durum`` makinesiyle."""

    __tablename__ = "talepler"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    firma_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("firmalar.id", ondelete="SET NULL"), index=True, nullable=True
    )
    baslik: Mapped[str] = mapped_column(String(200), nullable=False)
    aciklama: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    tur: Mapped[str] = mapped_column(String(20), default="destek", nullable=False)
    oncelik: Mapped[str] = mapped_column(String(10), default="orta", index=True, nullable=False)
    durum: Mapped[str] = mapped_column(String(20), default=ILK_DURUM, index=True, nullable=False)
    atanan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    talep_eden_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    talep_eden_ad: Mapped[str] = mapped_column(String(200), default="", nullable=False)
