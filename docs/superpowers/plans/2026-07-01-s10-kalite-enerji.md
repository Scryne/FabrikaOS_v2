# S10 — Kalite & Enerji Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Çekirdeğin üzerine çok-kiracılı, RBAC-korumalı, canlı bir **Kalite & Enerji** modülü kurmak: kalite denetimi + Tam CAPA (uygunsuzluk + kök-neden + düzeltici/önleyici aksiyonlar) yaşam döngüsü; enerji tüketimi (TimescaleDB hypertable) + continuous aggregate trend; backend + frontend uçtan uca.

**Architecture:** İki standart modül (`app/modules/kalite/`, `app/modules/enerji/`). Kalite: saf CAPA durum makinesi (`durum.py`) birim testli; servis geçiş kurallarını uygular; uygunsuzluk açılışında transactional outbox `kalite.uygunsuzluk`. Enerji: `UretimVerisi` hypertable deseni + **TimescaleDB continuous aggregate** (`enerji_tuketim_saatlik`, `autocommit_block` ile migrate); trend ucu CAGG'den (real-time aggregation). Uçlar tenant-kapsamlı (`tenant_cozumle` + `izin_gerekli`) + audit; frontend S6/S9 deseniyle (`SunucuTablo`, TanStack hooks, izin-duyarlı aksiyonlar, ECharts) + canlı invalidate.

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy 2 (async) / Alembic (iki-ağaç fan-out) / PostgreSQL + TimescaleDB (hypertable + continuous aggregate) / Redis pub-sub; React 18 + TS strict + Ant Design v5 + TanStack Query + Zustand + ECharts + Vite.

## Global Constraints

