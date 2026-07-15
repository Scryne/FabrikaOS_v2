"""Vardiya tanımı (tenant şeması) — üretim verisi ``vardiya`` alanının kataloğu.

``uretim_verileri.vardiya`` serbest metin kolonu S3'ten beri vardı; bu katalog FE
seçeneklerini ve OEE vardiya kırılımını (``/oee/ozet?vardiya=``) besler. Gece vardiyası
gibi gün aşan aralıklar desteklenir (``bitis_saat < baslangic_saat`` geçerli).
"""

from __future__ import annotations

from datetime import time

from sqlalchemy import Boolean, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin


class Vardiya(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Vardiya tanımı (ad + saat aralığı)."""

    __tablename__ = "vardiyalar"

    ad: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    baslangic_saat: Mapped[time] = mapped_column(Time, nullable=False)
    bitis_saat: Mapped[time] = mapped_column(Time, nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
