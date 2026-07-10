"""Control-plane modelleri (public şema): ``Tenant``, ``Abonelik``, ``Plan``,
``ModulHakki``, ``OzellikBayragi``, ``PlatformYonetici``, ``TenantIhrac`` ve
``PlatformDenetimIzi``.

``Tenant.slug`` aynı zamanda şema adının (``tenant_<slug>``) kaynağıdır; bu yüzden
katı bir biçim (küçük harf, rakam, tire) zorunludur — bkz. ``tenancy.SLUG_DESENI``.

S16 (ADR-0018): ``planlar`` satış planlarını (modül seti + koltuk limiti) tutar;
``modul_haklari`` / ``ozellik_bayraklari`` tenant-başına istisnalardır (override).
Etkin entitlement hesabı için bkz. ``entitlement.py`` (saf) + ``entitlement_service.py``.

S17 (ADR-0019): ``platform_yonetici`` control-plane operatör kimliğidir (tenant
RBAC'inden ayrık düzlem); ``tenant_ihraclari`` KVKK dışa aktarma işleri,
``platform_denetim_izi`` platform yazma işlemlerinin denetim kaydıdır.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import KimlikMixin, PublicBase, ZamanDamgaliMixin

# Abonelik durumları — geçerli sayılanlar erişime izin verir.
ABONELIK_GECERLI_DURUMLAR = frozenset({"deneme", "aktif"})


class Tenant(KimlikMixin, ZamanDamgaliMixin, PublicBase):
    """Bir fabrika/kiracı. Her tenant'ın izole bir ``tenant_<slug>`` şeması vardır."""

    __tablename__ = "tenant"

    slug: Mapped[str] = mapped_column(String(63), unique=True, index=True, nullable=False)
    ad: Mapped[str] = mapped_column(String(200), nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    abonelikler: Mapped[list[Abonelik]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def gecerli_abonelik(self) -> Abonelik | None:
        """İlk geçerli (deneme/aktif ve süresi geçmemiş) aboneliği döndürür.

        Not: ``abonelikler`` ilişkisinin önceden yüklenmiş olması gerekir (eager load).
        """
        simdi = datetime.now(UTC)
        for ab in self.abonelikler:
            if ab.durum not in ABONELIK_GECERLI_DURUMLAR:
                continue
            if ab.bitis_tarihi is not None and ab.bitis_tarihi < simdi:
                continue
            return ab
        return None

    @property
    def abonelik_gecerli(self) -> bool:
        """Geçerli bir abonelik var mı? (bkz. ``gecerli_abonelik``)."""
        return self.gecerli_abonelik is not None


class Abonelik(KimlikMixin, ZamanDamgaliMixin, PublicBase):
    """Bir tenant'ın plan/abonelik kaydı (control-plane)."""

    __tablename__ = "abonelik"

    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenant.id", ondelete="CASCADE"), index=True, nullable=False
    )
    plan_kodu: Mapped[str] = mapped_column(
        String(50), ForeignKey("planlar.kod"), default="deneme", nullable=False
    )
    durum: Mapped[str] = mapped_column(String(20), default="deneme", nullable=False)
    baslangic_tarihi: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bitis_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped[Tenant] = relationship(back_populates="abonelikler")


class Plan(KimlikMixin, ZamanDamgaliMixin, PublicBase):
    """Satış planı: modül seti + koltuk limiti + özellik seti (kaynak: ``PLAN_KATALOGU``)."""

    __tablename__ = "planlar"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    ad: Mapped[str] = mapped_column(String(100), nullable=False)
    # None = sınırsız koltuk (kurumsal).
    koltuk_limiti: Mapped[int | None] = mapped_column(Integer, nullable=True)
    moduller: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    ozellikler: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ModulHakki(KimlikMixin, ZamanDamgaliMixin, PublicBase):
    """Tenant-başına modül istisnası (entitlement override) — plandan sapma."""

    __tablename__ = "modul_haklari"
    __table_args__ = (UniqueConstraint("tenant_id", "modul_kodu"),)

    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenant.id", ondelete="CASCADE"), index=True, nullable=False
    )
    modul_kodu: Mapped[str] = mapped_column(String(50), nullable=False)
    acik: Mapped[bool] = mapped_column(Boolean, nullable=False)


class OzellikBayragi(KimlikMixin, ZamanDamgaliMixin, PublicBase):
    """Tenant-başına özellik bayrağı istisnası (feature flag override)."""

    __tablename__ = "ozellik_bayraklari"
    __table_args__ = (UniqueConstraint("tenant_id", "kod"),)

    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenant.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kod: Mapped[str] = mapped_column(String(50), nullable=False)
    acik: Mapped[bool] = mapped_column(Boolean, nullable=False)


class PlatformYonetici(KimlikMixin, ZamanDamgaliMixin, PublicBase):
    """Control-plane operatör hesabı — hiçbir tenant'a bağlı DEĞİLDİR (S17/ADR-0019).

    Tenant ``Kullanici``/RBAC düzleminden ayrıktır; token tipi ``platform_access``
    olduğu için tenant uçlarında yapısal olarak geçersizdir (ve tersi).
    """

    __tablename__ = "platform_yonetici"

    eposta: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    parola_ozet: Mapped[str] = mapped_column(String(255), nullable=False)
    ad_soyad: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    son_giris_tarihi: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


# İhraç durum makinesi: kuyrukta → hazirlaniyor → hazir | basarisiz (terminalden çıkış yok).
IHRAC_DURUMLARI = frozenset({"kuyrukta", "hazirlaniyor", "hazir", "basarisiz"})


class TenantIhrac(KimlikMixin, ZamanDamgaliMixin, PublicBase):
    """KVKK tenant veri ihracı işi (S14 rapor async deseninin control-plane aynası).

    ``slug`` denormalize tutulur: artefakt anahtarı ve arka plan görevi, tenant
    satırı kilitlenmeden/silinmeden bağımsız çalışabilsin.
    """

    __tablename__ = "tenant_ihraclari"

    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenant.id", ondelete="CASCADE"), index=True, nullable=False
    )
    slug: Mapped[str] = mapped_column(String(63), nullable=False)
    durum: Mapped[str] = mapped_column(String(20), default="kuyrukta", nullable=False)
    nesne_anahtari: Mapped[str | None] = mapped_column(String(500), nullable=True)
    boyut: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tablo_sayisi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hata: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    olusturan_eposta: Mapped[str | None] = mapped_column(String(255), nullable=True)


class PlatformDenetimIzi(KimlikMixin, ZamanDamgaliMixin, PublicBase):
    """Platform (control-plane) yazma işlemlerinin kim-ne-ne zaman kaydı.

    Tenant şemasındaki ``denetim_izi``'nin platform düzlemi aynasıdır; tenant
    yaşam döngüsü işlemleri (provizyon/askıya alma/silme/entitlement) buraya işlenir.
    """

    __tablename__ = "platform_denetim_izi"

    yonetici_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    yonetici_eposta: Mapped[str | None] = mapped_column(String(255), nullable=True)
    eylem: Mapped[str] = mapped_column(String(50), nullable=False)
    kaynak: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    kaynak_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_adresi: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detay: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