- **Türkçe-ASCII identifier standardı** (`turkce-identifier-standardi`): model/tablo/kolon/route/DTO adları Türkçe-ASCII. Kaynak adları çoğul kebab REST: `/kalite-kontrolleri`, `/uygunsuzluklar`, `/enerji-tuketimleri`, `/enerji-tuketimleri/trend`.
- **Tenant izolasyonu (`tenant-rbac-conventions`):** tenant-kapsamlı **her uç** iki dependency'den geçer — `Depends(tenant_cozumle)` (realtime yayını olan uçlarda `Tenant` tipiyle) ve `Depends(izin_gerekli("modul:islem"))`. FK'ler şema öneki **yazılmaz** (`makineler.id`, `kullanici.id`); `search_path` çözer. Sabit `tenant_xyz.tablo` öneki yasak.
- **Yanıt zarfı:** `{success, message, data, meta}`; liste uçları `sayfali(...)`; sayfalama `?sayfa=&adet=&siralama=&yon=&arama=`.
- **Miktar tipi:** DB `Numeric(18, 3)` (Decimal aritmetik). **İstek DTO** miktar alanları `Decimal` (`Field(gt=0)` / `ge=0`); **cevap DTO** alanları `float` (sınırda `float(...)` dönüşümü). Outbox/realtime `govde` JSON-native olmalı → `float(...)` kullan (Decimal JSONB'ye serialize edilemez).
- **Migration:** tenant ağacı, `down_revision = "a3d9f1c52e84"` (uygulama anında `python -m alembic -n tenant heads` ile doğrula; farklıysa çıkan head'i kullan). Enerji **hypertable**; ayrıca **continuous aggregate** (`autocommit_block` zorunlu — CAGG transaction içinde oluşturulamaz). `public` + ≥2 tenant şemasında fan-out up/down.
- **Audit:** her yazma ucu `denetim_yaz(...)` üretir.
- **Kalite kapısı:** `ruff check .` + `ruff format --check .` + `mypy app` temiz (backend); `npm run lint` + `npm run typecheck` (tsc --strict) + `npm run format:check` + `npm run test` + `npm run build` temiz (frontend). Conventional Commits; görev başına commit.
- **Komutlar (backend `backend/` dizininden):** test `python -m pytest`, lint `ruff check .`, tip `python -m mypy app`. Migration head kontrolü: `python -m alembic -n tenant heads`. **Frontend (`frontend/`):** `npm run test`, `npm run lint`, `npm run typecheck`, `npm run build`, `npm run codegen`. Entegrasyon testleri çalışan PostgreSQL+TimescaleDB ister (`docker compose up -d db redis`).
- **CAGG karar:** materialized view `WITH (timescaledb.continuous, timescaledb.materialized_only = false)` → **real-time aggregation** açık; trend ucu son (henüz materialize edilmemiş) veriyi de görür, testte manuel refresh gerekmez.

---

## Task 1: Saf sabitler (kalite + enerji) + CAPA durum makinesi

**Files:**
- Create: `backend/app/modules/kalite/__init__.py`
- Create: `backend/app/modules/kalite/birimler.py`
- Create: `backend/app/modules/kalite/durum.py`
- Create: `backend/app/modules/enerji/__init__.py`
- Create: `backend/app/modules/enerji/birimler.py`
- Test: `backend/tests/test_s10_durum.py`

**Interfaces:**
- Produces:
  - `kalite.birimler.KONTROL_TURLERI: frozenset[str]` (= `{"uretim","giris","final"}`), `KONTROL_SONUCLARI` (= `{"gecti","kaldi","sartli"}`), `UYGUNSUZLUK_ONEMLERI` (= `{"dusuk","orta","yuksek","kritik"}`), `CAPA_AKSIYON_TURLERI` (= `{"duzeltici","onleyici"}`), `CAPA_AKSIYON_DURUMLARI` (= `{"planlandi","tamamlandi","iptal"}`)
  - `enerji.birimler.ENERJI_TURLERI: frozenset[str]` (= `{"elektrik","dogalgaz","su","hava","buhar"}`)
  - `kalite.durum.GECISLER: dict[str, frozenset[str]]`, `DURUMLAR: frozenset[str]`, `TERMINAL_DURUMLAR: frozenset[str]`, `AKTIF_DURUMLAR: frozenset[str]`, `ILK_DURUM: str` (= `"acik"`)
  - `kalite.durum.gecerli_hedefler(mevcut: str) -> frozenset[str]`, `gecis_gecerli_mi(mevcut: str, hedef: str) -> bool`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_s10_durum.py`:
```python
"""S10 birim testleri: CAPA durum makinesi + kalite/enerji sabitleri (saf, DB'siz)."""

from __future__ import annotations

from app.modules.enerji import birimler as enerji_birimler
from app.modules.kalite import birimler as kalite_birimler
from app.modules.kalite import durum


def test_ilk_durum_acik() -> None:
    assert durum.ILK_DURUM == "acik"


def test_acik_gecerli_hedefler() -> None:
    assert durum.gecerli_hedefler("acik") == frozenset({"kok_neden", "iptal"})


def test_dogrulama_hedefleri_geri_donus_dahil() -> None:
    # doğrulama başarısız → uygulama'ya geri; başarılı → kapandi; veya iptal
    assert durum.gecerli_hedefler("dogrulama") == frozenset({"kapandi", "uygulama", "iptal"})


def test_terminal_durumlardan_cikis_yok() -> None:
    for d in ("kapandi", "iptal"):
        assert durum.gecerli_hedefler(d) == frozenset()
    assert durum.TERMINAL_DURUMLAR == frozenset({"kapandi", "iptal"})


def test_aktif_durumlar() -> None:
    assert durum.AKTIF_DURUMLAR == frozenset(
        {"acik", "kok_neden", "aksiyon_plani", "uygulama", "dogrulama"}
    )


def test_gecerli_ve_gecersiz_gecisler() -> None:
    assert durum.gecis_gecerli_mi("acik", "kok_neden") is True
    assert durum.gecis_gecerli_mi("dogrulama", "kapandi") is True
    assert durum.gecis_gecerli_mi("dogrulama", "uygulama") is True
    # acik'ten doğrudan kapandi yasak
    assert durum.gecis_gecerli_mi("acik", "kapandi") is False
    # terminalden çıkış yasak
    assert durum.gecis_gecerli_mi("kapandi", "uygulama") is False
    # tanımsız durum → boş
    assert durum.gecis_gecerli_mi("yok", "acik") is False


def test_kalite_sabitler() -> None:
    assert kalite_birimler.KONTROL_SONUCLARI == frozenset({"gecti", "kaldi", "sartli"})
    assert kalite_birimler.KONTROL_TURLERI == frozenset({"uretim", "giris", "final"})
    assert kalite_birimler.UYGUNSUZLUK_ONEMLERI == frozenset(
        {"dusuk", "orta", "yuksek", "kritik"}
    )
    assert kalite_birimler.CAPA_AKSIYON_TURLERI == frozenset({"duzeltici", "onleyici"})
    assert kalite_birimler.CAPA_AKSIYON_DURUMLARI == frozenset(
        {"planlandi", "tamamlandi", "iptal"}
    )


def test_enerji_sabitler() -> None:
    assert enerji_birimler.ENERJI_TURLERI == frozenset(
        {"elektrik", "dogalgaz", "su", "hava", "buhar"}
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_s10_durum.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.modules.kalite'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/modules/kalite/__init__.py`:
```python
"""Kalite modülü (denetim + Tam CAPA: uygunsuzluk + düzeltici/önleyici aksiyonlar)."""
```

`backend/app/modules/kalite/birimler.py`:
```python
"""Kalite modülü saf sabitleri — beyaz-listeler (DTO/router doğrulamasında kullanılır)."""

from __future__ import annotations

# Kalite kontrol türü (denetim bağlamı).
KONTROL_TURLERI: frozenset[str] = frozenset({"uretim", "giris", "final"})

# Kalite kontrol sonucu.
KONTROL_SONUCLARI: frozenset[str] = frozenset({"gecti", "kaldi", "sartli"})

# Uygunsuzluk önem derecesi.
UYGUNSUZLUK_ONEMLERI: frozenset[str] = frozenset({"dusuk", "orta", "yuksek", "kritik"})

# CAPA aksiyon türü: düzeltici (corrective) / önleyici (preventive).
CAPA_AKSIYON_TURLERI: frozenset[str] = frozenset({"duzeltici", "onleyici"})

# CAPA aksiyon durumu (aksiyon başına, ana uygunsuzluk durumundan bağımsız).
CAPA_AKSIYON_DURUMLARI: frozenset[str] = frozenset({"planlandi", "tamamlandi", "iptal"})
```

`backend/app/modules/kalite/durum.py`:
```python
"""CAPA (uygunsuzluk) durum makinesi — saf (DB'siz) iş kuralı, kapsamlı birim testli.

Yaşam döngüsü (Tam CAPA)::

    acik ─> kok_neden ─> aksiyon_plani ─> uygulama ─> dogrulama ─> kapandi*
      │         │             │              │          │  │
      │         │             │              │          │  └─> uygulama  (doğrulama başarısız)
      └─────────┴─────────────┴──────────────┴──────────┴─> iptal*

``*`` terminal: çıkış geçişi yoktur. Tüm geçişler çağıran katmanda ``kalite:yaz`` iznini
gerektirir (ayrı onay izni yoktur).
"""

from __future__ import annotations

# mevcut durum -> izin verilen hedef durumlar.
GECISLER: dict[str, frozenset[str]] = {
    "acik": frozenset({"kok_neden", "iptal"}),
    "kok_neden": frozenset({"aksiyon_plani", "iptal"}),
    "aksiyon_plani": frozenset({"uygulama", "iptal"}),
    "uygulama": frozenset({"dogrulama", "iptal"}),
    "dogrulama": frozenset({"kapandi", "uygulama", "iptal"}),
    "kapandi": frozenset(),
    "iptal": frozenset(),
}

DURUMLAR: frozenset[str] = frozenset(GECISLER)
TERMINAL_DURUMLAR: frozenset[str] = frozenset({"kapandi", "iptal"})
AKTIF_DURUMLAR: frozenset[str] = DURUMLAR - TERMINAL_DURUMLAR
ILK_DURUM = "acik"


def gecerli_hedefler(mevcut: str) -> frozenset[str]:
    """``mevcut`` durumdan gidilebilecek hedef durumlar (tanımsızsa boş küme)."""
    return GECISLER.get(mevcut, frozenset())


def gecis_gecerli_mi(mevcut: str, hedef: str) -> bool:
    """``mevcut`` → ``hedef`` geçişi durum makinesine göre geçerli mi?"""
    return hedef in gecerli_hedefler(mevcut)
```

`backend/app/modules/enerji/__init__.py`:
```python
"""Enerji modülü (tüketim hypertable + continuous aggregate trend)."""
```

`backend/app/modules/enerji/birimler.py`:
```python
"""Enerji modülü saf sabitleri — enerji türü beyaz-listesi."""

from __future__ import annotations

# Enerji türleri (beyaz-liste; DTO/router doğrulamasında kullanılır).
ENERJI_TURLERI: frozenset[str] = frozenset({"elektrik", "dogalgaz", "su", "hava", "buhar"})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_s10_durum.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Lint + commit**

```bash
cd backend && ruff check app/modules/kalite app/modules/enerji tests/test_s10_durum.py && ruff format --check app/modules/kalite app/modules/enerji && python -m mypy app/modules/kalite app/modules/enerji
git add backend/app/modules/kalite/__init__.py backend/app/modules/kalite/birimler.py backend/app/modules/kalite/durum.py backend/app/modules/enerji/__init__.py backend/app/modules/enerji/birimler.py backend/tests/test_s10_durum.py
git commit -m "feat(kalite): saf CAPA durum makinesi + kalite/enerji sabitleri (S10)"
```

---

## Task 2: Modeller (kalite 3 tablo + enerji hypertable) + registry + migration (fan-out + CAGG)

> **En riskli task.** Continuous aggregate `autocommit_block` içinde oluşturulur (TimescaleDB transaction içinde CAGG yaratamaz). Async engine + `run_sync` + `autocommit_block` etkileşimi burada kanıtlanır.

**Files:**
- Create: `backend/app/modules/kalite/models.py`
- Create: `backend/app/modules/enerji/models.py`
- Modify: `backend/app/core/db/registry.py` (2 import satırı)
- Create: `backend/migrations/tenant/versions/b7e4c2f9a016_kalite_enerji.py`
- Test: `backend/tests/test_s10_migration.py`

**Interfaces:**
- Produces (SQLAlchemy modelleri, tenant şeması):
  - `KaliteKontrol` (`kalite_kontrolleri`): `id, kod, makine_id, is_emri_id, kontrol_turu, sonuc, olculen_deger, alt_limit, ust_limit, numune_adedi, uygunsuz_adet, aciklama, kontrol_eden_kullanici_id, zaman, olusturma_tarihi, guncelleme_tarihi`
  - `Uygunsuzluk` (`uygunsuzluklar`): `id, kod, baslik, aciklama, kaynak_kontrol_id, makine_id, onem, durum, kok_neden, acan_kullanici_id, sorumlu_kullanici_id, dogrulama_notu, kapanis_tarihi, olusturma_tarihi, guncelleme_tarihi`; `aksiyonlar` relationship
  - `CapaAksiyon` (`capa_aksiyonlari`): `id, uygunsuzluk_id, tur, aciklama, sorumlu_kullanici_id, termin_tarihi, durum, tamamlanma_tarihi, olusturma_tarihi, guncelleme_tarihi`; `uygunsuzluk` relationship
  - `EnerjiTuketim` (`enerji_tuketim`, hypertable, PK `(zaman, id)`): `id, zaman, makine_id, enerji_turu, tuketim, birim`
  - CAGG görünüm: `enerji_tuketim_saatlik (kova, makine_id, enerji_turu, toplam_tuketim, olcum_adedi)`

- [ ] **Step 1: Write the models**

`backend/app/modules/kalite/models.py`:
```python
"""Kalite modülü modelleri (tenant şeması) — denetim + Tam CAPA.

- ``KaliteKontrol`` — denetim/muayene kaydı (makine + opsiyonel iş emri).
- ``Uygunsuzluk`` — CAPA vakası; durum ``durum.py`` makinesiyle yönetilir; ``kok_neden``
  kök-neden aşamasında dolar.
- ``CapaAksiyon`` — düzeltici/önleyici aksiyon (n–1 uygunsuzluk); kendi durumu vardır.

FK'ler şema önekiyle yazılmaz (``makineler.id``, ``kullanici.id``); ``search_path`` çözer.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin
from app.modules.kalite.durum import ILK_DURUM

_OLCU = Numeric(18, 3)


class KaliteKontrol(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Kalite denetim/muayene kaydı."""

    __tablename__ = "kalite_kontrolleri"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    makine_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("makineler.id", ondelete="SET NULL"), index=True, nullable=True
    )
    is_emri_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("is_emirleri.id", ondelete="SET NULL"), index=True, nullable=True
    )
    kontrol_turu: Mapped[str] = mapped_column(String(20), default="uretim", nullable=False)
    sonuc: Mapped[str] = mapped_column(String(20), nullable=False)
    olculen_deger: Mapped[Decimal | None] = mapped_column(_OLCU, nullable=True)
    alt_limit: Mapped[Decimal | None] = mapped_column(_OLCU, nullable=True)
    ust_limit: Mapped[Decimal | None] = mapped_column(_OLCU, nullable=True)
    numune_adedi: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    uygunsuz_adet: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    aciklama: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    kontrol_eden_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    zaman: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Uygunsuzluk(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Uygunsuzluk / CAPA vakası — yaşam döngüsü ``durum.py``."""

    __tablename__ = "uygunsuzluklar"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    baslik: Mapped[str] = mapped_column(String(200), nullable=False)
    aciklama: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    kaynak_kontrol_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("kalite_kontrolleri.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    makine_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("makineler.id", ondelete="SET NULL"), index=True, nullable=True
    )
    onem: Mapped[str] = mapped_column(String(20), default="orta", index=True, nullable=False)
    durum: Mapped[str] = mapped_column(String(20), default=ILK_DURUM, index=True, nullable=False)
    kok_neden: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    acan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    sorumlu_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    dogrulama_notu: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    kapanis_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    aksiyonlar: Mapped[list[CapaAksiyon]] = relationship(
        back_populates="uygunsuzluk",
        cascade="all, delete-orphan",
        order_by="CapaAksiyon.id",
    )


class CapaAksiyon(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Düzeltici/önleyici aksiyon (n–1 uygunsuzluk)."""

    __tablename__ = "capa_aksiyonlari"

    uygunsuzluk_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("uygunsuzluklar.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    tur: Mapped[str] = mapped_column(String(20), nullable=False)
    aciklama: Mapped[str] = mapped_column(String(1000), nullable=False)
    sorumlu_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    termin_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    durum: Mapped[str] = mapped_column(String(20), default="planlandi", nullable=False)
    tamamlanma_tarihi: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    uygunsuzluk: Mapped[Uygunsuzluk] = relationship(back_populates="aksiyonlar")
```

`backend/app/modules/enerji/models.py`:
```python
"""Enerji modülü modelleri (tenant şeması).

``EnerjiTuketim`` — TimescaleDB **hypertable** (yüksek hacimli zaman serisi); partition
kolonu ``zaman``, PK ``(zaman, id)`` (uretim ``UretimVerisi`` deseni). ``makine_id`` nullable
= tesis geneli tüketim. Continuous aggregate (``enerji_tuketim_saatlik``) migration'da kurulur.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    PrimaryKeyConstraint,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import TenantBase


class EnerjiTuketim(TenantBase):
    """Enerji tüketim ölçümü (zaman serisi / hypertable)."""

    __tablename__ = "enerji_tuketim"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    zaman: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    makine_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("makineler.id", ondelete="SET NULL"), nullable=True
    )
    enerji_turu: Mapped[str] = mapped_column(String(20), nullable=False)
    tuketim: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    birim: Mapped[str] = mapped_column(String(20), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("zaman", "id", name="pk_enerji_tuketim"),
        Index("ix_enerji_tuketim_makine_zaman", "makine_id", "zaman"),
        Index("ix_enerji_tuketim_turu_zaman", "enerji_turu", "zaman"),
    )
```

- [ ] **Step 2: Register models in the metadata registry**

`backend/app/core/db/registry.py` — mevcut `import app.modules.*` bloğuna, alfabetik sıraya ekle (`isemri` sonrası `kalite`; `enerji` `bakim` sonrası). Nihai tenant-model import bloğu:
```python
import app.modules.bakim.models  # noqa: F401
import app.modules.enerji.models  # noqa: F401
import app.modules.isemri.models  # noqa: F401
import app.modules.kalite.models  # noqa: F401
import app.modules.saha.models  # noqa: F401
import app.modules.stok.models  # noqa: F401
import app.modules.uretim.models  # noqa: F401
```

- [ ] **Step 3: Verify head revision, then write the migration**

Run: `cd backend && python -m alembic -n tenant heads`
Expected: `a3d9f1c52e84 (head)`. (Farklıysa aşağıdaki `down_revision`'ı çıkan head ile değiştir.)

`backend/migrations/tenant/versions/b7e4c2f9a016_kalite_enerji.py`:
```python
"""kalite (denetim + CAPA) + enerji (hypertable + continuous aggregate)

Revision ID: b7e4c2f9a016
Revises: a3d9f1c52e84
Create Date: 2026-07-01 09:00:00.000000

Tenant şemasında; fan-out döngüsünde (env.py) public + her aktif tenant şemasında çalışır.
Enerji hypertable + continuous aggregate. CAGG ``autocommit_block`` içinde oluşturulur
(TimescaleDB CAGG'i transaction bloğunda yaratamaz). search_path env'de ``SET`` (session)
ile ayarlandığından autocommit commit'inden sonra korunur → CAGG doğru tenant şemasında oluşur.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b7e4c2f9a016"
down_revision: str | None = "a3d9f1c52e84"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kalite_kontrolleri",
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("makine_id", sa.BigInteger(), nullable=True),
        sa.Column("is_emri_id", sa.BigInteger(), nullable=True),
        sa.Column("kontrol_turu", sa.String(length=20), nullable=False, server_default="uretim"),
        sa.Column("sonuc", sa.String(length=20), nullable=False),
        sa.Column("olculen_deger", sa.Numeric(18, 3), nullable=True),
        sa.Column("alt_limit", sa.Numeric(18, 3), nullable=True),
        sa.Column("ust_limit", sa.Numeric(18, 3), nullable=True),
        sa.Column("numune_adedi", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uygunsuz_adet", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("aciklama", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("kontrol_eden_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("zaman", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("olusturma_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["makine_id"], ["makineler.id"], name=op.f("fk_kalite_kontrolleri_makine_id_makineler"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["is_emri_id"], ["is_emirleri.id"], name=op.f("fk_kalite_kontrolleri_is_emri_id_is_emirleri"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["kontrol_eden_kullanici_id"], ["kullanici.id"], name=op.f("fk_kalite_kontrolleri_kontrol_eden_kullanici_id_kullanici"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kalite_kontrolleri")),
    )
    op.create_index(op.f("ix_kalite_kontrolleri_kod"), "kalite_kontrolleri", ["kod"], unique=True)
    op.create_index(op.f("ix_kalite_kontrolleri_makine_id"), "kalite_kontrolleri", ["makine_id"], unique=False)
    op.create_index(op.f("ix_kalite_kontrolleri_is_emri_id"), "kalite_kontrolleri", ["is_emri_id"], unique=False)
    op.create_index(op.f("ix_kalite_kontrolleri_kontrol_eden_kullanici_id"), "kalite_kontrolleri", ["kontrol_eden_kullanici_id"], unique=False)

    op.create_table(
        "uygunsuzluklar",
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("baslik", sa.String(length=200), nullable=False),
        sa.Column("aciklama", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("kaynak_kontrol_id", sa.BigInteger(), nullable=True),
        sa.Column("makine_id", sa.BigInteger(), nullable=True),
        sa.Column("onem", sa.String(length=20), nullable=False, server_default="orta"),
        sa.Column("durum", sa.String(length=20), nullable=False, server_default="acik"),
        sa.Column("kok_neden", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("acan_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("sorumlu_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("dogrulama_notu", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("kapanis_tarihi", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("olusturma_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["kaynak_kontrol_id"], ["kalite_kontrolleri.id"], name=op.f("fk_uygunsuzluklar_kaynak_kontrol_id_kalite_kontrolleri"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["makine_id"], ["makineler.id"], name=op.f("fk_uygunsuzluklar_makine_id_makineler"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["acan_kullanici_id"], ["kullanici.id"], name=op.f("fk_uygunsuzluklar_acan_kullanici_id_kullanici"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sorumlu_kullanici_id"], ["kullanici.id"], name=op.f("fk_uygunsuzluklar_sorumlu_kullanici_id_kullanici"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_uygunsuzluklar")),
    )
    op.create_index(op.f("ix_uygunsuzluklar_kod"), "uygunsuzluklar", ["kod"], unique=True)
    op.create_index(op.f("ix_uygunsuzluklar_kaynak_kontrol_id"), "uygunsuzluklar", ["kaynak_kontrol_id"], unique=False)
    op.create_index(op.f("ix_uygunsuzluklar_makine_id"), "uygunsuzluklar", ["makine_id"], unique=False)
    op.create_index(op.f("ix_uygunsuzluklar_onem"), "uygunsuzluklar", ["onem"], unique=False)
    op.create_index(op.f("ix_uygunsuzluklar_durum"), "uygunsuzluklar", ["durum"], unique=False)
    op.create_index(op.f("ix_uygunsuzluklar_acan_kullanici_id"), "uygunsuzluklar", ["acan_kullanici_id"], unique=False)
    op.create_index(op.f("ix_uygunsuzluklar_sorumlu_kullanici_id"), "uygunsuzluklar", ["sorumlu_kullanici_id"], unique=False)

    op.create_table(
        "capa_aksiyonlari",
        sa.Column("uygunsuzluk_id", sa.BigInteger(), nullable=False),
        sa.Column("tur", sa.String(length=20), nullable=False),
        sa.Column("aciklama", sa.String(length=1000), nullable=False),
        sa.Column("sorumlu_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("termin_tarihi", sa.DateTime(timezone=True), nullable=True),
        sa.Column("durum", sa.String(length=20), nullable=False, server_default="planlandi"),
        sa.Column("tamamlanma_tarihi", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("olusturma_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["uygunsuzluk_id"], ["uygunsuzluklar.id"], name=op.f("fk_capa_aksiyonlari_uygunsuzluk_id_uygunsuzluklar"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sorumlu_kullanici_id"], ["kullanici.id"], name=op.f("fk_capa_aksiyonlari_sorumlu_kullanici_id_kullanici"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_capa_aksiyonlari")),
    )
    op.create_index(op.f("ix_capa_aksiyonlari_uygunsuzluk_id"), "capa_aksiyonlari", ["uygunsuzluk_id"], unique=False)
    op.create_index(op.f("ix_capa_aksiyonlari_sorumlu_kullanici_id"), "capa_aksiyonlari", ["sorumlu_kullanici_id"], unique=False)

    op.create_table(
        "enerji_tuketim",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("zaman", sa.DateTime(timezone=True), nullable=False),
        sa.Column("makine_id", sa.BigInteger(), nullable=True),
        sa.Column("enerji_turu", sa.String(length=20), nullable=False),
        sa.Column("tuketim", sa.Numeric(18, 3), nullable=False),
        sa.Column("birim", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["makine_id"], ["makineler.id"], name=op.f("fk_enerji_tuketim_makine_id_makineler"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("zaman", "id", name="pk_enerji_tuketim"),
    )
    op.create_index("ix_enerji_tuketim_makine_zaman", "enerji_tuketim", ["makine_id", "zaman"], unique=False)
    op.create_index("ix_enerji_tuketim_turu_zaman", "enerji_tuketim", ["enerji_turu", "zaman"], unique=False)

    # enerji_tuketim'i hypertable'a çevir (transaction içinde çalışır — uretim'de kanıtlı).
    op.execute("SELECT create_hypertable('enerji_tuketim', 'zaman', if_not_exists => TRUE)")

    # Continuous aggregate + refresh policy TRANSACTION DIŞINDA olmalı (TimescaleDB kısıtı).
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS enerji_tuketim_saatlik
            WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
            SELECT time_bucket('1 hour', zaman) AS kova,
                   makine_id,
                   enerji_turu,
                   sum(tuketim) AS toplam_tuketim,
                   count(*) AS olcum_adedi
            FROM enerji_tuketim
            GROUP BY kova, makine_id, enerji_turu
            WITH NO DATA
            """
        )
        op.execute(
            """
            SELECT add_continuous_aggregate_policy('enerji_tuketim_saatlik',
                start_offset => INTERVAL '3 days',
                end_offset => INTERVAL '1 hour',
                schedule_interval => INTERVAL '1 hour',
                if_not_exists => TRUE)
            """
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP MATERIALIZED VIEW IF EXISTS enerji_tuketim_saatlik")
    op.drop_index("ix_enerji_tuketim_turu_zaman", table_name="enerji_tuketim")
    op.drop_index("ix_enerji_tuketim_makine_zaman", table_name="enerji_tuketim")
    op.drop_table("enerji_tuketim")
    op.drop_index(op.f("ix_capa_aksiyonlari_sorumlu_kullanici_id"), table_name="capa_aksiyonlari")
    op.drop_index(op.f("ix_capa_aksiyonlari_uygunsuzluk_id"), table_name="capa_aksiyonlari")
    op.drop_table("capa_aksiyonlari")
    op.drop_index(op.f("ix_uygunsuzluklar_sorumlu_kullanici_id"), table_name="uygunsuzluklar")
    op.drop_index(op.f("ix_uygunsuzluklar_acan_kullanici_id"), table_name="uygunsuzluklar")
    op.drop_index(op.f("ix_uygunsuzluklar_durum"), table_name="uygunsuzluklar")
    op.drop_index(op.f("ix_uygunsuzluklar_onem"), table_name="uygunsuzluklar")
    op.drop_index(op.f("ix_uygunsuzluklar_makine_id"), table_name="uygunsuzluklar")
    op.drop_index(op.f("ix_uygunsuzluklar_kaynak_kontrol_id"), table_name="uygunsuzluklar")
    op.drop_index(op.f("ix_uygunsuzluklar_kod"), table_name="uygunsuzluklar")
    op.drop_table("uygunsuzluklar")
    op.drop_index(op.f("ix_kalite_kontrolleri_kontrol_eden_kullanici_id"), table_name="kalite_kontrolleri")
    op.drop_index(op.f("ix_kalite_kontrolleri_is_emri_id"), table_name="kalite_kontrolleri")
    op.drop_index(op.f("ix_kalite_kontrolleri_makine_id"), table_name="kalite_kontrolleri")
    op.drop_index(op.f("ix_kalite_kontrolleri_kod"), table_name="kalite_kontrolleri")
    op.drop_table("kalite_kontrolleri")
```

- [ ] **Step 4: Write the fan-out migration test**

`backend/tests/test_s10_migration.py`:
```python
"""S10 migration fan-out testi: kalite/enerji tabloları + CAGG up/down (tenant_alfa)."""

from __future__ import annotations

import asyncio

import asyncpg
import pytest

from app.core.db import fanout
from tests.conftest import TEST_URL

pytestmark = pytest.mark.asyncio

_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
_TABLOLAR = (
    "kalite_kontrolleri",
    "uygunsuzluklar",
    "capa_aksiyonlari",
    "enerji_tuketim",
    "enerji_tuketim_saatlik",  # continuous aggregate görünümü
)


async def _var_mi(nesne: str) -> bool:
    conn = await asyncpg.connect(_DSN)
    try:
        return bool(await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", f"tenant_alfa.{nesne}"))
    finally:
        await conn.close()


async def test_kalite_enerji_up_down(test_db: str) -> None:
    # test_db fixture: head'e migrate edilmiş tenant_alfa şeması.
    for t in _TABLOLAR:
        assert await _var_mi(t), t

    # downgrade bir adım (stok head'ine) → S10 nesneleri gitmeli.
    await asyncio.to_thread(fanout.tenant_indir_tek, "alfa", "a3d9f1c52e84", db_url=TEST_URL)
    for t in _TABLOLAR:
        assert not await _var_mi(t), t

    # tekrar head'e çık (sonraki testler için durumu geri yükle).
    await asyncio.to_thread(fanout.tenant_yukselt_tek, "alfa", "head", db_url=TEST_URL)
    assert await _var_mi("enerji_tuketim_saatlik")
```

- [ ] **Step 5: Run the migration test**

Run: `cd backend && python -m pytest tests/test_s10_migration.py -v`
Expected: PASS — fixture provizyonlama yeni migration'ı uygular; 4 tablo + CAGG `tenant_alfa` + `tenant_beta`'da oluşur, downgrade düşürür, tekrar yükselir. **Bu, `autocommit_block` + async fan-out'un çalıştığının kanıtıdır.**

> **Sorun giderme:** `CREATE MATERIALIZED VIEW ... cannot run inside a transaction block` hatası alırsan `autocommit_block` doğru sarmıyor demektir — `op.get_context().autocommit_block()` context manager'ının CAGG `op.execute` çağrılarını sardığını doğrula. `add_continuous_aggregate_policy` "function ... does not exist" verirse test DB imajı TSL değil (community `timescale/timescaledb` imajı gerekir).

- [ ] **Step 6: Lint + commit**

```bash
cd backend && ruff check app/modules/kalite/models.py app/modules/enerji/models.py app/core/db/registry.py tests/test_s10_migration.py && ruff format --check app/modules/kalite/models.py app/modules/enerji/models.py && python -m mypy app/modules/kalite/models.py app/modules/enerji/models.py
git add backend/app/modules/kalite/models.py backend/app/modules/enerji/models.py backend/app/core/db/registry.py backend/migrations/tenant/versions/b7e4c2f9a016_kalite_enerji.py backend/tests/test_s10_migration.py
git commit -m "feat(kalite,enerji): modeller + hypertable + continuous aggregate migration (fan-out up/down testli) (S10)"
```

---

## Task 3: Kalite kontrol dikey dilimi (schemas + repository + router)

**Files:**
- Create: `backend/app/modules/kalite/schemas.py` (kalite kontrol DTO'ları)
- Create: `backend/app/modules/kalite/repository.py` (kontrol sorguları)
- Create: `backend/app/modules/kalite/service.py` (oto kod yardımcıları)
- Create: `backend/app/modules/kalite/router.py` (kalite kontrol uçları)
- Modify: `backend/app/api/router.py` (kalite router'ını include et)
- Test: `backend/tests/test_s10_kalite_kontrol.py`

**Interfaces:**
- Consumes: `KaliteKontrol` (Task 2); `tenant_cozumle`, `izin_gerekli` (`app.core.deps`); `denetim_yaz`; `basari`/`sayfali`/`Zarf`; `siralama_uygula`; `KONTROL_TURLERI`/`KONTROL_SONUCLARI` (Task 1); `yayinla` (`app.core.gercekzaman`); `Tenant` (`app.control_plane.models`).
- Produces:
  - DTO'lar: `KaliteKontrolOlusturDTO`, `KaliteKontrolCevapDTO`
  - `service.kalite_kontrol_gecici_kod()`, `service.kalite_kontrol_kalici_kod(id: int)` (= `KK-{yıl}-{id:06d}`), `service.uygunsuzluk_gecici_kod()`, `service.uygunsuzluk_kalici_kod(id: int)` (= `UY-{yıl}-{id:06d}`)
  - Repository: `kontrol_ekle`, `kontrol_getir`, `kontrol_listele`
  - `kalite` router (mutlak yollar `/kalite-kontrolleri`)
  - `_kontrol_cevap(k: KaliteKontrol) -> dict` (Task 4 yeniden kullanmaz; kalite router tek dosyada büyür)

- [ ] **Step 1: Write the failing integration test**

`backend/tests/test_s10_kalite_kontrol.py`:
```python
"""S10 entegrasyon: kalite kontrol oluştur/listele + RBAC + tenant izolasyonu."""

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


async def _kontrol(istemci: AsyncClient, h: dict[str, str], **ek: object) -> dict:
    govde = {"kontrol_turu": "uretim", "sonuc": "gecti", "numune_adedi": 10, **ek}
    r = await istemci.post("/api/v1/kalite-kontrolleri", json=govde, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_kontrol_olustur_oto_kod(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _kontrol(kurulu_istemci, h)
    assert d["kod"].startswith("KK-")
    assert d["sonuc"] == "gecti"


async def test_kontrol_gecersiz_sonuc_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/kalite-kontrolleri",
        json={"sonuc": "belirsiz", "numune_adedi": 1},
        headers=h,
    )
    assert r.status_code == 422, r.text


async def test_kontrol_uygunsuz_numuneden_fazla_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/kalite-kontrolleri",
        json={"sonuc": "kaldi", "numune_adedi": 5, "uygunsuz_adet": 9},
        headers=h,
    )
    assert r.status_code == 422, r.text


async def test_kontrol_listele_filtre_sonuc(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await _kontrol(kurulu_istemci, h, sonuc="gecti")
    await _kontrol(kurulu_istemci, h, sonuc="kaldi")
    r = await kurulu_istemci.get("/api/v1/kalite-kontrolleri?sonuc=kaldi", headers=h)
    assert r.status_code == 200, r.text
    assert all(x["sonuc"] == "kaldi" for x in r.json()["data"])


async def test_kontrol_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "izl-kl@alfa.test", "parola": "Izleyici123!", "roller": ["izleyici"]},
        headers=admin,
    )
    izl = _h(
        "alfa",
        await _giris(
            kurulu_istemci, {"slug": "alfa", "eposta": "izl-kl@alfa.test", "parola": "Izleyici123!"}
        ),
    )
    # kalite:oku var → liste 200
    assert (await kurulu_istemci.get("/api/v1/kalite-kontrolleri", headers=izl)).status_code == 200
    # kalite:yaz yok → oluştur 403
    r = await kurulu_istemci.post(
        "/api/v1/kalite-kontrolleri", json={"sonuc": "gecti", "numune_adedi": 1}, headers=izl
    )
    assert r.status_code == 403, r.text


async def test_kontrol_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    ha = _h("alfa", await _giris(kurulu_istemci, ALFA))
    da = await _kontrol(kurulu_istemci, ha)
    hb = _h("beta", await _giris(kurulu_istemci, BETA))
    assert (
        await kurulu_istemci.get(f"/api/v1/kalite-kontrolleri/{da['id']}", headers=hb)
    ).status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_s10_kalite_kontrol.py -v`
Expected: FAIL — `404` (uç yok) / router henüz include edilmedi.

- [ ] **Step 3: Write the kalite schemas**

`backend/app/modules/kalite/schemas.py`:
```python
"""Kalite modülü Pydantic DTO'ları.

İstek ölçümleri ``Decimal``; cevap ölçümleri ``float`` (sınırda ``float(...)``). Uygunsuzluk
ve CAPA aksiyon DTO'ları sonraki task'ta eklenir.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class KaliteKontrolOlusturDTO(BaseModel):
    makine_id: int | None = None
    is_emri_id: int | None = None
    kontrol_turu: str = Field(default="uretim", max_length=20)
    sonuc: str = Field(min_length=1, max_length=20)
    olculen_deger: Decimal | None = None
    alt_limit: Decimal | None = None
    ust_limit: Decimal | None = None
    numune_adedi: int = Field(default=0, ge=0)
    uygunsuz_adet: int = Field(default=0, ge=0)
    aciklama: str = Field(default="", max_length=1000)
    zaman: datetime | None = None


class KaliteKontrolCevapDTO(BaseModel):
    id: int
    kod: str
    makine_id: int | None = None
    is_emri_id: int | None = None
    kontrol_turu: str
    sonuc: str
    olculen_deger: float | None = None
    alt_limit: float | None = None
    ust_limit: float | None = None
    numune_adedi: int
    uygunsuz_adet: int
    aciklama: str
    kontrol_eden_kullanici_id: int | None = None
    zaman: datetime
```

- [ ] **Step 4: Write the kalite service (oto kod)**

`backend/app/modules/kalite/service.py`:
```python
"""Kalite iş kuralları — oto kod üretimi + CAPA durum geçişi (durum geçişi Task 4'te eklenir)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime


def kalite_kontrol_gecici_kod() -> str:
    return f"GECICI-{uuid.uuid4().hex}"


def kalite_kontrol_kalici_kod(kontrol_id: int) -> str:
    """İnsan-okur kalite kontrol numarası: ``KK-{yıl}-{id:06d}``."""
    return f"KK-{datetime.now(UTC).year}-{kontrol_id:06d}"


def uygunsuzluk_gecici_kod() -> str:
    return f"GECICI-{uuid.uuid4().hex}"


def uygunsuzluk_kalici_kod(uygunsuzluk_id: int) -> str:
    """İnsan-okur uygunsuzluk numarası: ``UY-{yıl}-{id:06d}``."""
    return f"UY-{datetime.now(UTC).year}-{uygunsuzluk_id:06d}"
```

- [ ] **Step 5: Write the kalite repository**

`backend/app/modules/kalite/repository.py`:
```python
"""Kalite veri erişimi (repository). Sorgular şema adı yazmaz; ``search_path`` çözer.

Uygunsuzluk/aksiyon sorguları sonraki task'ta eklenir.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sorgu import siralama_uygula
from app.modules.kalite.models import KaliteKontrol

_KONTROL_SIRALAMA = {
    "id": KaliteKontrol.id,
    "kod": KaliteKontrol.kod,
    "sonuc": KaliteKontrol.sonuc,
    "zaman": KaliteKontrol.zaman,
    "olusturma_tarihi": KaliteKontrol.olusturma_tarihi,
}


async def kontrol_ekle(db: AsyncSession, kontrol: KaliteKontrol) -> KaliteKontrol:
    db.add(kontrol)
    await db.flush()
    return kontrol


async def kontrol_getir(db: AsyncSession, kontrol_id: int) -> KaliteKontrol | None:
    return await db.get(KaliteKontrol, kontrol_id)


async def kontrol_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    makine_id: int | None = None,
    sonuc: str | None = None,
    arama: str | None = None,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[KaliteKontrol], int]:
    filtreler: list[Any] = []
    if makine_id is not None:
        filtreler.append(KaliteKontrol.makine_id == makine_id)
    if sonuc is not None:
        filtreler.append(KaliteKontrol.sonuc == sonuc)
    if arama:
        filtreler.append(KaliteKontrol.kod.ilike(f"%{arama}%"))
    if baslangic is not None:
        filtreler.append(KaliteKontrol.zaman >= baslangic)
    if bitis is not None:
        filtreler.append(KaliteKontrol.zaman <= bitis)

    kosul = select(KaliteKontrol)
    sayim = select(func.count()).select_from(KaliteKontrol)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul, siralama=siralama, yon=yon, izinli=_KONTROL_SIRALAMA,
        varsayilan=KaliteKontrol.id, varsayilan_yon="desc",
    )
    sonuc_ = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc_.scalars().all(), int(toplam)
```

- [ ] **Step 6: Write the kalite router (kontrol uçları)**

`backend/app/modules/kalite/router.py`:
```python
"""Kalite uçları (``/api/v1``) — denetim + Tam CAPA.

Tüm uçlar tenant-kapsamlı + RBAC (``kalite:oku``/``kalite:yaz``); yazma işlemleri audit'lenir.
Uygunsuzluk + CAPA uçları sonraki task'ta eklenir.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, tenant_cozumle
from app.core.exceptions import DogrulamaHatasi, KaynakBulunamadi
from app.core.gercekzaman import yayinla
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.kalite import repository, service
from app.modules.kalite.birimler import KONTROL_SONUCLARI, KONTROL_TURLERI
from app.modules.kalite.models import KaliteKontrol
from app.modules.kalite.schemas import KaliteKontrolCevapDTO, KaliteKontrolOlusturDTO

router = APIRouter(tags=["Kalite"])


def _kontrol_cevap(k: KaliteKontrol) -> dict[str, Any]:
    return KaliteKontrolCevapDTO(
        id=k.id,
        kod=k.kod,
        makine_id=k.makine_id,
        is_emri_id=k.is_emri_id,
        kontrol_turu=k.kontrol_turu,
        sonuc=k.sonuc,
        olculen_deger=float(k.olculen_deger) if k.olculen_deger is not None else None,
        alt_limit=float(k.alt_limit) if k.alt_limit is not None else None,
        ust_limit=float(k.ust_limit) if k.ust_limit is not None else None,
        numune_adedi=k.numune_adedi,
        uygunsuz_adet=k.uygunsuz_adet,
        aciklama=k.aciklama,
        kontrol_eden_kullanici_id=k.kontrol_eden_kullanici_id,
        zaman=k.zaman,
    ).model_dump()


def _kontrol_dogrula(govde: KaliteKontrolOlusturDTO) -> None:
    if govde.sonuc not in KONTROL_SONUCLARI:
        raise DogrulamaHatasi(
            "Geçersiz sonuç",
            detaylar=[{"alan": "sonuc", "mesaj": f"Geçerli: {', '.join(sorted(KONTROL_SONUCLARI))}"}],
        )
    if govde.kontrol_turu not in KONTROL_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz kontrol türü",
            detaylar=[{"alan": "kontrol_turu", "mesaj": f"Geçerli: {', '.join(sorted(KONTROL_TURLERI))}"}],
        )
    if govde.uygunsuz_adet > govde.numune_adedi:
        raise DogrulamaHatasi(
            "Uygunsuz adet numune adedini aşamaz",
            detaylar=[{"alan": "uygunsuz_adet", "mesaj": f"<= numune_adedi ({govde.numune_adedi})"}],
        )
    if (
        govde.alt_limit is not None
        and govde.ust_limit is not None
        and govde.alt_limit > govde.ust_limit
    ):
        raise DogrulamaHatasi(
            "alt_limit ust_limit'ten büyük olamaz",
            detaylar=[{"alan": "alt_limit", "mesaj": "<= ust_limit"}],
        )


@router.post(
    "/kalite-kontrolleri",
    response_model=Zarf[KaliteKontrolCevapDTO],
    status_code=201,
    summary="Kalite kontrol kaydı oluştur",
)
async def kontrol_olustur(
    govde: KaliteKontrolOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    _kontrol_dogrula(govde)
    kontrol = KaliteKontrol(
        kod=service.kalite_kontrol_gecici_kod(),
        makine_id=govde.makine_id,
        is_emri_id=govde.is_emri_id,
        kontrol_turu=govde.kontrol_turu,
        sonuc=govde.sonuc,
        olculen_deger=govde.olculen_deger,
        alt_limit=govde.alt_limit,
        ust_limit=govde.ust_limit,
        numune_adedi=govde.numune_adedi,
        uygunsuz_adet=govde.uygunsuz_adet,
        aciklama=govde.aciklama,
        kontrol_eden_kullanici_id=kullanici.id,
        **({"zaman": govde.zaman} if govde.zaman is not None else {}),
    )
    await repository.kontrol_ekle(db, kontrol)
    kontrol.kod = service.kalite_kontrol_kalici_kod(kontrol.id)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="kalite_kontrol", kaynak_id=str(kontrol.id), kullanici=kullanici
    )
    await yayinla(tenant.slug, {"tur": "kalite.kontrol", "id": kontrol.id})
    return basari(_kontrol_cevap(kontrol), mesaj="Kalite kontrol oluşturuldu")


@router.get(
    "/kalite-kontrolleri",
    response_model=Zarf[list[KaliteKontrolCevapDTO]],
    summary="Kalite kontrolleri listele",
)
async def kontrol_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    makine_id: int | None = None,
    sonuc: str | None = None,
    arama: str | None = None,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.kontrol_listele(
        db, sayfa=sayfa, adet=adet, makine_id=makine_id, sonuc=sonuc, arama=arama,
        baslangic=baslangic, bitis=bitis, siralama=siralama, yon=yon,
    )
    return sayfali([_kontrol_cevap(k) for k in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/kalite-kontrolleri/{kontrol_id}",
    response_model=Zarf[KaliteKontrolCevapDTO],
    summary="Kalite kontrol detayı",
)
async def kontrol_detay(
    kontrol_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    kontrol = await repository.kontrol_getir(db, kontrol_id)
    if kontrol is None:
        raise KaynakBulunamadi("Kalite kontrol bulunamadı")
    return basari(_kontrol_cevap(kontrol), mesaj="Kalite kontrol detayı")
```

- [ ] **Step 7: Include the kalite router**

`backend/app/api/router.py` — import + include ekle (stok satırlarının yanına):
```python
from app.modules.kalite.router import router as kalite_router
```
```python
api_router.include_router(kalite_router)
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_s10_kalite_kontrol.py -v`
Expected: PASS (6 passed)

- [ ] **Step 9: Lint + commit**

```bash
cd backend && ruff check app/modules/kalite tests/test_s10_kalite_kontrol.py app/api/router.py && ruff format --check app/modules/kalite && python -m mypy app/modules/kalite app/api/router.py
git add backend/app/modules/kalite/schemas.py backend/app/modules/kalite/repository.py backend/app/modules/kalite/service.py backend/app/modules/kalite/router.py backend/app/api/router.py backend/tests/test_s10_kalite_kontrol.py
git commit -m "feat(kalite): kalite kontrol dikey dilimi (oto kod + RBAC + izolasyon) (S10)"
```

---

## Task 4: Uygunsuzluk + CAPA (durum geçişi + düzeltici/önleyici aksiyonlar)

**Files:**
- Modify: `backend/app/modules/kalite/schemas.py` (uygunsuzluk + aksiyon DTO'ları ekle)
- Modify: `backend/app/modules/kalite/repository.py` (uygunsuzluk + aksiyon sorguları ekle)
- Modify: `backend/app/modules/kalite/service.py` (`capa_durum_gecisi` ekle)
- Modify: `backend/app/modules/kalite/router.py` (uygunsuzluk + CAPA uçları ekle)
- Test: `backend/tests/test_s10_capa.py`

**Interfaces:**
- Consumes: `Uygunsuzluk`, `CapaAksiyon` (Task 2); `durum` (Task 1); `olay_yayinla` (`app.core.olaylar`); Task 3 altyapısı.
- Produces:
  - DTO'lar: `UygunsuzlukOlusturDTO`, `UygunsuzlukGuncelleDTO`, `DurumGecisDTO`, `AksiyonOlusturDTO`, `AksiyonGuncelleDTO`, `AksiyonCevapDTO`, `UygunsuzlukCevapDTO`, `UygunsuzlukDetayDTO`
  - `service.capa_durum_gecisi(db, uygunsuzluk, *, hedef, kok_neden=None, dogrulama_notu=None) -> Uygunsuzluk`
  - Repository: `uygunsuzluk_ekle`, `uygunsuzluk_getir`, `uygunsuzluk_getir_kilitli`, `uygunsuzluk_getir_aksiyonlu`, `uygunsuzluk_listele`, `aksiyon_getir`
  - Uçlar: `POST/GET /uygunsuzluklar`, `GET/PATCH /uygunsuzluklar/{id}`, `PATCH /uygunsuzluklar/{id}/durum`, `POST /uygunsuzluklar/{id}/aksiyonlar`, `PATCH /uygunsuzluklar/{id}/aksiyonlar/{aksiyon_id}`

- [ ] **Step 1: Write the failing CAPA lifecycle test**

`backend/tests/test_s10_capa.py`:
```python
"""S10 entegrasyon: Tam CAPA yaşam döngüsü + aksiyonlar + RBAC + izolasyon."""

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


async def _uygunsuzluk(istemci: AsyncClient, h: dict[str, str], **ek: object) -> dict:
    govde = {"baslik": "Yüzey çizik", "onem": "yuksek", **ek}
    r = await istemci.post("/api/v1/uygunsuzluklar", json=govde, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def _durum(istemci: AsyncClient, h: dict[str, str], uid: int, hedef: str, **ek: object) -> None:
    r = await istemci.patch(
        f"/api/v1/uygunsuzluklar/{uid}/durum", json={"hedef": hedef, **ek}, headers=h
    )
    assert r.status_code == 200, r.text


async def test_capa_tam_yasam_dongusu(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _uygunsuzluk(kurulu_istemci, h)
    assert d["kod"].startswith("UY-")
    assert d["durum"] == "acik"
    uid = d["id"]

    await _durum(kurulu_istemci, h, uid, "kok_neden", kok_neden="Kalıp aşınması")
    await _durum(kurulu_istemci, h, uid, "aksiyon_plani")

    # düzeltici + önleyici aksiyon ekle
    for tur in ("duzeltici", "onleyici"):
        r = await kurulu_istemci.post(
            f"/api/v1/uygunsuzluklar/{uid}/aksiyonlar",
            json={"tur": tur, "aciklama": f"{tur} aksiyon"},
            headers=h,
        )
        assert r.status_code == 201, r.text

    await _durum(kurulu_istemci, h, uid, "uygulama")
    await _durum(kurulu_istemci, h, uid, "dogrulama")
    await _durum(kurulu_istemci, h, uid, "kapandi", dogrulama_notu="Etkin")

    r = await kurulu_istemci.get(f"/api/v1/uygunsuzluklar/{uid}", headers=h)
    body = r.json()["data"]
    assert body["durum"] == "kapandi"
    assert body["kok_neden"] == "Kalıp aşınması"
    assert body["kapanis_tarihi"] is not None
    assert len(body["aksiyonlar"]) == 2


async def test_capa_gecersiz_gecis_409(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _uygunsuzluk(kurulu_istemci, h)
    # acik → kapandi doğrudan yasak
    r = await kurulu_istemci.patch(
        f"/api/v1/uygunsuzluklar/{d['id']}/durum", json={"hedef": "kapandi"}, headers=h
    )
    assert r.status_code == 409, r.text


async def test_capa_gecersiz_hedef_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _uygunsuzluk(kurulu_istemci, h)
    r = await kurulu_istemci.patch(
        f"/api/v1/uygunsuzluklar/{d['id']}/durum", json={"hedef": "yok"}, headers=h
    )
    assert r.status_code == 422, r.text


async def test_dogrulamadan_uygulamaya_geri(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _uygunsuzluk(kurulu_istemci, h)
    uid = d["id"]
    for hedef in ("kok_neden", "aksiyon_plani", "uygulama", "dogrulama"):
        await _durum(kurulu_istemci, h, uid, hedef)
    # doğrulama başarısız → uygulamaya geri
    await _durum(kurulu_istemci, h, uid, "uygulama")
    r = await kurulu_istemci.get(f"/api/v1/uygunsuzluklar/{uid}", headers=h)
    assert r.json()["data"]["durum"] == "uygulama"


async def test_aksiyon_durum_guncelle(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _uygunsuzluk(kurulu_istemci, h)
    uid = d["id"]
    r = await kurulu_istemci.post(
        f"/api/v1/uygunsuzluklar/{uid}/aksiyonlar",
        json={"tur": "duzeltici", "aciklama": "Kalıbı değiştir"},
        headers=h,
    )
    aid = r.json()["data"]["aksiyonlar"][-1]["id"]
    r = await kurulu_istemci.patch(
        f"/api/v1/uygunsuzluklar/{uid}/aksiyonlar/{aid}",
        json={"durum": "tamamlandi"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    hedef = next(a for a in r.json()["data"]["aksiyonlar"] if a["id"] == aid)
    assert hedef["durum"] == "tamamlandi"
    assert hedef["tamamlanma_tarihi"] is not None


async def test_uygunsuzluk_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "izl-uy@alfa.test", "parola": "Izleyici123!", "roller": ["izleyici"]},
        headers=admin,
    )
    izl = _h(
        "alfa",
        await _giris(
            kurulu_istemci, {"slug": "alfa", "eposta": "izl-uy@alfa.test", "parola": "Izleyici123!"}
        ),
    )
    assert (await kurulu_istemci.get("/api/v1/uygunsuzluklar", headers=izl)).status_code == 200
    r = await kurulu_istemci.post(
        "/api/v1/uygunsuzluklar", json={"baslik": "X", "onem": "orta"}, headers=izl
    )
    assert r.status_code == 403, r.text


async def test_uygunsuzluk_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    ha = _h("alfa", await _giris(kurulu_istemci, ALFA))
    da = await _uygunsuzluk(kurulu_istemci, ha)
    hb = _h("beta", await _giris(kurulu_istemci, BETA))
    assert (
        await kurulu_istemci.get(f"/api/v1/uygunsuzluklar/{da['id']}", headers=hb)
    ).status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_s10_capa.py -v`
Expected: FAIL — `404` (uygunsuzluk uçları yok).

- [ ] **Step 3: Add uygunsuzluk + aksiyon schemas**

`backend/app/modules/kalite/schemas.py` — dosyanın sonuna ekle:
```python
class UygunsuzlukOlusturDTO(BaseModel):
    baslik: str = Field(min_length=1, max_length=200)
    aciklama: str = Field(default="", max_length=2000)
    onem: str = Field(default="orta", max_length=20)
    kaynak_kontrol_id: int | None = None
    makine_id: int | None = None
    sorumlu_kullanici_id: int | None = None


class UygunsuzlukGuncelleDTO(BaseModel):
    baslik: str | None = Field(default=None, min_length=1, max_length=200)
    aciklama: str | None = Field(default=None, max_length=2000)
    onem: str | None = Field(default=None, max_length=20)
    sorumlu_kullanici_id: int | None = None


class DurumGecisDTO(BaseModel):
    hedef: str = Field(min_length=1, max_length=20)
    kok_neden: str | None = Field(default=None, max_length=2000)
    dogrulama_notu: str | None = Field(default=None, max_length=2000)


class AksiyonOlusturDTO(BaseModel):
    tur: str = Field(min_length=1, max_length=20)
    aciklama: str = Field(min_length=1, max_length=1000)
    sorumlu_kullanici_id: int | None = None
    termin_tarihi: datetime | None = None


class AksiyonGuncelleDTO(BaseModel):
    durum: str | None = Field(default=None, max_length=20)
    aciklama: str | None = Field(default=None, min_length=1, max_length=1000)
    sorumlu_kullanici_id: int | None = None
    termin_tarihi: datetime | None = None


class AksiyonCevapDTO(BaseModel):
    id: int
    tur: str
    aciklama: str
    sorumlu_kullanici_id: int | None = None
    termin_tarihi: datetime | None = None
    durum: str
    tamamlanma_tarihi: datetime | None = None


class UygunsuzlukCevapDTO(BaseModel):
    id: int
    kod: str
    baslik: str
    aciklama: str
    kaynak_kontrol_id: int | None = None
    makine_id: int | None = None
    onem: str
    durum: str
    kok_neden: str
    acan_kullanici_id: int | None = None
    sorumlu_kullanici_id: int | None = None
    dogrulama_notu: str
    kapanis_tarihi: datetime | None = None
    olusturma_tarihi: datetime


class UygunsuzlukDetayDTO(UygunsuzlukCevapDTO):
    aksiyonlar: list[AksiyonCevapDTO] = Field(default_factory=list)
```

- [ ] **Step 4: Add capa_durum_gecisi to service**

`backend/app/modules/kalite/service.py` — importları ve fonksiyonu ekle:
```python
from datetime import UTC, datetime  # (mevcut import satırını bununla değiştir)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CakismaHatasi, DogrulamaHatasi
from app.modules.kalite import durum
from app.modules.kalite.models import Uygunsuzluk
```
```python
async def capa_durum_gecisi(
    db: AsyncSession,
    uygunsuzluk: Uygunsuzluk,
    *,
    hedef: str,
    kok_neden: str | None = None,
    dogrulama_notu: str | None = None,
) -> Uygunsuzluk:
    """Uygunsuzluğu ``hedef`` duruma geçirir (saf makine + alan yan etkileri).

    - Tanımsız hedef → 422; makineye aykırı geçiş → 409.
    - ``kok_neden`` durumuna geçişte kök-neden yazılabilir.
    - ``kapandi``: kapanış tarihi + doğrulama notu.
    """
    if hedef not in durum.DURUMLAR:
        raise DogrulamaHatasi(
            "Geçersiz durum",
            detaylar=[{"alan": "hedef", "mesaj": f"Geçerli: {', '.join(sorted(durum.DURUMLAR))}"}],
        )
    if not durum.gecis_gecerli_mi(uygunsuzluk.durum, hedef):
        raise CakismaHatasi(f"Geçersiz durum geçişi: {uygunsuzluk.durum} → {hedef}")

    uygunsuzluk.durum = hedef
    if hedef == "kok_neden" and kok_neden is not None:
        uygunsuzluk.kok_neden = kok_neden
    if hedef == "kapandi":
        uygunsuzluk.kapanis_tarihi = datetime.now(UTC)
        if dogrulama_notu is not None:
            uygunsuzluk.dogrulama_notu = dogrulama_notu
    await db.flush()
    return uygunsuzluk
```

- [ ] **Step 5: Add uygunsuzluk + aksiyon repository queries**

`backend/app/modules/kalite/repository.py` — importlara `or_`, `selectinload`, modelleri ekle ve fonksiyonları ekle:
```python
from sqlalchemy import func, or_, select  # (mevcut import satırını bununla değiştir)
from sqlalchemy.orm import selectinload

from app.modules.kalite.models import CapaAksiyon, KaliteKontrol, Uygunsuzluk  # (mevcut satırı değiştir)
```
```python
_UYGUNSUZLUK_SIRALAMA = {
    "id": Uygunsuzluk.id,
    "kod": Uygunsuzluk.kod,
    "baslik": Uygunsuzluk.baslik,
    "onem": Uygunsuzluk.onem,
    "durum": Uygunsuzluk.durum,
    "olusturma_tarihi": Uygunsuzluk.olusturma_tarihi,
}


async def uygunsuzluk_ekle(db: AsyncSession, u: Uygunsuzluk) -> Uygunsuzluk:
    db.add(u)
    await db.flush()
    return u


async def uygunsuzluk_getir(db: AsyncSession, uid: int) -> Uygunsuzluk | None:
    return await db.get(Uygunsuzluk, uid)


async def uygunsuzluk_getir_kilitli(db: AsyncSession, uid: int) -> Uygunsuzluk | None:
    sonuc = await db.execute(
        select(Uygunsuzluk).where(Uygunsuzluk.id == uid).with_for_update()
    )
    return sonuc.scalar_one_or_none()


async def uygunsuzluk_getir_aksiyonlu(db: AsyncSession, uid: int) -> Uygunsuzluk | None:
    sonuc = await db.execute(
        select(Uygunsuzluk)
        .where(Uygunsuzluk.id == uid)
        .options(selectinload(Uygunsuzluk.aksiyonlar))
    )
    return sonuc.scalar_one_or_none()


async def aksiyon_getir(db: AsyncSession, aksiyon_id: int) -> CapaAksiyon | None:
    return await db.get(CapaAksiyon, aksiyon_id)


async def uygunsuzluk_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    durum: str | None = None,
    onem: str | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[Uygunsuzluk], int]:
    filtreler: list[Any] = []
    if durum is not None:
        filtreler.append(Uygunsuzluk.durum == durum)
    if onem is not None:
        filtreler.append(Uygunsuzluk.onem == onem)
    if arama:
        kalip = f"%{arama}%"
        filtreler.append(or_(Uygunsuzluk.kod.ilike(kalip), Uygunsuzluk.baslik.ilike(kalip)))

    kosul = select(Uygunsuzluk)
    sayim = select(func.count()).select_from(Uygunsuzluk)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul, siralama=siralama, yon=yon, izinli=_UYGUNSUZLUK_SIRALAMA,
        varsayilan=Uygunsuzluk.id, varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)
```
> Not: `uygunsuzluk_listele` parametresi `durum` yerel değişken adı modül-seviyesi `durum` import'unu **gölgelemez** çünkü repository `durum` modülünü import etmez (yalnız router/service eder). Repository'de çakışma yok.

- [ ] **Step 6: Add uygunsuzluk + CAPA endpoints to router**

`backend/app/modules/kalite/router.py` — importlara ekle:
```python
from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi  # (mevcut satırı değiştir)
from app.core.olaylar import olay_yayinla
from app.modules.kalite.birimler import (  # (mevcut satırı değiştir)
    CAPA_AKSIYON_DURUMLARI,
    CAPA_AKSIYON_TURLERI,
    KONTROL_SONUCLARI,
    KONTROL_TURLERI,
    UYGUNSUZLUK_ONEMLERI,
)
from app.modules.kalite.models import CapaAksiyon, KaliteKontrol, Uygunsuzluk  # (mevcut satırı değiştir)
from app.modules.kalite.schemas import (  # (mevcut satırı genişlet)
    AksiyonCevapDTO,
    AksiyonGuncelleDTO,
    AksiyonOlusturDTO,
    DurumGecisDTO,
    KaliteKontrolCevapDTO,
    KaliteKontrolOlusturDTO,
    UygunsuzlukCevapDTO,
    UygunsuzlukDetayDTO,
    UygunsuzlukGuncelleDTO,
    UygunsuzlukOlusturDTO,
)
```
Router gövdesinin sonuna ekle:
```python
def _aksiyon_cevap(a: CapaAksiyon) -> dict[str, Any]:
    return AksiyonCevapDTO(
        id=a.id,
        tur=a.tur,
        aciklama=a.aciklama,
        sorumlu_kullanici_id=a.sorumlu_kullanici_id,
        termin_tarihi=a.termin_tarihi,
        durum=a.durum,
        tamamlanma_tarihi=a.tamamlanma_tarihi,
    ).model_dump()


def _uygunsuzluk_cevap(u: Uygunsuzluk) -> dict[str, Any]:
    return UygunsuzlukCevapDTO(
        id=u.id, kod=u.kod, baslik=u.baslik, aciklama=u.aciklama,
        kaynak_kontrol_id=u.kaynak_kontrol_id, makine_id=u.makine_id, onem=u.onem,
        durum=u.durum, kok_neden=u.kok_neden, acan_kullanici_id=u.acan_kullanici_id,
        sorumlu_kullanici_id=u.sorumlu_kullanici_id, dogrulama_notu=u.dogrulama_notu,
        kapanis_tarihi=u.kapanis_tarihi, olusturma_tarihi=u.olusturma_tarihi,
    ).model_dump()


def _uygunsuzluk_detay_cevap(u: Uygunsuzluk) -> dict[str, Any]:
    return UygunsuzlukDetayDTO(
        id=u.id, kod=u.kod, baslik=u.baslik, aciklama=u.aciklama,
        kaynak_kontrol_id=u.kaynak_kontrol_id, makine_id=u.makine_id, onem=u.onem,
        durum=u.durum, kok_neden=u.kok_neden, acan_kullanici_id=u.acan_kullanici_id,
        sorumlu_kullanici_id=u.sorumlu_kullanici_id, dogrulama_notu=u.dogrulama_notu,
        kapanis_tarihi=u.kapanis_tarihi, olusturma_tarihi=u.olusturma_tarihi,
        aksiyonlar=[AksiyonCevapDTO(**_aksiyon_cevap(a)) for a in u.aksiyonlar],
    ).model_dump()


def _onem_dogrula(onem: str) -> None:
    if onem not in UYGUNSUZLUK_ONEMLERI:
        raise DogrulamaHatasi(
            "Geçersiz önem",
            detaylar=[{"alan": "onem", "mesaj": f"Geçerli: {', '.join(sorted(UYGUNSUZLUK_ONEMLERI))}"}],
        )


@router.post(
    "/uygunsuzluklar",
    response_model=Zarf[UygunsuzlukDetayDTO],
    status_code=201,
    summary="Uygunsuzluk (CAPA) oluştur",
)
async def uygunsuzluk_olustur(
    govde: UygunsuzlukOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    _onem_dogrula(govde.onem)
    if govde.kaynak_kontrol_id is not None and await repository.kontrol_getir(db, govde.kaynak_kontrol_id) is None:
        raise KaynakBulunamadi("Kaynak kalite kontrol bulunamadı")
    u = Uygunsuzluk(
        kod=service.uygunsuzluk_gecici_kod(),
        baslik=govde.baslik,
        aciklama=govde.aciklama,
        onem=govde.onem,
        kaynak_kontrol_id=govde.kaynak_kontrol_id,
        makine_id=govde.makine_id,
        sorumlu_kullanici_id=govde.sorumlu_kullanici_id,
        acan_kullanici_id=kullanici.id,
    )
    await repository.uygunsuzluk_ekle(db, u)
    u.kod = service.uygunsuzluk_kalici_kod(u.id)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="uygunsuzluk", kaynak_id=str(u.id), kullanici=kullanici
    )
    await olay_yayinla(
        db,
        olay_turu="kalite.uygunsuzluk",
        govde={"uygunsuzluk_id": u.id, "kod": u.kod, "baslik": u.baslik, "onem": u.onem, "durum": u.durum},
    )
    await yayinla(tenant.slug, {"tur": "kalite.uygunsuzluk", "id": u.id, "durum": u.durum})
    tam = await repository.uygunsuzluk_getir_aksiyonlu(db, u.id)
    assert tam is not None
    return basari(_uygunsuzluk_detay_cevap(tam), mesaj="Uygunsuzluk oluşturuldu")


@router.get(
    "/uygunsuzluklar",
    response_model=Zarf[list[UygunsuzlukCevapDTO]],
    summary="Uygunsuzlukları listele",
)
async def uygunsuzluk_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    durum: str | None = None,
    onem: str | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.uygunsuzluk_listele(
        db, sayfa=sayfa, adet=adet, durum=durum, onem=onem, arama=arama, siralama=siralama, yon=yon,
    )
    return sayfali([_uygunsuzluk_cevap(u) for u in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/uygunsuzluklar/{uygunsuzluk_id}",
    response_model=Zarf[UygunsuzlukDetayDTO],
    summary="Uygunsuzluk detayı (aksiyonlarla)",
)
async def uygunsuzluk_detay(
    uygunsuzluk_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    u = await repository.uygunsuzluk_getir_aksiyonlu(db, uygunsuzluk_id)
    if u is None:
        raise KaynakBulunamadi("Uygunsuzluk bulunamadı")
    return basari(_uygunsuzluk_detay_cevap(u), mesaj="Uygunsuzluk detayı")


@router.patch(
    "/uygunsuzluklar/{uygunsuzluk_id}",
    response_model=Zarf[UygunsuzlukDetayDTO],
    summary="Uygunsuzluk düzenle (yalnız aktif durumlar)",
)
async def uygunsuzluk_guncelle(
    uygunsuzluk_id: int,
    govde: UygunsuzlukGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    u = await repository.uygunsuzluk_getir(db, uygunsuzluk_id)
    if u is None:
        raise KaynakBulunamadi("Uygunsuzluk bulunamadı")
    if u.durum in durum.TERMINAL_DURUMLAR:
        raise CakismaHatasi("Terminal durumda uygunsuzluk düzenlenemez")
    if govde.onem is not None:
        _onem_dogrula(govde.onem)
        u.onem = govde.onem
    for alan in ("baslik", "aciklama", "sorumlu_kullanici_id"):
        deger = getattr(govde, alan)
        if deger is not None:
            setattr(u, alan, deger)
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="uygunsuzluk", kaynak_id=str(u.id), kullanici=kullanici
    )
    tam = await repository.uygunsuzluk_getir_aksiyonlu(db, u.id)
    assert tam is not None
    return basari(_uygunsuzluk_detay_cevap(tam), mesaj="Uygunsuzluk güncellendi")


@router.patch(
    "/uygunsuzluklar/{uygunsuzluk_id}/durum",
    response_model=Zarf[UygunsuzlukCevapDTO],
    summary="CAPA durum geçişi",
)
async def uygunsuzluk_durum(
    uygunsuzluk_id: int,
    govde: DurumGecisDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    u = await repository.uygunsuzluk_getir_kilitli(db, uygunsuzluk_id)
    if u is None:
        raise KaynakBulunamadi("Uygunsuzluk bulunamadı")
    await service.capa_durum_gecisi(
        db, u, hedef=govde.hedef, kok_neden=govde.kok_neden, dogrulama_notu=govde.dogrulama_notu
    )
    await denetim_yaz(
        db, eylem="durum_guncelle", kaynak="uygunsuzluk", kaynak_id=str(u.id),
        kullanici=kullanici, detay={"durum": u.durum},
    )
    await yayinla(tenant.slug, {"tur": "kalite.uygunsuzluk", "id": u.id, "durum": u.durum})
    return basari(_uygunsuzluk_cevap(u), mesaj="Durum güncellendi")


@router.post(
    "/uygunsuzluklar/{uygunsuzluk_id}/aksiyonlar",
    response_model=Zarf[UygunsuzlukDetayDTO],
    status_code=201,
    summary="CAPA aksiyonu ekle (düzeltici/önleyici)",
)
async def aksiyon_ekle(
    uygunsuzluk_id: int,
    govde: AksiyonOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    u = await repository.uygunsuzluk_getir(db, uygunsuzluk_id)
    if u is None:
        raise KaynakBulunamadi("Uygunsuzluk bulunamadı")
    if govde.tur not in CAPA_AKSIYON_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz aksiyon türü",
            detaylar=[{"alan": "tur", "mesaj": f"Geçerli: {', '.join(sorted(CAPA_AKSIYON_TURLERI))}"}],
        )
    aksiyon = CapaAksiyon(
        uygunsuzluk_id=u.id,
        tur=govde.tur,
        aciklama=govde.aciklama,
        sorumlu_kullanici_id=govde.sorumlu_kullanici_id,
        termin_tarihi=govde.termin_tarihi,
    )
    db.add(aksiyon)
    await db.flush()
    await denetim_yaz(
        db, eylem="aksiyon_ekle", kaynak="uygunsuzluk", kaynak_id=str(u.id),
        kullanici=kullanici, detay={"aksiyon_id": aksiyon.id, "tur": aksiyon.tur},
    )
    tam = await repository.uygunsuzluk_getir_aksiyonlu(db, u.id)
    assert tam is not None
    return basari(_uygunsuzluk_detay_cevap(tam), mesaj="Aksiyon eklendi")


@router.patch(
    "/uygunsuzluklar/{uygunsuzluk_id}/aksiyonlar/{aksiyon_id}",
    response_model=Zarf[UygunsuzlukDetayDTO],
    summary="CAPA aksiyonu güncelle",
)
async def aksiyon_guncelle(
    uygunsuzluk_id: int,
    aksiyon_id: int,
    govde: AksiyonGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    aksiyon = await repository.aksiyon_getir(db, aksiyon_id)
    if aksiyon is None or aksiyon.uygunsuzluk_id != uygunsuzluk_id:
        raise KaynakBulunamadi("Aksiyon bulunamadı")
    if govde.durum is not None:
        if govde.durum not in CAPA_AKSIYON_DURUMLARI:
            raise DogrulamaHatasi(
                "Geçersiz aksiyon durumu",
                detaylar=[{"alan": "durum", "mesaj": f"Geçerli: {', '.join(sorted(CAPA_AKSIYON_DURUMLARI))}"}],
            )
        aksiyon.durum = govde.durum
        aksiyon.tamamlanma_tarihi = datetime.now(UTC) if govde.durum == "tamamlandi" else None
    for alan in ("aciklama", "sorumlu_kullanici_id", "termin_tarihi"):
        deger = getattr(govde, alan)
        if deger is not None:
            setattr(aksiyon, alan, deger)
    await db.flush()
    await denetim_yaz(
        db, eylem="aksiyon_guncelle", kaynak="uygunsuzluk", kaynak_id=str(uygunsuzluk_id),
        kullanici=kullanici, detay={"aksiyon_id": aksiyon.id},
    )
    tam = await repository.uygunsuzluk_getir_aksiyonlu(db, uygunsuzluk_id)
    assert tam is not None
    return basari(_uygunsuzluk_detay_cevap(tam), mesaj="Aksiyon güncellendi")
```
> **`datetime` + `durum` import notu:** router zaten `from datetime import datetime` (Task 3) ve `from app.modules.kalite import repository, service` içeriyor. Ek olarak modül-seviyesinde `from app.modules.kalite import durum` import satırı ekle (uygunsuzluk_guncelle `durum.TERMINAL_DURUMLAR` kullanır). `UTC` için `from datetime import UTC, datetime` yap.

- [ ] **Step 7: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_s10_capa.py -v`
Expected: PASS (7 passed)

- [ ] **Step 8: Lint + commit**

```bash
cd backend && ruff check app/modules/kalite tests/test_s10_capa.py && ruff format --check app/modules/kalite && python -m mypy app/modules/kalite
git add backend/app/modules/kalite backend/tests/test_s10_capa.py
git commit -m "feat(kalite): uygunsuzluk + Tam CAPA (durum geçişi + düzeltici/önleyici aksiyonlar) (S10)"
```

---

## Task 5: Enerji dikey dilimi (ölçüm + continuous aggregate trend)

**Files:**
- Create: `backend/app/modules/enerji/schemas.py`
- Create: `backend/app/modules/enerji/repository.py`
- Create: `backend/app/modules/enerji/service.py`
- Create: `backend/app/modules/enerji/router.py`
- Modify: `backend/app/api/router.py` (enerji router'ını include et)
- Test: `backend/tests/test_s10_enerji.py`

**Interfaces:**
- Consumes: `EnerjiTuketim` (Task 2); `ENERJI_TURLERI` (Task 1); `tenant_cozumle`, `izin_gerekli`, `denetim_yaz`, `basari`/`sayfali`/`Zarf`, `siralama_uygula`, `yayinla`, `Tenant`.
- Produces:
  - DTO'lar: `EnerjiOlcumOlusturDTO`, `EnerjiOlcumCevapDTO`, `EnerjiTrendNoktaDTO`
  - `service.olcum_yaz(db, *, makine_id, enerji_turu, tuketim, birim, zaman) -> EnerjiTuketim` (audit + realtime router katmanında)
  - Repository: `olcum_listele`, `trend` (CAGG'den; `aralik` ∈ {`saat`,`gun`})
  - `enerji` router (mutlak yollar `/enerji-tuketimleri`, `/enerji-tuketimleri/trend`)

- [ ] **Step 1: Write the failing integration test**

`backend/tests/test_s10_enerji.py`:
```python
"""S10 entegrasyon: enerji ölçüm yaz/listele + CAGG trend + RBAC + izolasyon."""

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


async def _olcum(istemci: AsyncClient, h: dict[str, str], **ek: object) -> dict:
    govde = {"enerji_turu": "elektrik", "tuketim": 10, "birim": "kWh", **ek}
    r = await istemci.post("/api/v1/enerji-tuketimleri", json=govde, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_olcum_yaz_listele(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await _olcum(kurulu_istemci, h, tuketim=12.5)
    r = await kurulu_istemci.get("/api/v1/enerji-tuketimleri?enerji_turu=elektrik", headers=h)
    assert r.status_code == 200, r.text
    assert any(x["tuketim"] == 12.5 for x in r.json()["data"])


async def test_olcum_gecersiz_tur_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/enerji-tuketimleri",
        json={"enerji_turu": "plazma", "tuketim": 5, "birim": "kWh"},
        headers=h,
    )
    assert r.status_code == 422, r.text


async def test_olcum_negatif_tuketim_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/enerji-tuketimleri",
        json={"enerji_turu": "elektrik", "tuketim": -3, "birim": "kWh"},
        headers=h,
    )
    assert r.status_code == 422, r.text


async def test_trend_saatlik_toplar(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    # Aynı saat kovasında iki ölçüm → trend tek noktada toplam 30 (real-time aggregation).
    await _olcum(kurulu_istemci, h, tuketim=10, zaman="2026-07-01T08:05:00Z")
    await _olcum(kurulu_istemci, h, tuketim=20, zaman="2026-07-01T08:40:00Z")
    r = await kurulu_istemci.get(
        "/api/v1/enerji-tuketimleri/trend?enerji_turu=elektrik&aralik=saat"
        "&baslangic=2026-07-01T00:00:00Z&bitis=2026-07-02T00:00:00Z",
        headers=h,
    )
    assert r.status_code == 200, r.text
    noktalar = r.json()["data"]
    toplam = sum(n["toplam"] for n in noktalar)
    assert toplam == 30.0
    # Bir saatlik kova → tek nokta.
    assert len(noktalar) == 1


async def test_trend_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "izl-en@alfa.test", "parola": "Izleyici123!", "roller": ["izleyici"]},
        headers=admin,
    )
    izl = _h(
        "alfa",
        await _giris(
            kurulu_istemci, {"slug": "alfa", "eposta": "izl-en@alfa.test", "parola": "Izleyici123!"}
        ),
    )
    # enerji:oku var → trend 200
    assert (
        await kurulu_istemci.get("/api/v1/enerji-tuketimleri/trend", headers=izl)
    ).status_code == 200
    # enerji:yaz yok → yaz 403
    r = await kurulu_istemci.post(
        "/api/v1/enerji-tuketimleri",
        json={"enerji_turu": "elektrik", "tuketim": 1, "birim": "kWh"},
        headers=izl,
    )
    assert r.status_code == 403, r.text


async def test_enerji_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    ha = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await _olcum(kurulu_istemci, ha, tuketim=99, zaman="2026-07-01T08:05:00Z")
    hb = _h("beta", await _giris(kurulu_istemci, BETA))
    r = await kurulu_istemci.get(
        "/api/v1/enerji-tuketimleri/trend?aralik=saat"
        "&baslangic=2026-07-01T00:00:00Z&bitis=2026-07-02T00:00:00Z",
        headers=hb,
    )
    assert r.status_code == 200, r.text
    assert sum(n["toplam"] for n in r.json()["data"]) == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_s10_enerji.py -v`
Expected: FAIL — `404` (enerji uçları yok).

- [ ] **Step 3: Write the enerji schemas**

`backend/app/modules/enerji/schemas.py`:
```python
"""Enerji modülü Pydantic DTO'ları.

İstek tüketimi ``Decimal`` (`gt=0`); cevap tüketimi ``float``. Trend noktası CAGG toplamı.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class EnerjiOlcumOlusturDTO(BaseModel):
    makine_id: int | None = None
    enerji_turu: str = Field(min_length=1, max_length=20)
    tuketim: Decimal = Field(gt=0)
    birim: str = Field(min_length=1, max_length=20)
    zaman: datetime | None = None


class EnerjiOlcumCevapDTO(BaseModel):
    id: int
    makine_id: int | None = None
    enerji_turu: str
    tuketim: float
    birim: str
    zaman: datetime


class EnerjiTrendNoktaDTO(BaseModel):
    zaman: datetime
    toplam: float
    adet: int
```

- [ ] **Step 4: Write the enerji service**

`backend/app/modules/enerji/service.py`:
```python
"""Enerji iş kuralları — ölçüm yazımı (append-only)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.enerji.models import EnerjiTuketim


async def olcum_yaz(
    db: AsyncSession,
    *,
    makine_id: int | None,
    enerji_turu: str,
    tuketim: Decimal,
    birim: str,
    zaman: datetime | None,
) -> EnerjiTuketim:
    """Enerji ölçümünü hypertable'a yazar (append-only)."""
    olcum = EnerjiTuketim(
        zaman=zaman or datetime.now(UTC),
        makine_id=makine_id,
        enerji_turu=enerji_turu,
        tuketim=tuketim,
        birim=birim,
    )
    db.add(olcum)
    await db.flush()
    return olcum
```

- [ ] **Step 5: Write the enerji repository (liste + CAGG trend)**

`backend/app/modules/enerji/repository.py`:
```python
"""Enerji veri erişimi (repository) — ham liste + continuous aggregate trend sorgusu.

Trend, ``enerji_tuketim_saatlik`` CAGG'inden okur. Real-time aggregation açık
(``materialized_only = false``) → materialize edilmemiş son veri de dahil olur.
``aralik`` beyaz-liste (``saat``/``gun``) → SQL enjeksiyonu yok; ``gun`` CAGG üstünde
``time_bucket('1 day', kova)`` ile toplulaştırır.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sorgu import siralama_uygula
from app.modules.enerji.models import EnerjiTuketim

_OLCUM_SIRALAMA = {
    "id": EnerjiTuketim.id,
    "zaman": EnerjiTuketim.zaman,
    "tuketim": EnerjiTuketim.tuketim,
    "enerji_turu": EnerjiTuketim.enerji_turu,
}


async def olcum_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    makine_id: int | None = None,
    enerji_turu: str | None = None,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[EnerjiTuketim], int]:
    filtreler: list[Any] = []
    if makine_id is not None:
        filtreler.append(EnerjiTuketim.makine_id == makine_id)
    if enerji_turu is not None:
        filtreler.append(EnerjiTuketim.enerji_turu == enerji_turu)
    if baslangic is not None:
        filtreler.append(EnerjiTuketim.zaman >= baslangic)
    if bitis is not None:
        filtreler.append(EnerjiTuketim.zaman <= bitis)

    kosul = select(EnerjiTuketim)
    sayim = select(func.count()).select_from(EnerjiTuketim)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul, siralama=siralama, yon=yon, izinli=_OLCUM_SIRALAMA,
        varsayilan=EnerjiTuketim.zaman, varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)


async def trend(
    db: AsyncSession,
    *,
    makine_id: int | None = None,
    enerji_turu: str | None = None,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    aralik: str = "saat",
) -> list[dict[str, Any]]:
    # aralik beyaz-liste (server-side) → f-string güvenli.
    zaman_ifade = "time_bucket(INTERVAL '1 day', kova)" if aralik == "gun" else "kova"
    sql = text(
        f"""
        SELECT {zaman_ifade} AS zaman,
               sum(toplam_tuketim) AS toplam,
               sum(olcum_adedi) AS adet
        FROM enerji_tuketim_saatlik
        WHERE (:makine_id IS NULL OR makine_id = :makine_id)
          AND (:enerji_turu IS NULL OR enerji_turu = :enerji_turu)
          AND (:baslangic IS NULL OR kova >= :baslangic)
          AND (:bitis IS NULL OR kova < :bitis)
        GROUP BY 1
        ORDER BY 1
        """
    )
    sonuc = await db.execute(
        sql,
        {
            "makine_id": makine_id,
            "enerji_turu": enerji_turu,
            "baslangic": baslangic,
            "bitis": bitis,
        },
    )
    return [
        {"zaman": r.zaman, "toplam": float(r.toplam or 0), "adet": int(r.adet or 0)}
        for r in sonuc
    ]
```

- [ ] **Step 6: Write the enerji router**

`backend/app/modules/enerji/router.py`:
```python
"""Enerji uçları (``/api/v1``) — tüketim ölçümü + continuous aggregate trend.

Tenant-kapsamlı + RBAC (``enerji:oku``/``enerji:yaz``); yazma audit'lenir.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, tenant_cozumle
from app.core.exceptions import DogrulamaHatasi
from app.core.gercekzaman import yayinla
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.enerji import repository, service
from app.modules.enerji.birimler import ENERJI_TURLERI
from app.modules.enerji.models import EnerjiTuketim
from app.modules.enerji.schemas import (
    EnerjiOlcumCevapDTO,
    EnerjiOlcumOlusturDTO,
    EnerjiTrendNoktaDTO,
)

router = APIRouter(tags=["Enerji"])

# Trend granülerlik beyaz-listesi (SQL enjeksiyonuna karşı; geçersiz → varsayılan 'saat').
_ARALIKLAR = frozenset({"saat", "gun"})


def _olcum_cevap(o: EnerjiTuketim) -> dict[str, Any]:
    return EnerjiOlcumCevapDTO(
        id=o.id,
        makine_id=o.makine_id,
        enerji_turu=o.enerji_turu,
        tuketim=float(o.tuketim),
        birim=o.birim,
        zaman=o.zaman,
    ).model_dump()


@router.post(
    "/enerji-tuketimleri",
    response_model=Zarf[EnerjiOlcumCevapDTO],
    status_code=201,
    summary="Enerji tüketim ölçümü ekle",
)
async def olcum_olustur(
    govde: EnerjiOlcumOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("enerji:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    if govde.enerji_turu not in ENERJI_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz enerji türü",
            detaylar=[{"alan": "enerji_turu", "mesaj": f"Geçerli: {', '.join(sorted(ENERJI_TURLERI))}"}],
        )
    olcum = await service.olcum_yaz(
        db,
        makine_id=govde.makine_id,
        enerji_turu=govde.enerji_turu,
        tuketim=govde.tuketim,
        birim=govde.birim,
        zaman=govde.zaman,
    )
    await denetim_yaz(
        db, eylem="olustur", kaynak="enerji_tuketim", kaynak_id=str(olcum.id), kullanici=kullanici
    )
    await yayinla(tenant.slug, {"tur": "enerji.olcum", "makine_id": olcum.makine_id})
    return basari(_olcum_cevap(olcum), mesaj="Enerji ölçümü eklendi")


@router.get(
    "/enerji-tuketimleri",
    response_model=Zarf[list[EnerjiOlcumCevapDTO]],
    summary="Enerji tüketim ölçümlerini listele",
)
async def olcum_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("enerji:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    makine_id: int | None = None,
    enerji_turu: str | None = None,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.olcum_listele(
        db, sayfa=sayfa, adet=adet, makine_id=makine_id, enerji_turu=enerji_turu,
        baslangic=baslangic, bitis=bitis, siralama=siralama, yon=yon,
    )
    return sayfali([_olcum_cevap(o) for o in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/enerji-tuketimleri/trend",
    response_model=Zarf[list[EnerjiTrendNoktaDTO]],
    summary="Enerji tüketim trendi (continuous aggregate)",
)
async def enerji_trend(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("enerji:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    makine_id: int | None = None,
    enerji_turu: str | None = None,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    aralik: str = "saat",
) -> dict[str, Any]:
    if aralik not in _ARALIKLAR:
        aralik = "saat"
    noktalar = await repository.trend(
        db, makine_id=makine_id, enerji_turu=enerji_turu,
        baslangic=baslangic, bitis=bitis, aralik=aralik,
    )
    return basari(
        [EnerjiTrendNoktaDTO(**n).model_dump() for n in noktalar], mesaj="Enerji trendi"
    )
```
> **Rota sırası:** `/enerji-tuketimleri/trend` statik yol, `/enerji-tuketimleri` GET'inden ayrı path olduğu için FastAPI eşleştirmesinde sorun yok (parametreli `{id}` yolu yok). Yine de `trend` rotasını listeleme rotasından **sonra** tanımlamak sıralamayı netleştirir.

- [ ] **Step 7: Include the enerji router**

`backend/app/api/router.py` — import + include ekle:
```python
from app.modules.enerji.router import router as enerji_router
```
```python
api_router.include_router(enerji_router)
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_s10_enerji.py -v`
Expected: PASS (6 passed). **CAGG real-time aggregation** sayesinde manuel refresh olmadan trend doğru toplar.

> **Sorun giderme:** trend boş dönerse (0 nokta) real-time aggregation kapalı olabilir — migration'da `timescaledb.materialized_only = false` olduğunu doğrula. `relation "enerji_tuketim_saatlik" does not exist` → Task 2 migration'ı bu tenant şemasında koşmamış (fixture head'e migrate etmeli).

- [ ] **Step 9: Lint + commit**

```bash
cd backend && ruff check app/modules/enerji tests/test_s10_enerji.py app/api/router.py && ruff format --check app/modules/enerji && python -m mypy app/modules/enerji app/api/router.py
git add backend/app/modules/enerji backend/app/api/router.py backend/tests/test_s10_enerji.py
git commit -m "feat(enerji): tüketim ölçümü + continuous aggregate trend ucu (S10)"
```

---

## Task 6: RBAC tohumu (enerji:yaz izni + kalite/enerji rolleri)

**Files:**
- Modify: `backend/app/kimlik/izinler.py` (`enerji:yaz` + 2 rol)
- Test: `backend/tests/test_s10_rbac_seed.py`

**Interfaces:**
- Consumes: `IZIN_KATALOGU`, `VARSAYILAN_ROLLER` (mevcut).
- Produces: katalogda `enerji:yaz`; `VARSAYILAN_ROLLER["kalite"]`, `VARSAYILAN_ROLLER["enerji"]`.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_s10_rbac_seed.py`:
```python
"""S10: izin katalogu + varsayılan roller (kalite/enerji görev rolleri)."""

from __future__ import annotations

from app.kimlik.izinler import IZIN_KATALOGU, VARSAYILAN_ROLLER


def test_enerji_yaz_katalogda() -> None:
    assert "enerji:yaz" in IZIN_KATALOGU


def test_kalite_rolu() -> None:
    assert VARSAYILAN_ROLLER["kalite"] == frozenset({"kalite:oku", "kalite:yaz"})


def test_enerji_rolu() -> None:
    assert VARSAYILAN_ROLLER["enerji"] == frozenset({"enerji:oku", "enerji:yaz"})


def test_izleyici_enerji_okur_yazmaz() -> None:
    # izleyici tüm :oku'ları alır (enerji:oku dahil) ama enerji:yaz almaz.
    assert "enerji:oku" in VARSAYILAN_ROLLER["izleyici"]
    assert "enerji:yaz" not in VARSAYILAN_ROLLER["izleyici"]


def test_admin_yeni_izni_alir() -> None:
    assert "enerji:yaz" in VARSAYILAN_ROLLER["admin"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_s10_rbac_seed.py -v`
Expected: FAIL — `enerji:yaz` katalogda yok / `kalite`,`enerji` rolleri yok.

- [ ] **Step 3: Add enerji:yaz + roles**

`backend/app/kimlik/izinler.py` — `"enerji:oku"` satırının hemen altına ekle:
```python
    "enerji:yaz": "Enerji tüketim girişi",
```
`VARSAYILAN_ROLLER` sözlüğüne (satinalma-onaylayan'dan sonra) ekle:
```python
    # Kalite sorumlusu: denetim + uygunsuzluk/CAPA yönetir.
    "kalite": frozenset({"kalite:oku", "kalite:yaz"}),
    # Enerji sorumlusu: tüketim görüntüler + girer.
    "enerji": frozenset({"enerji:oku", "enerji:yaz"}),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_s10_rbac_seed.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Lint + commit**

```bash
cd backend && ruff check app/kimlik/izinler.py tests/test_s10_rbac_seed.py && python -m mypy app/kimlik/izinler.py
git add backend/app/kimlik/izinler.py backend/tests/test_s10_rbac_seed.py
git commit -m "feat(rbac): enerji:yaz izni + kalite/enerji varsayılan rolleri (S10)"
```

---

## Task 7: OpenAPI regen + dokümanlar (ADR-0012, veri sözlüğü, yol haritası, README)

**Files:**
- Modify: `frontend/openapi.json` (regen)
- Create: `docs/adr/0012-kalite-enerji.md`
- Modify: `docs/veri-sozlugu.md`
- Modify: `docs/yol-haritasi.md`
- Modify: `README.md`

**Interfaces:** Yok (dokümantasyon + sözleşme senkronu).

- [ ] **Step 1: Run the full backend suite (regression gate)**

Run: `cd backend && python -m pytest -q`
Expected: PASS — S10 öncesi 144 + S10 birim/entegrasyon testleri (durum + migration + kalite kontrol + CAPA + enerji + RBAC seed). Tüm suite yeşil.

- [ ] **Step 2: Regenerate OpenAPI JSON**

Run (proje kökünden):
```bash
./.venv/Scripts/python.exe -c "import json;from app.main import create_app;open('frontend/openapi.json','w',encoding='utf-8').write(json.dumps(create_app().openapi(),ensure_ascii=False))"
```
Expected: `frontend/openapi.json` güncellenir; `/kalite-kontrolleri`, `/uygunsuzluklar`, `/enerji-tuketimleri`, `/enerji-tuketimleri/trend` yolları içerir.

- [ ] **Step 3: Write ADR-0012**

`docs/adr/0012-kalite-enerji.md` (mevcut ADR biçimini izle: Başlık/Durum/Bağlam/Karar/Sonuçlar):
```markdown
# ADR-0012: Kalite (Tam CAPA) & Enerji (hypertable + continuous aggregate)

- Durum: Kabul edildi
- Tarih: 2026-07-01
- Sprint: S10 (Faz 2)

## Bağlam
S10 iki iş modülü ekler: Kalite (denetim + uygunsuzluk/CAPA) ve Enerji (tüketim zaman
serisi + trend). Enerji trendi için S3'te (ADR-0006) ertelenen **continuous aggregate**
kararı burada uygulanır.

## Karar
1. **Tam CAPA:** `Uygunsuzluk` saf durum makinesiyle (`acik→kok_neden→aksiyon_plani→uygulama
   →dogrulama→kapandi`, +iptal; doğrulama→uygulama geri dönüşü) yönetilir; düzeltici/önleyici
   aksiyonlar ayrı `CapaAksiyon` satırlarıdır (kendi durumu). Tüm geçişler `kalite:yaz`
   (ayrı onay izni yok). `KaliteKontrol` denetim kaydı (makine/iş emri opsiyonel); kaldı
   denetim otomatik uygunsuzluk üretmez (elle, opsiyonel FK bağı).
2. **Enerji hypertable:** `enerji_tuketim` `UretimVerisi` deseniyle hypertable (PK `(zaman,id)`);
   `makine_id` nullable = tesis geneli; elle giriş (edge sonraki fazda).
3. **Continuous aggregate:** `enerji_tuketim_saatlik` (saatlik `time_bucket`) materialized view
   `WITH (timescaledb.continuous, timescaledb.materialized_only = false)` + refresh policy.
   Migration'da **`op.get_context().autocommit_block()`** zorunlu — CAGG/policy transaction
   bloğunda oluşturulamaz; `search_path` env'de `SET` (session) olduğundan autocommit sonrası
   korunur → CAGG doğru tenant şemasında. Trend ucu CAGG'den okur; `aralik=gun` CAGG üstünde
   günlük toplar. **Real-time aggregation** ile son (materialize edilmemiş) veri de görünür.
4. **RBAC:** `enerji:yaz` katalog eklenir (`kalite:oku/yaz`, `enerji:oku` zaten vardı);
   görev rolleri `kalite`, `enerji`.

## Sonuçlar
- (+) Enerji trendi hızlı okunur; ADR-0006'nın ertelediği CAGG işi kapanır.
- (+) OEE hattı (S3) değişmez; kalite/enerji ayrık modüller.
- (−) CAGG migration `autocommit_block` gerektirir; test DB **TSL** TimescaleDB imajı ister
  (`add_continuous_aggregate_policy`). Fan-out testinde erken doğrulanır.
- Ertelenen: compression/retention politikaları (S19); kalite→OEE kalite oranı beslemesi;
  edge enerji ingestion (Faz 5).
```

- [ ] **Step 4: Update veri-sozlugu.md**

`docs/veri-sozlugu.md` — S9 bölümünün ardına S10 tablolarını ekle (mevcut biçimde tablo/kolon açıklamaları): `kalite_kontrolleri`, `uygunsuzluklar`, `capa_aksiyonlari`, `enerji_tuketim` + CAGG `enerji_tuketim_saatlik`. Her tablo için kolon adı + tip + açıklama satırları; FK ve durum makinesi notu.

- [ ] **Step 5: Update yol-haritasi.md + README.md**

- `docs/yol-haritasi.md`: S10 satırını **✅ tamam** işaretle; kapsam özeti (Kalite CAPA + Enerji CAGG).
- `README.md`: durum tablosunda S10 ✅; gerekiyorsa modül listesine Kalite/Enerji ekle.

- [ ] **Step 6: Commit**

```bash
git add frontend/openapi.json docs/adr/0012-kalite-enerji.md docs/veri-sozlugu.md docs/yol-haritasi.md README.md
git commit -m "docs(s10): ADR-0012 + openapi regen + veri sözlüğü/yol-haritası/README (S10 backend kapanış)"
```

---

## Task 8: Frontend codegen + CAPA durum aynası + rozetler + hooks + çizgi grafik seçeneği

**Files:**
- Modify: `frontend/src/api/types.gen.ts` (codegen çıktısı — elle düzenlenmez)
- Create: `frontend/src/modules/kalite/durum.ts`
- Create: `frontend/src/modules/kalite/durum.test.ts`
- Create: `frontend/src/modules/kalite/rozetler.tsx`
- Create: `frontend/src/modules/kalite/hooks.ts`
- Create: `frontend/src/modules/enerji/hooks.ts`
- Modify: `frontend/src/components/grafik/grafikSecenek.ts` (`cizgiSecenek` ekle)
- Modify: `frontend/src/components/grafik/grafikSecenek.test.ts` (cizgi testi)
- Modify: `frontend/src/i18n/tr.json`, `frontend/src/i18n/en.json` (kalite/enerji/menu anahtarları)

**Interfaces:**
- Consumes: `components['schemas']` (codegen); `istek`, `PREFIX`, `ApiHata` (`@/api/client`); `useSayfaliSorgu`; `EChartsOption`.
- Produces:
  - `kalite/durum.ts`: `GECISLER`, `TERMINAL`, `AKTIF`, `gecerliHedefler(mevcut)`
  - `kalite/rozetler.tsx`: `UygunsuzlukDurumEtiketi`, `OnemEtiketi`, `KontrolSonucEtiketi`
  - `kalite/hooks.ts`: `useKaliteKontroller`, `useKontrolOlustur`, `useUygunsuzluklar`, `useUygunsuzluk`, `useUygunsuzlukOlustur`, `useCapaDurum`, `useAksiyonEkle`, `useAksiyonGuncelle`, `KALITE_ANAHTAR`
  - `enerji/hooks.ts`: `useEnerjiOlcumler`, `useOlcumEkle`, `useEnerjiTrend`, `ENERJI_ANAHTAR`
  - `grafikSecenek.cizgiSecenek(veri: { zaman: string; deger: number }[]): EChartsOption`

- [ ] **Step 1: Regenerate TS types from OpenAPI**

Run: `cd frontend && npm run codegen`
Expected: `src/api/types.gen.ts` yeni şemaları içerir (`KaliteKontrolCevapDTO`, `UygunsuzlukDetayDTO`, `EnerjiOlcumCevapDTO`, `EnerjiTrendNoktaDTO`, ...).

- [ ] **Step 2: Write the CAPA durum mirror + failing test**

`frontend/src/modules/kalite/durum.test.ts`:
```typescript
import { describe, expect, it } from 'vitest';

import { AKTIF, gecerliHedefler, GECISLER, TERMINAL } from './durum';

describe('CAPA durum aynası', () => {
  it('acik hedefleri backend ile aynı', () => {
    expect(gecerliHedefler('acik')).toEqual(['kok_neden', 'iptal']);
  });
  it('dogrulama geri dönüş içerir', () => {
    expect(gecerliHedefler('dogrulama')).toEqual(['kapandi', 'uygulama', 'iptal']);
  });
  it('terminal durumdan çıkış yok', () => {
    for (const d of TERMINAL) expect(gecerliHedefler(d)).toEqual([]);
  });
  it('aktif durumlar terminal olmayanlar', () => {
    expect(AKTIF).toEqual(['acik', 'kok_neden', 'aksiyon_plani', 'uygulama', 'dogrulama']);
  });
  it('bilinmeyen durum boş', () => {
    expect(gecerliHedefler('yok')).toEqual([]);
  });
});
```

`frontend/src/modules/kalite/durum.ts`:
```typescript
/**
 * CAPA (uygunsuzluk) durum makinesi **aynası** — backend ``kalite/durum.py`` ile birebir.
 * UI yalnız geçerli hedefleri gösterir; nihai doğrulama backend'dedir.
 */

export const GECISLER: Record<string, string[]> = {
  acik: ['kok_neden', 'iptal'],
  kok_neden: ['aksiyon_plani', 'iptal'],
  aksiyon_plani: ['uygulama', 'iptal'],
  uygulama: ['dogrulama', 'iptal'],
  dogrulama: ['kapandi', 'uygulama', 'iptal'],
  kapandi: [],
  iptal: [],
};

export const TERMINAL = ['kapandi', 'iptal'] as const;
export const AKTIF = ['acik', 'kok_neden', 'aksiyon_plani', 'uygulama', 'dogrulama'] as const;

export function gecerliHedefler(mevcut: string): string[] {
  return GECISLER[mevcut] ?? [];
}
```

Run: `cd frontend && npm run test -- durum`
Expected: PASS (kalite/durum.test.ts 5 passed).

- [ ] **Step 3: Write kalite rozetler**

`frontend/src/modules/kalite/rozetler.tsx`:
```typescript
/** Kalite rozetleri (durum/önem/sonuç) — AntD Tag + i18n. */

import { useTranslation } from 'react-i18next';
import { Tag } from 'antd';

const DURUM_RENK: Record<string, string> = {
  acik: 'default',
  kok_neden: 'processing',
  aksiyon_plani: 'processing',
  uygulama: 'warning',
  dogrulama: 'cyan',
  kapandi: 'success',
  iptal: 'default',
};

const ONEM_RENK: Record<string, string> = {
  dusuk: 'default',
  orta: 'blue',
  yuksek: 'orange',
  kritik: 'error',
};

const SONUC_RENK: Record<string, string> = {
  gecti: 'success',
  kaldi: 'error',
  sartli: 'warning',
};

export function UygunsuzlukDurumEtiketi({ durum }: { durum: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={DURUM_RENK[durum] ?? 'default'} bordered={false}>
      {t(`kalite.durum_${durum}`)}
    </Tag>
  );
}

export function OnemEtiketi({ onem }: { onem: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={ONEM_RENK[onem] ?? 'default'} bordered={false}>
      {t(`kalite.onem_${onem}`)}
    </Tag>
  );
}

export function KontrolSonucEtiketi({ sonuc }: { sonuc: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={SONUC_RENK[sonuc] ?? 'default'} bordered={false}>
      {t(`kalite.sonuc_${sonuc}`)}
    </Tag>
  );
}
```

- [ ] **Step 4: Write kalite hooks**

`frontend/src/modules/kalite/hooks.ts` (stok `hooks.ts` desenini izler — `useHataGoster`, `useSayfaliSorgu`, `istek`/`PREFIX`):
```typescript
/** Kalite veri hook'ları (TanStack Query). Anahtarlar olayIsle.ts ile birebir aynıdır. */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type KaliteKontrol = components['schemas']['KaliteKontrolCevapDTO'];
export type KaliteKontrolOlustur = components['schemas']['KaliteKontrolOlusturDTO'];
export type Uygunsuzluk = components['schemas']['UygunsuzlukCevapDTO'];
export type UygunsuzlukDetay = components['schemas']['UygunsuzlukDetayDTO'];
export type UygunsuzlukOlustur = components['schemas']['UygunsuzlukOlusturDTO'];
export type AksiyonOlustur = components['schemas']['AksiyonOlusturDTO'];

export const KALITE_ANAHTAR = {
  kontroller: ['kalite-kontrolleri'] as const,
  uygunsuzluklar: ['uygunsuzluklar'] as const,
  uygunsuzluk: (id: number) => ['uygunsuzluk', id] as const,
};

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

export function useKaliteKontroller(param: SayfaParam) {
  return useSayfaliSorgu<KaliteKontrol>(KALITE_ANAHTAR.kontroller, '/kalite-kontrolleri', param);
}

export function useKontrolOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: KaliteKontrolOlustur) =>
      istek<KaliteKontrol>('POST', `${PREFIX}/kalite-kontrolleri`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KALITE_ANAHTAR.kontroller });
      message.success(t('kalite.kontrol_olusturuldu'));
    },
    onError: hataGoster,
  });
}

export function useUygunsuzluklar(param: SayfaParam) {
  return useSayfaliSorgu<Uygunsuzluk>(KALITE_ANAHTAR.uygunsuzluklar, '/uygunsuzluklar', param);
}

export function useUygunsuzluk(id: number) {
  return useQuery({
    queryKey: KALITE_ANAHTAR.uygunsuzluk(id),
    queryFn: () => istek<UygunsuzlukDetay>('GET', `${PREFIX}/uygunsuzluklar/${id}`),
    enabled: id > 0,
  });
}

export function useUygunsuzlukOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: UygunsuzlukOlustur) =>
      istek<UygunsuzlukDetay>('POST', `${PREFIX}/uygunsuzluklar`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KALITE_ANAHTAR.uygunsuzluklar });
      message.success(t('kalite.uygunsuzluk_olusturuldu'));
    },
    onError: hataGoster,
  });
}

export function useCapaDurum() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({
      id,
      hedef,
      kok_neden,
      dogrulama_notu,
    }: {
      id: number;
      hedef: string;
      kok_neden?: string;
      dogrulama_notu?: string;
    }) =>
      istek<Uygunsuzluk>('PATCH', `${PREFIX}/uygunsuzluklar/${id}/durum`, {
        hedef,
        kok_neden,
        dogrulama_notu,
      }),
    onSuccess: (_v, { id }) => {
      void qc.invalidateQueries({ queryKey: KALITE_ANAHTAR.uygunsuzluklar });
      void qc.invalidateQueries({ queryKey: KALITE_ANAHTAR.uygunsuzluk(id) });
      message.success(t('kalite.durum_guncellendi'));
    },
    onError: hataGoster,
  });
}

export function useAksiyonEkle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, govde }: { id: number; govde: AksiyonOlustur }) =>
      istek<UygunsuzlukDetay>('POST', `${PREFIX}/uygunsuzluklar/${id}/aksiyonlar`, govde),
    onSuccess: (_v, { id }) => {
      void qc.invalidateQueries({ queryKey: KALITE_ANAHTAR.uygunsuzluk(id) });
      message.success(t('kalite.aksiyon_eklendi'));
    },
    onError: hataGoster,
  });
}

