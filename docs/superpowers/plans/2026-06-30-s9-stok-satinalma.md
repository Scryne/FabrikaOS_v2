# S9 — Stok & Satınalma Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Çekirdeğin üzerine çok-kiracılı, RBAC-korumalı, canlı bir **Stok & Satınalma** modülü kurmak: malzeme + stok hareketi (tutulan bakiye), kritik-eşik olayı, çok-kalemli satınalma talebi + onay akışı; backend + frontend uçtan uca.

**Architecture:** Standart modül deseni (`app/modules/stok/`): saf durum makinesi + saf sabitler birim testli; servis `FOR UPDATE` satır kilidiyle bakiyeyi günceller ve kenar-tetikli `stok.kritik` olayını transactional outbox'a yazar; uçlar tenant-kapsamlı (`tenant_cozumle` + `izin_gerekli`) + audit; frontend S6 deseniyle (`SunucuTablo`, TanStack hooks, izin-duyarlı aksiyonlar) + canlı invalidate.

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy 2 (async) / Alembic (iki-ağaç fan-out) / PostgreSQL+TimescaleDB / Redis pub-sub; React 18 + TS strict + Ant Design v5 + TanStack Query + Zustand + Vite.

## Global Constraints

- **Türkçe-ASCII identifier standardı** (`turkce-identifier-standardi`): model/tablo/kolon/route/DTO adları Türkçe-ASCII. Kaynak adları çoğul kebab REST: `/malzemeler`, `/stok-hareketleri`, `/stok/kritik`, `/satinalma-talepleri`.
- **Tenant izolasyonu (`tenant-rbac-conventions`):** tenant-kapsamlı **her uç** iki dependency'den geçer — `Depends(tenant_cozumle)` (gerekiyorsa) ve `Depends(izin_gerekli("modul:islem"))`. FK'ler şema öneki **yazılmaz** (`malzemeler.id`, `kullanici.id`); `search_path` çözer. Sabit `tenant_xyz.tablo` öneki yasak.
- **Yanıt zarfı:** `{success, message, data, meta}`; liste uçları `sayfali(...)`; sayfalama `?sayfa=&adet=&siralama=&yon=&arama=`.
- **Miktar tipi:** DB `Numeric(18, 3)` (Decimal aritmetik); para `Numeric(18, 2)`. **İstek DTO** miktar alanları `Decimal` (`Field(gt=0)`); **cevap DTO** alanları `float` (sınırda `float(...)` dönüşümü). Outbox/realtime `govde` JSON-native olmalı → `float(...)` kullan (Decimal JSONB'ye serialize edilemez).
- **Migration:** tenant ağacı, `down_revision = "f3a9c1d72b84"` (uygulama anında `alembic heads` ile doğrula). Hypertable yok. `public` + ≥2 tenant şemasında fan-out up/down.
- **Audit:** her yazma ucu `denetim_yaz(...)` üretir.
- **Kalite kapısı:** `ruff` + `mypy` temiz (backend); `eslint` + `tsc --strict` + `prettier` + `vitest` + `vite build` temiz (frontend). Conventional Commits; görev başına commit.
- **Komutlar (backend `backend/` dizininden):** test `python -m pytest`, lint `ruff check .`, tip `mypy app`. **Frontend (`frontend/`):** `npm run test`, `npm run lint`, `npm run build`, `npm run codegen`. Entegrasyon testleri çalışan PostgreSQL ister (`docker compose up db`).

---

## Task 1: Saf sabitler + satınalma talebi durum makinesi

**Files:**
- Create: `backend/app/modules/stok/__init__.py`
- Create: `backend/app/modules/stok/birimler.py`
- Create: `backend/app/modules/stok/talep_durum.py`
- Test: `backend/tests/test_s9_durum.py`

**Interfaces:**
- Produces:
  - `birimler.BIRIMLER: frozenset[str]`, `birimler.STOK_HAREKET_TURLERI: frozenset[str]`
  - `talep_durum.GECISLER: dict[str, frozenset[str]]`, `talep_durum.DURUMLAR: frozenset[str]`, `talep_durum.TERMINAL_DURUMLAR: frozenset[str]`, `talep_durum.ILK_DURUM: str` (= `"taslak"`)
  - `talep_durum.gecerli_hedefler(mevcut: str) -> frozenset[str]`
  - `talep_durum.gecis_gecerli_mi(mevcut: str, hedef: str) -> bool`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_s9_durum.py`:
```python
"""S9 birim testleri: satınalma talebi durum makinesi + stok sabitleri (saf, DB'siz)."""

from __future__ import annotations

from app.modules.stok import birimler, talep_durum


def test_ilk_durum_taslak() -> None:
    assert talep_durum.ILK_DURUM == "taslak"


def test_taslak_gecerli_hedefler() -> None:
    assert talep_durum.gecerli_hedefler("taslak") == frozenset({"onay_bekliyor", "iptal"})


def test_onay_bekliyor_gecerli_hedefler() -> None:
    assert talep_durum.gecerli_hedefler("onay_bekliyor") == frozenset(
        {"onaylandi", "reddedildi", "iptal"}
    )


def test_terminal_durumlardan_cikis_yok() -> None:
    for d in ("onaylandi", "reddedildi", "iptal"):
        assert talep_durum.gecerli_hedefler(d) == frozenset()
    assert talep_durum.TERMINAL_DURUMLAR == frozenset({"onaylandi", "reddedildi", "iptal"})


def test_gecerli_ve_gecersiz_gecisler() -> None:
    assert talep_durum.gecis_gecerli_mi("taslak", "onay_bekliyor") is True
    assert talep_durum.gecis_gecerli_mi("onay_bekliyor", "onaylandi") is True
    # taslak'tan doğrudan onaylandı yasak (önce gönderilmeli)
    assert talep_durum.gecis_gecerli_mi("taslak", "onaylandi") is False
    # terminalden çıkış yasak
    assert talep_durum.gecis_gecerli_mi("onaylandi", "iptal") is False
    # tanımsız durum → boş
    assert talep_durum.gecis_gecerli_mi("yok", "taslak") is False


def test_sabitler() -> None:
    assert {"adet", "kg", "litre", "metre"} <= birimler.BIRIMLER
    assert birimler.STOK_HAREKET_TURLERI == frozenset({"giris", "cikis", "duzeltme"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_s9_durum.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.modules.stok'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/modules/stok/__init__.py`:
```python
"""Stok & Satınalma modülü (malzeme, stok hareketi, satınalma talebi)."""
```

`backend/app/modules/stok/birimler.py`:
```python
"""Stok modülü saf sabitleri — ölçü birimleri ve hareket türleri (beyaz-liste)."""

from __future__ import annotations

# Desteklenen ölçü birimleri (beyaz-liste; DTO/router doğrulamasında kullanılır).
BIRIMLER: frozenset[str] = frozenset(
    {
        "adet",
        "kg",
        "gram",
        "litre",
        "mililitre",
        "metre",
        "santimetre",
        "paket",
        "kutu",
        "koli",
        "ton",
        "rulo",
    }
)

# Stok hareketi türleri: giriş (+), çıkış (−), düzeltme (mutlak sayım sonucu).
STOK_HAREKET_TURLERI: frozenset[str] = frozenset({"giris", "cikis", "duzeltme"})
```

`backend/app/modules/stok/talep_durum.py`:
```python
"""Satınalma talebi durum makinesi — saf (DB'siz) iş kuralı, kapsamlı birim testli.

Yaşam döngüsü::

    taslak ──> onay_bekliyor ──> onaylandi*
       │            │
       │            └──────────> reddedildi*
       └──> iptal*   onay_bekliyor ──> iptal*

``*`` terminal: çıkış geçişi yoktur. ``onaylandi``/``reddedildi`` hedefleri çağıran
katmanda ``satinalma:onay`` iznini gerektirir (kural durum tablosunda değil router'da).
"""

from __future__ import annotations

# mevcut durum -> izin verilen hedef durumlar.
GECISLER: dict[str, frozenset[str]] = {
    "taslak": frozenset({"onay_bekliyor", "iptal"}),
    "onay_bekliyor": frozenset({"onaylandi", "reddedildi", "iptal"}),
    "onaylandi": frozenset(),
    "reddedildi": frozenset(),
    "iptal": frozenset(),
}

DURUMLAR: frozenset[str] = frozenset(GECISLER)
TERMINAL_DURUMLAR: frozenset[str] = frozenset({"onaylandi", "reddedildi", "iptal"})
ILK_DURUM = "taslak"


def gecerli_hedefler(mevcut: str) -> frozenset[str]:
    """``mevcut`` durumdan gidilebilecek hedef durumlar (tanımsızsa boş küme)."""
    return GECISLER.get(mevcut, frozenset())


def gecis_gecerli_mi(mevcut: str, hedef: str) -> bool:
    """``mevcut`` → ``hedef`` geçişi durum makinesine göre geçerli mi?"""
    return hedef in gecerli_hedefler(mevcut)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_s9_durum.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Lint + commit**

```bash
cd backend && ruff check app/modules/stok tests/test_s9_durum.py && mypy app/modules/stok
git add backend/app/modules/stok/__init__.py backend/app/modules/stok/birimler.py backend/app/modules/stok/talep_durum.py backend/tests/test_s9_durum.py
git commit -m "feat(stok): saf birim sabitleri + satınalma talebi durum makinesi (S9)"
```

---

## Task 2: Modeller + registry kaydı + migration (fan-out)

**Files:**
- Create: `backend/app/modules/stok/models.py`
- Modify: `backend/app/core/db/registry.py` (yeni import satırı)
- Create: `backend/migrations/tenant/versions/a3d9f1c52e84_stok_satinalma.py`
- Test: `backend/tests/test_s9_migration.py`

**Interfaces:**
- Produces (SQLAlchemy modelleri, tenant şeması):
  - `Malzeme` (`malzemeler`): `id, kod, ad, birim, kategori, mevcut_miktar, min_stok, max_stok, kritik_stok, aktif, olusturma_tarihi, guncelleme_tarihi`
  - `StokHareketi` (`stok_hareketleri`): `id, malzeme_id, tur, miktar, bakiye_sonrasi, aciklama, kaynak, olusturan_kullanici_id, idempotency_anahtari, olusturma_tarihi`
  - `SatinalmaTalebi` (`satinalma_talepleri`): `id, kod, baslik, aciklama, durum, para_birimi, talep_eden_kullanici_id, onaylayan_kullanici_id, onay_tarihi, red_nedeni`; `kalemler` relationship
  - `SatinalmaTalebiKalemi` (`satinalma_talebi_kalemleri`): `id, talep_id, malzeme_id, miktar, birim, tahmini_birim_fiyat, aciklama`; `talep` relationship

- [ ] **Step 1: Write the models**

`backend/app/modules/stok/models.py`:
```python
"""Stok & Satınalma modelleri (tenant şeması).

- ``Malzeme`` — stok kartı; ``mevcut_miktar`` **tutulan bakiyedir** (her ``StokHareketi``
  servis katmanında ``FOR UPDATE`` ile günceller). ``kritik_stok`` kenar-tetikli
  ``stok.kritik`` olayının eşiğidir.
- ``StokHareketi`` — append-only hareket; ``bakiye_sonrasi`` o andaki bakiye snapshot'ı.
  ``idempotency_anahtari`` opsiyonel tekil — çift-gönderimi engeller.
- ``SatinalmaTalebi`` + ``SatinalmaTalebiKalemi`` — çok-kalemli talep; durum ``talep_durum.py``
  makinesiyle yönetilir.

FK'ler şema önekiyle yazılmaz (``malzemeler.id``, ``kullanici.id``); aktif ``search_path`` çözer.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin
from app.modules.stok.talep_durum import ILK_DURUM

_MIKTAR = Numeric(18, 3)
_PARA = Numeric(18, 2)


class Malzeme(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Stok kartı — tutulan bakiye + min/max/kritik eşikler."""

    __tablename__ = "malzemeler"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    ad: Mapped[str] = mapped_column(String(200), nullable=False)
    birim: Mapped[str] = mapped_column(String(20), nullable=False)
    kategori: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    mevcut_miktar: Mapped[Decimal] = mapped_column(_MIKTAR, default=Decimal(0), nullable=False)
    min_stok: Mapped[Decimal] = mapped_column(_MIKTAR, default=Decimal(0), nullable=False)
    max_stok: Mapped[Decimal | None] = mapped_column(_MIKTAR, nullable=True)
    kritik_stok: Mapped[Decimal] = mapped_column(_MIKTAR, default=Decimal(0), nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class StokHareketi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Stok hareketi (append-only) — bakiyeyi güncelleyen kayıt."""

    __tablename__ = "stok_hareketleri"

    malzeme_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("malzemeler.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    tur: Mapped[str] = mapped_column(String(10), nullable=False)
    miktar: Mapped[Decimal] = mapped_column(_MIKTAR, nullable=False)
    bakiye_sonrasi: Mapped[Decimal] = mapped_column(_MIKTAR, nullable=False)
    aciklama: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    kaynak: Mapped[str | None] = mapped_column(String(50), nullable=True)
    olusturan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    idempotency_anahtari: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )


class SatinalmaTalebi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Çok-kalemli satınalma talebi — yaşam döngüsü ``talep_durum.py``."""

    __tablename__ = "satinalma_talepleri"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    baslik: Mapped[str] = mapped_column(String(200), nullable=False)
    aciklama: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    durum: Mapped[str] = mapped_column(String(20), default=ILK_DURUM, index=True, nullable=False)
    para_birimi: Mapped[str] = mapped_column(String(3), default="TRY", nullable=False)
    talep_eden_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    onaylayan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    onay_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    red_nedeni: Mapped[str | None] = mapped_column(String(500), nullable=True)

    kalemler: Mapped[list[SatinalmaTalebiKalemi]] = relationship(
        back_populates="talep",
        cascade="all, delete-orphan",
        order_by="SatinalmaTalebiKalemi.id",
    )


class SatinalmaTalebiKalemi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Satınalma talebi kalemi (n–1 talep)."""

    __tablename__ = "satinalma_talebi_kalemleri"

    talep_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("satinalma_talepleri.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    malzeme_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("malzemeler.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    miktar: Mapped[Decimal] = mapped_column(_MIKTAR, nullable=False)
    birim: Mapped[str] = mapped_column(String(20), nullable=False)
    tahmini_birim_fiyat: Mapped[Decimal | None] = mapped_column(_PARA, nullable=True)
    aciklama: Mapped[str] = mapped_column(String(500), default="", nullable=False)

    talep: Mapped[SatinalmaTalebi] = relationship(back_populates="kalemler")
```

- [ ] **Step 2: Register models in the metadata registry**

`backend/app/core/db/registry.py` — `app.modules.saha.models` import satırının altına ekle:
```python
import app.modules.stok.models  # noqa: F401
```
(alfabetik sıra: `saha` → `stok` → `uretim` arasına gelir.)

- [ ] **Step 3: Verify head revision, then write the migration**

Run: `cd backend && python -m alembic -c alembic.ini -n tenant heads`
Expected: `f3a9c1d72b84 (head)`. (Farklıysa aşağıdaki `down_revision`'ı çıkan head ile değiştir.)

`backend/migrations/tenant/versions/a3d9f1c52e84_stok_satinalma.py`:
```python
"""stok: malzemeler + stok_hareketleri + satinalma_talepleri + kalemler (Stok & Satınalma)

Revision ID: a3d9f1c52e84
Revises: f3a9c1d72b84
Create Date: 2026-06-30 14:00:00.000000

Tenant şemasında; fan-out döngüsünde (env.py) public + her aktif tenant şemasında çalışır.
Hypertable yoktur (ilişkisel, düşük hacim). FK sırası: malzemeler önce, kalemler en son.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "a3d9f1c52e84"
down_revision: str | None = "f3a9c1d72b84"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "malzemeler",
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("ad", sa.String(length=200), nullable=False),
        sa.Column("birim", sa.String(length=20), nullable=False),
        sa.Column("kategori", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("mevcut_miktar", sa.Numeric(18, 3), nullable=False, server_default="0"),
        sa.Column("min_stok", sa.Numeric(18, 3), nullable=False, server_default="0"),
        sa.Column("max_stok", sa.Numeric(18, 3), nullable=True),
        sa.Column("kritik_stok", sa.Numeric(18, 3), nullable=False, server_default="0"),
        sa.Column("aktif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "olusturma_tarihi",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "guncelleme_tarihi",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_malzemeler")),
    )
    op.create_index(op.f("ix_malzemeler_kod"), "malzemeler", ["kod"], unique=True)

    op.create_table(
        "stok_hareketleri",
        sa.Column("malzeme_id", sa.BigInteger(), nullable=False),
        sa.Column("tur", sa.String(length=10), nullable=False),
        sa.Column("miktar", sa.Numeric(18, 3), nullable=False),
        sa.Column("bakiye_sonrasi", sa.Numeric(18, 3), nullable=False),
        sa.Column("aciklama", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("kaynak", sa.String(length=50), nullable=True),
        sa.Column("olusturan_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("idempotency_anahtari", sa.String(length=64), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "olusturma_tarihi",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "guncelleme_tarihi",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["malzeme_id"],
            ["malzemeler.id"],
            name=op.f("fk_stok_hareketleri_malzeme_id_malzemeler"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["olusturan_kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_stok_hareketleri_olusturan_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stok_hareketleri")),
    )
    op.create_index(
        op.f("ix_stok_hareketleri_malzeme_id"), "stok_hareketleri", ["malzeme_id"], unique=False
    )
    op.create_index(
        op.f("ix_stok_hareketleri_olusturan_kullanici_id"),
        "stok_hareketleri",
        ["olusturan_kullanici_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_stok_hareketleri_idempotency_anahtari"),
        "stok_hareketleri",
        ["idempotency_anahtari"],
        unique=True,
    )

    op.create_table(
        "satinalma_talepleri",
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("baslik", sa.String(length=200), nullable=False),
        sa.Column("aciklama", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("durum", sa.String(length=20), nullable=False, server_default="taslak"),
        sa.Column("para_birimi", sa.String(length=3), nullable=False, server_default="TRY"),
        sa.Column("talep_eden_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("onaylayan_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("onay_tarihi", sa.DateTime(timezone=True), nullable=True),
        sa.Column("red_nedeni", sa.String(length=500), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "olusturma_tarihi",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "guncelleme_tarihi",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["talep_eden_kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_satinalma_talepleri_talep_eden_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["onaylayan_kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_satinalma_talepleri_onaylayan_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_satinalma_talepleri")),
    )
    op.create_index(
        op.f("ix_satinalma_talepleri_kod"), "satinalma_talepleri", ["kod"], unique=True
    )
    op.create_index(
        op.f("ix_satinalma_talepleri_durum"), "satinalma_talepleri", ["durum"], unique=False
    )
    op.create_index(
        op.f("ix_satinalma_talepleri_talep_eden_kullanici_id"),
        "satinalma_talepleri",
        ["talep_eden_kullanici_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_satinalma_talepleri_onaylayan_kullanici_id"),
        "satinalma_talepleri",
        ["onaylayan_kullanici_id"],
        unique=False,
    )

    op.create_table(
        "satinalma_talebi_kalemleri",
        sa.Column("talep_id", sa.BigInteger(), nullable=False),
        sa.Column("malzeme_id", sa.BigInteger(), nullable=False),
        sa.Column("miktar", sa.Numeric(18, 3), nullable=False),
        sa.Column("birim", sa.String(length=20), nullable=False),
        sa.Column("tahmini_birim_fiyat", sa.Numeric(18, 2), nullable=True),
        sa.Column("aciklama", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "olusturma_tarihi",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "guncelleme_tarihi",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["talep_id"],
            ["satinalma_talepleri.id"],
            name=op.f("fk_satinalma_talebi_kalemleri_talep_id_satinalma_talepleri"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["malzeme_id"],
            ["malzemeler.id"],
            name=op.f("fk_satinalma_talebi_kalemleri_malzeme_id_malzemeler"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_satinalma_talebi_kalemleri")),
    )
    op.create_index(
        op.f("ix_satinalma_talebi_kalemleri_talep_id"),
        "satinalma_talebi_kalemleri",
        ["talep_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_satinalma_talebi_kalemleri_malzeme_id"),
        "satinalma_talebi_kalemleri",
        ["malzeme_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("satinalma_talebi_kalemleri")
    op.drop_index(op.f("ix_satinalma_talepleri_onaylayan_kullanici_id"), table_name="satinalma_talepleri")
    op.drop_index(op.f("ix_satinalma_talepleri_talep_eden_kullanici_id"), table_name="satinalma_talepleri")
    op.drop_index(op.f("ix_satinalma_talepleri_durum"), table_name="satinalma_talepleri")
    op.drop_index(op.f("ix_satinalma_talepleri_kod"), table_name="satinalma_talepleri")
    op.drop_table("satinalma_talepleri")
    op.drop_index(op.f("ix_stok_hareketleri_idempotency_anahtari"), table_name="stok_hareketleri")
    op.drop_index(op.f("ix_stok_hareketleri_olusturan_kullanici_id"), table_name="stok_hareketleri")
    op.drop_index(op.f("ix_stok_hareketleri_malzeme_id"), table_name="stok_hareketleri")
    op.drop_table("stok_hareketleri")
    op.drop_index(op.f("ix_malzemeler_kod"), table_name="malzemeler")
    op.drop_table("malzemeler")
```

- [ ] **Step 4: Write the fan-out migration test**

`backend/tests/test_s9_migration.py`:
```python
"""S9 migration fan-out testi: stok tabloları up/down (tenant_alfa şeması)."""

from __future__ import annotations

import asyncio

import asyncpg
import pytest

from app.core.db import fanout
from tests.conftest import TEST_URL

pytestmark = pytest.mark.asyncio

_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
_TABLOLAR = (
    "malzemeler",
    "stok_hareketleri",
    "satinalma_talepleri",
    "satinalma_talebi_kalemleri",
)


async def _tablo_var_mi(tablo: str) -> bool:
    conn = await asyncpg.connect(_DSN)
    try:
        return bool(await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", f"tenant_alfa.{tablo}"))
    finally:
        await conn.close()


async def test_stok_tablolari_up_down(test_db: str) -> None:
    # test_db fixture: head'e migrate edilmiş tenant_alfa şeması.
    for t in _TABLOLAR:
        assert await _tablo_var_mi(t), t

    # downgrade bir adım (saha head'ine) → stok tabloları gitmeli.
    await asyncio.to_thread(fanout.tenant_indir_tek, "alfa", "f3a9c1d72b84", db_url=TEST_URL)
    for t in _TABLOLAR:
        assert not await _tablo_var_mi(t), t

    # tekrar head'e çık (sonraki testler için durumu geri yükle).
    await asyncio.to_thread(fanout.tenant_yukselt_tek, "alfa", "head", db_url=TEST_URL)
    assert await _tablo_var_mi("malzemeler")
```

- [ ] **Step 5: Run the migration test**

Run: `cd backend && python -m pytest tests/test_s9_migration.py -v`
Expected: PASS — fixture provizyonlama yeni migration'ı uygular; 4 tablo `tenant_alfa` + `tenant_beta`'da oluşur, downgrade düşürür, tekrar yükselir.

- [ ] **Step 6: Lint + commit**

```bash
cd backend && ruff check app/modules/stok/models.py app/core/db/registry.py tests/test_s9_migration.py && mypy app/modules/stok/models.py
git add backend/app/modules/stok/models.py backend/app/core/db/registry.py backend/migrations/tenant/versions/a3d9f1c52e84_stok_satinalma.py backend/tests/test_s9_migration.py
git commit -m "feat(stok): 4 tablo modeli + tenant migration (fan-out up/down testli) (S9)"
```

---

## Task 3: Malzeme dikey dilimi (şema + repository + router + /stok/kritik)

**Files:**
- Create: `backend/app/modules/stok/schemas.py` (malzeme DTO'ları)
- Create: `backend/app/modules/stok/repository.py` (malzeme sorguları)
- Create: `backend/app/modules/stok/router.py` (malzeme + kritik uçları)
- Modify: `backend/app/api/router.py` (stok router'ını include et)
- Test: `backend/tests/test_s9_malzeme.py`

**Interfaces:**
- Consumes: `Malzeme` (Task 2); `tenant_cozumle`, `izin_gerekli` (`app.core.deps`); `denetim_yaz`; `basari`/`sayfali`/`Zarf`; `siralama_uygula`; `BIRIMLER` (Task 1).
- Produces:
  - DTO'lar: `MalzemeOlusturDTO`, `MalzemeGuncelleDTO`, `MalzemeCevapDTO`
  - Repository: `malzeme_kod_var_mi`, `malzeme_ekle`, `malzeme_getir`, `malzeme_getir_kilitli`, `malzeme_listele`, `kritik_listele`
  - `stok` router (prefix yok; mutlak yollar `/malzemeler`, `/stok/kritik`)
  - `_malzeme_cevap(m: Malzeme) -> dict` (sonraki task'lar yeniden kullanır)

- [ ] **Step 1: Write the failing integration test**

`backend/tests/test_s9_malzeme.py`:
```python
"""S9 entegrasyon: malzeme CRUD + kritik liste + RBAC + tenant izolasyonu."""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import ALFA, BETA

KIMLIK = "/api/v1/kimlik"


async def _giris(istemci: AsyncClient, t: dict) -> str:
    r = await istemci.post(
        f"{KIMLIK}/token",
        data={"username": t["eposta"], "password": t["parola"]},
        headers={"X-Tenant": t["slug"]},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["access_token"]


def _h(slug: str, access: str) -> dict[str, str]:
    return {"X-Tenant": slug, "Authorization": f"Bearer {access}"}


async def _malzeme(istemci: AsyncClient, h: dict[str, str], **ek: object) -> dict:
    govde = {"kod": "MLZ-1", "ad": "Rulman 6203", "birim": "adet", **ek}
    r = await istemci.post("/api/v1/malzemeler", json=govde, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_malzeme_olustur_varsayilanlar(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _malzeme(kurulu_istemci, h, kod="MLZ-VAR")
    assert d["mevcut_miktar"] == 0
    assert d["aktif"] is True
    assert d["kritik"] is False


async def test_malzeme_gecersiz_birim_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/malzemeler",
        json={"kod": "MLZ-X", "ad": "X", "birim": "sihirli"},
        headers=h,
    )
    assert r.status_code == 422, r.text


async def test_malzeme_kod_cakismasi_409(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await _malzeme(kurulu_istemci, h, kod="MLZ-DUP")
    r = await kurulu_istemci.post(
        "/api/v1/malzemeler", json={"kod": "MLZ-DUP", "ad": "Y", "birim": "adet"}, headers=h
    )
    assert r.status_code == 409, r.text


async def test_malzeme_guncelle_esikler(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _malzeme(kurulu_istemci, h, kod="MLZ-UPD")
    r = await kurulu_istemci.patch(
        f"/api/v1/malzemeler/{d['id']}",
        json={"kritik_stok": 5, "ad": "Rulman (güncel)"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["kritik_stok"] == 5
    assert r.json()["data"]["ad"] == "Rulman (güncel)"


async def test_kritik_liste(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    # mevcut 0, kritik 5 → kritik listede; kritik 0 olan listelenmez.
    await _malzeme(kurulu_istemci, h, kod="MLZ-KRT", kritik_stok=5)
    await _malzeme(kurulu_istemci, h, kod="MLZ-NORMAL", kritik_stok=0)
    r = await kurulu_istemci.get("/api/v1/stok/kritik", headers=h)
    assert r.status_code == 200, r.text
    kodlar = [m["kod"] for m in r.json()["data"]]
    assert "MLZ-KRT" in kodlar
    assert "MLZ-NORMAL" not in kodlar


async def test_malzeme_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "izl-st@alfa.test", "parola": "Izleyici123!", "roller": ["izleyici"]},
        headers=admin,
    )
    izl = _h(
        "alfa",
        await _giris(
            kurulu_istemci, {"slug": "alfa", "eposta": "izl-st@alfa.test", "parola": "Izleyici123!"}
        ),
    )
    # stok:oku var → liste 200
    assert (await kurulu_istemci.get("/api/v1/malzemeler", headers=izl)).status_code == 200
    # stok:yaz yok → oluştur 403
    r = await kurulu_istemci.post(
        "/api/v1/malzemeler", json={"kod": "MLZ-RBAC", "ad": "X", "birim": "adet"}, headers=izl
    )
    assert r.status_code == 403, r.text


async def test_malzeme_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    ha = _h("alfa", await _giris(kurulu_istemci, ALFA))
    da = await _malzeme(kurulu_istemci, ha, kod="MLZ-GIZLI-A")
    hb = _h("beta", await _giris(kurulu_istemci, BETA))
    # beta listede görmez + id ile 404
    r = await kurulu_istemci.get("/api/v1/malzemeler", headers=hb)
    assert "MLZ-GIZLI-A" not in [m["kod"] for m in r.json()["data"]]
    assert (await kurulu_istemci.get(f"/api/v1/malzemeler/{da['id']}", headers=hb)).status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_s9_malzeme.py -v`
Expected: FAIL — `404` (uç yok) / router henüz include edilmedi.

- [ ] **Step 3: Write the malzeme schemas**

`backend/app/modules/stok/schemas.py`:
```python
"""Stok & Satınalma Pydantic DTO'ları.

İstek miktarları ``Decimal`` (kesinlik); cevap miktarları ``float`` (JSON sayı, sınırda
``float(...)`` dönüşümü). Hareket ve satınalma DTO'ları sonraki task'larda eklenir.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class MalzemeOlusturDTO(BaseModel):
    kod: str = Field(min_length=1, max_length=50)
    ad: str = Field(min_length=1, max_length=200)
    birim: str = Field(min_length=1, max_length=20)
    kategori: str = Field(default="", max_length=100)
    min_stok: Decimal = Field(default=Decimal(0), ge=0)
    max_stok: Decimal | None = Field(default=None, ge=0)
    kritik_stok: Decimal = Field(default=Decimal(0), ge=0)


class MalzemeGuncelleDTO(BaseModel):
    ad: str | None = Field(default=None, min_length=1, max_length=200)
    birim: str | None = Field(default=None, min_length=1, max_length=20)
    kategori: str | None = Field(default=None, max_length=100)
    min_stok: Decimal | None = Field(default=None, ge=0)
    max_stok: Decimal | None = Field(default=None, ge=0)
    kritik_stok: Decimal | None = Field(default=None, ge=0)
    aktif: bool | None = None


class MalzemeCevapDTO(BaseModel):
    id: int
    kod: str
    ad: str
    birim: str
    kategori: str
    mevcut_miktar: float
    min_stok: float
    max_stok: float | None = None
    kritik_stok: float
    aktif: bool
    kritik: bool
    olusturma_tarihi: datetime
```

- [ ] **Step 4: Write the malzeme repository**

`backend/app/modules/stok/repository.py`:
```python
"""Stok & Satınalma veri erişimi (repository).

Sorgular şema adı yazmaz; aktif ``search_path`` (tenant şeması) çözer. Hareket ve
satınalma sorguları sonraki task'larda eklenir.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sorgu import siralama_uygula
from app.modules.stok.models import Malzeme

_MALZEME_SIRALAMA = {
    "id": Malzeme.id,
    "kod": Malzeme.kod,
    "ad": Malzeme.ad,
    "mevcut_miktar": Malzeme.mevcut_miktar,
    "kritik_stok": Malzeme.kritik_stok,
    "olusturma_tarihi": Malzeme.olusturma_tarihi,
}


async def malzeme_kod_var_mi(db: AsyncSession, kod: str) -> bool:
    return (await db.scalar(select(Malzeme.id).where(Malzeme.kod == kod))) is not None


async def malzeme_ekle(db: AsyncSession, malzeme: Malzeme) -> Malzeme:
    db.add(malzeme)
    await db.flush()
    return malzeme


async def malzeme_getir(db: AsyncSession, malzeme_id: int) -> Malzeme | None:
    return await db.get(Malzeme, malzeme_id)


async def malzeme_getir_kilitli(db: AsyncSession, malzeme_id: int) -> Malzeme | None:
    """Malzemeyi satır kilidiyle (``FOR UPDATE``) getirir — eşzamanlı stok hareketlerini
    seri hâle getirir, böylece bakiye çift güncellenmez."""
    sonuc = await db.execute(select(Malzeme).where(Malzeme.id == malzeme_id).with_for_update())
    return sonuc.scalar_one_or_none()


async def malzeme_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    arama: str | None = None,
    kategori: str | None = None,
    aktif: bool | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[Malzeme], int]:
    filtreler: list[Any] = []
    if kategori is not None:
        filtreler.append(Malzeme.kategori == kategori)
    if aktif is not None:
        filtreler.append(Malzeme.aktif == aktif)
    if arama:
        kalip = f"%{arama}%"
        filtreler.append(or_(Malzeme.kod.ilike(kalip), Malzeme.ad.ilike(kalip)))

    kosul = select(Malzeme)
    sayim = select(func.count()).select_from(Malzeme)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul, siralama=siralama, yon=yon, izinli=_MALZEME_SIRALAMA,
        varsayilan=Malzeme.id, varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)


async def kritik_listele(db: AsyncSession) -> Sequence[Malzeme]:
    """Aktif + ``kritik_stok > 0`` + ``mevcut_miktar <= kritik_stok`` malzemeler."""
    kosul = (
        select(Malzeme)
        .where(Malzeme.aktif.is_(True))
        .where(Malzeme.kritik_stok > 0)
        .where(Malzeme.mevcut_miktar <= Malzeme.kritik_stok)
        .order_by(Malzeme.kod)
    )
    return (await db.execute(kosul)).scalars().all()
```

- [ ] **Step 5: Write the malzeme router**

`backend/app/modules/stok/router.py`:
```python
"""Stok & Satınalma uçları (``/api/v1``).

Tüm uçlar tenant-kapsamlı + RBAC korumalı; yazma işlemleri audit'lenir. Hareket ve
satınalma uçları sonraki task'larda eklenir.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, tenant_cozumle
from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.stok import repository
from app.modules.stok.birimler import BIRIMLER
from app.modules.stok.models import Malzeme
from app.modules.stok.schemas import MalzemeCevapDTO, MalzemeGuncelleDTO, MalzemeOlusturDTO

router = APIRouter(tags=["Stok & Satınalma"])


def _malzeme_cevap(m: Malzeme) -> dict[str, Any]:
    kritik = m.kritik_stok > 0 and m.mevcut_miktar <= m.kritik_stok
    return MalzemeCevapDTO(
        id=m.id,
        kod=m.kod,
        ad=m.ad,
        birim=m.birim,
        kategori=m.kategori,
        mevcut_miktar=float(m.mevcut_miktar),
        min_stok=float(m.min_stok),
        max_stok=float(m.max_stok) if m.max_stok is not None else None,
        kritik_stok=float(m.kritik_stok),
        aktif=m.aktif,
        kritik=kritik,
        olusturma_tarihi=m.olusturma_tarihi,
    ).model_dump()


def _birim_dogrula(birim: str) -> None:
    if birim not in BIRIMLER:
        raise DogrulamaHatasi(
            "Geçersiz birim",
            detaylar=[{"alan": "birim", "mesaj": f"Geçerli: {', '.join(sorted(BIRIMLER))}"}],
        )


@router.post(
    "/malzemeler", response_model=Zarf[MalzemeCevapDTO], status_code=201, summary="Malzeme oluştur"
)
async def malzeme_olustur(
    govde: MalzemeOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("stok:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    _birim_dogrula(govde.birim)
    if await repository.malzeme_kod_var_mi(db, govde.kod):
        raise CakismaHatasi("Bu kod ile malzeme zaten var")
    malzeme = Malzeme(
        kod=govde.kod,
        ad=govde.ad,
        birim=govde.birim,
        kategori=govde.kategori,
        min_stok=govde.min_stok,
        max_stok=govde.max_stok,
        kritik_stok=govde.kritik_stok,
    )
    await repository.malzeme_ekle(db, malzeme)
    await denetim_yaz(
        db, eylem="olustur", kaynak="malzeme", kaynak_id=str(malzeme.id), kullanici=kullanici
    )
    return basari(_malzeme_cevap(malzeme), mesaj="Malzeme oluşturuldu")


@router.get("/malzemeler", response_model=Zarf[list[MalzemeCevapDTO]], summary="Malzemeleri listele")
async def malzeme_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("stok:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    arama: str | None = None,
    kategori: str | None = None,
    aktif: bool | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.malzeme_listele(
        db, sayfa=sayfa, adet=adet, arama=arama, kategori=kategori, aktif=aktif,
        siralama=siralama, yon=yon,
    )
    return sayfali([_malzeme_cevap(m) for m in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get("/stok/kritik", response_model=Zarf[list[MalzemeCevapDTO]], summary="Kritik stoktakiler")
async def kritik_stok(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("stok:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    kayitlar = await repository.kritik_listele(db)
    return basari([_malzeme_cevap(m) for m in kayitlar], mesaj="Kritik stok")


@router.get("/malzemeler/{malzeme_id}", response_model=Zarf[MalzemeCevapDTO], summary="Malzeme detayı")
async def malzeme_detay(
    malzeme_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("stok:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    malzeme = await repository.malzeme_getir(db, malzeme_id)
    if malzeme is None:
        raise KaynakBulunamadi("Malzeme bulunamadı")
    return basari(_malzeme_cevap(malzeme), mesaj="Malzeme detayı")


@router.patch(
    "/malzemeler/{malzeme_id}", response_model=Zarf[MalzemeCevapDTO], summary="Malzeme güncelle"
)
async def malzeme_guncelle(
    malzeme_id: int,
    govde: MalzemeGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("stok:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    malzeme = await repository.malzeme_getir(db, malzeme_id)
    if malzeme is None:
        raise KaynakBulunamadi("Malzeme bulunamadı")
    if govde.birim is not None:
        _birim_dogrula(govde.birim)
        malzeme.birim = govde.birim
    for alan in ("ad", "kategori", "min_stok", "max_stok", "kritik_stok", "aktif"):
        deger = getattr(govde, alan)
        if deger is not None:
            setattr(malzeme, alan, deger)
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="malzeme", kaynak_id=str(malzeme.id), kullanici=kullanici
    )
    return basari(_malzeme_cevap(malzeme), mesaj="Malzeme güncellendi")
```

- [ ] **Step 6: Register the router**

`backend/app/api/router.py` — `saha_router` satırlarına paralel olarak ekle:
```python
from app.modules.stok.router import router as stok_router
```
ve include bloğuna (`bakim_router`'dan sonra, `ws_router`'dan önce):
```python
api_router.include_router(stok_router)
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_s9_malzeme.py -v`
Expected: PASS (7 passed)

- [ ] **Step 8: Lint + type + commit**

```bash
cd backend && ruff check app/modules/stok app/api/router.py tests/test_s9_malzeme.py && mypy app/modules/stok app/api/router.py
git add backend/app/modules/stok/schemas.py backend/app/modules/stok/repository.py backend/app/modules/stok/router.py backend/app/api/router.py backend/tests/test_s9_malzeme.py
git commit -m "feat(stok): malzeme CRUD + /stok/kritik uçları (RBAC + izolasyon testli) (S9)"
```

---

## Task 4: Stok hareketi dilimi (servis + bakiye + kenar-tetikli stok.kritik + idempotency)

**Files:**
- Create: `backend/app/modules/stok/service.py` (`stok_hareketi_uygula`)
- Modify: `backend/app/modules/stok/schemas.py` (hareket DTO'ları ekle)
- Modify: `backend/app/modules/stok/repository.py` (hareket sorguları ekle)
- Modify: `backend/app/modules/stok/router.py` (hareket uçları ekle)
- Test: `backend/tests/test_s9_hareket.py`

**Interfaces:**
- Consumes: `Malzeme`, `StokHareketi` (Task 2); `malzeme_getir_kilitli`, `_malzeme_cevap` (Task 3); `olay_yayinla` (`app.core.olaylar`); `yayinla` (`app.core.gercekzaman`); `STOK_HAREKET_TURLERI` (Task 1).
- Produces:
  - `service.stok_hareketi_uygula(db, malzeme, *, tur, miktar, aciklama="", kaynak=None, kullanici, idempotency_anahtari=None) -> tuple[StokHareketi, bool]` — `(hareket, kritige_dustu)`; outbox `stok.kritik` olayını **aynı transaction'da** yazar.
  - `service.OLAY_KRITIK = "stok.kritik"`
  - DTO'lar: `StokHareketiOlusturDTO`, `StokHareketiCevapDTO`
  - Repository: `hareket_ekle`, `hareket_idempotent_getir`, `hareket_listele`
  - Router: `POST/GET /stok-hareketleri`; `_hareket_cevap(h)`

- [ ] **Step 1: Write the failing integration test**

`backend/tests/test_s9_hareket.py`:
```python
"""S9 entegrasyon: stok hareketi bakiye + negatif + idempotency + kenar-tetikli stok.kritik."""

from __future__ import annotations

import json

import asyncpg
from httpx import AsyncClient

from tests.conftest import ALFA

KIMLIK = "/api/v1/kimlik"
ASYNCPG_URL = "postgresql://fabrikaos:fabrikaos@localhost:5432/fabrikaos_test"


async def _giris(istemci: AsyncClient, t: dict) -> str:
    r = await istemci.post(
        f"{KIMLIK}/token",
        data={"username": t["eposta"], "password": t["parola"]},
        headers={"X-Tenant": t["slug"]},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["access_token"]


def _h(slug: str, access: str) -> dict[str, str]:
    return {"X-Tenant": slug, "Authorization": f"Bearer {access}"}


async def _malzeme_id(istemci: AsyncClient, h: dict[str, str], kod: str, kritik: float = 0) -> int:
    r = await istemci.post(
        "/api/v1/malzemeler",
        json={"kod": kod, "ad": kod, "birim": "adet", "kritik_stok": kritik},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return int(r.json()["data"]["id"])


async def _hareket(istemci: AsyncClient, h: dict[str, str], mid: int, tur: str, miktar: float,
                   anahtar: str | None = None) -> tuple[int, dict]:
    bh = dict(h)
    if anahtar is not None:
        bh["Idempotency-Key"] = anahtar
    r = await istemci.post(
        "/api/v1/stok-hareketleri",
        json={"malzeme_id": mid, "tur": tur, "miktar": miktar},
        headers=bh,
    )
    return r.status_code, r.json()


async def _outbox(sema: str, olay_turu: str) -> list[dict]:
    c = await asyncpg.connect(ASYNCPG_URL)
    try:
        rows = await c.fetch(
            f'SELECT govde FROM "{sema}".giden_olaylar WHERE olay_turu = $1 ORDER BY id', olay_turu
        )
        return [json.loads(r["govde"]) if isinstance(r["govde"], str) else r["govde"] for r in rows]
    finally:
        await c.close()


async def test_giris_cikis_bakiye(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, h, "MLZ-BAK")
    sk, d = await _hareket(kurulu_istemci, h, mid, "giris", 10)
    assert sk == 201, d
    assert d["data"]["bakiye_sonrasi"] == 10
    sk, d = await _hareket(kurulu_istemci, h, mid, "cikis", 4)
    assert d["data"]["bakiye_sonrasi"] == 6
    # malzeme bakiyesi de güncel
    r = await kurulu_istemci.get(f"/api/v1/malzemeler/{mid}", headers=h)
    assert r.json()["data"]["mevcut_miktar"] == 6


async def test_negatif_cikis_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, h, "MLZ-NEG")
    sk, d = await _hareket(kurulu_istemci, h, mid, "cikis", 1)
    assert sk == 422, d


async def test_duzeltme_mutlak(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, h, "MLZ-DUZ")
    await _hareket(kurulu_istemci, h, mid, "giris", 10)
    sk, d = await _hareket(kurulu_istemci, h, mid, "duzeltme", 7)
    assert sk == 201, d
    assert d["data"]["bakiye_sonrasi"] == 7


async def test_idempotency_tek_hareket(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, h, "MLZ-IDEM")
    await _hareket(kurulu_istemci, h, mid, "giris", 5, anahtar="ANAH-1")
    # aynı anahtar → bakiye 1 kez değişti (10 değil 5)
    await _hareket(kurulu_istemci, h, mid, "giris", 5, anahtar="ANAH-1")
    r = await kurulu_istemci.get(f"/api/v1/malzemeler/{mid}", headers=h)
    assert r.json()["data"]["mevcut_miktar"] == 5


async def test_kritik_kenar_tetik_bir_kez(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, h, "MLZ-KENAR", kritik=5)
    await _hareket(kurulu_istemci, h, mid, "giris", 10)  # 10, eşik üstü
    await _hareket(kurulu_istemci, h, mid, "cikis", 6)   # 4, eşik altına ilk geçiş → olay
    await _hareket(kurulu_istemci, h, mid, "cikis", 1)   # 3, hâlâ altında → YENİ olay yok

    govdeler = [g for g in await _outbox("tenant_alfa", "stok.kritik") if g.get("malzeme_id") == mid]
    assert len(govdeler) == 1, govdeler
    assert govdeler[0]["kod"] == "MLZ-KENAR"
    assert govdeler[0]["mevcut_miktar"] == 4


async def test_hareket_listele_filtre(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, h, "MLZ-LIST")
    await _hareket(kurulu_istemci, h, mid, "giris", 3)
    r = await kurulu_istemci.get(f"/api/v1/stok-hareketleri?malzeme_id={mid}&tur=giris", headers=h)
    assert r.status_code == 200, r.text
    assert all(x["tur"] == "giris" and x["malzeme_id"] == mid for x in r.json()["data"])
    assert "meta" in r.json()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_s9_hareket.py -v`
Expected: FAIL — `POST /stok-hareketleri` yok (404/405).

- [ ] **Step 3: Write the service**

`backend/app/modules/stok/service.py`:
```python
"""Stok & Satınalma iş kuralları — bakiye güncelleme + kenar-tetikli kritik olay.

``stok_hareketi_uygula`` malzemeyi (çağıran ``FOR UPDATE`` ile kilitli getirir) günceller;
bakiye **kritik eşiğin üstünden altına ilk geçtiğinde** (kenar tetik) ``stok.kritik`` olayını
hareketi yazan iş ile **aynı transaction'da** outbox'a yazar (transactional outbox / ADR-0007).
``govde`` JSON-native olmalı → Decimal'ler ``float`` olarak verilir.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DogrulamaHatasi
from app.core.olaylar import olay_yayinla
from app.kimlik.models import Kullanici
from app.modules.stok.models import Malzeme, StokHareketi

OLAY_KRITIK = "stok.kritik"


def _yeni_bakiye(eski: Decimal, *, tur: str, miktar: Decimal) -> Decimal:
    if tur == "giris":
        return eski + miktar
    if tur == "cikis":
        yeni = eski - miktar
        if yeni < 0:
            raise DogrulamaHatasi(
                "Yetersiz stok",
                detaylar=[{"alan": "miktar", "mesaj": f"Mevcut bakiye {eski}, çıkış {miktar}"}],
            )
        return yeni
    # duzeltme: mutlak sayım sonucu (miktar = yeni bakiye).
    return miktar


async def stok_hareketi_uygula(
    db: AsyncSession,
    malzeme: Malzeme,
    *,
    tur: str,
    miktar: Decimal,
    aciklama: str = "",
    kaynak: str | None = None,
    kullanici: Kullanici,
    idempotency_anahtari: str | None = None,
) -> tuple[StokHareketi, bool]:
    """Bakiyeyi günceller, hareketi yazar, gerekirse kenar-tetikli ``stok.kritik`` yayınlar."""
    eski = malzeme.mevcut_miktar
    yeni = _yeni_bakiye(eski, tur=tur, miktar=miktar)

    kritik = malzeme.kritik_stok
    ustteydi = kritik > 0 and eski > kritik
    simdi_altinda = kritik > 0 and yeni <= kritik
    kritige_dustu = ustteydi and simdi_altinda

    malzeme.mevcut_miktar = yeni
    hareket = StokHareketi(
        malzeme_id=malzeme.id,
        tur=tur,
        miktar=miktar,
        bakiye_sonrasi=yeni,
        aciklama=aciklama,
        kaynak=kaynak,
        olusturan_kullanici_id=kullanici.id,
        idempotency_anahtari=idempotency_anahtari,
    )
    db.add(hareket)

    if kritige_dustu:
        await olay_yayinla(
            db,
            olay_turu=OLAY_KRITIK,
            govde={
                "malzeme_id": malzeme.id,
                "kod": malzeme.kod,
                "ad": malzeme.ad,
                "mevcut_miktar": float(yeni),
                "kritik_stok": float(kritik),
            },
        )
    await db.flush()
    return hareket, kritige_dustu
```

- [ ] **Step 4: Add hareket schemas**

`backend/app/modules/stok/schemas.py` — dosya sonuna ekle:
```python
class StokHareketiOlusturDTO(BaseModel):
    malzeme_id: int
    tur: str = Field(min_length=1, max_length=10)
    miktar: Decimal = Field(gt=0)
    aciklama: str = Field(default="", max_length=500)
    kaynak: str | None = Field(default=None, max_length=50)


class StokHareketiCevapDTO(BaseModel):
    id: int
    malzeme_id: int
    tur: str
    miktar: float
    bakiye_sonrasi: float
    aciklama: str
    kaynak: str | None = None
    olusturan_kullanici_id: int | None = None
    olusturma_tarihi: datetime
```

- [ ] **Step 5: Add hareket repository functions**

`backend/app/modules/stok/repository.py` — importlara `StokHareketi` ekle ve dosya sonuna fonksiyonları ekle:
```python
# importları güncelle:
from app.modules.stok.models import Malzeme, StokHareketi

# ... mevcut malzeme fonksiyonlarından sonra:

_HAREKET_SIRALAMA = {
    "id": StokHareketi.id,
    "tur": StokHareketi.tur,
    "miktar": StokHareketi.miktar,
    "olusturma_tarihi": StokHareketi.olusturma_tarihi,
}


async def hareket_ekle(db: AsyncSession, hareket: StokHareketi) -> StokHareketi:
    db.add(hareket)
    await db.flush()
    return hareket


async def hareket_idempotent_getir(db: AsyncSession, anahtar: str) -> StokHareketi | None:
    sonuc = await db.execute(
        select(StokHareketi).where(StokHareketi.idempotency_anahtari == anahtar)
    )
    return sonuc.scalar_one_or_none()


async def hareket_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    malzeme_id: int | None = None,
    tur: str | None = None,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[StokHareketi], int]:
    filtreler: list[Any] = []
    if malzeme_id is not None:
        filtreler.append(StokHareketi.malzeme_id == malzeme_id)
    if tur is not None:
        filtreler.append(StokHareketi.tur == tur)
    if baslangic is not None:
        filtreler.append(StokHareketi.olusturma_tarihi >= baslangic)
    if bitis is not None:
        filtreler.append(StokHareketi.olusturma_tarihi <= bitis)

    kosul = select(StokHareketi)
    sayim = select(func.count()).select_from(StokHareketi)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul, siralama=siralama, yon=yon, izinli=_HAREKET_SIRALAMA,
        varsayilan=StokHareketi.id, varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)
```
Ayrıca `repository.py` başındaki import bloğuna `from datetime import datetime` ekle.

- [ ] **Step 6: Add hareket endpoints to the router**

`backend/app/modules/stok/router.py` — importları genişlet ve hareket uçlarını ekle:
```python
# importlara ekle:
from datetime import datetime

from fastapi import APIRouter, Depends, Header

from app.control_plane.models import Tenant
from app.core.gercekzaman import yayinla
from app.modules.stok import repository, service
from app.modules.stok.birimler import BIRIMLER, STOK_HAREKET_TURLERI
from app.modules.stok.models import Malzeme, StokHareketi
from app.modules.stok.schemas import (
    MalzemeCevapDTO,
    MalzemeGuncelleDTO,
    MalzemeOlusturDTO,
    StokHareketiCevapDTO,
    StokHareketiOlusturDTO,
)


def _hareket_cevap(h: StokHareketi) -> dict[str, Any]:
    return StokHareketiCevapDTO(
        id=h.id,
        malzeme_id=h.malzeme_id,
        tur=h.tur,
        miktar=float(h.miktar),
        bakiye_sonrasi=float(h.bakiye_sonrasi),
        aciklama=h.aciklama,
        kaynak=h.kaynak,
        olusturan_kullanici_id=h.olusturan_kullanici_id,
        olusturma_tarihi=h.olusturma_tarihi,
    ).model_dump()


@router.post(
    "/stok-hareketleri",
    response_model=Zarf[StokHareketiCevapDTO],
    status_code=201,
    summary="Stok hareketi ekle (giriş/çıkış/düzeltme)",
)
async def stok_hareketi_olustur(
    govde: StokHareketiOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("stok:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    if govde.tur not in STOK_HAREKET_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz hareket türü",
            detaylar=[{"alan": "tur", "mesaj": f"Geçerli: {', '.join(sorted(STOK_HAREKET_TURLERI))}"}],
        )
    if idempotency_key is not None:
        mevcut = await repository.hareket_idempotent_getir(db, idempotency_key)
        if mevcut is not None:
            return basari(_hareket_cevap(mevcut), mesaj="Hareket zaten işlenmiş")

    malzeme = await repository.malzeme_getir_kilitli(db, govde.malzeme_id)
    if malzeme is None:
        raise KaynakBulunamadi("Malzeme bulunamadı")

    hareket, kritige_dustu = await service.stok_hareketi_uygula(
        db, malzeme, tur=govde.tur, miktar=govde.miktar, aciklama=govde.aciklama,
        kaynak=govde.kaynak, kullanici=kullanici, idempotency_anahtari=idempotency_key,
    )
    await denetim_yaz(
        db, eylem="hareket", kaynak="stok_hareketi", kaynak_id=str(hareket.id),
        kullanici=kullanici, detay={"tur": govde.tur, "malzeme_id": malzeme.id},
    )
    await yayinla(tenant.slug, {"tur": "stok.hareket", "malzeme_id": malzeme.id})
    if kritige_dustu:
        await yayinla(tenant.slug, {"tur": "stok.kritik", "malzeme_id": malzeme.id, "kod": malzeme.kod})
    return basari(_hareket_cevap(hareket), mesaj="Stok hareketi eklendi")


@router.get(
    "/stok-hareketleri",
    response_model=Zarf[list[StokHareketiCevapDTO]],
    summary="Stok hareketlerini listele",
)
async def stok_hareketi_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("stok:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    malzeme_id: int | None = None,
    tur: str | None = None,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.hareket_listele(
        db, sayfa=sayfa, adet=adet, malzeme_id=malzeme_id, tur=tur,
        baslangic=baslangic, bitis=bitis, siralama=siralama, yon=yon,
    )
    return sayfali([_hareket_cevap(x) for x in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)
```
> Not: `Malzeme` importu zaten Task 3'te var; yukarıdaki import bloğu mevcut satırların **güncellenmiş** hâlidir (tekrar eklenmez, mevcut import'lar genişletilir).

- [ ] **Step 7: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_s9_hareket.py -v`
Expected: PASS (6 passed)

- [ ] **Step 8: Lint + type + commit**

```bash
cd backend && ruff check app/modules/stok tests/test_s9_hareket.py && mypy app/modules/stok
git add backend/app/modules/stok/service.py backend/app/modules/stok/schemas.py backend/app/modules/stok/repository.py backend/app/modules/stok/router.py backend/tests/test_s9_hareket.py
git commit -m "feat(stok): stok hareketi + bakiye + kenar-tetikli stok.kritik + idempotency (S9)"
```

---

## Task 5: Satınalma talebi dilimi (çok-kalemli + onay akışı + satinalma:onay ayrımı)

**Files:**
- Modify: `backend/app/modules/stok/service.py` (`talep_durum_gecisi` + kod yardımcıları)
- Modify: `backend/app/modules/stok/schemas.py` (talep DTO'ları)
- Modify: `backend/app/modules/stok/repository.py` (talep sorguları)
- Modify: `backend/app/modules/stok/router.py` (talep uçları + aksiyonlar)
- Test: `backend/tests/test_s9_satinalma.py`

**Interfaces:**
- Consumes: `SatinalmaTalebi`, `SatinalmaTalebiKalemi`, `Malzeme` (Task 2); `talep_durum` (Task 1); `malzeme_getir` (Task 3).
- Produces:
  - `service.talep_durum_gecisi(db, talep, *, hedef, onaylayan=None, red_nedeni=None) -> SatinalmaTalebi`
  - `service.talep_gecici_kod() -> str`, `service.talep_kalici_kod(id: int) -> str` (`ST-{yıl}-{id:06d}`)
  - DTO'lar: `SatinalmaKalemDTO`, `SatinalmaTalebiOlusturDTO`, `SatinalmaTalebiGuncelleDTO`, `RedDTO`, `SatinalmaKalemCevapDTO`, `SatinalmaTalebiCevapDTO`, `SatinalmaTalebiDetayDTO`
  - Repository: `talep_kod_var_mi`, `talep_ekle`, `talep_getir`, `talep_getir_kilitli`, `talep_getir_kalemli`, `talep_listele`
  - Router: `POST/GET /satinalma-talepleri`, `GET/PATCH /satinalma-talepleri/{id}`, `POST /{id}/gonder|onayla|reddet|iptal`

- [ ] **Step 1: Write the failing integration test**

`backend/tests/test_s9_satinalma.py`:
```python
"""S9 entegrasyon: çok-kalemli satınalma talebi + onay akışı + satinalma:onay ayrımı + izolasyon."""

from __future__ import annotations

import re

from httpx import AsyncClient

from tests.conftest import ALFA, BETA

KIMLIK = "/api/v1/kimlik"


async def _giris(istemci: AsyncClient, t: dict) -> str:
    r = await istemci.post(
        f"{KIMLIK}/token",
        data={"username": t["eposta"], "password": t["parola"]},
        headers={"X-Tenant": t["slug"]},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["access_token"]


def _h(slug: str, access: str) -> dict[str, str]:
    return {"X-Tenant": slug, "Authorization": f"Bearer {access}"}


async def _malzeme_id(istemci: AsyncClient, h: dict[str, str], kod: str) -> int:
    r = await istemci.post(
        "/api/v1/malzemeler", json={"kod": kod, "ad": kod, "birim": "adet"}, headers=h
    )
    assert r.status_code == 201, r.text
    return int(r.json()["data"]["id"])


async def _talep(istemci: AsyncClient, h: dict[str, str], mid: int, fiyat: float | None = 100) -> dict:
    govde = {
        "baslik": "Rulman alımı",
        "kalemler": [{"malzeme_id": mid, "miktar": 3, "birim": "adet", "tahmini_birim_fiyat": fiyat}],
    }
    r = await istemci.post("/api/v1/satinalma-talepleri", json=govde, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_talep_olustur_oto_kod_ve_toplam(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, h, "MLZ-ST1")
    d = await _talep(kurulu_istemci, h, mid, fiyat=100)
    assert d["durum"] == "taslak"
    assert re.fullmatch(r"ST-\d{4}-\d{6}", d["kod"]), d["kod"]
    # detay: tahmini_toplam = 3 * 100
    r = await kurulu_istemci.get(f"/api/v1/satinalma-talepleri/{d['id']}", headers=h)
    assert r.json()["data"]["tahmini_toplam"] == 300
    assert len(r.json()["data"]["kalemler"]) == 1


async def test_talep_bos_kalem_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/satinalma-talepleri", json={"baslik": "Boş", "kalemler": []}, headers=h
    )
    assert r.status_code == 422, r.text


async def test_akis_gonder_onayla(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, h, "MLZ-ST2")
    d = await _talep(kurulu_istemci, h, mid)
    tid = d["id"]
    assert (await kurulu_istemci.post(f"/api/v1/satinalma-talepleri/{tid}/gonder", headers=h)).status_code == 200
    r = await kurulu_istemci.post(f"/api/v1/satinalma-talepleri/{tid}/onayla", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["durum"] == "onaylandi"
    assert r.json()["data"]["onaylayan_kullanici_id"] is not None


async def test_gecersiz_gecis_409(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, h, "MLZ-ST3")
    d = await _talep(kurulu_istemci, h, mid)
    # taslak → onayla (önce gönderilmeli) yasak
    r = await kurulu_istemci.post(f"/api/v1/satinalma-talepleri/{d['id']}/onayla", headers=h)
    assert r.status_code == 409, r.text


async def test_reddet_neden_gerekli_ve_calisir(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, h, "MLZ-ST4")
    d = await _talep(kurulu_istemci, h, mid)
    tid = d["id"]
    await kurulu_istemci.post(f"/api/v1/satinalma-talepleri/{tid}/gonder", headers=h)
    # neden yok → 422
    assert (await kurulu_istemci.post(f"/api/v1/satinalma-talepleri/{tid}/reddet", json={"red_nedeni": ""}, headers=h)).status_code == 422
    r = await kurulu_istemci.post(
        f"/api/v1/satinalma-talepleri/{tid}/reddet", json={"red_nedeni": "Bütçe yok"}, headers=h
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["durum"] == "reddedildi"
    assert r.json()["data"]["red_nedeni"] == "Bütçe yok"


async def test_onay_ayri_izin_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, admin, "MLZ-ST5")
    # 'depo' rolü: satinalma:yaz var ama satinalma:onay YOK (Task 6'da seed edilir).
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "depo@alfa.test", "parola": "Depo12345!", "roller": ["depo"]},
        headers=admin,
    )
    depo = _h("alfa", await _giris(kurulu_istemci, {"slug": "alfa", "eposta": "depo@alfa.test", "parola": "Depo12345!"}))
    d = await _talep(kurulu_istemci, depo, mid)
    tid = d["id"]
    assert (await kurulu_istemci.post(f"/api/v1/satinalma-talepleri/{tid}/gonder", headers=depo)).status_code == 200
    # satinalma:onay yok → 403
    r = await kurulu_istemci.post(f"/api/v1/satinalma-talepleri/{tid}/onayla", headers=depo)
    assert r.status_code == 403, r.text


async def test_talep_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    ha = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, ha, "MLZ-ST6")
    d = await _talep(kurulu_istemci, ha, mid)
    hb = _h("beta", await _giris(kurulu_istemci, BETA))
    assert (await kurulu_istemci.get(f"/api/v1/satinalma-talepleri/{d['id']}", headers=hb)).status_code == 404
```

> Not: `test_onay_ayri_izin_403` ve `depo` rolü Task 6 seed'ine bağlıdır. Bu testi Task 6 tamamlanınca koş; Task 5'i koşarken bu tek testi `-k "not onay_ayri_izin"` ile dışla.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_s9_satinalma.py -v -k "not onay_ayri_izin"`
Expected: FAIL — `/satinalma-talepleri` yok.

- [ ] **Step 3: Add code helpers + state transition to service**

`backend/app/modules/stok/service.py` — importlara ekle ve dosya sonuna fonksiyonları ekle:
```python
# importlara ekle:
import uuid
from datetime import UTC, datetime

from app.core.exceptions import CakismaHatasi
from app.modules.stok import talep_durum
from app.modules.stok.models import Malzeme, SatinalmaTalebi, StokHareketi

# ... mevcut stok_hareketi_uygula'dan sonra:


def talep_gecici_kod() -> str:
    """Kalıcı kod üretilene dek (id bilinene dek) kullanılan geçici tekil değer."""
    return f"GECICI-{uuid.uuid4().hex}"


def talep_kalici_kod(talep_id: int) -> str:
    """İnsan-okur satınalma talebi numarası: ``ST-{yıl}-{id:06d}``."""
    return f"ST-{datetime.now(UTC).year}-{talep_id:06d}"


async def talep_durum_gecisi(
    db: AsyncSession,
    talep: SatinalmaTalebi,
    *,
    hedef: str,
    onaylayan: Kullanici | None = None,
    red_nedeni: str | None = None,
) -> SatinalmaTalebi:
    """Talebi ``hedef`` duruma geçirir; durum makinesi + onay/red alanlarını uygular.

    - Tanımsız hedef → 422; makineye aykırı geçiş → 409.
    - ``reddedildi`` ``red_nedeni`` gerektirir → 422.
    - ``onaylandi``/``reddedildi`` onaylayan + onay tarihini yazar.
    """
    if hedef not in talep_durum.DURUMLAR:
        raise DogrulamaHatasi(
            "Geçersiz durum",
            detaylar=[{"alan": "durum", "mesaj": f"Geçerli: {', '.join(sorted(talep_durum.DURUMLAR))}"}],
        )
    if not talep_durum.gecis_gecerli_mi(talep.durum, hedef):
        raise CakismaHatasi(f"Geçersiz durum geçişi: {talep.durum} → {hedef}")

    if hedef == "reddedildi" and not (red_nedeni and red_nedeni.strip()):
        raise DogrulamaHatasi(
            "Red nedeni gerekli",
            detaylar=[{"alan": "red_nedeni", "mesaj": "'reddedildi' için zorunlu"}],
        )

    talep.durum = hedef
    if hedef in ("onaylandi", "reddedildi"):
        talep.onaylayan_kullanici_id = onaylayan.id if onaylayan is not None else None
        talep.onay_tarihi = datetime.now(UTC)
    if hedef == "reddedildi":
        talep.red_nedeni = red_nedeni
    await db.flush()
    return talep
```

- [ ] **Step 4: Add talep schemas**

`backend/app/modules/stok/schemas.py` — dosya sonuna ekle:
```python
class SatinalmaKalemDTO(BaseModel):
    malzeme_id: int
    miktar: Decimal = Field(gt=0)
    birim: str = Field(min_length=1, max_length=20)
    tahmini_birim_fiyat: Decimal | None = Field(default=None, ge=0)
    aciklama: str = Field(default="", max_length=500)


class SatinalmaTalebiOlusturDTO(BaseModel):
    baslik: str = Field(min_length=1, max_length=200)
    aciklama: str = Field(default="", max_length=1000)
    para_birimi: str = Field(default="TRY", min_length=3, max_length=3)
    kalemler: list[SatinalmaKalemDTO] = Field(min_length=1)


class SatinalmaTalebiGuncelleDTO(BaseModel):
    baslik: str | None = Field(default=None, min_length=1, max_length=200)
    aciklama: str | None = Field(default=None, max_length=1000)
    para_birimi: str | None = Field(default=None, min_length=3, max_length=3)
    kalemler: list[SatinalmaKalemDTO] | None = Field(default=None, min_length=1)


class RedDTO(BaseModel):
    red_nedeni: str = Field(default="", max_length=500)


class SatinalmaKalemCevapDTO(BaseModel):
    id: int
    malzeme_id: int
    miktar: float
    birim: str
    tahmini_birim_fiyat: float | None = None
    aciklama: str


class SatinalmaTalebiCevapDTO(BaseModel):
    id: int
    kod: str
    baslik: str
    aciklama: str
    durum: str
    para_birimi: str
    talep_eden_kullanici_id: int | None = None
    onaylayan_kullanici_id: int | None = None
    onay_tarihi: datetime | None = None
    red_nedeni: str | None = None
    tahmini_toplam: float | None = None
    olusturma_tarihi: datetime


class SatinalmaTalebiDetayDTO(SatinalmaTalebiCevapDTO):
    kalemler: list[SatinalmaKalemCevapDTO] = Field(default_factory=list)
```

- [ ] **Step 5: Add talep repository functions**

`backend/app/modules/stok/repository.py` — importlara `SatinalmaTalebi` + `selectinload` ekle, dosya sonuna ekle:
```python
# importları güncelle:
from sqlalchemy.orm import selectinload

from app.modules.stok.models import Malzeme, SatinalmaTalebi, StokHareketi

# ...

_TALEP_SIRALAMA = {
    "id": SatinalmaTalebi.id,
    "kod": SatinalmaTalebi.kod,
    "baslik": SatinalmaTalebi.baslik,
    "durum": SatinalmaTalebi.durum,
    "olusturma_tarihi": SatinalmaTalebi.olusturma_tarihi,
}


async def talep_kod_var_mi(db: AsyncSession, kod: str) -> bool:
    return (await db.scalar(select(SatinalmaTalebi.id).where(SatinalmaTalebi.kod == kod))) is not None


async def talep_ekle(db: AsyncSession, talep: SatinalmaTalebi) -> SatinalmaTalebi:
    db.add(talep)
    await db.flush()
    return talep


async def talep_getir(db: AsyncSession, talep_id: int) -> SatinalmaTalebi | None:
    return await db.get(SatinalmaTalebi, talep_id)


async def talep_getir_kilitli(db: AsyncSession, talep_id: int) -> SatinalmaTalebi | None:
    sonuc = await db.execute(
        select(SatinalmaTalebi).where(SatinalmaTalebi.id == talep_id).with_for_update()
    )
    return sonuc.scalar_one_or_none()


async def talep_getir_kalemli(db: AsyncSession, talep_id: int) -> SatinalmaTalebi | None:
    sonuc = await db.execute(
        select(SatinalmaTalebi)
        .where(SatinalmaTalebi.id == talep_id)
        .options(selectinload(SatinalmaTalebi.kalemler))
    )
    return sonuc.scalar_one_or_none()


async def talep_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    durum: str | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[SatinalmaTalebi], int]:
    filtreler: list[Any] = []
    if durum is not None:
        filtreler.append(SatinalmaTalebi.durum == durum)
    if arama:
        kalip = f"%{arama}%"
        filtreler.append(or_(SatinalmaTalebi.kod.ilike(kalip), SatinalmaTalebi.baslik.ilike(kalip)))

    kosul = select(SatinalmaTalebi)
    sayim = select(func.count()).select_from(SatinalmaTalebi)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul, siralama=siralama, yon=yon, izinli=_TALEP_SIRALAMA,
        varsayilan=SatinalmaTalebi.id, varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)
```

- [ ] **Step 6: Add talep endpoints to the router**

`backend/app/modules/stok/router.py` — importları genişlet ve talep uçlarını ekle:
```python
# importlara ekle:
from app.modules.stok.models import (
    Malzeme,
    SatinalmaTalebi,
    SatinalmaTalebiKalemi,
    StokHareketi,
)
from app.modules.stok.schemas import (
    # ... mevcutlar +
    RedDTO,
    SatinalmaKalemCevapDTO,
    SatinalmaTalebiCevapDTO,
    SatinalmaTalebiDetayDTO,
    SatinalmaTalebiGuncelleDTO,
    SatinalmaTalebiOlusturDTO,
)


def _tahmini_toplam(kalemler: list[SatinalmaTalebiKalemi]) -> float | None:
    parcalar = [k.miktar * k.tahmini_birim_fiyat for k in kalemler if k.tahmini_birim_fiyat is not None]
    return float(sum(parcalar)) if parcalar else None


def _talep_cevap(t: SatinalmaTalebi) -> dict[str, Any]:
    return SatinalmaTalebiCevapDTO(
        id=t.id, kod=t.kod, baslik=t.baslik, aciklama=t.aciklama, durum=t.durum,
        para_birimi=t.para_birimi, talep_eden_kullanici_id=t.talep_eden_kullanici_id,
        onaylayan_kullanici_id=t.onaylayan_kullanici_id, onay_tarihi=t.onay_tarihi,
        red_nedeni=t.red_nedeni, olusturma_tarihi=t.olusturma_tarihi,
    ).model_dump()


def _talep_detay_cevap(t: SatinalmaTalebi) -> dict[str, Any]:
    return SatinalmaTalebiDetayDTO(
        id=t.id, kod=t.kod, baslik=t.baslik, aciklama=t.aciklama, durum=t.durum,
        para_birimi=t.para_birimi, talep_eden_kullanici_id=t.talep_eden_kullanici_id,
        onaylayan_kullanici_id=t.onaylayan_kullanici_id, onay_tarihi=t.onay_tarihi,
        red_nedeni=t.red_nedeni, tahmini_toplam=_tahmini_toplam(list(t.kalemler)),
        olusturma_tarihi=t.olusturma_tarihi,
        kalemler=[
            SatinalmaKalemCevapDTO(
                id=k.id, malzeme_id=k.malzeme_id, miktar=float(k.miktar), birim=k.birim,
                tahmini_birim_fiyat=float(k.tahmini_birim_fiyat) if k.tahmini_birim_fiyat is not None else None,
                aciklama=k.aciklama,
            )
            for k in t.kalemler
        ],
    ).model_dump()


async def _kalemleri_dogrula(db: AsyncSession, kalemler: list) -> None:
    for k in kalemler:
        if k.birim not in BIRIMLER:
            raise DogrulamaHatasi(
                "Geçersiz birim",
                detaylar=[{"alan": "kalemler.birim", "mesaj": f"Geçerli: {', '.join(sorted(BIRIMLER))}"}],
            )
        if await repository.malzeme_getir(db, k.malzeme_id) is None:
            raise KaynakBulunamadi(f"Malzeme bulunamadı: {k.malzeme_id}")


@router.post(
    "/satinalma-talepleri",
    response_model=Zarf[SatinalmaTalebiDetayDTO],
    status_code=201,
    summary="Satınalma talebi oluştur (çok-kalemli)",
)
async def talep_olustur(
    govde: SatinalmaTalebiOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("satinalma:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    await _kalemleri_dogrula(db, govde.kalemler)
    talep = SatinalmaTalebi(
        kod=service.talep_gecici_kod(), baslik=govde.baslik, aciklama=govde.aciklama,
        para_birimi=govde.para_birimi, talep_eden_kullanici_id=kullanici.id,
        kalemler=[
            SatinalmaTalebiKalemi(
                malzeme_id=k.malzeme_id, miktar=k.miktar, birim=k.birim,
                tahmini_birim_fiyat=k.tahmini_birim_fiyat, aciklama=k.aciklama,
            )
            for k in govde.kalemler
        ],
    )
    await repository.talep_ekle(db, talep)
    talep.kod = service.talep_kalici_kod(talep.id)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="satinalma_talebi", kaynak_id=str(talep.id), kullanici=kullanici
    )
    await yayinla(tenant.slug, {"tur": "satinalma.durum", "id": talep.id, "durum": talep.durum})
    talep_tam = await repository.talep_getir_kalemli(db, talep.id)
    assert talep_tam is not None
    return basari(_talep_detay_cevap(talep_tam), mesaj="Satınalma talebi oluşturuldu")


@router.get(
    "/satinalma-talepleri",
    response_model=Zarf[list[SatinalmaTalebiCevapDTO]],
    summary="Satınalma taleplerini listele",
)
async def talep_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("satinalma:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    durum: str | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.talep_listele(
        db, sayfa=sayfa, adet=adet, durum=durum, arama=arama, siralama=siralama, yon=yon
    )
    return sayfali([_talep_cevap(t) for t in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/satinalma-talepleri/{talep_id}",
    response_model=Zarf[SatinalmaTalebiDetayDTO],
    summary="Satınalma talebi detayı (kalemlerle)",
)
async def talep_detay(
    talep_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("satinalma:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    talep = await repository.talep_getir_kalemli(db, talep_id)
    if talep is None:
        raise KaynakBulunamadi("Satınalma talebi bulunamadı")
    return basari(_talep_detay_cevap(talep), mesaj="Satınalma talebi detayı")


@router.patch(
    "/satinalma-talepleri/{talep_id}",
    response_model=Zarf[SatinalmaTalebiDetayDTO],
    summary="Satınalma talebini düzenle (yalnız taslak)",
)
async def talep_guncelle(
    talep_id: int,
    govde: SatinalmaTalebiGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("satinalma:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    talep = await repository.talep_getir_kalemli(db, talep_id)
    if talep is None:
        raise KaynakBulunamadi("Satınalma talebi bulunamadı")
    if talep.durum != "taslak":
        raise CakismaHatasi("Yalnız taslak talep düzenlenebilir")
    if govde.baslik is not None:
        talep.baslik = govde.baslik
    if govde.aciklama is not None:
        talep.aciklama = govde.aciklama
    if govde.para_birimi is not None:
        talep.para_birimi = govde.para_birimi
    if govde.kalemler is not None:
        await _kalemleri_dogrula(db, govde.kalemler)
        talep.kalemler = [
            SatinalmaTalebiKalemi(
                malzeme_id=k.malzeme_id, miktar=k.miktar, birim=k.birim,
                tahmini_birim_fiyat=k.tahmini_birim_fiyat, aciklama=k.aciklama,
            )
            for k in govde.kalemler
        ]
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="satinalma_talebi", kaynak_id=str(talep.id), kullanici=kullanici
    )
    talep_tam = await repository.talep_getir_kalemli(db, talep.id)
    assert talep_tam is not None
    return basari(_talep_detay_cevap(talep_tam), mesaj="Satınalma talebi güncellendi")


async def _gecis(
    db: AsyncSession, tenant: Tenant, kullanici: Kullanici, talep_id: int, hedef: str,
    *, onaylayan: Kullanici | None = None, red_nedeni: str | None = None,
) -> dict[str, Any]:
    talep = await repository.talep_getir_kilitli(db, talep_id)
    if talep is None:
        raise KaynakBulunamadi("Satınalma talebi bulunamadı")
    await service.talep_durum_gecisi(db, talep, hedef=hedef, onaylayan=onaylayan, red_nedeni=red_nedeni)
    await denetim_yaz(
        db, eylem="durum_guncelle", kaynak="satinalma_talebi", kaynak_id=str(talep.id),
        kullanici=kullanici, detay={"durum": talep.durum},
    )
    await yayinla(tenant.slug, {"tur": "satinalma.durum", "id": talep.id, "durum": talep.durum})
    return basari(_talep_cevap(talep), mesaj="Durum güncellendi")


@router.post("/satinalma-talepleri/{talep_id}/gonder", response_model=Zarf[SatinalmaTalebiCevapDTO], summary="Talebi onaya gönder")
async def talep_gonder(
    talep_id: int,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("satinalma:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    return await _gecis(db, tenant, kullanici, talep_id, "onay_bekliyor")


@router.post("/satinalma-talepleri/{talep_id}/onayla", response_model=Zarf[SatinalmaTalebiCevapDTO], summary="Talebi onayla")
async def talep_onayla(
    talep_id: int,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("satinalma:onay"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    return await _gecis(db, tenant, kullanici, talep_id, "onaylandi", onaylayan=kullanici)


@router.post("/satinalma-talepleri/{talep_id}/reddet", response_model=Zarf[SatinalmaTalebiCevapDTO], summary="Talebi reddet")
async def talep_reddet(
    talep_id: int,
    govde: RedDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("satinalma:onay"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    return await _gecis(db, tenant, kullanici, talep_id, "reddedildi", onaylayan=kullanici, red_nedeni=govde.red_nedeni)


@router.post("/satinalma-talepleri/{talep_id}/iptal", response_model=Zarf[SatinalmaTalebiCevapDTO], summary="Talebi iptal et")
async def talep_iptal(
    talep_id: int,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("satinalma:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    return await _gecis(db, tenant, kullanici, talep_id, "iptal")
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_s9_satinalma.py -v -k "not onay_ayri_izin"`
Expected: PASS (6 passed; `onay_ayri_izin` Task 6'da koşulacak)

- [ ] **Step 8: Lint + type + commit**

```bash
cd backend && ruff check app/modules/stok tests/test_s9_satinalma.py && mypy app/modules/stok
git add backend/app/modules/stok/service.py backend/app/modules/stok/schemas.py backend/app/modules/stok/repository.py backend/app/modules/stok/router.py backend/tests/test_s9_satinalma.py
git commit -m "feat(stok): çok-kalemli satınalma talebi + onay akışı (satinalma:onay ayrı) (S9)"
```

---

## Task 6: RBAC varsayılan rolleri (depo + satinalma-onaylayan) + görev-ayrımı testi

**Files:**
- Modify: `backend/app/kimlik/izinler.py` (`VARSAYILAN_ROLLER`'a 2 rol)
- Test: `backend/tests/test_s9_seed.py`

**Interfaces:**
- Consumes: `IZIN_KATALOGU` (mevcut; `stok:*`, `satinalma:*` zaten var).
- Produces: `VARSAYILAN_ROLLER["depo"]`, `VARSAYILAN_ROLLER["satinalma-onaylayan"]` (provizyonlama tohumu otomatik yazar).

> İzinler (`stok:oku/yaz`, `satinalma:oku/yaz/onay`) `IZIN_KATALOGU`'nda zaten var (S2). Bu task yalnız görev-ayrımını canlı gösterecek **rolleri** ekler.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_s9_seed.py`:
```python
"""S9 seed: depo + satinalma-onaylayan rollerinin izin kümeleri (görev ayrımı)."""

from __future__ import annotations

from app.kimlik.izinler import VARSAYILAN_ROLLER


def test_depo_rolu_onaylayamaz() -> None:
    depo = VARSAYILAN_ROLLER["depo"]
    assert {"stok:oku", "stok:yaz", "satinalma:oku", "satinalma:yaz"} <= depo
    assert "satinalma:onay" not in depo


def test_onaylayan_rolu_yalniz_onay() -> None:
    rol = VARSAYILAN_ROLLER["satinalma-onaylayan"]
    assert rol == frozenset({"satinalma:oku", "satinalma:onay"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_s9_seed.py -v`
Expected: FAIL — `KeyError: 'depo'`

- [ ] **Step 3: Add the roles**

`backend/app/kimlik/izinler.py` — `VARSAYILAN_ROLLER` sözlüğüne (`saha-cihaz`'dan sonra) ekle:
```python
    # Depo sorumlusu: stok + talep oluşturur, ONAYLAYAMAZ (görev ayrımı).
    "depo": frozenset({"stok:oku", "stok:yaz", "satinalma:oku", "satinalma:yaz"}),
    # Satınalma onaylayan: yalnız talep görüntüleme + onay.
    "satinalma-onaylayan": frozenset({"satinalma:oku", "satinalma:onay"}),
```

- [ ] **Step 4: Run the seed test + the deferred satınalma test**

Run: `cd backend && python -m pytest tests/test_s9_seed.py tests/test_s9_satinalma.py::test_onay_ayri_izin_403 -v`
Expected: PASS (3 passed). (`test_db` fixture yeni rolleri her iki tenant'a tohumlar → `depo` kullanıcısı `onayla`'da 403 alır.)

- [ ] **Step 5: Lint + commit**

```bash
cd backend && ruff check app/kimlik/izinler.py tests/test_s9_seed.py && mypy app/kimlik/izinler.py
git add backend/app/kimlik/izinler.py backend/tests/test_s9_seed.py
git commit -m "feat(rbac): depo + satinalma-onaylayan varsayılan rolleri (görev ayrımı) (S9)"
```

---

## Task 7: OpenAPI regen + ADR-0011 + veri sözlüğü/README/yol-haritası

**Files:**
- Modify: `backend/openapi.json` (regen)
- Create: `docs/adr/0011-stok-satinalma.md`
- Modify: `docs/veri-sozlugu.md` (yeni tablolar) — varsa; yoksa atla
- Modify: `docs/yol-haritasi.md` (S9 ✅)
- Modify: `README.md` (durum tablosu S9)

**Interfaces:** Yok (dokümantasyon + sözleşme yenileme).

- [ ] **Step 1: Run the full backend suite (yeşil taban)**

Run: `cd backend && python -m pytest -q`
Expected: PASS — tüm S9 testleri + mevcut 127 test (toplam ~150) geçer.

- [ ] **Step 2: Regenerate openapi.json**

Run (projedeki openapi üretim komutu; S6/S8 ile aynı):
```bash
cd backend && python -m app.tools.openapi_uret > openapi.json
```
> Komut adı farklıysa (`scripts/openapi.py` vb.) repodaki mevcut üretim betiğini kullan; amaç `openapi.json`'a stok/satınalma uçlarını + DTO şemalarını işlemek. Üretildiğini doğrula:
```bash
grep -c "satinalma-talepleri\|malzemeler\|stok-hareketleri" openapi.json
```
Expected: > 0.

- [ ] **Step 3: Write ADR-0011**

`docs/adr/0011-stok-satinalma.md` (`docs/adr/0000-sablon.md` biçiminde) — şu kararları belgele:
- **Bağlam:** S9 stok + satınalma; kabul: bakiye doğru, kritik tetikler, `satinalma:onay` ayrı.
- **Karar:** (1) **Tutulan bakiye** (`Malzeme.mevcut_miktar`) + `FOR UPDATE` satır kilidi — türetilmiş toplam yerine; hızlı okuma + kritik kontrol. (2) **Kenar-tetikli `stok.kritik`** (eşik üstünden altına ilk geçiş) — gürültüsüz, transactional outbox (S18 webhook). (3) **Çok-kalemli talep** + saf durum makinesi (`taslak→onay_bekliyor→onaylandi/reddedildi`+iptal); `onaylandi/reddedildi` `satinalma:onay` ister → **görev ayrımı**. (4) **Opsiyonel `Idempotency-Key`** stok hareketinde (nullable unique) — çift-gönderim koruması; ileride genel middleware'e çıkarılabilir (seam). (5) Talep ↔ stok **ayrık** (mal kabul/sipariş ileride).
- **Sonuçlar:** OEE hattı değişmedi; webhook `stok.kritik` hazır; düzeltme türü sayım için; para türetilmiş (`tahmini_toplam`).

- [ ] **Step 4: Update veri sözlüğü + yol-haritası + README**

- `docs/veri-sozlugu.md` (varsa): `malzemeler`, `stok_hareketleri`, `satinalma_talepleri`, `satinalma_talebi_kalemleri` tabloları + kolon açıklamaları ekle.
- `docs/yol-haritasi.md`: durum tablosunda `| | S9 | Stok & Satınalma | ⬜ |` → `✅ ADR-0011`; "Faz ve sprint planı" S9 bölümüne "(karşılandı)" notu.
- `README.md`: durum tablosunda S9 ✅.

- [ ] **Step 5: Commit**

```bash
git add backend/openapi.json docs/adr/0011-stok-satinalma.md docs/yol-haritasi.md README.md
git add docs/veri-sozlugu.md 2>/dev/null || true
git commit -m "docs(s9): ADR-0011 + openapi regen + veri sözlüğü/yol-haritası/README (S9 backend kapanış)"
```

---

## Task 8: Frontend veri/mantık katmanı (codegen + hooks + durum aynası + rozetler + olayIsle)

**Files:**
- Modify: `frontend/src/api/types.gen.ts` (codegen — elle düzenlenmez, üretilir)
- Create: `frontend/src/modules/stok/talepDurum.ts`
- Create: `frontend/src/modules/stok/talepDurum.test.ts`
- Create: `frontend/src/modules/stok/rozetler.tsx`
- Create: `frontend/src/modules/stok/hooks.ts`
- Modify: `frontend/src/modules/ortak/olayIsle.ts`
- Modify: `frontend/src/modules/ortak/olayIsle.test.ts`

**Interfaces:**
- Consumes: `useSayfaliSorgu`, `istek`, `PREFIX`, `ApiHata`, `components` (codegen tipleri), `SayfaParam`.
- Produces:
  - `talepDurum.GECISLER`, `talepDurum.gecerliHedefler(mevcut)`, `talepDurum.TERMINAL` — backend `talep_durum.py` aynası.
  - `rozetler.TalepDurumEtiketi`
  - Hooks: `useMalzemeler`, `useMalzeme`, `useKritikStok`, `useMalzemeOlustur`, `useMalzemeGuncelle`, `useStokHareketleri`, `useStokHareketEkle`, `useTalepler`, `useTalep`, `useTalepOlustur`, `useTalepDurumAksiyon`
  - Tipler: `Malzeme`, `StokHareketi`, `SatinalmaTalebi`, `SatinalmaTalebiDetay`

- [ ] **Step 1: Regenerate API types**

Backend `openapi.json` Task 7'de güncellendi. Frontend tiplerini üret:
```bash
cd frontend && npm run codegen
```
`src/api/types.gen.ts` artık `MalzemeCevapDTO`, `StokHareketiCevapDTO`, `SatinalmaTalebiCevapDTO`, `SatinalmaTalebiDetayDTO`, `SatinalmaKalemCevapDTO`, `*OlusturDTO` şemalarını içerir. Doğrula:
```bash
grep -c "MalzemeCevapDTO\|SatinalmaTalebiDetayDTO" src/api/types.gen.ts
```
Expected: > 0.

- [ ] **Step 2: Write the durum mirror + its test (TDD)**

`frontend/src/modules/stok/talepDurum.test.ts`:
```ts
import { describe, expect, it } from 'vitest';

import { gecerliHedefler, TERMINAL } from './talepDurum';

describe('satınalma talebi durum aynası', () => {
  it('taslak → onay_bekliyor / iptal', () => {
    expect(gecerliHedefler('taslak')).toEqual(['onay_bekliyor', 'iptal']);
  });
  it('onay_bekliyor → onaylandi / reddedildi / iptal', () => {
    expect(gecerliHedefler('onay_bekliyor')).toEqual(['onaylandi', 'reddedildi', 'iptal']);
  });
  it('terminal durumlardan çıkış yok', () => {
    for (const d of TERMINAL) expect(gecerliHedefler(d)).toEqual([]);
  });
});
```

`frontend/src/modules/stok/talepDurum.ts`:
```ts
/**
 * Satınalma talebi durum makinesi **aynası** — backend ``talep_durum.py`` ile birebir.
 * UI yalnız geçerli aksiyonları gösterir; nihai doğrulama backend'dedir.
 */

export const GECISLER: Record<string, string[]> = {
  taslak: ['onay_bekliyor', 'iptal'],
  onay_bekliyor: ['onaylandi', 'reddedildi', 'iptal'],
  onaylandi: [],
  reddedildi: [],
  iptal: [],
};

export const TERMINAL = ['onaylandi', 'reddedildi', 'iptal'] as const;

export function gecerliHedefler(mevcut: string): string[] {
  return GECISLER[mevcut] ?? [];
}
```

Run: `cd frontend && npm run test -- talepDurum`
Expected: PASS (3 passed).

- [ ] **Step 3: Write the durum badge**

`frontend/src/modules/stok/rozetler.tsx`:
```tsx
/** Satınalma talebi durum rozeti (renk + i18n etiket). AntD Tag tabanlı. */

import { useTranslation } from 'react-i18next';
import { Tag } from 'antd';

const DURUM_RENK: Record<string, string> = {
  taslak: 'default',
  onay_bekliyor: 'processing',
  onaylandi: 'success',
  reddedildi: 'error',
  iptal: 'default',
};

export function TalepDurumEtiketi({ durum }: { durum: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={DURUM_RENK[durum] ?? 'default'} bordered={false}>
      {t(`satinalma.durum_${durum}`)}
    </Tag>
  );
}
```

- [ ] **Step 4: Write the hooks**

`frontend/src/modules/stok/hooks.ts`:
```ts
/**
 * Stok & Satınalma veri hook'ları (TanStack Query). Anahtarlar olayIsle.ts ile birebir
 * aynıdır (canlı invalidate). Mutasyonlar ilgili listeleri/detayları geçersizleştirir.
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type Malzeme = components['schemas']['MalzemeCevapDTO'];
export type MalzemeOlustur = components['schemas']['MalzemeOlusturDTO'];
export type MalzemeGuncelle = components['schemas']['MalzemeGuncelleDTO'];
export type StokHareketi = components['schemas']['StokHareketiCevapDTO'];
export type StokHareketiOlustur = components['schemas']['StokHareketiOlusturDTO'];
export type SatinalmaTalebi = components['schemas']['SatinalmaTalebiCevapDTO'];
export type SatinalmaTalebiDetay = components['schemas']['SatinalmaTalebiDetayDTO'];
export type SatinalmaTalebiOlustur = components['schemas']['SatinalmaTalebiOlusturDTO'];

export const STOK_ANAHTAR = {
  malzemeler: ['malzemeler'] as const,
  malzeme: (id: number) => ['malzeme', id] as const,
  kritik: ['stok-kritik'] as const,
  hareketler: ['stok-hareketleri'] as const,
  talepler: ['satinalma-talepleri'] as const,
  talep: (id: number) => ['satinalma-talebi', id] as const,
};

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

// --- Malzeme ---
export function useMalzemeler(param: SayfaParam) {
  return useSayfaliSorgu<Malzeme>(STOK_ANAHTAR.malzemeler, '/malzemeler', param);
}

export function useMalzeme(id: number) {
  return useQuery({
    queryKey: STOK_ANAHTAR.malzeme(id),
    queryFn: () => istek<Malzeme>('GET', `${PREFIX}/malzemeler/${id}`),
    enabled: id > 0,
  });
}

export function useKritikStok() {
  return useQuery({
    queryKey: STOK_ANAHTAR.kritik,
    queryFn: () => istek<Malzeme[]>('GET', `${PREFIX}/stok/kritik`),
  });
}

export function useMalzemeOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: MalzemeOlustur) => istek<Malzeme>('POST', `${PREFIX}/malzemeler`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.malzemeler });
      message.success(t('stok.malzeme_olusturuldu'));
    },
    onError: hataGoster,
  });
}

export function useMalzemeGuncelle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, govde }: { id: number; govde: MalzemeGuncelle }) =>
      istek<Malzeme>('PATCH', `${PREFIX}/malzemeler/${id}`, govde),
    onSuccess: (_v, { id }) => {
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.malzemeler });
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.malzeme(id) });
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.kritik });
      message.success(t('stok.guncellendi'));
    },
    onError: hataGoster,
  });
}

// --- Stok hareketi ---
export function useStokHareketleri(param: SayfaParam, malzemeId?: number) {
  const yol = malzemeId ? `/stok-hareketleri?malzeme_id=${malzemeId}` : '/stok-hareketleri';
  // Not: useSayfaliSorgu sorgu dizesini ekler; malzeme filtresi için ayrı anahtar kullan.
  return useSayfaliSorgu<StokHareketi>(
    malzemeId ? [...STOK_ANAHTAR.hareketler, malzemeId] : STOK_ANAHTAR.hareketler,
    yol,
    param,
  );
}

export function useStokHareketEkle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: StokHareketiOlustur) =>
      istek<StokHareketi>('POST', `${PREFIX}/stok-hareketleri`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.hareketler });
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.malzemeler });
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.kritik });
      message.success(t('stok.hareket_eklendi'));
    },
    onError: hataGoster,
  });
}

// --- Satınalma talebi ---
export function useTalepler(param: SayfaParam) {
  return useSayfaliSorgu<SatinalmaTalebi>(STOK_ANAHTAR.talepler, '/satinalma-talepleri', param);
}

export function useTalep(id: number) {
  return useQuery({
    queryKey: STOK_ANAHTAR.talep(id),
    queryFn: () => istek<SatinalmaTalebiDetay>('GET', `${PREFIX}/satinalma-talepleri/${id}`),
    enabled: id > 0,
  });
}

export function useTalepOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: SatinalmaTalebiOlustur) =>
      istek<SatinalmaTalebiDetay>('POST', `${PREFIX}/satinalma-talepleri`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.talepler });
      message.success(t('satinalma.olusturuldu'));
    },
    onError: hataGoster,
  });
}

/** Durum aksiyonu: gonder | onayla | reddet | iptal. */
export function useTalepDurumAksiyon() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, aksiyon, red_nedeni }: { id: number; aksiyon: string; red_nedeni?: string }) =>
      istek<SatinalmaTalebi>(
        'POST',
        `${PREFIX}/satinalma-talepleri/${id}/${aksiyon}`,
        aksiyon === 'reddet' ? { red_nedeni: red_nedeni ?? '' } : undefined,
      ),
    onSuccess: (_v, { id }) => {
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.talepler });
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.talep(id) });
      message.success(t('satinalma.durum_guncellendi'));
    },
    onError: hataGoster,
  });
}
```

- [ ] **Step 5: Extend olayIsle + its test**

`frontend/src/modules/ortak/olayIsle.ts` — `switch` içine, `default`'tan önce ekle:
```ts
    case 'stok.hareket':
    case 'stok.kritik':
      void qc.invalidateQueries({ queryKey: ['malzemeler'] });
      void qc.invalidateQueries({ queryKey: ['stok-kritik'] });
      void qc.invalidateQueries({ queryKey: ['stok-hareketleri'] });
      break;
    case 'satinalma.durum': {
      void qc.invalidateQueries({ queryKey: ['satinalma-talepleri'] });
      const talepId = typeof olay.id === 'number' ? olay.id : undefined;
      if (talepId !== undefined)
        void qc.invalidateQueries({ queryKey: ['satinalma-talebi', talepId] });
      break;
    }
```

`frontend/src/modules/ortak/olayIsle.test.ts` — mevcut testlere ekle (dosyadaki mevcut deseni izle: sahte `QueryClient` + `invalidateQueries` spy):
```ts
  it('stok.kritik → malzeme + kritik sorgularını invalidate eder', () => {
    const qc = { invalidateQueries: vi.fn() } as unknown as QueryClient;
    olayIsle(qc, { tur: 'stok.kritik', malzeme_id: 3 });
    const cagrilar = (qc.invalidateQueries as unknown as ReturnType<typeof vi.fn>).mock.calls.map(
      (c) => (c[0] as { queryKey: unknown[] }).queryKey[0],
    );
    expect(cagrilar).toContain('malzemeler');
    expect(cagrilar).toContain('stok-kritik');
  });

  it('satinalma.durum → talep listesi + detayını invalidate eder', () => {
    const qc = { invalidateQueries: vi.fn() } as unknown as QueryClient;
    olayIsle(qc, { tur: 'satinalma.durum', id: 7 });
    const cagrilar = (qc.invalidateQueries as unknown as ReturnType<typeof vi.fn>).mock.calls.map(
      (c) => (c[0] as { queryKey: unknown[] }).queryKey[0],
    );
    expect(cagrilar).toContain('satinalma-talepleri');
    expect(cagrilar).toContain('satinalma-talebi');
  });
```
> `import { QueryClient } from '@tanstack/react-query'` ve `vi` zaten dosyada importlu değilse ekle (mevcut testlerin import bloğunu izle).

- [ ] **Step 6: Run frontend tests + lint + type**

```bash
cd frontend && npm run test -- talepDurum olayIsle && npm run lint && npx tsc --noEmit
```
Expected: PASS (tüm yeni + mevcut testler), eslint temiz, tsc strict temiz.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/types.gen.ts frontend/src/modules/stok/talepDurum.ts frontend/src/modules/stok/talepDurum.test.ts frontend/src/modules/stok/rozetler.tsx frontend/src/modules/stok/hooks.ts frontend/src/modules/ortak/olayIsle.ts frontend/src/modules/ortak/olayIsle.test.ts
git commit -m "feat(frontend): stok/satınalma codegen + hooks + durum aynası + canlı invalidate (S9)"
```

---

## Task 9: Stok ekranları (malzeme listesi/detay/form + hareket formu + kritik) + rota/menü/i18n

**Files:**
- Create: `frontend/src/modules/stok/MalzemeListesi.tsx`
- Create: `frontend/src/modules/stok/MalzemeFormu.tsx`
- Create: `frontend/src/modules/stok/MalzemeDetay.tsx`
- Create: `frontend/src/modules/stok/StokHareketFormu.tsx`
- Create: `frontend/src/modules/stok/KritikStok.tsx`
- Create: `frontend/src/modules/stok/MalzemeListesi.test.tsx`
- Modify: `frontend/src/layouts/menu.ts`, `frontend/src/App.tsx`, `frontend/src/i18n/tr.json`, `frontend/src/i18n/en.json`

**Interfaces:**
- Consumes: hooks (Task 8), `SunucuTablo`, `SayfaBaslik`, `useSayfaParam`, `DurumRozet`/`Tag`, `IzinKapisi`.
- Produces: `MalzemeListesi`, `MalzemeDetay`, `MalzemeFormu`, `StokHareketFormu`, `KritikStok` bileşenleri; rotalar `/malzemeler`, `/malzemeler/:id`, `/stok/kritik`.

- [ ] **Step 1: Add i18n keys**

`frontend/src/i18n/tr.json` — kök nesneye `stok` ve `menu`/güncelleme ekle (mevcut `saha`/`isemri` bloklarının yanına):
```json
"menu": {
  "bolum_stok": "Stok & Satınalma",
  "malzemeler": "Malzemeler",
  "kritik_stok": "Kritik stok",
  "satinalma": "Satınalma talepleri"
},
"stok": {
  "alt": "Malzeme kartları ve stok hareketleri",
  "kod": "Kod", "ad": "Ad", "birim": "Birim", "kategori": "Kategori",
  "mevcut": "Mevcut", "min": "Min", "max": "Maks", "kritik_esik": "Kritik eşik",
  "durum": "Durum", "aktif": "Aktif", "pasif": "Pasif",
  "ara": "Kod veya ad ara", "bos": "Malzeme yok",
  "yeni": "Yeni malzeme", "duzenle": "Düzenle",
  "malzeme_olusturuldu": "Malzeme oluşturuldu", "guncellendi": "Malzeme güncellendi",
  "hareket_ekle": "Stok hareketi", "hareket_eklendi": "Stok hareketi eklendi",
  "tur": "Hareket türü", "giris": "Giriş", "cikis": "Çıkış", "duzeltme": "Düzeltme",
  "miktar": "Miktar", "aciklama": "Açıklama", "kaynak": "Kaynak",
  "son_hareketler": "Son hareketler", "bakiye_sonrasi": "Sonraki bakiye",
  "kritik_baslik": "Kritik stoktaki malzemeler", "kritik_bos": "Kritik stok yok",
  "kritik_rozet": "KRİTİK"
}
```
`frontend/src/i18n/en.json` — aynı anahtarların İngilizcesi (`"giris": "In"`, `"cikis": "Out"`, `"duzeltme": "Adjust"`, `"kritik_rozet": "CRITICAL"`, vb.).

- [ ] **Step 2: Write MalzemeListesi (+ test)**

`frontend/src/modules/stok/MalzemeListesi.tsx`:
```tsx
/** Malzeme listesi — sunucu-taraflı tablo + kritik rozet + "yeni malzeme" + hareket aksiyonu. */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Space, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';

import { type Malzeme, useMalzemeler } from './hooks';
import { MalzemeFormu } from './MalzemeFormu';
import { StokHareketFormu } from './StokHareketFormu';

export function MalzemeListesi() {
  const { t } = useTranslation();
  const nav = useNavigate();
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useMalzemeler(param);
  const [formAcik, setFormAcik] = useState(false);
  const [hareketMalzeme, setHareketMalzeme] = useState<Malzeme | null>(null);

  const kolonlar: ColumnsType<Malzeme> = [
    {
      title: t('stok.kod'), dataIndex: 'kod', key: 'kod', sorter: true,
      render: (v: string, m) => (
        <Space>
          <a onClick={() => nav(`/malzemeler/${m.id}`)} className="sayisal">{v}</a>
          {m.kritik && <Tag color="red" bordered={false}>{t('stok.kritik_rozet')}</Tag>}
        </Space>
      ),
    },
    { title: t('stok.ad'), dataIndex: 'ad', key: 'ad', sorter: true },
    {
      title: t('stok.mevcut'), dataIndex: 'mevcut_miktar', key: 'mevcut_miktar', sorter: true,
      align: 'right', render: (v: number, m) => <span className="sayisal">{v} {m.birim}</span>,
    },
    { title: t('stok.kritik_esik'), dataIndex: 'kritik_stok', key: 'kritik_stok', align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span> },
    {
      title: t('stok.durum'), dataIndex: 'aktif', key: 'aktif',
      render: (aktif: boolean) => (
        <Tag color={aktif ? 'green' : 'default'}>{aktif ? t('stok.aktif') : t('stok.pasif')}</Tag>
      ),
    },
    {
      title: '', key: 'aksiyon', align: 'right',
      render: (_: unknown, m) => (
        <Button size="small" onClick={() => setHareketMalzeme(m)}>{t('stok.hareket_ekle')}</Button>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik
        baslik={t('menu.malzemeler')}
        alt={t('stok.alt')}
        aksiyon={<Button type="primary" onClick={() => setFormAcik(true)}>{t('stok.yeni')}</Button>}
      />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<Malzeme>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('stok.ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('stok.bos')}
        />
      </Card>
      <MalzemeFormu acik={formAcik} kapat={() => setFormAcik(false)} />
      <StokHareketFormu malzeme={hareketMalzeme} kapat={() => setHareketMalzeme(null)} />
    </div>
  );
}
```
> `SayfaBaslik`'in `aksiyon` prop'u yoksa, mevcut `SayfaBaslik.tsx`'i kontrol et; yoksa başlığın yanına `Button`'ı `MalzemeListesi` içinde ayrı bir satırda render et (prop ekleme zorunlu değil).

`frontend/src/modules/stok/MalzemeListesi.test.tsx` (saha `CihazListesi.test.tsx` desenini izle — `QueryClientProvider` + i18n + fetch-mock; liste render olur, kod görünür):
```tsx
import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

import { TestSarmalayici } from '@/test/setup'; // mevcut test yardımcısı; yoksa CihazListesi.test.tsx'teki sarmalayıcıyı kopyala
import { MalzemeListesi } from './MalzemeListesi';

describe('MalzemeListesi', () => {
  it('başlığı render eder', async () => {
    render(<MalzemeListesi />, { wrapper: TestSarmalayici });
    await waitFor(() => expect(screen.getByText(/Malzemeler/i)).toBeInTheDocument());
  });
});
```
> Eğer projede ortak `TestSarmalayici` yoksa, `CihazListesi.test.tsx`'teki kurulum bloğunu (QueryClient + I18nextProvider + AntD `App`) bu teste birebir uyarlayarak kullan.

- [ ] **Step 3: Write MalzemeFormu**

`frontend/src/modules/stok/MalzemeFormu.tsx` — AntD `Modal` + `Form`; `MakineFormu.tsx` desenini izle. Alanlar: `kod`, `ad`, `birim` (Select: `BIRIMLER` listesinden — sabiti `talepDurum.ts` yanına `birimler.ts` olarak koy ya da elle dizi gir), `kategori`, `min_stok`, `max_stok`, `kritik_stok` (`InputNumber`). Submit → `useMalzemeOlustur`. Düzenleme modunda `malzeme` prop'u verilirse `useMalzemeGuncelle`.
```tsx
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Form, InputNumber, Input, Modal, Select } from 'antd';

import { type Malzeme, useMalzemeGuncelle, useMalzemeOlustur } from './hooks';

const BIRIMLER = ['adet', 'kg', 'gram', 'litre', 'mililitre', 'metre', 'santimetre', 'paket', 'kutu', 'koli', 'ton', 'rulo'];

export function MalzemeFormu({ acik, kapat, malzeme }: { acik: boolean; kapat: () => void; malzeme?: Malzeme }) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useMalzemeOlustur();
  const guncelle = useMalzemeGuncelle();
  const duzenleme = malzeme != null;

  useEffect(() => {
    if (acik) form.setFieldsValue(malzeme ?? { birim: 'adet', min_stok: 0, kritik_stok: 0 });
  }, [acik, malzeme, form]);

  const gonder = async () => {
    const v = await form.validateFields();
    if (duzenleme) await guncelle.mutateAsync({ id: malzeme.id, govde: v });
    else await olustur.mutateAsync(v);
    kapat();
  };

  return (
    <Modal open={acik} onCancel={kapat} onOk={gonder} title={duzenleme ? t('stok.duzenle') : t('stok.yeni')}
           confirmLoading={olustur.isPending || guncelle.isPending} destroyOnClose>
      <Form form={form} layout="vertical">
        {!duzenleme && (
          <Form.Item name="kod" label={t('stok.kod')} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
        )}
        <Form.Item name="ad" label={t('stok.ad')} rules={[{ required: true }]}><Input /></Form.Item>
        <Form.Item name="birim" label={t('stok.birim')} rules={[{ required: true }]}>
          <Select options={BIRIMLER.map((b) => ({ value: b, label: b }))} />
        </Form.Item>
        <Form.Item name="kategori" label={t('stok.kategori')}><Input /></Form.Item>
        <Form.Item name="min_stok" label={t('stok.min')}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
        <Form.Item name="max_stok" label={t('stok.max')}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
        <Form.Item name="kritik_stok" label={t('stok.kritik_esik')}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
      </Form>
    </Modal>
  );
}
```

- [ ] **Step 4: Write StokHareketFormu**

`frontend/src/modules/stok/StokHareketFormu.tsx` — `Modal` + `Form`; `tur` Select (giris/cikis/duzeltme), `miktar` InputNumber (>0), `aciklama`. Submit → `useStokHareketEkle` (govde'ye `malzeme_id` ekle). Açık koşulu `malzeme != null`.
```tsx
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Form, Input, InputNumber, Modal, Select } from 'antd';

import { type Malzeme, useStokHareketEkle } from './hooks';

export function StokHareketFormu({ malzeme, kapat }: { malzeme: Malzeme | null; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const ekle = useStokHareketEkle();

  useEffect(() => {
    if (malzeme) form.setFieldsValue({ tur: 'giris', miktar: 1, aciklama: '' });
  }, [malzeme, form]);

  const gonder = async () => {
    const v = await form.validateFields();
    await ekle.mutateAsync({ malzeme_id: malzeme!.id, ...v });
    kapat();
  };

  return (
    <Modal open={malzeme != null} onCancel={kapat} onOk={gonder}
           title={`${t('stok.hareket_ekle')} — ${malzeme?.kod ?? ''}`}
           confirmLoading={ekle.isPending} destroyOnClose>
      <Form form={form} layout="vertical">
        <Form.Item name="tur" label={t('stok.tur')} rules={[{ required: true }]}>
          <Select options={[
            { value: 'giris', label: t('stok.giris') },
            { value: 'cikis', label: t('stok.cikis') },
            { value: 'duzeltme', label: t('stok.duzeltme') },
          ]} />
        </Form.Item>
        <Form.Item name="miktar" label={t('stok.miktar')} rules={[{ required: true }]}>
          <InputNumber min={0.001} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="aciklama" label={t('stok.aciklama')}><Input.TextArea rows={2} /></Form.Item>
      </Form>
    </Modal>
  );
}
```

- [ ] **Step 5: Write MalzemeDetay + KritikStok**

`frontend/src/modules/stok/MalzemeDetay.tsx` — `useParams` id; `useMalzeme(id)` + `useStokHareketleri(param, id)`; `Descriptions` (bakiye/eşikler) + `SunucuTablo` son hareketler + "stok hareketi ekle" butonu (`StokHareketFormu`) + "düzenle" (`MalzemeFormu` malzeme prop'lu). `MakineDetay.tsx` yapısını izle.

`frontend/src/modules/stok/KritikStok.tsx` — `useKritikStok()` → AntD `Table`/`List`; başlık `t('stok.kritik_baslik')`, boşsa `t('stok.kritik_bos')`. Kod + mevcut + kritik eşik sütunları, kırmızı rozet. (Sayfasız; backend `/stok/kritik` tüm kritikleri döner.)
```tsx
import { useTranslation } from 'react-i18next';
import { Card, Table, Tag } from 'antd';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { type Malzeme, useKritikStok } from './hooks';

export function KritikStok() {
  const { t } = useTranslation();
  const { data, isPending } = useKritikStok();
  return (
    <div style={{ maxWidth: 1100 }}>
      <SayfaBaslik baslik={t('stok.kritik_baslik')} />
      <Card styles={{ body: { padding: 18 } }}>
        <Table<Malzeme>
          rowKey="id"
          loading={isPending}
          dataSource={data ?? []}
          locale={{ emptyText: t('stok.kritik_bos') }}
          pagination={false}
          columns={[
            { title: t('stok.kod'), dataIndex: 'kod', render: (v: string) => (
              <span className="sayisal">{v} <Tag color="red" bordered={false}>{t('stok.kritik_rozet')}</Tag></span>
            ) },
            { title: t('stok.ad'), dataIndex: 'ad' },
            { title: t('stok.mevcut'), dataIndex: 'mevcut_miktar', align: 'right',
              render: (v: number, m) => <span className="sayisal">{v} {m.birim}</span> },
            { title: t('stok.kritik_esik'), dataIndex: 'kritik_stok', align: 'right',
              render: (v: number) => <span className="sayisal">{v}</span> },
          ]}
        />
      </Card>
    </div>
  );
}
```

- [ ] **Step 6: Wire menu + routes**

`frontend/src/layouts/menu.ts` — `MENU` dizisine ekle (kullanicilar'dan önce):
```ts
  { anahtar: 'malzemeler', etiketAnahtari: 'menu.malzemeler', bolum: 'menu.bolum_stok', yol: '/malzemeler', izin: 'stok:oku' },
  { anahtar: 'kritik-stok', etiketAnahtari: 'menu.kritik_stok', bolum: 'menu.bolum_stok', yol: '/stok/kritik', izin: 'stok:oku' },
  { anahtar: 'satinalma', etiketAnahtari: 'menu.satinalma', bolum: 'menu.bolum_stok', yol: '/satinalma-talepleri', izin: 'satinalma:oku' },
```
(satinalma rotası Task 10'da bağlanır; menü öğesi şimdiden eklenebilir.)

`frontend/src/App.tsx` — importlar + rotalar (saha rotasından sonra):
```tsx
import { KritikStok } from '@/modules/stok/KritikStok';
import { MalzemeDetay } from '@/modules/stok/MalzemeDetay';
import { MalzemeListesi } from '@/modules/stok/MalzemeListesi';
```
```tsx
          <Route path="malzemeler" element={<IzinKapisi izin="stok:oku"><MalzemeListesi /></IzinKapisi>} />
          <Route path="malzemeler/:id" element={<IzinKapisi izin="stok:oku"><MalzemeDetay /></IzinKapisi>} />
          <Route path="stok/kritik" element={<IzinKapisi izin="stok:oku"><KritikStok /></IzinKapisi>} />
```

- [ ] **Step 7: Run tests + lint + type + build**

```bash
cd frontend && npm run test && npm run lint && npx tsc --noEmit && npm run build
```
Expected: PASS / temiz / build başarılı.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/modules/stok/MalzemeListesi.tsx frontend/src/modules/stok/MalzemeFormu.tsx frontend/src/modules/stok/MalzemeDetay.tsx frontend/src/modules/stok/StokHareketFormu.tsx frontend/src/modules/stok/KritikStok.tsx frontend/src/modules/stok/MalzemeListesi.test.tsx frontend/src/layouts/menu.ts frontend/src/App.tsx frontend/src/i18n/tr.json frontend/src/i18n/en.json
git commit -m "feat(frontend): malzeme listesi/detay/form + stok hareket formu + kritik ekranı (S9)"
```

---

## Task 10: Satınalma ekranları (liste + detay çekmecesi + çok-kalemli form + izin-duyarlı aksiyonlar)

**Files:**
- Create: `frontend/src/modules/stok/SatinalmaTalepListesi.tsx`
- Create: `frontend/src/modules/stok/SatinalmaTalepDetay.tsx`
- Create: `frontend/src/modules/stok/SatinalmaTalepFormu.tsx`
- Create: `frontend/src/modules/stok/SatinalmaTalepListesi.test.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/i18n/tr.json`, `frontend/src/i18n/en.json`

**Interfaces:**
- Consumes: `useTalepler`, `useTalep`, `useTalepOlustur`, `useTalepDurumAksiyon` (Task 8); `TalepDurumEtiketi`, `gecerliHedefler` (Task 8); `useMalzemeler` (malzeme seçimi); `useAuthStore` (izin kontrolü); `IzinKapisi`.
- Produces: `SatinalmaTalepListesi`, `SatinalmaTalepDetay`, `SatinalmaTalepFormu`; rota `/satinalma-talepleri`.

- [ ] **Step 1: Add i18n keys**

`frontend/src/i18n/tr.json` — kök nesneye `satinalma` bloğu:
```json
"satinalma": {
  "alt": "Çok-kalemli satınalma talepleri ve onay akışı",
  "kod": "Kod", "baslik": "Başlık", "durum": "Durum", "talep_eden": "Talep eden",
  "para_birimi": "Para birimi", "tahmini_toplam": "Tahmini toplam",
  "durum_taslak": "Taslak", "durum_onay_bekliyor": "Onay bekliyor",
  "durum_onaylandi": "Onaylandı", "durum_reddedildi": "Reddedildi", "durum_iptal": "İptal",
  "ara": "Kod veya başlık ara", "bos": "Talep yok", "yeni": "Yeni talep",
  "olusturuldu": "Talep oluşturuldu", "durum_guncellendi": "Durum güncellendi",
  "kalemler": "Kalemler", "malzeme": "Malzeme", "miktar": "Miktar", "birim": "Birim",
  "birim_fiyat": "Tahmini birim fiyat", "kalem_ekle": "Kalem ekle", "aciklama": "Açıklama",
  "gonder": "Onaya gönder", "onayla": "Onayla", "reddet": "Reddet", "iptal": "İptal et",
  "red_nedeni": "Red nedeni", "red_baslik": "Talebi reddet", "onaylayan": "Onaylayan"
}
```
`frontend/src/i18n/en.json` — aynı anahtarların İngilizcesi.

- [ ] **Step 2: Write SatinalmaTalepFormu (dinamik kalemler)**

`frontend/src/modules/stok/SatinalmaTalepFormu.tsx` — `Modal` + `Form` + `Form.List` (dinamik kalem satırları). Her satır: malzeme `Select` (`useMalzemeler` ile en güncel 100), `miktar` `InputNumber`, `birim` `Select`, `tahmini_birim_fiyat` `InputNumber`. Submit → `useTalepOlustur`.
```tsx
import { useTranslation } from 'react-i18next';
import { Button, Form, Input, InputNumber, Modal, Select, Space } from 'antd';
import { MinusCircleOutlined, PlusOutlined } from '@ant-design/icons';

import { useMalzemeler, useTalepOlustur } from './hooks';

const BIRIMLER = ['adet', 'kg', 'gram', 'litre', 'mililitre', 'metre', 'santimetre', 'paket', 'kutu', 'koli', 'ton', 'rulo'];

export function SatinalmaTalepFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useTalepOlustur();
  const { data: malzemeler } = useMalzemeler({ sayfa: 1, adet: 100 });
  const secenekler = (malzemeler?.veri ?? []).map((m) => ({ value: m.id, label: `${m.kod} — ${m.ad}` }));

  const gonder = async () => {
    const v = await form.validateFields();
    await olustur.mutateAsync({ para_birimi: 'TRY', ...v });
    form.resetFields();
    kapat();
  };

  return (
    <Modal open={acik} onCancel={kapat} onOk={gonder} title={t('satinalma.yeni')} width={720}
           confirmLoading={olustur.isPending} destroyOnClose>
      <Form form={form} layout="vertical" initialValues={{ kalemler: [{ birim: 'adet', miktar: 1 }] }}>
        <Form.Item name="baslik" label={t('satinalma.baslik')} rules={[{ required: true }]}><Input /></Form.Item>
        <Form.List name="kalemler" rules={[{ validator: async (_, k) => { if (!k || k.length < 1) throw new Error(); } }]}>
          {(alanlar, { add, remove }) => (
            <>
              {alanlar.map((alan) => (
                <Space key={alan.key} align="baseline" style={{ display: 'flex', marginBottom: 8 }}>
                  <Form.Item name={[alan.name, 'malzeme_id']} rules={[{ required: true }]}>
                    <Select style={{ width: 240 }} options={secenekler} placeholder={t('satinalma.malzeme')} showSearch optionFilterProp="label" />
                  </Form.Item>
                  <Form.Item name={[alan.name, 'miktar']} rules={[{ required: true }]}>
                    <InputNumber min={0.001} placeholder={t('satinalma.miktar')} />
                  </Form.Item>
                  <Form.Item name={[alan.name, 'birim']} rules={[{ required: true }]}>
                    <Select style={{ width: 110 }} options={BIRIMLER.map((b) => ({ value: b, label: b }))} />
                  </Form.Item>
                  <Form.Item name={[alan.name, 'tahmini_birim_fiyat']}>
                    <InputNumber min={0} placeholder={t('satinalma.birim_fiyat')} />
                  </Form.Item>
                  {alanlar.length > 1 && <MinusCircleOutlined onClick={() => remove(alan.name)} />}
                </Space>
              ))}
              <Button type="dashed" onClick={() => add({ birim: 'adet', miktar: 1 })} icon={<PlusOutlined />} block>
                {t('satinalma.kalem_ekle')}
              </Button>
            </>
          )}
        </Form.List>
      </Form>
    </Modal>
  );
}
```

- [ ] **Step 3: Write SatinalmaTalepDetay (izin-duyarlı aksiyonlar)**

`frontend/src/modules/stok/SatinalmaTalepDetay.tsx` — AntD `Drawer`; `useTalep(id)` ile künye + `TalepDurumEtiketi` + kalem tablosu + `tahmini_toplam`. Aksiyon butonları `gecerliHedefler(durum)` + izin filtresi:
- `onay_bekliyor` hedefi (`gonder`) → `satinalma:yaz`
- `onaylandi`/`reddedildi` → `satinalma:onay` (yoksa **gizli**)
- `iptal` → `satinalma:yaz`
Reddet → `Modal` ile `red_nedeni` sor.
```tsx
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, Descriptions, Drawer, Input, Modal, Space, Table } from 'antd';

import { useAuthStore } from '@/store/authStore';
import { gecerliHedefler } from './talepDurum';
import { TalepDurumEtiketi } from './rozetler';
import { useTalep, useTalepDurumAksiyon } from './hooks';

const HEDEF_AKSIYON: Record<string, { aksiyon: string; izin: string; etiket: string }> = {
  onay_bekliyor: { aksiyon: 'gonder', izin: 'satinalma:yaz', etiket: 'satinalma.gonder' },
  onaylandi: { aksiyon: 'onayla', izin: 'satinalma:onay', etiket: 'satinalma.onayla' },
  reddedildi: { aksiyon: 'reddet', izin: 'satinalma:onay', etiket: 'satinalma.reddet' },
  iptal: { aksiyon: 'iptal', izin: 'satinalma:yaz', etiket: 'satinalma.iptal' },
};

export function SatinalmaTalepDetay({ id, kapat }: { id: number | null; kapat: () => void }) {
  const { t } = useTranslation();
  const { data: talep } = useTalep(id ?? 0);
  const aksiyonMut = useTalepDurumAksiyon();
  const izinVar = useAuthStore((s) => s.izinVar);
  const [redAcik, setRedAcik] = useState(false);
  const [redNeden, setRedNeden] = useState('');

  const hedefler = talep ? gecerliHedefler(talep.durum) : [];
  const butonlar = hedefler
    .map((h) => HEDEF_AKSIYON[h])
    .filter((a) => a && izinVar(a.izin));

  const calistir = async (aksiyon: string) => {
    if (!talep) return;
    if (aksiyon === 'reddet') { setRedAcik(true); return; }
    await aksiyonMut.mutateAsync({ id: talep.id, aksiyon });
  };

  const redGonder = async () => {
    if (!talep) return;
    await aksiyonMut.mutateAsync({ id: talep.id, aksiyon: 'reddet', red_nedeni: redNeden });
    setRedAcik(false); setRedNeden('');
  };

  return (
    <Drawer open={id != null} onClose={kapat} width={620} title={talep?.kod}
            extra={talep && <TalepDurumEtiketi durum={talep.durum} />}>
      {talep && (
        <>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label={t('satinalma.baslik')}>{talep.baslik}</Descriptions.Item>
            <Descriptions.Item label={t('satinalma.tahmini_toplam')}>
              {talep.tahmini_toplam != null ? `${talep.tahmini_toplam} ${talep.para_birimi}` : '—'}
            </Descriptions.Item>
            {talep.red_nedeni && (
              <Descriptions.Item label={t('satinalma.red_nedeni')}>{talep.red_nedeni}</Descriptions.Item>
            )}
          </Descriptions>
          <Table
            style={{ marginTop: 16 }}
            rowKey="id"
            pagination={false}
            dataSource={talep.kalemler}
            columns={[
              { title: t('satinalma.malzeme'), dataIndex: 'malzeme_id' },
              { title: t('satinalma.miktar'), dataIndex: 'miktar', align: 'right',
                render: (v: number, k) => `${v} ${k.birim}` },
              { title: t('satinalma.birim_fiyat'), dataIndex: 'tahmini_birim_fiyat', align: 'right',
                render: (v: number | null) => v ?? '—' },
            ]}
          />
          <Space style={{ marginTop: 16 }}>
            {butonlar.map((a) => (
              <Button key={a.aksiyon}
                      type={a.aksiyon === 'onayla' ? 'primary' : 'default'}
                      danger={a.aksiyon === 'reddet'}
                      loading={aksiyonMut.isPending}
                      onClick={() => calistir(a.aksiyon)}>
                {t(a.etiket)}
              </Button>
            ))}
          </Space>
          <Modal open={redAcik} onCancel={() => setRedAcik(false)} onOk={redGonder}
                 title={t('satinalma.red_baslik')} confirmLoading={aksiyonMut.isPending}>
            <Input.TextArea rows={3} value={redNeden} onChange={(e) => setRedNeden(e.target.value)}
                            placeholder={t('satinalma.red_nedeni')} />
          </Modal>
        </>
      )}
    </Drawer>
  );
}
```
> `useAuthStore`'da `izinVar` selector'ı yoksa, `IzinKapisi`/`gorunurMenu`'nün kullandığı izin kontrol fonksiyonunu (store'daki mevcut `izinVar`/`izinler.includes`) kullan; `authStore.ts`'i kontrol et ve mevcut API'yi çağır.

- [ ] **Step 4: Write SatinalmaTalepListesi (+ test) + route**

`frontend/src/modules/stok/SatinalmaTalepListesi.tsx` — `SunucuTablo` (kod/başlık/durum rozeti/tarih) + satır tıkla → `SatinalmaTalepDetay` çekmecesi + "yeni talep" → `SatinalmaTalepFormu`. `MalzemeListesi` + `IsEmriListesi` desenini izle.
```tsx
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, Card } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';

import { type SatinalmaTalebi, useTalepler } from './hooks';
import { TalepDurumEtiketi } from './rozetler';
import { SatinalmaTalepDetay } from './SatinalmaTalepDetay';
import { SatinalmaTalepFormu } from './SatinalmaTalepFormu';

export function SatinalmaTalepListesi() {
  const { t } = useTranslation();
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useTalepler(param);
  const [detayId, setDetayId] = useState<number | null>(null);
  const [formAcik, setFormAcik] = useState(false);

  const kolonlar: ColumnsType<SatinalmaTalebi> = [
    { title: t('satinalma.kod'), dataIndex: 'kod', key: 'kod', sorter: true,
      render: (v: string, r) => <a onClick={() => setDetayId(r.id)} className="sayisal">{v}</a> },
    { title: t('satinalma.baslik'), dataIndex: 'baslik', key: 'baslik', sorter: true },
    { title: t('satinalma.durum'), dataIndex: 'durum', key: 'durum',
      render: (d: string) => <TalepDurumEtiketi durum={d} /> },
  ];

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik baslik={t('menu.satinalma')} alt={t('satinalma.alt')}
                   aksiyon={<Button type="primary" onClick={() => setFormAcik(true)}>{t('satinalma.yeni')}</Button>} />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<SatinalmaTalebi>
          kolonlar={kolonlar} veri={data?.veri ?? []} meta={data?.meta} yukleniyor={isPending}
          param={param} paramDegistir={paramDegistir} rowKey="id"
          aramaYer={t('satinalma.ara')} bosMetin={isError ? t('ortak.hata_baslik') : t('satinalma.bos')}
        />
      </Card>
      <SatinalmaTalepDetay id={detayId} kapat={() => setDetayId(null)} />
      <SatinalmaTalepFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </div>
  );
}
```

`frontend/src/modules/stok/SatinalmaTalepListesi.test.tsx` — `MalzemeListesi.test.tsx` desenini izle (başlık render olur).

`frontend/src/App.tsx` — import + rota:
```tsx
import { SatinalmaTalepListesi } from '@/modules/stok/SatinalmaTalepListesi';
```
```tsx
          <Route path="satinalma-talepleri" element={<IzinKapisi izin="satinalma:oku"><SatinalmaTalepListesi /></IzinKapisi>} />
```

- [ ] **Step 5: Run tests + lint + type + build**

```bash
cd frontend && npm run test && npm run lint && npx tsc --noEmit && npm run build
```
Expected: PASS / temiz / build başarılı.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/modules/stok/SatinalmaTalepListesi.tsx frontend/src/modules/stok/SatinalmaTalepDetay.tsx frontend/src/modules/stok/SatinalmaTalepFormu.tsx frontend/src/modules/stok/SatinalmaTalepListesi.test.tsx frontend/src/App.tsx frontend/src/i18n/tr.json frontend/src/i18n/en.json
git commit -m "feat(frontend): satınalma talep listesi/detay/form + izin-duyarlı onay aksiyonları (S9)"
```

---

## Task 11: Uçtan uca doğrulama + DoD + dal kapanışı

**Files:**
- Modify: `frontend/src/layouts/menu.test.ts` (yeni menü öğeleri için sayım/izin testi güncellenirse)
- (Doğrulama; yeni üretim kodu yok)

**Interfaces:** Yok.

- [ ] **Step 1: Full backend suite**

Run: `cd backend && python -m pytest -q && ruff check . && mypy app`
Expected: tüm testler PASS (S9: durum+migration+malzeme+hareket+satinalma+seed ≈ 26 yeni test; toplam ~152), ruff+mypy temiz.

- [ ] **Step 2: Full frontend suite**

Run: `cd frontend && npm run test && npm run lint && npx tsc --noEmit && npm run build`
Expected: tüm testler PASS, eslint+tsc strict temiz, `vite build` temiz (chunk uyarısı yok).
> `menu.test.ts` menü uzunluğunu/izinlerini doğruluyorsa, eklenen 3 öğeyi (`malzemeler`, `kritik-stok`, `satinalma`) yansıtacak şekilde beklentileri güncelle ve testi tekrar koş.

- [ ] **Step 3: Live end-to-end verification (gerçek yığın)**

```bash
docker compose up -d db redis
cd backend && uvicorn app.main:app --reload   # ayrı terminal
cd frontend && npm run dev                      # ayrı terminal
```
Tarayıcıda doğrula (izole `demo` tenant ya da `alfa`):
1. **Malzeme oluştur** (`MLZ-DEMO`, birim `adet`, kritik eşik `5`) → listede görünür.
2. **Stok girişi** 10 → bakiye 10; **çıkış** 6 → bakiye 4 → **Kritik stok** ekranında `MLZ-DEMO` belirir (canlı; `stok.kritik` WS olayı → invalidate); ikinci sekmede manuel yenileme olmadan güncellenir.
3. **Çok-kalemli satınalma talebi** oluştur → `taslak`; **Onaya gönder** → `onay_bekliyor`; `admin` ile **Onayla** → `onaylandi`. `depo` rolüyle giriş yapınca **Onayla/Reddet butonları görünmez** (izin-duyarlı).
4. Negatif çıkış denemesi → hata mesajı (422), bakiye değişmez.

Beklenen: tüm akışlar çalışır; kritik rozet canlı belirir; onay görev-ayrımı UI'da görünür.

- [ ] **Step 4: DoD kontrol listesi (spec §10)**

`docs/superpowers/specs/2026-06-30-s9-stok-satinalma-design.md` §10'daki tüm kutuları doğrula:
- [ ] ruff+mypy temiz; FE eslint+tsc+prettier temiz.
- [ ] Bakiye doğruluğu + kenar-tetikli kritik + idempotency + tenant izolasyonu + `satinalma:onay` 403 testleri yeşil ve kalıcı.
- [ ] API zarfı + doğru HTTP kodu; openapi.json + FE codegen güncel.
- [ ] Migration `public` + ≥2 tenant şemasında fan-out + downgrade (test_s9_migration).
- [ ] Yazma uçları audit üretir.
- [ ] ADR-0011 + veri sözlüğü + README/yol-haritası güncel.
- [ ] Conventional Commit'ler.

- [ ] **Step 5: Update memory + roadmap closure note**

`C:\Users\scryn\.claude\projects\C--Users-scryn-OneDrive-Belgeler-Projeler-FabrikaOS-v2\memory\project-fabrikaos-plan.md` ve `MEMORY.md`'ye S9 kapanış özetini ekle (S8 girişiyle aynı biçim: kapsam, test sayıları, ADR-0011, sıradaki **S10 (Kalite & Enerji)**).

- [ ] **Step 6: Finish the branch (superpowers:finishing-a-development-branch)**

`superpowers:finishing-a-development-branch` skill'ini çağır. Varsayılan: `main`'e **ff-merge** + origin'e push (S8 deseni):
```bash
git checkout main && git merge --ff-only feat/s9-stok-satinalma && git push origin main
git branch -d feat/s9-stok-satinalma
```
(Kullanıcı PR isterse onun yerine PR aç.)

- [ ] **Step 7: Final verification claim**

`superpowers:verification-before-completion` ile: BE+FE test çıktısını, lint/type temizliğini ve canlı uçtan-uca sonucu **gerçek komut çıktısıyla** doğrula; ancak hepsi yeşilse "tamamlandı" de.

---

## Notlar

- **Decimal/JSON sınırı:** modeller `Numeric(18,3)` (Decimal); cevap DTO'ları `float`; outbox/realtime `govde` `float` (JSONB serileştirme Decimal'i kabul etmez). Bu kural her mapper'da uygulanır.
- **Idempotency yarışı:** eşzamanlı aynı `Idempotency-Key` nadir; `idempotency_anahtari` **unique** kısıtı sert garantidir (ikinci yazım IntegrityError → 500; istenirse ileride yakalanıp mevcut döndürülür). S9 sıralı çift-gönderim senaryosunu (test) karşılar.
- **Talep ↔ stok ayrık** (mal kabul/sipariş Faz ilerisi). `duzeltme` türü `miktar`'ı **mutlak yeni bakiye** olarak yorumlar (sayım düzeltmesi).
- **Kenar tetik** yalnız "eşik üstünden altına ilk geçiş"te yayınlar; başlangıçta zaten eşik altında oluşturulan malzeme ilk çıkışta olay üretmez (yapısal — `/stok/kritik` yine listeler).