export function useAksiyonGuncelle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({
      id,
      aksiyonId,
      durum,
    }: {
      id: number;
      aksiyonId: number;
      durum: string;
    }) =>
      istek<UygunsuzlukDetay>('PATCH', `${PREFIX}/uygunsuzluklar/${id}/aksiyonlar/${aksiyonId}`, {
        durum,
      }),
    onSuccess: (_v, { id }) => {
      void qc.invalidateQueries({ queryKey: KALITE_ANAHTAR.uygunsuzluk(id) });
      message.success(t('kalite.aksiyon_guncellendi'));
    },
    onError: hataGoster,
  });
}
```

- [ ] **Step 5: Write enerji hooks**

`frontend/src/modules/enerji/hooks.ts`:
```typescript
/** Enerji veri hook'ları (TanStack Query). Trend anahtarı filtreye göre ayrışır. */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type EnerjiOlcum = components['schemas']['EnerjiOlcumCevapDTO'];
export type EnerjiOlcumOlustur = components['schemas']['EnerjiOlcumOlusturDTO'];
export type TrendNokta = components['schemas']['EnerjiTrendNoktaDTO'];

export const ENERJI_ANAHTAR = {
  olcumler: ['enerji-tuketimleri'] as const,
  trend: ['enerji-trend'] as const,
};

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

export function useEnerjiOlcumler(param: SayfaParam) {
  return useSayfaliSorgu<EnerjiOlcum>(ENERJI_ANAHTAR.olcumler, '/enerji-tuketimleri', param);
}

export function useOlcumEkle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: EnerjiOlcumOlustur) =>
      istek<EnerjiOlcum>('POST', `${PREFIX}/enerji-tuketimleri`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ENERJI_ANAHTAR.olcumler });
      void qc.invalidateQueries({ queryKey: ENERJI_ANAHTAR.trend });
      message.success(t('enerji.olcum_eklendi'));
    },
    onError: hataGoster,
  });
}

export function useEnerjiTrend(sorgu: {
  enerji_turu?: string;
  makine_id?: number;
  aralik: string;
  baslangic?: string;
  bitis?: string;
}) {
  const params = new URLSearchParams();
  if (sorgu.enerji_turu) params.set('enerji_turu', sorgu.enerji_turu);
  if (sorgu.makine_id) params.set('makine_id', String(sorgu.makine_id));
  params.set('aralik', sorgu.aralik);
  if (sorgu.baslangic) params.set('baslangic', sorgu.baslangic);
  if (sorgu.bitis) params.set('bitis', sorgu.bitis);
  const qs = params.toString();
  return useQuery({
    queryKey: [...ENERJI_ANAHTAR.trend, qs],
    queryFn: () => istek<TrendNokta[]>('GET', `${PREFIX}/enerji-tuketimleri/trend?${qs}`),
  });
}
```

- [ ] **Step 6: Add cizgiSecenek to grafikSecenek + test**

`frontend/src/components/grafik/grafikSecenek.ts` — dosyanın sonuna ekle:
```typescript
/** Zaman serisi çizgi grafiği (ör. enerji tüketim trendi). */
export function cizgiSecenek(veri: { zaman: string; deger: number }[]): EChartsOption {
  return {
    grid: { left: 6, right: 14, top: 18, bottom: 4, containLabel: true },
    tooltip: {
      trigger: 'axis',
      backgroundColor: RENKLER.yuzeyUst,
      borderColor: RENKLER.kenarlik,
      textStyle: { color: RENKLER.metin, fontFamily: GOVDE },
    },
    xAxis: {
      type: 'category',
      data: veri.map((v) => v.zaman),
      axisLabel: { color: RENKLER.metinSoluk, fontFamily: GOVDE, fontSize: 11 },
      axisLine: { lineStyle: { color: RENKLER.kenarlik } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      min: 0,
      splitLine: { lineStyle: { color: IZGARA_RENK } },
      axisLabel: { color: RENKLER.metinSoluk, fontFamily: MONO },
    },
    series: [
      {
        type: 'line',
        smooth: true,
        showSymbol: false,
        areaStyle: { opacity: 0.12, color: RENKLER.bilgi },
        lineStyle: { color: RENKLER.bilgi, width: 2 },
        itemStyle: { color: RENKLER.bilgi },
        data: veri.map((v) => v.deger),
      },
    ],
  };
}
```
> `RENKLER.bilgi` (info/cyan) `tema.ts`'te tanımlı olmalı; yoksa `RENKLER.metin` kullan. `grafikSecenek.test.ts`'e ekle:
```typescript
import { cizgiSecenek } from './grafikSecenek';

it('cizgiSecenek zaman serisini seriye çevirir', () => {
  const o = cizgiSecenek([{ zaman: '08:00', deger: 30 }]) as unknown as {
    series: { data: number[] }[];
  };
  expect(o.series[0].data).toEqual([30]);
});
```

- [ ] **Step 7: Add i18n keys (TR + EN)**

`frontend/src/i18n/tr.json` — `menu.*` bloğuna ekle: `"kalite": "Kalite kontrol"`, `"uygunsuzluklar": "Uygunsuzluklar"`, `"enerji": "Enerji"`, `"enerji_trend": "Enerji trendi"`, `"bolum_kalite": "Kalite & Enerji"`. Yeni `kalite` + `enerji` blokları ekle (durum/önem/sonuç etiketleri + mesajlar):
```json
"kalite": {
  "kontrol_olusturuldu": "Kalite kontrol oluşturuldu",
  "uygunsuzluk_olusturuldu": "Uygunsuzluk oluşturuldu",
  "durum_guncellendi": "Durum güncellendi",
  "aksiyon_eklendi": "Aksiyon eklendi",
  "aksiyon_guncellendi": "Aksiyon güncellendi",
  "durum_acik": "Açık",
  "durum_kok_neden": "Kök-neden analizi",
  "durum_aksiyon_plani": "Aksiyon planı",
  "durum_uygulama": "Uygulama",
  "durum_dogrulama": "Doğrulama",
  "durum_kapandi": "Kapandı",
  "durum_iptal": "İptal",
  "onem_dusuk": "Düşük",
  "onem_orta": "Orta",
  "onem_yuksek": "Yüksek",
  "onem_kritik": "Kritik",
  "sonuc_gecti": "Geçti",
  "sonuc_kaldi": "Kaldı",
  "sonuc_sartli": "Şartlı"
},
"enerji": {
  "olcum_eklendi": "Enerji ölçümü eklendi",
  "tur_elektrik": "Elektrik",
  "tur_dogalgaz": "Doğalgaz",
  "tur_su": "Su",
  "tur_hava": "Basınçlı hava",
  "tur_buhar": "Buhar",
  "aralik_saat": "Saatlik",
  "aralik_gun": "Günlük"
}
```
`frontend/src/i18n/en.json` — aynı anahtarların İngilizcesi (Quality control / Non-conformities / Energy / Energy trend; Open / Root-cause / Action plan / Implementation / Verification / Closed / Cancelled; Low/Medium/High/Critical; Pass/Fail/Conditional; Electricity/Natural gas/Water/Compressed air/Steam; Hourly/Daily).

- [ ] **Step 8: Run FE unit tests + lint + commit**

```bash
cd frontend && npm run test -- durum grafikSecenek && npm run lint && npm run typecheck && npm run format:check
git add frontend/src/api/types.gen.ts frontend/src/modules/kalite/durum.ts frontend/src/modules/kalite/durum.test.ts frontend/src/modules/kalite/rozetler.tsx frontend/src/modules/kalite/hooks.ts frontend/src/modules/enerji/hooks.ts frontend/src/components/grafik/grafikSecenek.ts frontend/src/components/grafik/grafikSecenek.test.ts frontend/src/i18n/tr.json frontend/src/i18n/en.json
git commit -m "feat(frontend): kalite/enerji codegen + CAPA durum aynası + rozetler + hooks + çizgi grafik (S10)"
```

---

## Task 9: Frontend kalite ekranları + menü/rota

**Files:**
- Create: `frontend/src/modules/kalite/KaliteKontrolListesi.tsx`
- Create: `frontend/src/modules/kalite/KaliteKontrolFormu.tsx`
- Create: `frontend/src/modules/kalite/UygunsuzlukListesi.tsx`
- Create: `frontend/src/modules/kalite/UygunsuzlukFormu.tsx`
- Create: `frontend/src/modules/kalite/UygunsuzlukDetay.tsx`
- Create: `frontend/src/modules/kalite/UygunsuzlukListesi.test.tsx`
- Modify: `frontend/src/layouts/menu.ts` (2 menü öğesi)
- Modify: `frontend/src/App.tsx` (2 rota)

**Interfaces:**
- Consumes: Task 8 hooks + rozetler + durum; `SunucuTablo` (`@/components/SunucuTablo`); `useSayfaParam` (`@/modules/ortak/useSayfaParam`); `IzinKapisi`, `KorunanRota` (App'te zaten); `useAuthStore` (izin kontrolü aksiyon görünürlüğü).

- [ ] **Step 1: KaliteKontrolListesi + Formu** (mirror `frontend/src/modules/stok/MalzemeListesi.tsx` + `MalzemeFormu.tsx`)

`KaliteKontrolListesi.tsx`: `SunucuTablo` ile `useKaliteKontroller`; sütunlar: `kod`, `kontrol_turu`, `sonuc` (→ `<KontrolSonucEtiketi>`), `numune_adedi`, `uygunsuz_adet`, `zaman`; araç çubuğunda "Yeni kayıt" butonu (`kalite:yaz` varsa) → `KaliteKontrolFormu` (AntD `Modal`/`Drawer`). Filtre: `sonuc` (Select: gecti/kaldi/sartli). Başlık `SayfaBaslik` `t('menu.kalite')`.

`KaliteKontrolFormu.tsx`: AntD `Form` alanları: `kontrol_turu` (Select KONTROL_TURLERI), `sonuc` (Select gecti/kaldi/sartli, zorunlu), `makine_id`/`is_emri_id` (opsiyonel `InputNumber`), `olculen_deger`/`alt_limit`/`ust_limit` (`InputNumber`), `numune_adedi`/`uygunsuz_adet` (`InputNumber` min 0), `aciklama` (`Input.TextArea`). Submit → `useKontrolOlustur`.

- [ ] **Step 2: UygunsuzlukListesi + Formu + Detay** (mirror `SatinalmaTalepListesi.tsx` + `SatinalmaTalepFormu.tsx` + `SatinalmaTalepDetay.tsx`)

`UygunsuzlukListesi.tsx`: `SunucuTablo` ile `useUygunsuzluklar`; sütunlar: `kod`, `baslik`, `onem` (→ `<OnemEtiketi>`), `durum` (→ `<UygunsuzlukDurumEtiketi>`), `olusturma_tarihi`; satıra tıkla → `UygunsuzlukDetay` (Drawer). Araç çubuğu "Yeni uygunsuzluk" (`kalite:yaz`). Filtreler: `durum`, `onem` (Select).

`UygunsuzlukFormu.tsx`: alanlar `baslik` (zorunlu), `aciklama` (`TextArea`), `onem` (Select dusuk/orta/yuksek/kritik), `makine_id`/`kaynak_kontrol_id`/`sorumlu_kullanici_id` (opsiyonel). Submit → `useUygunsuzlukOlustur`.

`UygunsuzlukDetay.tsx` (Drawer, `SatinalmaTalepDetay` deseninin CAPA uyarlaması):
- Künye: kod, başlık, önem rozeti, durum rozeti, açıklama, kök-neden.
- **CAPA durum geçişi:** `gecerliHedefler(uygunsuzluk.durum)` → yalnız geçerli hedef butonları (`useAuthStore` `izinler.includes('kalite:yaz')` yoksa gizle). `kok_neden` hedefine geçerken kök-neden metin girişi (Modal/inline); `kapandi` hedefine geçerken `dogrulama_notu` girişi → `useCapaDurum`.
- **Aksiyonlar:** `uygunsuzluk.aksiyonlar` listesi (tür rozeti + açıklama + durum + termin); "Aksiyon ekle" (tür Select duzeltici/onleyici + açıklama) → `useAksiyonEkle`; her aksiyonda "Tamamla" → `useAksiyonGuncelle({durum:'tamamlandi'})`.

- [ ] **Step 3: Write UygunsuzlukListesi.test.tsx** (mirror `SatinalmaTalepListesi.test.tsx`)

Fetch-mock ile listeyi render eder; `durum`/`onem` rozetlerinin göründüğünü + `kalite:yaz` yokken "Yeni uygunsuzluk" butonunun **gizli** olduğunu doğrular (izin-duyarlı). En az 2 test.

- [ ] **Step 4: Register menu + routes**

`frontend/src/layouts/menu.ts` — `MENU` dizisine ekle (yeni `bolum_kalite` bölümü):
```typescript
  {
    anahtar: 'kalite',
    etiketAnahtari: 'menu.kalite',
    bolum: 'menu.bolum_kalite',
    yol: '/kalite-kontrolleri',
    izin: 'kalite:oku',
  },
  {
    anahtar: 'uygunsuzluklar',
    etiketAnahtari: 'menu.uygunsuzluklar',
    bolum: 'menu.bolum_kalite',
    yol: '/uygunsuzluklar',
    izin: 'kalite:oku',
  },
```
`frontend/src/App.tsx` — importları + rotaları ekle (stok rotaları deseniyle, `IzinKapisi izin="kalite:oku"`):
```tsx
<Route path="kalite-kontrolleri" element={<IzinKapisi izin="kalite:oku"><KaliteKontrolListesi /></IzinKapisi>} />
<Route path="uygunsuzluklar" element={<IzinKapisi izin="kalite:oku"><UygunsuzlukListesi /></IzinKapisi>} />
```
İlgili `import { KaliteKontrolListesi } from '@/modules/kalite/KaliteKontrolListesi';` + `UygunsuzlukListesi` importlarını ekle.

- [ ] **Step 5: Test + lint + commit**

```bash
cd frontend && npm run test -- UygunsuzlukListesi && npm run lint && npm run typecheck && npm run format:check
git add frontend/src/modules/kalite frontend/src/layouts/menu.ts frontend/src/App.tsx
git commit -m "feat(frontend): kalite kontrol listesi/form + uygunsuzluk liste/detay/CAPA aksiyonlar (S10)"
```

---

## Task 10: Frontend enerji ekranları (liste + giriş + trend) + menü/rota

**Files:**
- Create: `frontend/src/modules/enerji/EnerjiTuketimListesi.tsx`
- Create: `frontend/src/modules/enerji/EnerjiGirisFormu.tsx`
- Create: `frontend/src/modules/enerji/EnerjiTrend.tsx`
- Create: `frontend/src/modules/enerji/EnerjiTrend.test.tsx`
- Modify: `frontend/src/layouts/menu.ts` (1 menü öğesi)
- Modify: `frontend/src/App.tsx` (1 rota)

**Interfaces:**
- Consumes: Task 8 enerji hooks; `EGrafik` (`@/components/grafik/EGrafik`); `cizgiSecenek`; `SunucuTablo`; ENERJI_TURLERI etiketleri (i18n).

- [ ] **Step 1: EnerjiTuketimListesi + EnerjiGirisFormu** (mirror `MalzemeListesi` + `StokHareketFormu`)

`EnerjiTuketimListesi.tsx`: `SunucuTablo` ile `useEnerjiOlcumler`; sütunlar `zaman`, `enerji_turu` (→ i18n `enerji.tur_{deger}`), `tuketim`, `birim`, `makine_id`; araç çubuğunda "Ölçüm ekle" (`enerji:yaz`) + tür filtre Select; üstte **`EnerjiTrend`** kartı gömülü. Başlık `t('menu.enerji')`.

`EnerjiGirisFormu.tsx`: AntD `Form`: `enerji_turu` (Select ENERJI_TURLERI, zorunlu), `tuketim` (`InputNumber` min>0, zorunlu), `birim` (`Input`, öntanımlı "kWh"), `makine_id` (opsiyonel `InputNumber`), `zaman` (`DatePicker` showTime, opsiyonel). Submit → `useOlcumEkle`.

- [ ] **Step 2: EnerjiTrend chart component**

`frontend/src/modules/enerji/EnerjiTrend.tsx`:
```tsx
/** Enerji tüketim trendi (ECharts çizgi). Tür + aralık (saat/gün) filtreleri. */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, Segmented, Select, Space } from 'antd';

import { EGrafik } from '@/components/grafik/EGrafik';
import { cizgiSecenek } from '@/components/grafik/grafikSecenek';
import { useEnerjiTrend } from './hooks';

const TURLER = ['elektrik', 'dogalgaz', 'su', 'hava', 'buhar'];

export function EnerjiTrend() {
  const { t } = useTranslation();
  const [tur, setTur] = useState('elektrik');
  const [aralik, setAralik] = useState('saat');
  const { data } = useEnerjiTrend({ enerji_turu: tur, aralik });

  const secenek = useMemo(
    () =>
      cizgiSecenek(
        (data ?? []).map((n) => ({
          zaman: new Date(n.zaman).toLocaleString(),
          deger: n.toplam,
        })),
      ),
    [data],
  );

  return (
    <Card
      title={t('menu.enerji_trend')}
      extra={
        <Space>
          <Select
            value={tur}
            onChange={setTur}
            options={TURLER.map((x) => ({ value: x, label: t(`enerji.tur_${x}`) }))}
            style={{ width: 150 }}
          />
          <Segmented
            value={aralik}
            onChange={(v) => setAralik(String(v))}
            options={[
              { value: 'saat', label: t('enerji.aralik_saat') },
              { value: 'gun', label: t('enerji.aralik_gun') },
            ]}
          />
        </Space>
      }
    >
      <EGrafik secenek={secenek} yukseklik={280} />
    </Card>
  );
}
```
> `EGrafik` props adları (`secenek`, `yukseklik`) mevcut kullanımla eşleşmeli — `MakineDetay.tsx`/`PanoIcerik.tsx`'teki `EGrafik` kullanımını kontrol et; farklıysa oradaki prop adlarını kullan.

- [ ] **Step 3: EnerjiTrend.test.tsx**

Fetch-mock ile trend verisi döndürür; `EGrafik` mock'lanır (canvas yok); tür Select + aralık Segmented render edildiğini + veri değişince `cizgiSecenek` çağrıldığını doğrular. En az 1 test.

- [ ] **Step 4: Register menu + route**

`menu.ts` — ekle:
```typescript
  {
    anahtar: 'enerji',
    etiketAnahtari: 'menu.enerji',
    bolum: 'menu.bolum_kalite',
    yol: '/enerji-tuketimleri',
    izin: 'enerji:oku',
  },
```
`App.tsx`:
```tsx
<Route path="enerji-tuketimleri" element={<IzinKapisi izin="enerji:oku"><EnerjiTuketimListesi /></IzinKapisi>} />
```
+ `import { EnerjiTuketimListesi } from '@/modules/enerji/EnerjiTuketimListesi';`

- [ ] **Step 5: Test + lint + commit**

```bash
cd frontend && npm run test -- EnerjiTrend && npm run lint && npm run typecheck && npm run format:check
git add frontend/src/modules/enerji frontend/src/layouts/menu.ts frontend/src/App.tsx
git commit -m "feat(frontend): enerji tüketim listesi/giriş + continuous aggregate trend grafiği (S10)"
```

---

## Task 11: Canlı invalidate + tam kalite kapısı + uçtan uca doğrulama

**Files:**
- Modify: `frontend/src/modules/ortak/olayIsle.ts` (3 olay dalı)
- Modify: `frontend/src/modules/ortak/olayIsle.test.ts` (yeni olaylar)

**Interfaces:** Yok (entegrasyon + doğrulama).

- [ ] **Step 1: Add live-event invalidation**

`frontend/src/modules/ortak/olayIsle.ts` — `switch` içine `satinalma.durum` dalından sonra ekle:
```typescript
    case 'kalite.kontrol':
      void qc.invalidateQueries({ queryKey: ['kalite-kontrolleri'] });
      break;
    case 'kalite.uygunsuzluk': {
      void qc.invalidateQueries({ queryKey: ['uygunsuzluklar'] });
      const uid = typeof olay.id === 'number' ? olay.id : undefined;
      if (uid !== undefined) void qc.invalidateQueries({ queryKey: ['uygunsuzluk', uid] });
      break;
    }
    case 'enerji.olcum':
      void qc.invalidateQueries({ queryKey: ['enerji-tuketimleri'] });
      void qc.invalidateQueries({ queryKey: ['enerji-trend'] });
      break;
```

- [ ] **Step 2: Add olayIsle tests**

`frontend/src/modules/ortak/olayIsle.test.ts` — mevcut desende 3 test ekle: `kalite.kontrol` → `['kalite-kontrolleri']` invalidate; `kalite.uygunsuzluk` (id ile) → `['uygunsuzluklar']` + `['uygunsuzluk', id]`; `enerji.olcum` → `['enerji-tuketimleri']` + `['enerji-trend']`.

- [ ] **Step 3: Run FULL frontend gate**

```bash
cd frontend && npm run test && npm run lint && npm run typecheck && npm run format:check && npm run build
```
Expected: tüm testler (65 önceki + S10 yeni) PASS; eslint/tsc/prettier temiz; `vite build` uyarısız.

- [ ] **Step 4: Run FULL backend gate**

```bash
cd backend && python -m pytest -q && ruff check . && ruff format --check . && python -m mypy app
```
Expected: tüm suite PASS; ruff/mypy temiz.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/modules/ortak/olayIsle.ts frontend/src/modules/ortak/olayIsle.test.ts
git commit -m "feat(frontend): kalite/enerji canlı invalidate (olayIsle) (S10)"
```

- [ ] **Step 6: Uçtan uca doğrulama (gerçek yığın)**

Manuel/scriptli doğrulama (S9 deseni — `docker compose up -d db redis`, host `DATABASE_URL/REDIS_URL=localhost` override ile uvicorn; taze `s10live` tenant head'e migrate):
1. **Migration + CAGG:** `s10live` tenant provizyonla → `enerji_tuketim` hypertable + `enerji_tuketim_saatlik` CAGG oluştu (psql `\d+ tenant_s10live.enerji_tuketim_saatlik`).
2. **CAPA akışı (HTTP e2e):** uygunsuzluk oluştur → `kok_neden`→`aksiyon_plani`→aksiyon ekle→`uygulama`→`dogrulama`→`kapandi`; geçersiz geçiş 409; `kalite:yaz` yok → 403.
3. **Enerji trend:** birkaç ölçüm yaz (aynı + farklı saat) → `GET /enerji-tuketimleri/trend?aralik=saat` doğru toplar (real-time aggregation, refresh beklemeden); `aralik=gun` günlük toplar.
4. **Gerçek tarayıcı (Playwright bundled chromium, `npx playwright screenshot`):** giriş → Kalite kontrol listesi + Uygunsuzluk detay (CAPA durum butonları + aksiyon ekle) + Enerji ekranı (trend grafiği çizili). Ekran görüntülerini `Read` ile teyit et.
5. Sonuçları hafızaya (`project-fabrikaos-plan.md`) işle: S10 TAMAM + gerçek çıktı kanıtı.

- [ ] **Step 7: Final commit + dal kapanışı**

DoD tam (BE + FE yeşil, lint/tip temiz, migration fan-out + CAGG testli, ADR-0012 + docs güncel, uçtan uca geçti) → `finishing-a-development-branch` skill'i ile `feat/s10-kalite-enerji` dalını `main`'e entegrasyon seçeneklerini sun.

---

## Self-Review Notları (plan yazarı)

- **Spec kapsam eşlemesi:** Kalite kontrol (T3) · Uygunsuzluk+CAPA+aksiyon (T4) · Enerji ölçüm+trend/CAGG (T5, T2) · RBAC `enerji:yaz`+roller (T6) · outbox `kalite.uygunsuzluk`+realtime (T4/T5) · migration fan-out+CAGG autocommit_block (T2) · docs/ADR-0012 (T7) · FE ekranlar+canlı (T8–T11). Spec'teki her madde bir task'a bağlı.
- **Tip tutarlılığı:** durum makinesi `hedef` alan adı BE (`DurumGecisDTO.hedef`) ↔ FE (`useCapaDurum({hedef})`) eşleşir; realtime olay adları `kalite.kontrol`/`kalite.uygunsuzluk`/`enerji.olcum` BE router ↔ FE `olayIsle` ↔ hooks anahtarları (`kalite-kontrolleri`/`uygunsuzluklar`/`uygunsuzluk`/`enerji-tuketimleri`/`enerji-trend`) birebir.
- **En yüksek risk:** T2 CAGG `autocommit_block` (async fan-out). Erken ve izole; migration testi (T2 Step 5) kanıt kapısı.
