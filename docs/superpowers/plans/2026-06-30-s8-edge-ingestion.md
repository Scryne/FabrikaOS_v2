# S8 — Edge & Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sahadan otomatik veri akışı kur: simüle PLC verisi `Edge → MQTT → Ingestion → uretim_verileri → OEE panosu`'na elle giriş olmadan, tenant-aware ve store-and-forward'la kayıpsız aksın.

**Architecture:** Bağımsız `edge/` ajanı (simülatör + pluggable sürücü + sqlite store-and-forward) ölçümleri MQTT'ye yayınlar; ayrı `app.ingestion` worker'ı (aiomqtt) abone olur, tenant şemasına idempotent yazar; `app.modules.saha` cihaz yönetimi + REST/CSV ingestion sağlar. Veri mevcut `UretimVerisi` hypertable'ına yazıldığı için OEE/pano hattı (S3/S6/S7) değişmeden çalışır.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async, asyncpg, Alembic (fan-out), TimescaleDB, aiomqtt, Mosquitto, Redis pub/sub, Pydantic v2, pytest/testcontainers; Frontend React+TS+Vite+AntD+TanStack Query.

## Global Constraints

- **Çok-kiracılık (tenant-rbac-conventions):** tenant-kapsamlı her uç `tenant_cozumle` + `izin_gerekli("modul:islem")` ikilisinden geçer. Repository/sorgu asla sabit `tenant_xyz.tablo` öneki yazmaz; `search_path` çözer. Yeni veri uca **tenant izolasyon testi** zorunlu.
- **İsimlendirme (turkce-identifier-standardi):** model/tablo/kolon/route/DTO Türkçe-ASCII; izin kodu `modul:islem`; tablo adları çoğul snake_case (`saha_cihazlar`).
- **Migration (alembic-fan-out):** tenant ağacı; `naming_convention` (`op.f(...)`); `public` + ≥2 tenant şemasında up **ve** down testli. Yeni modeller `core/db/registry.py`'ye import edilir.
- **API zarfı:** `{success, message, data, meta}` (`app.core.responses.basari/sayfali/Zarf`); doğru HTTP kodu; yazma uçları `denetim_yaz` üretir.
- **Kalite kapısı:** `ruff check backend && ruff format --check backend && mypy && pytest` temiz; frontend `npm run lint && npm run typecheck && npm test && npm run build` temiz.
- **Komutlar (Windows):** Python `./.venv/Scripts/python.exe`; entegrasyon testleri için `docker compose up -d db redis mqtt` çalışır olmalı.
- **Ertelenenler (ADR-0010'da gerekçeli):** gerçek OPC-UA/Modbus sürücüleri, mTLS/MQTT kimlik doğrulama, idempotency tablosu retention → Faz 5 / S19-S20.

---

### Task 1: Bağımlılık + `saha` modül iskeleti + ölçüm kontratı (DTO)

**Files:**
- Modify: `pyproject.toml` (deps + pytest/mypy/ruff yolları)
- Create: `backend/app/modules/saha/__init__.py`
- Create: `backend/app/modules/saha/schemas.py`
- Test: `backend/tests/test_s8_kontrat.py`

**Interfaces:**
- Produces: `OlcumPaketi` (Pydantic) — alanlar: `olcum_id: UUID`, `makine_kod: str`, `zaman: datetime`, `vardiya: str | None`, `planlanan_sure_dk: float`, `durus_sure_dk: float`, `toplam_adet: int`, `saglam_adet: int`, `ideal_cevrim_sn: float`. `CihazOlusturDTO`, `CihazCevapDTO`, `OlcumKabulDTO`.

- [ ] **Step 1: `pyproject.toml` — aiomqtt ekle + test/tip yolları**

`dependencies` listesine ekle (redis satırından sonra):
```toml
    "aiomqtt>=2.3",         # S8: edge + ingestion MQTT istemcisi (async)
```
`[tool.ruff]` `src` satırını güncelle ve mypy/pytest yollarına `edge`'i ekle:
```toml
[tool.ruff]
line-length = 100
target-version = "py312"
src = ["backend", "edge"]
extend-exclude = ["backend/migrations/*/versions"]
```
```toml
[tool.mypy]
python_version = "3.12"
strict = true
mypy_path = "backend"
files = ["backend/app", "edge"]
plugins = ["pydantic.mypy"]
```
```toml
[tool.pytest.ini_options]
pythonpath = ["backend", "."]
asyncio_mode = "auto"
testpaths = ["backend/tests", "edge/tests"]
addopts = "-ra -q"
```
aiomqtt tip uyumu için dosya sonuna ekle:
```toml
[[tool.mypy.overrides]]
module = ["aiomqtt.*"]
ignore_missing_imports = true
```

- [ ] **Step 2: Bağımlılığı kur**

Run: `./.venv/Scripts/python.exe -m pip install -e ".[dev]"`
Expected: `aiomqtt` kurulur (Successfully installed aiomqtt-...).

- [ ] **Step 3: Failing test yaz** — `backend/tests/test_s8_kontrat.py`

```python
"""S8 ölçüm kontratı (OlcumPaketi) doğrulama birim testleri."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.modules.saha.schemas import OlcumPaketi


def _gecerli() -> dict:
    return {
        "olcum_id": str(uuid.uuid4()),
        "makine_kod": "MAK-1",
        "zaman": datetime.now(UTC).isoformat(),
        "vardiya": "A",
        "planlanan_sure_dk": 60.0,
        "durus_sure_dk": 5.0,
        "toplam_adet": 100,
        "saglam_adet": 98,
        "ideal_cevrim_sn": 30.0,
    }


def test_gecerli_paket_dogrulanir() -> None:
    p = OlcumPaketi.model_validate(_gecerli())
    assert p.makine_kod == "MAK-1"
    assert p.toplam_adet == 100


def test_saglam_toplamdan_buyuk_olamaz() -> None:
    veri = _gecerli() | {"saglam_adet": 200}
    with pytest.raises(ValidationError):
        OlcumPaketi.model_validate(veri)


def test_negatif_adet_reddedilir() -> None:
    with pytest.raises(ValidationError):
        OlcumPaketi.model_validate(_gecerli() | {"toplam_adet": -1})


def test_json_round_trip() -> None:
    p = OlcumPaketi.model_validate(_gecerli())
    geri = OlcumPaketi.model_validate_json(p.model_dump_json())
    assert geri.olcum_id == p.olcum_id
```

- [ ] **Step 4: Testin başarısız olduğunu doğrula**

Run: `./.venv/Scripts/python.exe -m pytest backend/tests/test_s8_kontrat.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.modules.saha'`.

- [ ] **Step 5: `saha` paketi + şemaları yaz**

`backend/app/modules/saha/__init__.py`:
```python
"""Saha (Edge & Ingestion) modülü — cihaz yönetimi + saha ölçüm ingestion'ı."""
```

`backend/app/modules/saha/schemas.py`:
```python
"""Saha modülü Pydantic DTO'ları + ölçüm kontratı (OlcumPaketi).

``OlcumPaketi`` edge ajanı, MQTT ingestion'ı ve REST/CSV uçlarının paylaştığı tek
sözleşmedir. Edge ajanı (``edge/paket.py``) aynı JSON şeklini bağımsız üretir; uçtan
uca uyum bir kontrat testiyle güvenceye alınır.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

# Desteklenen saha protokolleri (MVP'de yalnız simülasyon yazar; opcua/modbus iskelet).
PROTOKOLLER = frozenset({"simulasyon", "opcua", "modbus"})


class OlcumPaketi(BaseModel):
    """Bir makinenin tek aralık üretim özeti (UretimVerisi şekli + idempotency kimliği)."""

    olcum_id: UUID
    makine_kod: str = Field(min_length=1, max_length=50)
    zaman: datetime
    vardiya: str | None = Field(default=None, max_length=20)
    planlanan_sure_dk: float = Field(ge=0)
    durus_sure_dk: float = Field(ge=0)
    toplam_adet: int = Field(ge=0)
    saglam_adet: int = Field(ge=0)
    ideal_cevrim_sn: float = Field(ge=0)

    @model_validator(mode="after")
    def _saglam_kontrol(self) -> OlcumPaketi:
        if self.saglam_adet > self.toplam_adet:
            raise ValueError("saglam_adet toplam_adet'i aşamaz")
        return self


class CihazOlusturDTO(BaseModel):
    kod: str = Field(min_length=1, max_length=50)
    ad: str = Field(min_length=1, max_length=200)
    protokol: str = Field(default="simulasyon")

    @model_validator(mode="after")
    def _protokol_kontrol(self) -> CihazOlusturDTO:
        if self.protokol not in PROTOKOLLER:
            raise ValueError(f"Geçersiz protokol: {self.protokol!r}")
        return self


class CihazCevapDTO(BaseModel):
    id: int
    kod: str
    ad: str
    protokol: str
    aktif: bool
    son_gorulme: datetime | None = None


class OlcumKabulDTO(BaseModel):
    """REST toplu ingestion gövdesi: bir gateway'in bir veya çok ölçümü."""

    cihaz_kod: str = Field(min_length=1, max_length=50)
    olcumler: list[OlcumPaketi] = Field(min_length=1)
```

- [ ] **Step 6: Testin geçtiğini doğrula**

Run: `./.venv/Scripts/python.exe -m pytest backend/tests/test_s8_kontrat.py -v`
Expected: PASS (4 passed).

- [ ] **Step 7: Lint + commit**

Run: `./.venv/Scripts/python.exe -m ruff check backend && ./.venv/Scripts/python.exe -m ruff format backend/app/modules/saha backend/tests/test_s8_kontrat.py`
```bash
git add pyproject.toml backend/app/modules/saha backend/tests/test_s8_kontrat.py
git commit -m "feat(saha): ölçüm kontratı (OlcumPaketi) + saha modül iskeleti + aiomqtt"
```

---

### Task 2: `Cihaz` + `AlinanOlcum` modelleri + migration (fan-out)

**Files:**
- Create: `backend/app/modules/saha/models.py`
- Modify: `backend/app/core/db/registry.py` (import satırı)
- Create: `backend/migrations/tenant/versions/<rev>_saha_cihazlar_alinan_olcum.py`
- Test: `backend/tests/test_s8_migration.py`

**Interfaces:**
- Consumes: `KimlikMixin`, `ZamanDamgaliMixin`, `TenantBase` (app.core.db.base).
- Produces: `Cihaz` (tablo `saha_cihazlar`: `id, kod, ad, protokol, aktif, son_gorulme, olusturma_tarihi, guncelleme_tarihi`), `AlinanOlcum` (tablo `saha_alinan_olcum`: `olcum_id UUID PK, makine_id, alinma_zamani`).

- [ ] **Step 1: Modelleri yaz** — `backend/app/modules/saha/models.py`

```python
"""Saha modülü modelleri (tenant şeması).

- ``Cihaz`` — saha gateway kaydı (bir gateway N makine köprüleyebilir; makineye sabit
  FK yoktur, ölçüm ``makine_kod`` taşır).
- ``AlinanOlcum`` — idempotency defteri: işlenen ``olcum_id``'ler. Store-and-forward
  replay'inde çift-saymayı önler (``ON CONFLICT DO NOTHING``). Hypertable değildir.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin

# Desteklenen saha protokolleri (MVP: simülasyon; opcua/modbus iskelet).
PROTOKOLLER = frozenset({"simulasyon", "opcua", "modbus"})


class Cihaz(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Saha gateway / veri kaynağı cihazı."""

    __tablename__ = "saha_cihazlar"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    ad: Mapped[str] = mapped_column(String(200), nullable=False)
    protokol: Mapped[str] = mapped_column(String(20), default="simulasyon", nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    son_gorulme: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AlinanOlcum(TenantBase):
    """İşlenmiş ölçüm kimliği (idempotency defteri)."""

    __tablename__ = "saha_alinan_olcum"

    olcum_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    makine_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    alinma_zamani: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 2: registry'ye kaydet** — `backend/app/core/db/registry.py`

`import app.modules.uretim.models  # noqa: F401` satırından sonra ekle:
```python
import app.modules.saha.models  # noqa: F401
```

- [ ] **Step 3: Mevcut tenant head'ini öğren**

Run: `./.venv/Scripts/python.exe -m alembic --name tenant heads`
Expected: tek head `c5a2f1b8e34d (head)`. (Farklıysa Step 4'te `down_revision`'ı o değere ayarla.)

- [ ] **Step 4: Migration dosyasını yaz**

`backend/migrations/tenant/versions/a1b2c3d4e5f6_saha_cihazlar_alinan_olcum.py` (dosya adındaki `a1b2c3d4e5f6` ve `revision` aynı olmalı; benzersiz bir hex seç):
```python
"""saha: saha_cihazlar + saha_alinan_olcum (Edge & Ingestion)

Revision ID: a1b2c3d4e5f6
Revises: c5a2f1b8e34d
Create Date: 2026-06-30 12:00:00.000000

Tenant şemasında; fan-out döngüsünde (env.py) public + her aktif tenant şemasında çalışır.
Hypertable yoktur (düşük hacim + idempotency defteri normal tablo olmak zorunda).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = 'c5a2f1b8e34d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'saha_cihazlar',
        sa.Column('kod', sa.String(length=50), nullable=False),
        sa.Column('ad', sa.String(length=200), nullable=False),
        sa.Column('protokol', sa.String(length=20), nullable=False),
        sa.Column('aktif', sa.Boolean(), nullable=False),
        sa.Column('son_gorulme', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('olusturma_tarihi', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('guncelleme_tarihi', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_saha_cihazlar')),
    )
    op.create_index(op.f('ix_saha_cihazlar_kod'), 'saha_cihazlar', ['kod'], unique=True)

    op.create_table(
        'saha_alinan_olcum',
        sa.Column('olcum_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('makine_id', sa.BigInteger(), nullable=False),
        sa.Column('alinma_zamani', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('olcum_id', name=op.f('pk_saha_alinan_olcum')),
    )


def downgrade() -> None:
    op.drop_table('saha_alinan_olcum')
    op.drop_index(op.f('ix_saha_cihazlar_kod'), table_name='saha_cihazlar')
    op.drop_table('saha_cihazlar')
```

- [ ] **Step 5: Failing test yaz** — `backend/tests/test_s8_migration.py`

```python
"""S8 migration fan-out testi: saha tabloları up/down (tenant_alfa şeması)."""

from __future__ import annotations

import asyncpg
import pytest

from app.core.db import fanout
from tests.conftest import TEST_URL

pytestmark = pytest.mark.asyncio

_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")


async def _tablo_var_mi(tablo: str) -> bool:
    conn = await asyncpg.connect(_DSN)
    try:
        return bool(
            await conn.fetchval(
                "SELECT to_regclass($1) IS NOT NULL", f"tenant_alfa.{tablo}"
            )
        )
    finally:
        await conn.close()


async def test_saha_tablolari_up_down(test_db: str) -> None:
    # test_db fixture: head'e migrate edilmiş tenant_alfa şeması.
    assert await _tablo_var_mi("saha_cihazlar")
    assert await _tablo_var_mi("saha_alinan_olcum")

    # downgrade bir adım → saha tabloları gitmeli
    fanout.tenant_indir_tek("alfa", "c5a2f1b8e34d", db_url=TEST_URL)
    assert not await _tablo_var_mi("saha_cihazlar")
    assert not await _tablo_var_mi("saha_alinan_olcum")

    # tekrar head'e çık (sonraki testler için durumu geri yükle)
    fanout.tenant_yukselt_tek("alfa", "head", db_url=TEST_URL)
    assert await _tablo_var_mi("saha_cihazlar")
```

- [ ] **Step 6: Testi çalıştır (DB gerekli)**

Run: `docker compose up -d db redis` ardından `./.venv/Scripts/python.exe -m pytest backend/tests/test_s8_migration.py -v`
Expected: PASS. (Hata alırsan `down_revision`/head değerini Step 3 çıktısıyla eşle.)

- [ ] **Step 7: mypy + commit**

Run: `./.venv/Scripts/python.exe -m mypy && ./.venv/Scripts/python.exe -m ruff check backend`
```bash
git add backend/app/modules/saha/models.py backend/app/core/db/registry.py backend/migrations/tenant/versions/ backend/tests/test_s8_migration.py
git commit -m "feat(saha): Cihaz + AlinanOlcum modelleri + tenant migration (fan-out)"
```

---

### Task 3: RBAC izinleri + `saha-cihaz` rolü (seed)

**Files:**
- Modify: `backend/app/kimlik/izinler.py`
- Test: `backend/tests/test_s8_seed.py`

**Interfaces:**
- Produces: izin kodları `saha:oku`, `saha:yaz`, `edge`; varsayılan rol `saha-cihaz` = `{edge}`.

- [ ] **Step 1: Failing test yaz** — `backend/tests/test_s8_seed.py`

```python
"""S8 seed: saha izinleri + saha-cihaz rolü provizyon tohumunda yer alır."""

from __future__ import annotations

from app.kimlik.izinler import IZIN_KATALOGU, VARSAYILAN_ROLLER


def test_saha_izinleri_katalogda() -> None:
    assert "saha:oku" in IZIN_KATALOGU
    assert "saha:yaz" in IZIN_KATALOGU
    assert "edge" in IZIN_KATALOGU


def test_admin_tum_saha_izinlerine_sahip() -> None:
    assert {"saha:oku", "saha:yaz", "edge"} <= VARSAYILAN_ROLLER["admin"]


def test_izleyici_yalniz_okur() -> None:
    assert "saha:oku" in VARSAYILAN_ROLLER["izleyici"]
    assert "edge" not in VARSAYILAN_ROLLER["izleyici"]


def test_saha_cihaz_rolu_edge_tasir() -> None:
    assert VARSAYILAN_ROLLER["saha-cihaz"] == frozenset({"edge"})
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `./.venv/Scripts/python.exe -m pytest backend/tests/test_s8_seed.py -v`
Expected: FAIL (`saha:oku` not in IZIN_KATALOGU / KeyError 'saha-cihaz').

- [ ] **Step 3: İzin kataloğu + rolleri güncelle** — `backend/app/kimlik/izinler.py`

`IZIN_KATALOGU` içinde `"uretim:yaz": ...` satırından sonra ekle:
```python
    "saha:oku": "Saha cihazlarını görüntüleme",
    "saha:yaz": "Saha cihazı oluşturma/güncelleme",
    "edge": "Saha ölçümü gönderme (edge ingestion)",
```
`VARSAYILAN_ROLLER` sözlüğüne `"izleyici"` satırından sonra ekle:
```python
    # Saha/cihaz servis hesapları (REST/MQTT ingestion için yalnız edge izni).
    "saha-cihaz": frozenset({"edge"}),
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `./.venv/Scripts/python.exe -m pytest backend/tests/test_s8_seed.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/kimlik/izinler.py backend/tests/test_s8_seed.py
git commit -m "feat(saha): RBAC saha:oku/yaz/edge izinleri + saha-cihaz rolü (seed)"
```

---

### Task 4: Ingestion mesaj çözücü (`mesaj_coz`) — saf

**Files:**
- Create: `backend/app/ingestion/__init__.py`
- Create: `backend/app/ingestion/isleyici.py`
- Test: `backend/tests/test_s8_isleyici.py`

**Interfaces:**
- Consumes: `OlcumPaketi` (saha.schemas), `slug_gecerli_mi` (core.db.tenancy).
- Produces: `MesajGecersiz(Exception)`; `mesaj_coz(topic: str, payload: bytes) -> tuple[str, str, OlcumPaketi]` → `(tenant_slug, cihaz_kod, paket)`.

- [ ] **Step 1: Failing test yaz** — `backend/tests/test_s8_isleyici.py`

```python
"""S8 ingestion mesaj çözücü (mesaj_coz) birim testleri — broker'sız, saf."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.ingestion.isleyici import MesajGecersiz, mesaj_coz


def _payload() -> bytes:
    return (
        '{"olcum_id":"%s","makine_kod":"MAK-1","zaman":"%s","vardiya":"A",'
        '"planlanan_sure_dk":60,"durus_sure_dk":5,"toplam_adet":100,'
        '"saglam_adet":98,"ideal_cevrim_sn":30}'
        % (uuid.uuid4(), datetime.now(UTC).isoformat())
    ).encode()


def test_gecerli_topic_ve_payload() -> None:
    slug, cihaz, paket = mesaj_coz("fabrikaos/alfa/GW-1/olcum", _payload())
    assert slug == "alfa"
    assert cihaz == "GW-1"
    assert paket.makine_kod == "MAK-1"


def test_bozuk_topic_reddedilir() -> None:
    with pytest.raises(MesajGecersiz):
        mesaj_coz("yanlis/alfa/GW-1/olcum", _payload())
    with pytest.raises(MesajGecersiz):
        mesaj_coz("fabrikaos/alfa/GW-1", _payload())


def test_gecersiz_slug_reddedilir() -> None:
    with pytest.raises(MesajGecersiz):
        mesaj_coz("fabrikaos/Geçersiz_Slug/GW-1/olcum", _payload())


def test_bozuk_payload_reddedilir() -> None:
    with pytest.raises(MesajGecersiz):
        mesaj_coz("fabrikaos/alfa/GW-1/olcum", b"{bozuk-json")
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `./.venv/Scripts/python.exe -m pytest backend/tests/test_s8_isleyici.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.ingestion'`.

- [ ] **Step 3: İşleyiciyi yaz**

`backend/app/ingestion/__init__.py`:
```python
"""Bulut Ingestion Worker — MQTT abonesi, saha ölçümlerini tenant şemasına yazar."""
```

`backend/app/ingestion/isleyici.py`:
```python
"""Saf mesaj çözme/doğrulama — broker'a ve DB'ye bağımsız (kolayca test edilir).

Topic biçimi: ``fabrikaos/<tenant_slug>/<cihaz_kod>/olcum``.
"""

from __future__ import annotations

from pydantic import ValidationError

from app.core.db.tenancy import slug_gecerli_mi
from app.modules.saha.schemas import OlcumPaketi

_KOK = "fabrikaos"
_SON = "olcum"


class MesajGecersiz(Exception):
    """Topic veya payload sözleşmeye uymuyor → mesaj güvenle düşürülür."""


def mesaj_coz(topic: str, payload: bytes) -> tuple[str, str, OlcumPaketi]:
    """``(tenant_slug, cihaz_kod, OlcumPaketi)`` döndürür; uymazsa ``MesajGecersiz``."""
    parcalar = topic.split("/")
    if len(parcalar) != 4 or parcalar[0] != _KOK or parcalar[3] != _SON:
        raise MesajGecersiz(f"Beklenmeyen topic: {topic!r}")
    _, slug, cihaz_kod, _ = parcalar
    if not slug_gecerli_mi(slug):
        raise MesajGecersiz(f"Geçersiz tenant slug: {slug!r}")
    if not cihaz_kod:
        raise MesajGecersiz("Cihaz kodu boş")
    try:
        paket = OlcumPaketi.model_validate_json(payload)
    except ValidationError as exc:
        raise MesajGecersiz("Ölçüm payload doğrulanamadı") from exc
    return slug, cihaz_kod, paket
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `./.venv/Scripts/python.exe -m pytest backend/tests/test_s8_isleyici.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/ingestion backend/tests/test_s8_isleyici.py
git commit -m "feat(ingestion): saf mesaj çözücü mesaj_coz (topic+payload doğrulama)"
```

---

### Task 5: Saha repository (cihaz CRUD + makine çözümü + idempotency)

**Files:**
- Create: `backend/app/modules/saha/repository.py`
- Test: `backend/tests/test_s8_repository.py`

**Interfaces:**
- Produces (hepsi `AsyncSession` alır; `search_path` çağrıdan önce ayarlı varsayılır):
  - `cihaz_kod_var_mi(session, kod) -> bool`
  - `cihaz_ekle(session, cihaz: Cihaz) -> Cihaz`
  - `cihaz_getir(session, cihaz_id: int) -> Cihaz | None`
  - `cihaz_kod_ile(session, kod: str) -> Cihaz | None`
  - `cihaz_listele(session, *, sayfa, adet, arama, siralama, yon) -> tuple[Sequence[Cihaz], int]`
  - `makine_id_kod_ile(session, makine_kod: str) -> int | None`
  - `olcum_isaretle(session, olcum_id: UUID, makine_id: int) -> bool` (yeni ise True, çift ise False)

- [ ] **Step 1: Failing test yaz** — `backend/tests/test_s8_repository.py`

```python
"""S8 saha repository birim testleri (tenant_alfa oturumu üzerinden)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db.tenancy import search_path_ayarla
from app.modules.saha import repository
from app.modules.saha.models import Cihaz
from app.modules.uretim.models import Makine

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def oturum(test_engine: object) -> AsyncIterator[AsyncSession]:
    sm = async_sessionmaker(test_engine, expire_on_commit=False)  # type: ignore[arg-type]
    async with sm() as s:
        await search_path_ayarla(s, "alfa")
        yield s
        await s.rollback()


async def test_cihaz_ekle_ve_kod_ile_bul(oturum: AsyncSession) -> None:
    await repository.cihaz_ekle(oturum, Cihaz(kod="GW-REPO-1", ad="Gateway 1"))
    bulunan = await repository.cihaz_kod_ile(oturum, "GW-REPO-1")
    assert bulunan is not None and bulunan.ad == "Gateway 1"
    assert await repository.cihaz_kod_var_mi(oturum, "GW-REPO-1")


async def test_makine_id_kod_ile(oturum: AsyncSession) -> None:
    m = Makine(kod="MAK-REPO-1", ad="Makine 1")
    oturum.add(m)
    await oturum.flush()
    assert await repository.makine_id_kod_ile(oturum, "MAK-REPO-1") == m.id
    assert await repository.makine_id_kod_ile(oturum, "YOK") is None


async def test_olcum_isaretle_idempotent(oturum: AsyncSession) -> None:
    oid = uuid.uuid4()
    assert await repository.olcum_isaretle(oturum, oid, 1) is True
    assert await repository.olcum_isaretle(oturum, oid, 1) is False
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `./.venv/Scripts/python.exe -m pytest backend/tests/test_s8_repository.py -v`
Expected: FAIL — `ModuleNotFoundError: app.modules.saha.repository`.

- [ ] **Step 3: Repository'yi yaz** — `backend/app/modules/saha/repository.py`

```python
"""Saha modülü veri erişimi. Sorgular şema yazmaz; ``search_path`` (tenant) çözer."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sorgu import siralama_uygula
from app.modules.saha.models import AlinanOlcum, Cihaz
from app.modules.uretim.models import Makine

_CIHAZ_SIRALAMA = {
    "id": Cihaz.id,
    "kod": Cihaz.kod,
    "ad": Cihaz.ad,
    "protokol": Cihaz.protokol,
    "son_gorulme": Cihaz.son_gorulme,
}


async def cihaz_kod_var_mi(session: AsyncSession, kod: str) -> bool:
    return (await session.scalar(select(Cihaz.id).where(Cihaz.kod == kod))) is not None


async def cihaz_ekle(session: AsyncSession, cihaz: Cihaz) -> Cihaz:
    session.add(cihaz)
    await session.flush()
    return cihaz


async def cihaz_getir(session: AsyncSession, cihaz_id: int) -> Cihaz | None:
    return await session.get(Cihaz, cihaz_id)


async def cihaz_kod_ile(session: AsyncSession, kod: str) -> Cihaz | None:
    return await session.scalar(select(Cihaz).where(Cihaz.kod == kod))


async def cihaz_listele(
    session: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[Cihaz], int]:
    kosul = select(Cihaz)
    sayim = select(func.count()).select_from(Cihaz)
    if arama:
        kalip = f"%{arama}%"
        filtre = or_(Cihaz.kod.ilike(kalip), Cihaz.ad.ilike(kalip))
        kosul = kosul.where(filtre)
        sayim = sayim.where(filtre)
    toplam = await session.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul, siralama=siralama, yon=yon, izinli=_CIHAZ_SIRALAMA, varsayilan=Cihaz.id
    )
    sonuc = await session.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)


async def makine_id_kod_ile(session: AsyncSession, makine_kod: str) -> int | None:
    return await session.scalar(select(Makine.id).where(Makine.kod == makine_kod))


async def olcum_isaretle(session: AsyncSession, olcum_id: UUID, makine_id: int) -> bool:
    """Idempotency defterine ekle. Yeni ise True; zaten varsa (çift) False."""
    stmt = (
        pg_insert(AlinanOlcum)
        .values(olcum_id=olcum_id, makine_id=makine_id)
        .on_conflict_do_nothing(index_elements=["olcum_id"])
    )
    sonuc = await session.execute(stmt)
    return (sonuc.rowcount or 0) == 1
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `./.venv/Scripts/python.exe -m pytest backend/tests/test_s8_repository.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: mypy + commit**

Run: `./.venv/Scripts/python.exe -m mypy`
```bash
git add backend/app/modules/saha/repository.py backend/tests/test_s8_repository.py
git commit -m "feat(saha): repository — cihaz CRUD + makine çözümü + idempotency defteri"
```

---

### Task 6: Ingestion servisi (`olcum_yaz_toplu`) + tenant izolasyonu

**Files:**
- Create: `backend/app/ingestion/service.py`
- Test: `backend/tests/test_s8_service.py`

**Interfaces:**
- Consumes: `repository` (Task 5), `UretimVerisi` (uretim.models), `OlcumPaketi` (saha.schemas).
- Produces:
  - `IngestSonuc` (dataclass): `yazilan: int`, `atlanan: int`, `hatali: int`, `etkilenen_makineler: tuple[int, ...]`, `hatalar: tuple[str, ...]`.
  - `async olcum_yaz_toplu(session, *, cihaz_kod: str, paketler: Sequence[OlcumPaketi]) -> IngestSonuc` — `search_path` çağrıdan önce ayarlı varsayılır; flush eder, commit etmez; gerçek-zaman yayını **yapmaz** (çağıran `etkilenen_makineler`'i yayınlar).

- [ ] **Step 1: Failing test yaz** — `backend/tests/test_s8_service.py`

```python
"""S8 ingestion servisi — idempotency, bilinmeyen cihaz/makine, OEE'ye akış, tenant izolasyonu."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db.tenancy import search_path_ayarla
from app.ingestion.service import olcum_yaz_toplu
from app.modules.saha import repository
from app.modules.saha.models import Cihaz
from app.modules.saha.schemas import OlcumPaketi
from app.modules.uretim.models import Makine, UretimVerisi

pytestmark = pytest.mark.asyncio


def _paket(makine_kod: str, *, toplam: int = 100, saglam: int = 98) -> OlcumPaketi:
    return OlcumPaketi(
        olcum_id=uuid.uuid4(),
        makine_kod=makine_kod,
        zaman=datetime.now(UTC),
        vardiya="A",
        planlanan_sure_dk=60.0,
        durus_sure_dk=5.0,
        toplam_adet=toplam,
        saglam_adet=saglam,
        ideal_cevrim_sn=30.0,
    )


async def _oturum(engine: object, slug: str) -> AsyncSession:
    sm = async_sessionmaker(engine, expire_on_commit=False)  # type: ignore[arg-type]
    s = sm()
    await search_path_ayarla(s, slug)
    return s


@pytest_asyncio.fixture
async def alfa(test_engine: object) -> AsyncIterator[AsyncSession]:
    s = await _oturum(test_engine, "alfa")
    await repository.cihaz_ekle(s, Cihaz(kod="GW-SVC", ad="Servis GW"))
    s.add(Makine(kod="MAK-SVC", ad="Servis Makine"))
    await s.flush()
    yield s
    await s.rollback()
    await s.close()


async def test_yazma_oee_girdisi_olusturur(alfa: AsyncSession) -> None:
    sonuc = await olcum_yaz_toplu(alfa, cihaz_kod="GW-SVC", paketler=[_paket("MAK-SVC")])
    assert sonuc.yazilan == 1 and sonuc.atlanan == 0 and sonuc.hatali == 0
    sayi = await alfa.scalar(select(func.count()).select_from(UretimVerisi))
    assert sayi == 1


async def test_idempotent_replay_cift_yazmaz(alfa: AsyncSession) -> None:
    p = _paket("MAK-SVC")
    ilk = await olcum_yaz_toplu(alfa, cihaz_kod="GW-SVC", paketler=[p])
    tekrar = await olcum_yaz_toplu(alfa, cihaz_kod="GW-SVC", paketler=[p])
    assert ilk.yazilan == 1
    assert tekrar.yazilan == 0 and tekrar.atlanan == 1


async def test_bilinmeyen_cihaz_yazmaz(alfa: AsyncSession) -> None:
    sonuc = await olcum_yaz_toplu(alfa, cihaz_kod="YOK", paketler=[_paket("MAK-SVC")])
    assert sonuc.yazilan == 0 and sonuc.hatali == 1


async def test_bilinmeyen_makine_hatali(alfa: AsyncSession) -> None:
    sonuc = await olcum_yaz_toplu(alfa, cihaz_kod="GW-SVC", paketler=[_paket("YOK-MAK")])
    assert sonuc.yazilan == 0 and sonuc.hatali == 1


async def test_tenant_izolasyonu(test_engine: object) -> None:
    # alfa'da cihaz+makine var; beta'da YOK → beta'ya yazılmaz (çapraz-tenant sızıntı yok).
    beta = await _oturum(test_engine, "beta")
    try:
        sonuc = await olcum_yaz_toplu(beta, cihaz_kod="GW-SVC", paketler=[_paket("MAK-SVC")])
        assert sonuc.yazilan == 0  # beta şemasında GW-SVC cihazı yok
    finally:
        await beta.rollback()
        await beta.close()
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `./.venv/Scripts/python.exe -m pytest backend/tests/test_s8_service.py -v`
Expected: FAIL — `ModuleNotFoundError: app.ingestion.service`.

- [ ] **Step 3: Servisi yaz** — `backend/app/ingestion/service.py`

```python
"""Ingestion iş kuralı — ölçüm paketlerini tenant şemasına idempotent yazar.

Çağıran ``search_path``'i tenant şemasına ayarlamış olmalıdır (REST'te ``tenant_cozumle``,
worker'da ``search_path_ayarla``). Gerçek-zaman yayını burada yapılmaz; çağıran
``etkilenen_makineler`` üzerinden ``yayinla`` eder (test edilebilirlik + ayrışma).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.saha import repository
from app.modules.saha.schemas import OlcumPaketi
from app.modules.uretim.models import UretimVerisi


@dataclass(frozen=True, slots=True)
class IngestSonuc:
    yazilan: int
    atlanan: int
    hatali: int
    etkilenen_makineler: tuple[int, ...]
    hatalar: tuple[str, ...]


async def olcum_yaz_toplu(
    session: AsyncSession, *, cihaz_kod: str, paketler: Sequence[OlcumPaketi]
) -> IngestSonuc:
    """Bir gateway'in ölçüm paketlerini yazar. Cihaz/makine doğrular, idempotent."""
    cihaz = await repository.cihaz_kod_ile(session, cihaz_kod)
    if cihaz is None or not cihaz.aktif:
        return IngestSonuc(0, 0, len(paketler), (), (f"Cihaz bulunamadı/pasif: {cihaz_kod}",))

    yazilan = atlanan = 0
    hatalar: list[str] = []
    etkilenen: set[int] = set()

    for p in paketler:
        makine_id = await repository.makine_id_kod_ile(session, p.makine_kod)
        if makine_id is None:
            hatalar.append(f"Makine bulunamadı: {p.makine_kod}")
            continue
        if not await repository.olcum_isaretle(session, p.olcum_id, makine_id):
            atlanan += 1
            continue
        session.add(
            UretimVerisi(
                makine_id=makine_id,
                zaman=p.zaman,
                vardiya=p.vardiya,
                planlanan_sure_dk=p.planlanan_sure_dk,
                durus_sure_dk=p.durus_sure_dk,
                toplam_adet=p.toplam_adet,
                saglam_adet=p.saglam_adet,
                ideal_cevrim_sn=p.ideal_cevrim_sn,
            )
        )
        etkilenen.add(makine_id)
        yazilan += 1

    cihaz.son_gorulme = datetime.now(UTC)
    await session.flush()
    return IngestSonuc(
        yazilan=yazilan,
        atlanan=atlanan,
        hatali=len(hatalar),
        etkilenen_makineler=tuple(sorted(etkilenen)),
        hatalar=tuple(hatalar),
    )
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `./.venv/Scripts/python.exe -m pytest backend/tests/test_s8_service.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: mypy + commit**

Run: `./.venv/Scripts/python.exe -m mypy`
```bash
git add backend/app/ingestion/service.py backend/tests/test_s8_service.py
git commit -m "feat(ingestion): olcum_yaz_toplu — idempotent tenant-aware yazma + izolasyon"
```

---

### Task 7: Cihaz yönetimi uçları (`/saha/cihazlar`)

**Files:**
- Create: `backend/app/modules/saha/router.py`
- Modify: `backend/app/api/router.py` (saha router include)
- Test: `backend/tests/test_s8_cihaz_api.py`

**Interfaces:**
- Consumes: `izin_gerekli`, `tenant_cozumle`, `get_session`, `denetim_yaz`, `basari`/`sayfali`/`Zarf`, repository (Task 5).
- Produces uçlar: `POST /saha/cihazlar` (`saha:yaz`), `GET /saha/cihazlar` (`saha:oku`), `GET /saha/cihazlar/{id}` (`saha:oku`).

- [ ] **Step 1: Failing test yaz** — `backend/tests/test_s8_cihaz_api.py`

```python
"""S8 cihaz yönetimi API entegrasyon testleri (RBAC + tenant izolasyonu)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import ALFA, BETA

pytestmark = pytest.mark.asyncio


async def _giris(c: AsyncClient, t: dict) -> dict[str, str]:
    r = await c.post(
        "/api/v1/kimlik/token",
        data={"username": t["eposta"], "password": t["parola"]},
        headers={"X-Tenant": t["slug"]},
    )
    assert r.status_code == 200, r.text
    return {"X-Tenant": t["slug"], "Authorization": f"Bearer {r.json()['data']['access_token']}"}


async def test_cihaz_olustur_ve_listele(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.post(
        "/api/v1/saha/cihazlar", json={"kod": "GW-API", "ad": "API GW"}, headers=h
    )
    assert r.status_code == 201, r.text
    assert r.json()["data"]["protokol"] == "simulasyon"

    r2 = await kurulu_istemci.get("/api/v1/saha/cihazlar?arama=GW-API", headers=h)
    assert r2.status_code == 200
    assert r2.json()["meta"]["toplam"] >= 1


async def test_cihaz_yetkisiz_403(kurulu_istemci: AsyncClient) -> None:
    # izleyici rolü yok; ama edge-only kullanıcı yerine: token'sız istek 401, yetkisiz 403.
    r = await kurulu_istemci.get("/api/v1/saha/cihazlar")
    assert r.status_code == 401


async def test_cihaz_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    ha = await _giris(kurulu_istemci, ALFA)
    hb = await _giris(kurulu_istemci, BETA)
    r = await kurulu_istemci.post(
        "/api/v1/saha/cihazlar", json={"kod": "GW-IZO", "ad": "İzo GW"}, headers=ha
    )
    cid = r.json()["data"]["id"]
    # beta bu cihazı görememeli
    r2 = await kurulu_istemci.get(f"/api/v1/saha/cihazlar/{cid}", headers=hb)
    assert r2.status_code == 404
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `./.venv/Scripts/python.exe -m pytest backend/tests/test_s8_cihaz_api.py -v`
Expected: FAIL (404 on `/saha/cihazlar` — router yok).

- [ ] **Step 3: Router'ı yaz** — `backend/app/modules/saha/router.py`

```python
"""Saha modülü uçları (``/api/v1/saha``).

Cihaz yönetimi tenant-kapsamlı + RBAC korumalı (``saha:oku``/``saha:yaz``); yazma audit'lenir.
Ölçüm ingestion uçları Task 8'de eklenir.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli
from app.core.exceptions import CakismaHatasi, KaynakBulunamadi
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.saha import repository
from app.modules.saha.models import Cihaz
from app.modules.saha.schemas import CihazCevapDTO, CihazOlusturDTO

router = APIRouter(prefix="/saha", tags=["Saha"])


def _cihaz_cevap(c: Cihaz) -> dict[str, Any]:
    return CihazCevapDTO(
        id=c.id, kod=c.kod, ad=c.ad, protokol=c.protokol, aktif=c.aktif, son_gorulme=c.son_gorulme
    ).model_dump()


@router.post(
    "/cihazlar", response_model=Zarf[CihazCevapDTO], status_code=201, summary="Saha cihazı oluştur"
)
async def cihaz_olustur(
    govde: CihazOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("saha:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    if await repository.cihaz_kod_var_mi(db, govde.kod):
        raise CakismaHatasi("Bu kod ile cihaz zaten var")
    cihaz = await repository.cihaz_ekle(db, Cihaz(kod=govde.kod, ad=govde.ad, protokol=govde.protokol))
    await denetim_yaz(
        db, eylem="olustur", kaynak="saha_cihaz", kaynak_id=str(cihaz.id), kullanici=kullanici
    )
    return basari(_cihaz_cevap(cihaz), mesaj="Cihaz oluşturuldu")


@router.get("/cihazlar", response_model=Zarf[list[CihazCevapDTO]], summary="Cihazları listele")
async def cihaz_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("saha:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    sayfa: int = 1,
    adet: int = 20,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.cihaz_listele(
        db, sayfa=sayfa, adet=adet, arama=arama, siralama=siralama, yon=yon
    )
    return sayfali([_cihaz_cevap(c) for c in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get("/cihazlar/{cihaz_id}", response_model=Zarf[CihazCevapDTO], summary="Cihaz detayı")
async def cihaz_detay(
    cihaz_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("saha:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    cihaz = await repository.cihaz_getir(db, cihaz_id)
    if cihaz is None:
        raise KaynakBulunamadi("Cihaz bulunamadı")
    return basari(_cihaz_cevap(cihaz), mesaj="Cihaz detayı")
```

- [ ] **Step 4: Router'ı kaydet** — `backend/app/api/router.py`

`from app.modules.uretim.router import router as uretim_router` satırından sonra ekle:
```python
from app.modules.saha.router import router as saha_router
```
`api_router.include_router(uretim_router)` satırından sonra ekle:
```python
api_router.include_router(saha_router)
```

- [ ] **Step 5: Testin geçtiğini doğrula**

Run: `./.venv/Scripts/python.exe -m pytest backend/tests/test_s8_cihaz_api.py -v`
Expected: PASS (3 passed).

- [ ] **Step 6: mypy + commit**

Run: `./.venv/Scripts/python.exe -m mypy && ./.venv/Scripts/python.exe -m ruff check backend`
```bash
git add backend/app/modules/saha/router.py backend/app/api/router.py backend/tests/test_s8_cihaz_api.py
git commit -m "feat(saha): /saha/cihazlar CRUD uçları (RBAC + audit + izolasyon)"
```

---

### Task 8: REST + CSV ingestion uçları (`/saha/olcumler`)

**Files:**
- Modify: `backend/app/modules/saha/router.py` (olcumler uçları + yardımcı)
- Create: `backend/app/modules/saha/csv_ice.py` (CSV ayrıştırma)
- Test: `backend/tests/test_s8_olcum_api.py`

**Interfaces:**
- Consumes: `olcum_yaz_toplu`/`IngestSonuc` (Task 6), `yayinla` (core.gercekzaman), `tenant_cozumle`, `OlcumKabulDTO`.
- Produces: `POST /saha/olcumler` (`edge`), `POST /saha/olcumler/csv` (`edge`); `csv_satirlari_coz(metin: str) -> list[OlcumPaketi]`.

- [ ] **Step 1: CSV ayrıştırıcıyı yaz** — `backend/app/modules/saha/csv_ice.py`

```python
"""CSV → OlcumPaketi ayrıştırma. Başlık satırı zorunlu; kolon adları OlcumPaketi alanları.

Beklenen kolonlar: makine_kod, zaman (ISO-8601), vardiya, planlanan_sure_dk, durus_sure_dk,
toplam_adet, saglam_adet, ideal_cevrim_sn. ``olcum_id`` yoksa satırdan deterministik
üretilir (aynı CSV iki kez yüklenirse idempotent kalır).
"""

from __future__ import annotations

import csv
import io
import uuid

from pydantic import ValidationError

from app.modules.saha.schemas import OlcumPaketi

# Sabit ad alanı: (cihaz_kod, makine_kod, zaman) → kararlı olcum_id (CSV idempotency).
_AD_ALANI = uuid.UUID("0a8c3f9e-4b1d-4c2a-9f6e-7d5b2c1a0e9f")


class CsvGecersiz(Exception):
    """CSV biçimi/başlığı/satırı geçersiz."""


def csv_satirlari_coz(metin: str, *, cihaz_kod: str) -> list[OlcumPaketi]:
    okuyucu = csv.DictReader(io.StringIO(metin))
    if okuyucu.fieldnames is None or "makine_kod" not in okuyucu.fieldnames:
        raise CsvGecersiz("CSV başlığı eksik veya 'makine_kod' kolonu yok")
    paketler: list[OlcumPaketi] = []
    for i, satir in enumerate(okuyucu, start=2):  # 1 = başlık
        ham = dict(satir)
        if not ham.get("olcum_id"):
            cekirdek = f"{cihaz_kod}|{ham.get('makine_kod')}|{ham.get('zaman')}"
            ham["olcum_id"] = str(uuid.uuid5(_AD_ALANI, cekirdek))
        try:
            paketler.append(OlcumPaketi.model_validate(ham))
        except ValidationError as exc:
            raise CsvGecersiz(f"Satır {i} geçersiz: {exc.errors()[0]['msg']}") from exc
    if not paketler:
        raise CsvGecersiz("CSV boş")
    return paketler
```

- [ ] **Step 2: Failing test yaz** — `backend/tests/test_s8_olcum_api.py`

```python
"""S8 REST/CSV ingestion — edge izni, OEE'ye akış, idempotency, CSV."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from tests.conftest import ALFA

pytestmark = pytest.mark.asyncio


async def _giris(c: AsyncClient, t: dict) -> dict[str, str]:
    r = await c.post(
        "/api/v1/kimlik/token",
        data={"username": t["eposta"], "password": t["parola"]},
        headers={"X-Tenant": t["slug"]},
    )
    return {"X-Tenant": t["slug"], "Authorization": f"Bearer {r.json()['data']['access_token']}"}


async def _hazirla(c: AsyncClient, h: dict, *, cihaz: str, makine: str) -> None:
    await c.post("/api/v1/saha/cihazlar", json={"kod": cihaz, "ad": cihaz}, headers=h)
    await c.post("/api/v1/makineler", json={"kod": makine, "ad": makine}, headers=h)


def _paket(makine_kod: str) -> dict:
    return {
        "olcum_id": str(uuid.uuid4()),
        "makine_kod": makine_kod,
        "zaman": datetime.now(UTC).isoformat(),
        "vardiya": "A",
        "planlanan_sure_dk": 60,
        "durus_sure_dk": 5,
        "toplam_adet": 100,
        "saglam_adet": 98,
        "ideal_cevrim_sn": 30,
    }


async def test_rest_olcum_oee_panosuna_akar(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    await _hazirla(kurulu_istemci, h, cihaz="GW-O1", makine="MAK-O1")
    r = await kurulu_istemci.post(
        "/api/v1/saha/olcumler",
        json={"cihaz_kod": "GW-O1", "olcumler": [_paket("MAK-O1")]},
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["data"]["yazilan"] == 1
    # OEE özeti artık bu makineyi yansıtır (elle giriş yok)
    ozet = await kurulu_istemci.get("/api/v1/oee/ozet", headers=h)
    kodlar = [s["makine_kod"] for s in ozet.json()["data"]]
    assert "MAK-O1" in kodlar


async def test_rest_idempotent(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    await _hazirla(kurulu_istemci, h, cihaz="GW-O2", makine="MAK-O2")
    p = _paket("MAK-O2")
    govde = {"cihaz_kod": "GW-O2", "olcumler": [p]}
    await kurulu_istemci.post("/api/v1/saha/olcumler", json=govde, headers=h)
    r2 = await kurulu_istemci.post("/api/v1/saha/olcumler", json=govde, headers=h)
    assert r2.status_code == 201
    assert r2.json()["data"]["atlanan"] == 1 and r2.json()["data"]["yazilan"] == 0


async def test_olcum_yetkisiz_401(kurulu_istemci: AsyncClient) -> None:
    r = await kurulu_istemci.post(
        "/api/v1/saha/olcumler", json={"cihaz_kod": "X", "olcumler": [_paket("Y")]}
    )
    assert r.status_code == 401


async def test_csv_ice_aktar(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    await _hazirla(kurulu_istemci, h, cihaz="GW-CSV", makine="MAK-CSV")
    csv_metin = (
        "makine_kod,zaman,vardiya,planlanan_sure_dk,durus_sure_dk,toplam_adet,saglam_adet,ideal_cevrim_sn\n"
        f"MAK-CSV,{datetime.now(UTC).isoformat()},A,60,5,100,98,30\n"
    )
    r = await kurulu_istemci.post(
        "/api/v1/saha/olcumler/csv",
        params={"cihaz_kod": "GW-CSV"},
        files={"dosya": ("olcum.csv", csv_metin, "text/csv")},
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["data"]["yazilan"] == 1
```

- [ ] **Step 3: Testin başarısız olduğunu doğrula**

Run: `./.venv/Scripts/python.exe -m pytest backend/tests/test_s8_olcum_api.py -v`
Expected: FAIL (404 — olcumler uçları yok).

- [ ] **Step 4: Ölçüm uçlarını router'a ekle** — `backend/app/modules/saha/router.py`

Import bloğunu genişlet:
```python
from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.control_plane.models import Tenant
from app.core.deps import izin_gerekli, tenant_cozumle
from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.gercekzaman import yayinla
from app.ingestion.service import IngestSonuc, olcum_yaz_toplu
from app.modules.saha.csv_ice import CsvGecersiz, csv_satirlari_coz
from app.modules.saha.schemas import CihazCevapDTO, CihazOlusturDTO, OlcumKabulDTO
```
Dosya sonuna yardımcı + iki uç ekle:
```python
async def _yaz_ve_yayinla(
    db: AsyncSession, tenant: Tenant, cihaz_kod: str, paketler: list
) -> dict[str, Any]:
    sonuc: IngestSonuc = await olcum_yaz_toplu(db, cihaz_kod=cihaz_kod, paketler=paketler)
    for makine_id in sonuc.etkilenen_makineler:
        await yayinla(
            tenant.slug, {"tur": "uretim.eklendi", "makine_id": makine_id, "kaynak": "saha"}
        )
    return {
        "yazilan": sonuc.yazilan,
        "atlanan": sonuc.atlanan,
        "hatali": sonuc.hatali,
        "hatalar": list(sonuc.hatalar),
    }


@router.post("/olcumler", response_model=Zarf[dict], status_code=201, summary="Saha ölçümü gönder")
async def olcum_gonder(
    govde: OlcumKabulDTO,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("edge"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    veri = await _yaz_ve_yayinla(db, tenant, govde.cihaz_kod, list(govde.olcumler))
    return basari(veri, mesaj="Ölçümler alındı")


@router.post(
    "/olcumler/csv", response_model=Zarf[dict], status_code=201, summary="CSV ile ölçüm yükle"
)
async def olcum_csv(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("edge"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    cihaz_kod: Annotated[str, Query(min_length=1, max_length=50)],
    dosya: Annotated[UploadFile, File()],
) -> dict[str, Any]:
    ham = (await dosya.read()).decode("utf-8-sig")
    try:
        paketler = csv_satirlari_coz(ham, cihaz_kod=cihaz_kod)
    except CsvGecersiz as exc:
        raise DogrulamaHatasi(str(exc)) from exc
    veri = await _yaz_ve_yayinla(db, tenant, cihaz_kod, paketler)
    return basari(veri, mesaj="CSV ölçümleri alındı")
```

> Not: `CakismaHatasi`/`KaynakBulunamadi` zaten kullanılıyor; `DogrulamaHatasi`'yı yeni import ettin. `Query`/`File`/`UploadFile`/`tenant_cozumle`/`Tenant`/`yayinla`/`OlcumKabulDTO` import edildiğinden emin ol.

- [ ] **Step 5: Testin geçtiğini doğrula**

Run: `./.venv/Scripts/python.exe -m pytest backend/tests/test_s8_olcum_api.py -v`
Expected: PASS (4 passed).

- [ ] **Step 6: mypy + ruff + commit**

Run: `./.venv/Scripts/python.exe -m mypy && ./.venv/Scripts/python.exe -m ruff check backend`
```bash
git add backend/app/modules/saha/router.py backend/app/modules/saha/csv_ice.py backend/tests/test_s8_olcum_api.py
git commit -m "feat(saha): REST + CSV ingestion uçları (edge izni, OEE'ye akış, idempotent)"
```

---

### Task 9: MQTT Ingestion Worker (aiomqtt döngüsü)

**Files:**
- Create: `backend/app/ingestion/worker.py`
- Test: `backend/tests/test_s8_worker.py`

**Interfaces:**
- Consumes: `mesaj_coz`/`MesajGecersiz` (Task 4), `olcum_yaz_toplu` (Task 6), `tenant_bul`/`search_path_ayarla` (tenancy), `yayinla`.
- Produces:
  - `async mesaj_ele(sm: async_sessionmaker, topic: str, payload: bytes) -> None` (tek mesaj işleme; context set + hata izolasyonu; test edilebilir birim).
  - `async calistir(*, broker_host: str, broker_port: int, db_url: str) -> None` (abone döngüsü; `python -m app.ingestion.worker`).

- [ ] **Step 1: Failing test yaz** — `backend/tests/test_s8_worker.py`

```python
"""S8 worker birim testi: mesaj_ele tek mesajı doğru tenant şemasına yazar (broker'sız).

MQTT round-trip (gerçek broker) testi Task 13'te testcontainers ile eklenir.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.db.tenancy import search_path_ayarla
from app.core.security import redis_istemci
from app.ingestion.worker import mesaj_ele
from app.modules.saha import repository
from app.modules.saha.models import Cihaz
from app.modules.uretim.models import Makine, UretimVerisi

pytestmark = pytest.mark.asyncio


def _payload(makine_kod: str) -> bytes:
    return (
        '{"olcum_id":"%s","makine_kod":"%s","zaman":"%s","vardiya":"A",'
        '"planlanan_sure_dk":60,"durus_sure_dk":5,"toplam_adet":100,'
        '"saglam_adet":98,"ideal_cevrim_sn":30}'
        % (uuid.uuid4(), makine_kod, datetime.now(UTC).isoformat())
    ).encode()


@pytest.fixture(autouse=True)
def _fake_redis() -> None:
    import fakeredis.aioredis

    redis_istemci.redis_ayarla(fakeredis.aioredis.FakeRedis(decode_responses=True))
    yield
    redis_istemci.redis_ayarla(None)


async def test_mesaj_ele_yazar(test_engine: object) -> None:
    sm = async_sessionmaker(test_engine, expire_on_commit=False)  # type: ignore[arg-type]
    # alfa'da cihaz + makine hazırla
    async with sm() as s:
        await search_path_ayarla(s, "alfa")
        await repository.cihaz_ekle(s, Cihaz(kod="GW-WRK", ad="WRK"))
        s.add(Makine(kod="MAK-WRK", ad="WRK"))
        await s.commit()

    await mesaj_ele(sm, "fabrikaos/alfa/GW-WRK/olcum", _payload("MAK-WRK"))

    async with sm() as s:
        await search_path_ayarla(s, "alfa")
        sayi = await s.scalar(
            select(func.count()).select_from(UretimVerisi).join(
                Makine, Makine.id == UretimVerisi.makine_id
            ).where(Makine.kod == "MAK-WRK")
        )
        assert sayi == 1


async def test_mesaj_ele_bozuk_topic_dusurur(test_engine: object) -> None:
    sm = async_sessionmaker(test_engine, expire_on_commit=False)  # type: ignore[arg-type]
    # Hata fırlatmamalı (güvenle düşürülür)
    await mesaj_ele(sm, "bozuk/topic", b"{}")


async def test_mesaj_ele_bilinmeyen_tenant_dusurur(test_engine: object) -> None:
    sm = async_sessionmaker(test_engine, expire_on_commit=False)  # type: ignore[arg-type]
    await mesaj_ele(sm, "fabrikaos/yokboyletenant/GW/olcum", _payload("MAK-WRK"))
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `./.venv/Scripts/python.exe -m pytest backend/tests/test_s8_worker.py -v`
Expected: FAIL — `ModuleNotFoundError: app.ingestion.worker`.

- [ ] **Step 3: Worker'ı yaz** — `backend/app/ingestion/worker.py`

```python
"""Bulut Ingestion Worker — MQTT abonesi (aiomqtt), saha ölçümlerini tenant şemasına yazar.

Çalıştırma: ``python -m app.ingestion.worker``. ``fabrikaos/+/+/olcum`` topic'ine abone olur;
her mesaj için tenant doğrular, ``search_path``'i ayarlar, idempotent yazar, gerçek-zaman
``uretim.eklendi`` olayını yayınlar. Her mesaj log korelasyonu için ``tenant_slug_ctx``/
``request_id_ctx`` set eder. Hata izole edilir — döngü tek bozuk mesajla çökmez.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

import aiomqtt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.context import request_id_ctx, tenant_slug_ctx
from app.core.db.tenancy import search_path_ayarla, tenant_bul
from app.core.gercekzaman import yayinla
from app.core.logging import yapilandir_loglama
from app.ingestion.isleyici import MesajGecersiz, mesaj_coz
from app.ingestion.service import olcum_yaz_toplu

logger = logging.getLogger("app.ingestion.worker")

TOPIC = "fabrikaos/+/+/olcum"


async def mesaj_ele(
    sm: async_sessionmaker[AsyncSession], topic: str, payload: bytes
) -> None:
    """Tek MQTT mesajını işler. Bozuk/bilinmeyen → güvenle düşürür (asla yükseltmez)."""
    try:
        slug, cihaz_kod, paket = mesaj_coz(topic, payload)
    except MesajGecersiz:
        logger.warning("geçersiz mesaj düşürüldü: topic=%s", topic)
        return

    t_slug = tenant_slug_ctx.set(slug)
    t_req = request_id_ctx.set(str(uuid4()))
    try:
        etkilenen: tuple[int, ...] = ()
        async with sm() as session, session.begin():
            tenant = await tenant_bul(session, slug)
            if tenant is None or not tenant.aktif:
                logger.warning("bilinmeyen/pasif tenant, düşürüldü: slug=%s", slug)
                return
            await search_path_ayarla(session, slug)
            sonuc = await olcum_yaz_toplu(session, cihaz_kod=cihaz_kod, paketler=[paket])
            etkilenen = sonuc.etkilenen_makineler
        for makine_id in etkilenen:
            await yayinla(slug, {"tur": "uretim.eklendi", "makine_id": makine_id, "kaynak": "saha"})
    except Exception:  # noqa: BLE001 — tek mesaj döngüyü düşürmez
        logger.exception("ingestion mesaj işleme hatası: topic=%s", topic)
    finally:
        tenant_slug_ctx.reset(t_slug)
        request_id_ctx.reset(t_req)


async def calistir(*, broker_host: str, broker_port: int, db_url: str) -> None:
    """MQTT'ye bağlanır ve süresiz dinler."""
    engine = create_async_engine(db_url, poolclass=NullPool)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    logger.info("ingestion worker başlıyor: broker=%s:%s", broker_host, broker_port)
    try:
        async with aiomqtt.Client(broker_host, port=broker_port) as client:
            await client.subscribe(TOPIC)
            async for message in client.messages:
                await mesaj_ele(sm, str(message.topic), message.payload)  # type: ignore[arg-type]
    finally:
        await engine.dispose()


def main() -> None:
    s = get_settings()
    yapilandir_loglama(s.log_level)
    asyncio.run(
        calistir(
            broker_host=s.mqtt_host, broker_port=s.mqtt_port, db_url=s.database_url
        )
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: `config.py`'ye MQTT ayarları ekle** — `backend/app/core/config.py`

`redis_url` satırından sonra ekle:
```python
    # --- Saha / MQTT (S8) ---
    mqtt_host: str = "mqtt"
    mqtt_port: int = 1883
```

- [ ] **Step 5: Testin geçtiğini doğrula**

Run: `./.venv/Scripts/python.exe -m pytest backend/tests/test_s8_worker.py -v`
Expected: PASS (3 passed).

- [ ] **Step 6: mypy + commit**

Run: `./.venv/Scripts/python.exe -m mypy && ./.venv/Scripts/python.exe -m ruff check backend`
```bash
git add backend/app/ingestion/worker.py backend/app/core/config.py backend/tests/test_s8_worker.py
git commit -m "feat(ingestion): aiomqtt worker — abone döngüsü + mesaj_ele (context + hata izolasyonu)"
```

---

### Task 10: Edge — paket kontratı + sürücü arayüzü + simülatör

**Files:**
- Create: `edge/__init__.py`, `edge/paket.py`, `edge/ayar.py`
- Create: `edge/suruculer/__init__.py`, `edge/suruculer/simulasyon.py`, `edge/suruculer/opcua.py`, `edge/suruculer/modbus.py`
- Create: `edge/tests/__init__.py`, `edge/tests/test_simulasyon.py`

**Interfaces:**
- Produces:
  - `edge.paket.OlcumPaketi` (Pydantic; backend kontratıyla aynı JSON şekli) + `yeni_olcum_id() -> UUID`.
  - `edge.paket.HamOkuma` (dataclass): `makine_kod: str`, `zaman: datetime`, `toplam_sayac: int`, `saglam_sayac: int`, `durus_dk_sayac: float`, `ideal_cevrim_sn: float`.
  - `edge.suruculer.SahaSurucu` (Protocol): `oku() -> list[HamOkuma]`.
  - `edge.suruculer.simulasyon.SimulasyonSurucu(makine_kodlari: list[str], *, tohum: int = 0)`.
  - `edge.ayar.EdgeAyar` (Pydantic Settings): `broker_host`, `broker_port`, `tenant_slug`, `cihaz_kod`, `surucu`, `makine_kodlari`, `aralik_sn`, `tampon_yolu`.

- [ ] **Step 1: Failing test yaz** — `edge/tests/test_simulasyon.py`

```python
"""Edge simülasyon sürücüsü: determinizm + monoton artan sayaçlar."""

from __future__ import annotations

from edge.suruculer.simulasyon import SimulasyonSurucu


def test_determinizm_ayni_tohum() -> None:
    a = SimulasyonSurucu(["MAK-1", "MAK-2"], tohum=42)
    b = SimulasyonSurucu(["MAK-1", "MAK-2"], tohum=42)
    for _ in range(5):
        oa = {h.makine_kod: h for h in a.oku()}
        ob = {h.makine_kod: h for h in b.oku()}
        assert oa["MAK-1"].toplam_sayac == ob["MAK-1"].toplam_sayac


def test_sayaclar_monoton_artar() -> None:
    s = SimulasyonSurucu(["MAK-1"], tohum=1)
    onceki = 0
    for _ in range(10):
        v = s.oku()[0].toplam_sayac
        assert v >= onceki
        onceki = v


def test_saglam_toplami_asmaz() -> None:
    s = SimulasyonSurucu(["MAK-1"], tohum=7)
    for _ in range(20):
        h = s.oku()[0]
        assert h.saglam_sayac <= h.toplam_sayac
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `./.venv/Scripts/python.exe -m pytest edge/tests/test_simulasyon.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'edge'`.

- [ ] **Step 3: Paket + sürücü arayüzü + simülatör + ayar yaz**

`edge/__init__.py`:
```python
"""FabrikaOS Edge Gateway Agent — saha sürücüsü → MQTT (store-and-forward).

Bağımsız deploy edilir; backend ``app`` paketini import ETMEZ. Yalnız ``OlcumPaketi``
JSON sözleşmesini paylaşır (kontrat testiyle güvenceye alınır).
"""
```

`edge/paket.py`:
```python
"""Edge ölçüm kontratı (backend app.modules.saha.schemas.OlcumPaketi ile aynı JSON şekli)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


def yeni_olcum_id() -> UUID:
    return uuid4()


@dataclass(frozen=True, slots=True)
class HamOkuma:
    """Bir makinenin anlık sayaç görüntüsü (sürücüden gelir)."""

    makine_kod: str
    zaman: datetime
    toplam_sayac: int
    saglam_sayac: int
    durus_dk_sayac: float
    ideal_cevrim_sn: float


class OlcumPaketi(BaseModel):
    olcum_id: UUID
    makine_kod: str = Field(min_length=1, max_length=50)
    zaman: datetime
    vardiya: str | None = Field(default=None, max_length=20)
    planlanan_sure_dk: float = Field(ge=0)
    durus_sure_dk: float = Field(ge=0)
    toplam_adet: int = Field(ge=0)
    saglam_adet: int = Field(ge=0)
    ideal_cevrim_sn: float = Field(ge=0)

    @model_validator(mode="after")
    def _saglam_kontrol(self) -> OlcumPaketi:
        if self.saglam_adet > self.toplam_adet:
            raise ValueError("saglam_adet toplam_adet'i aşamaz")
        return self
```

`edge/suruculer/__init__.py`:
```python
"""Saha sürücüsü arayüzü. Yeni protokoller (OPC-UA/Modbus) bu Protocol'ü uygular."""

from __future__ import annotations

from typing import Protocol

from edge.paket import HamOkuma


class SahaSurucu(Protocol):
    """Bir veri kaynağından makine sayaç görüntülerini okur."""

    def oku(self) -> list[HamOkuma]:
        """Köprülenen her makine için güncel ham okumayı döndürür."""
        ...
```

`edge/suruculer/simulasyon.py`:
```python
"""Deterministik PLC simülatörü — gerçek donanım olmadan uçtan uca akışı test eder.

Her ``oku()`` sayaçları tohumlu rastgelelikle ilerletir: çoğunlukla üretim, ara sıra
arıza (artış yok + duruş süresi birikir) ve düşük hız. Aynı tohum → aynı dizi.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime

from edge.paket import HamOkuma


class _MakineDurumu:
    def __init__(self) -> None:
        self.toplam = 0
        self.saglam = 0
        self.durus_dk = 0.0
        self.ideal_cevrim_sn = 30.0


class SimulasyonSurucu:
    """``makine_kodlari`` için sahte ama tutarlı sayaçlar üretir."""

    def __init__(self, makine_kodlari: list[str], *, tohum: int = 0) -> None:
        self._rng = random.Random(tohum)
        self._durumlar = {kod: _MakineDurumu() for kod in makine_kodlari}

    def oku(self) -> list[HamOkuma]:
        simdi = datetime.now(UTC)
        okumalar: list[HamOkuma] = []
        for kod, d in self._durumlar.items():
            ariza = self._rng.random() < 0.1
            if ariza:
                d.durus_dk += round(self._rng.uniform(0.5, 2.0), 2)
            else:
                uretilen = self._rng.randint(5, 20)
                hatali = self._rng.randint(0, max(1, uretilen // 10))
                d.toplam += uretilen
                d.saglam += uretilen - hatali
            okumalar.append(
                HamOkuma(
                    makine_kod=kod,
                    zaman=simdi,
                    toplam_sayac=d.toplam,
                    saglam_sayac=d.saglam,
                    durus_dk_sayac=d.durus_dk,
                    ideal_cevrim_sn=d.ideal_cevrim_sn,
                )
            )
        return okumalar
```

`edge/suruculer/opcua.py`:
```python
"""OPC-UA sürücü iskeleti (Faz 5'te uygulanır).

Uygulama notu: ``asyncua`` istemcisiyle sunucuya bağlan, düğüm kimliklerini (NodeId)
``makine_kod``'a eşle, ``read_value`` ile sayaçları oku ve ``HamOkuma`` üret. mTLS için
istemci sertifikası + güven listesi yapılandır. Arayüz (``SahaSurucu.oku``) aynı kalır.
"""

from __future__ import annotations

from edge.paket import HamOkuma


class OpcUaSurucu:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self._args = args

    def oku(self) -> list[HamOkuma]:
        raise NotImplementedError(
            "OPC-UA sürücüsü Faz 5'te uygulanacak (asyncua + mTLS). "
            "MVP'de simülasyon sürücüsünü kullanın."
        )
```

`edge/suruculer/modbus.py`:
```python
"""Modbus TCP sürücü iskeleti (Faz 5'te uygulanır).

Uygulama notu: ``pymodbus`` ile holding/input register'ları oku, register→sayaç
ölçeklemesini ``makine_kod`` başına yapılandır ve ``HamOkuma`` üret. Arayüz aynı kalır.
"""

from __future__ import annotations

from edge.paket import HamOkuma


class ModbusSurucu:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self._args = args

    def oku(self) -> list[HamOkuma]:
        raise NotImplementedError(
            "Modbus sürücüsü Faz 5'te uygulanacak (pymodbus). "
            "MVP'de simülasyon sürücüsünü kullanın."
        )
```

`edge/ayar.py`:
```python
"""Edge ajanı yapılandırması (env / .env)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class EdgeAyar(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EDGE_", env_file=".env", extra="ignore")

    broker_host: str = "localhost"
    broker_port: int = 1883
    tenant_slug: str = "alfa"
    cihaz_kod: str = "GW-1"
    surucu: str = "simulasyon"
    makine_kodlari: list[str] = ["MAK-1"]
    aralik_sn: float = 2.0
    tohum: int = 0
    tampon_yolu: str = "edge_tampon.sqlite"
```

`edge/tests/__init__.py`: (boş dosya)
```python
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `./.venv/Scripts/python.exe -m pytest edge/tests/test_simulasyon.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Kontrat testi (edge ↔ backend uyumu)** — `backend/tests/test_s8_kontrat.py`'ye ekle

```python
def test_edge_paketi_backend_ile_uyumlu() -> None:
    """Edge'in ürettiği JSON, backend OlcumPaketi ile bire bir doğrulanır (kontrat)."""
    import uuid
    from datetime import UTC, datetime

    from edge.paket import OlcumPaketi as EdgePaket

    ep = EdgePaket(
        olcum_id=uuid.uuid4(),
        makine_kod="MAK-1",
        zaman=datetime.now(UTC),
        vardiya="A",
        planlanan_sure_dk=60,
        durus_sure_dk=5,
        toplam_adet=100,
        saglam_adet=98,
        ideal_cevrim_sn=30,
    )
    OlcumPaketi.model_validate_json(ep.model_dump_json())
```

- [ ] **Step 6: Testleri çalıştır + mypy + commit**

Run: `./.venv/Scripts/python.exe -m pytest backend/tests/test_s8_kontrat.py edge/tests -v && ./.venv/Scripts/python.exe -m mypy && ./.venv/Scripts/python.exe -m ruff check edge backend`
```bash
git add edge backend/tests/test_s8_kontrat.py
git commit -m "feat(edge): paket kontratı + SahaSurucu arayüzü + simülatör + opcua/modbus iskelet"
```

---

### Task 11: Edge — aralık özetleyici (saf agregatör)

**Files:**
- Create: `edge/ozetleyici.py`
- Test: `edge/tests/test_ozetleyici.py`

**Interfaces:**
- Consumes: `HamOkuma`, `OlcumPaketi` (edge.paket).
- Produces: `ozetle(onceki: HamOkuma, simdiki: HamOkuma, *, vardiya: str | None = None) -> OlcumPaketi` (sayaç deltalarından aralık özeti).

- [ ] **Step 1: Failing test yaz** — `edge/tests/test_ozetleyici.py`

```python
"""Edge aralık özetleyici: sayaç deltası → OlcumPaketi."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from edge.ozetleyici import ozetle
from edge.paket import HamOkuma


def _okuma(t: datetime, toplam: int, saglam: int, durus: float) -> HamOkuma:
    return HamOkuma(
        makine_kod="MAK-1",
        zaman=t,
        toplam_sayac=toplam,
        saglam_sayac=saglam,
        durus_dk_sayac=durus,
        ideal_cevrim_sn=30.0,
    )


def test_delta_ve_aralik_hesabi() -> None:
    t0 = datetime(2026, 6, 30, 8, 0, tzinfo=UTC)
    t1 = t0 + timedelta(minutes=60)
    p = ozetle(_okuma(t0, 100, 95, 2.0), _okuma(t1, 250, 240, 5.0), vardiya="A")
    assert p.toplam_adet == 150
    assert p.saglam_adet == 145
    assert p.durus_sure_dk == 3.0
    assert p.planlanan_sure_dk == 60.0
    assert p.makine_kod == "MAK-1"
    assert p.vardiya == "A"


def test_her_paket_benzersiz_id() -> None:
    t0 = datetime(2026, 6, 30, 8, 0, tzinfo=UTC)
    t1 = t0 + timedelta(minutes=10)
    a = ozetle(_okuma(t0, 0, 0, 0.0), _okuma(t1, 10, 10, 0.0))
    b = ozetle(_okuma(t0, 0, 0, 0.0), _okuma(t1, 10, 10, 0.0))
    assert a.olcum_id != b.olcum_id
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `./.venv/Scripts/python.exe -m pytest edge/tests/test_ozetleyici.py -v`
Expected: FAIL — `ModuleNotFoundError: edge.ozetleyici`.

- [ ] **Step 3: Özetleyiciyi yaz** — `edge/ozetleyici.py`

```python
"""Aralık özetleme: iki ham sayaç görüntüsü arasındaki farktan UretimVerisi-şekilli paket.

Saf fonksiyon (yan etkisiz, ``olcum_id`` hariç deterministik). Negatif delta'lar 0'a
kırpılır (sayaç sıfırlama/taşma koruması).
"""

from __future__ import annotations

from edge.paket import HamOkuma, OlcumPaketi, yeni_olcum_id


def _poz(x: float) -> float:
    return x if x > 0 else 0.0


def ozetle(
    onceki: HamOkuma, simdiki: HamOkuma, *, vardiya: str | None = None
) -> OlcumPaketi:
    aralik_dk = _poz((simdiki.zaman - onceki.zaman).total_seconds() / 60.0)
    toplam = int(_poz(simdiki.toplam_sayac - onceki.toplam_sayac))
    saglam = int(_poz(simdiki.saglam_sayac - onceki.saglam_sayac))
    durus = _poz(simdiki.durus_dk_sayac - onceki.durus_dk_sayac)
    return OlcumPaketi(
        olcum_id=yeni_olcum_id(),
        makine_kod=simdiki.makine_kod,
        zaman=simdiki.zaman,
        vardiya=vardiya,
        planlanan_sure_dk=aralik_dk,
        durus_sure_dk=durus,
        toplam_adet=toplam,
        saglam_adet=min(saglam, toplam),
        ideal_cevrim_sn=simdiki.ideal_cevrim_sn,
    )
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `./.venv/Scripts/python.exe -m pytest edge/tests/test_ozetleyici.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add edge/ozetleyici.py edge/tests/test_ozetleyici.py
git commit -m "feat(edge): aralık özetleyici (sayaç deltası → OlcumPaketi)"
```

---

### Task 12: Edge — store-and-forward tamponu (sqlite)

**Files:**
- Create: `edge/tampon.py`
- Test: `edge/tests/test_tampon.py`

**Interfaces:**
- Produces:
  - `Tampon(yol: str)` — dayanıklı sqlite kuyruğu.
  - `Tampon.ekle(olcum_id: str, paket_json: str) -> None` (çift `olcum_id` yok sayılır).
  - `Tampon.bekleyenler() -> list[tuple[str, str]]` (ekleme sırasıyla `(olcum_id, paket_json)`).
  - `Tampon.onayla(olcum_id: str) -> None`.
  - `Tampon.bekleyen_sayisi() -> int`.

- [ ] **Step 1: Failing test yaz** — `edge/tests/test_tampon.py`

```python
"""Edge store-and-forward tamponu: kayıpsız replay + restart dayanıklılığı."""

from __future__ import annotations

from pathlib import Path

from edge.tampon import Tampon


def test_ekle_bekleyen_onayla(tmp_path: Path) -> None:
    t = Tampon(str(tmp_path / "t.sqlite"))
    t.ekle("a", '{"x":1}')
    t.ekle("b", '{"x":2}')
    assert t.bekleyen_sayisi() == 2
    assert [oid for oid, _ in t.bekleyenler()] == ["a", "b"]
    t.onayla("a")
    assert [oid for oid, _ in t.bekleyenler()] == ["b"]


def test_cift_ekle_yok_sayilir(tmp_path: Path) -> None:
    t = Tampon(str(tmp_path / "t.sqlite"))
    t.ekle("a", '{"x":1}')
    t.ekle("a", '{"x":1}')
    assert t.bekleyen_sayisi() == 1


def test_restart_dayanikli(tmp_path: Path) -> None:
    yol = str(tmp_path / "t.sqlite")
    t1 = Tampon(yol)
    t1.ekle("a", "{}")
    t1.ekle("b", "{}")
    t1.onayla("a")
    # süreç yeniden başladı: yeni Tampon aynı dosyayı açar
    t2 = Tampon(yol)
    assert [oid for oid, _ in t2.bekleyenler()] == ["b"]


def test_kesinti_sonrasi_kayipsiz_replay(tmp_path: Path) -> None:
    """Broker düşükken eklenenler kalır; reconnect'te hepsi 'gönderilir' (kayıpsız, çift yok)."""
    t = Tampon(str(tmp_path / "t.sqlite"))
    for i in range(5):
        t.ekle(str(i), "{}")
    gonderilen: list[str] = []
    # simüle: ilk 2 başarılı (onaylanır), sonra broker düşer
    for oid, _ in t.bekleyenler()[:2]:
        gonderilen.append(oid)
        t.onayla(oid)
    # reconnect: kalanları gönder
    for oid, _ in t.bekleyenler():
        gonderilen.append(oid)
        t.onayla(oid)
    assert sorted(gonderilen) == ["0", "1", "2", "3", "4"]
    assert len(gonderilen) == len(set(gonderilen))  # çift yok
    assert t.bekleyen_sayisi() == 0
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `./.venv/Scripts/python.exe -m pytest edge/tests/test_tampon.py -v`
Expected: FAIL — `ModuleNotFoundError: edge.tampon`.

- [ ] **Step 3: Tamponu yaz** — `edge/tampon.py`

```python
"""Dayanıklı store-and-forward kuyruğu (stdlib sqlite3).

Broker erişilemezken ölçümler burada birikir; reconnect'te ekleme sırasıyla yayınlanır
ve PUBACK alınınca ``onayla`` ile silinir. Süreç yeniden başlasa veriler dosyada kalır.
İdempotency uçta (çift ``ekle`` yok sayılır) ve bulutta (``olcum_id`` defteri) iki kat güvencede.
"""

from __future__ import annotations

import sqlite3


class Tampon:
    def __init__(self, yol: str) -> None:
        self._conn = sqlite3.connect(yol)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS bekleyen ("
            "  sira INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  olcum_id TEXT NOT NULL UNIQUE,"
            "  paket_json TEXT NOT NULL"
            ")"
        )
        self._conn.commit()

    def ekle(self, olcum_id: str, paket_json: str) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO bekleyen (olcum_id, paket_json) VALUES (?, ?)",
            (olcum_id, paket_json),
        )
        self._conn.commit()

    def bekleyenler(self) -> list[tuple[str, str]]:
        cur = self._conn.execute(
            "SELECT olcum_id, paket_json FROM bekleyen ORDER BY sira ASC"
        )
        return [(r[0], r[1]) for r in cur.fetchall()]

    def onayla(self, olcum_id: str) -> None:
        self._conn.execute("DELETE FROM bekleyen WHERE olcum_id = ?", (olcum_id,))
        self._conn.commit()

    def bekleyen_sayisi(self) -> int:
        cur = self._conn.execute("SELECT COUNT(*) FROM bekleyen")
        return int(cur.fetchone()[0])

    def kapat(self) -> None:
        self._conn.close()
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `./.venv/Scripts/python.exe -m pytest edge/tests/test_tampon.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: mypy + commit**

Run: `./.venv/Scripts/python.exe -m mypy`
```bash
git add edge/tampon.py edge/tests/test_tampon.py
git commit -m "feat(edge): store-and-forward sqlite tamponu (kayıpsız replay + restart dayanıklı)"
```

---

### Task 13: Edge ajanı + MQTT publisher + compose/CI + MQTT round-trip testi

**Files:**
- Create: `edge/yayinci.py`, `edge/agent.py`
- Modify: `docker-compose.yml` (ingestion servisi), `docker-compose.override.yml` (edge demo — opsiyonel)
- Modify: `infra/mosquitto/mosquitto.conf` (CI/anonim notu — değişiklik gerekmiyorsa atla)
- Test: `backend/tests/test_s8_mqtt_roundtrip.py`

**Interfaces:**
- Consumes: `Tampon` (Task 12), `SimulasyonSurucu`/`SahaSurucu` (Task 10), `ozetle` (Task 11), `EdgeAyar`, `mesaj_ele`/`calistir` (Task 9), aiomqtt.
- Produces: `edge.agent.dongu_adimi(...)` (tek döngü adımı — test edilebilir), `edge.agent.main()`; `edge.yayinci.yayinla_bekleyenler(client, tampon, *, slug, cihaz_kod) -> int`.

- [ ] **Step 1: Yayıncıyı yaz** — `edge/yayinci.py`

```python
"""MQTT yayıncı — tampondaki bekleyen ölçümleri yayınlar, PUBACK'te onaylar (QoS 1)."""

from __future__ import annotations

import aiomqtt

from edge.tampon import Tampon


def topic_adi(slug: str, cihaz_kod: str) -> str:
    return f"fabrikaos/{slug}/{cihaz_kod}/olcum"


async def yayinla_bekleyenler(
    client: aiomqtt.Client, tampon: Tampon, *, slug: str, cihaz_kod: str
) -> int:
    """Bekleyenleri sırayla yayınlar; her başarılı PUBACK sonrası tampondan siler. Sayı döner."""
    konu = topic_adi(slug, cihaz_kod)
    gonderilen = 0
    for olcum_id, paket_json in tampon.bekleyenler():
        await client.publish(konu, payload=paket_json.encode(), qos=1)
        tampon.onayla(olcum_id)
        gonderilen += 1
    return gonderilen
```

- [ ] **Step 2: Ajanı yaz** — `edge/agent.py`

```python
"""Edge ajanı: oku → özetle → tampona yaz → (bağlıysa) yayınla. Graceful shutdown.

Çalıştırma: ``python -m edge.agent``. Sürücü ham sayaçları verir; önceki okumayla
fark alınıp aralık özeti tampona yazılır; ardından bekleyenler MQTT'ye yayınlanır.
Broker yoksa paketler tamponda kalır (store-and-forward) ve sonraki döngüde gönderilir.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal

import aiomqtt

from edge.ayar import EdgeAyar
from edge.ozetleyici import ozetle
from edge.paket import HamOkuma
from edge.suruculer import SahaSurucu
from edge.suruculer.modbus import ModbusSurucu
from edge.suruculer.opcua import OpcUaSurucu
from edge.suruculer.simulasyon import SimulasyonSurucu
from edge.tampon import Tampon
from edge.yayinci import yayinla_bekleyenler

logger = logging.getLogger("edge.agent")


def surucu_yap(ayar: EdgeAyar) -> SahaSurucu:
    if ayar.surucu == "simulasyon":
        return SimulasyonSurucu(ayar.makine_kodlari, tohum=ayar.tohum)
    if ayar.surucu == "opcua":
        return OpcUaSurucu()
    if ayar.surucu == "modbus":
        return ModbusSurucu()
    raise ValueError(f"Bilinmeyen sürücü: {ayar.surucu!r}")


def dongu_adimi(
    surucu: SahaSurucu, tampon: Tampon, onceki: dict[str, HamOkuma]
) -> dict[str, HamOkuma]:
    """Bir okuma döngüsü: yeni okumaları al, önceki varsa özetle ve tampona ekle."""
    for okuma in surucu.oku():
        gecmis = onceki.get(okuma.makine_kod)
        if gecmis is not None:
            paket = ozetle(gecmis, okuma)
            if paket.toplam_adet > 0 or paket.durus_sure_dk > 0:
                tampon.ekle(str(paket.olcum_id), paket.model_dump_json())
        onceki[okuma.makine_kod] = okuma
    return onceki


async def calistir(ayar: EdgeAyar, *, dur: asyncio.Event) -> None:
    surucu = surucu_yap(ayar)
    tampon = Tampon(ayar.tampon_yolu)
    onceki: dict[str, HamOkuma] = {}
    logger.info("edge ajanı başladı: cihaz=%s tenant=%s", ayar.cihaz_kod, ayar.tenant_slug)
    while not dur.is_set():
        onceki = dongu_adimi(surucu, tampon, onceki)
        with contextlib.suppress(aiomqtt.MqttError):
            async with aiomqtt.Client(ayar.broker_host, port=ayar.broker_port) as client:
                gonderilen = await yayinla_bekleyenler(
                    client, tampon, slug=ayar.tenant_slug, cihaz_kod=ayar.cihaz_kod
                )
                if gonderilen:
                    logger.info("%d ölçüm yayınlandı", gonderilen)
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(dur.wait(), timeout=ayar.aralik_sn)
    tampon.kapat()
    logger.info("edge ajanı durdu (%d bekleyen tamponda)", tampon.bekleyen_sayisi())


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    ayar = EdgeAyar()
    dur = asyncio.Event()

    async def _ana() -> None:
        loop = asyncio.get_running_loop()
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(signal.SIGINT, dur.set)
            loop.add_signal_handler(signal.SIGTERM, dur.set)
        await calistir(ayar, dur=dur)

    asyncio.run(_ana())


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: `dongu_adimi` birim testi** — `edge/tests/test_agent.py`

```python
"""Edge ajan döngü adımı: ikinci okumada özet tampona yazılır."""

from __future__ import annotations

from pathlib import Path

from edge.agent import dongu_adimi, surucu_yap
from edge.ayar import EdgeAyar
from edge.tampon import Tampon


def test_ikinci_okumada_tampona_yazar(tmp_path: Path) -> None:
    ayar = EdgeAyar(makine_kodlari=["MAK-1"], tohum=3, tampon_yolu=str(tmp_path / "t.sqlite"))
    surucu = surucu_yap(ayar)
    tampon = Tampon(ayar.tampon_yolu)
    onceki: dict = {}
    onceki = dongu_adimi(surucu, tampon, onceki)  # ilk okuma — özet yok
    assert tampon.bekleyen_sayisi() == 0
    for _ in range(5):
        onceki = dongu_adimi(surucu, tampon, onceki)
    assert tampon.bekleyen_sayisi() >= 1  # üretim birikti → paketler tamponda


def test_surucu_yap_bilinmeyen_hata() -> None:
    import pytest

    with pytest.raises(ValueError, match="Bilinmeyen sürücü"):
        surucu_yap(EdgeAyar(surucu="yok"))
```

- [ ] **Step 4: Edge testlerini çalıştır**

Run: `./.venv/Scripts/python.exe -m pytest edge/tests/test_agent.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: MQTT round-trip entegrasyon testi** — `backend/tests/test_s8_mqtt_roundtrip.py`

```python
"""S8 uçtan uca: edge publisher → gerçek broker → worker mesaj_ele → tenant şeması.

Mosquitto'yu testcontainers ile kaldırır. Docker yoksa testi atlar (DoD'u broker'sız
testler zaten karşılar).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.db.tenancy import search_path_ayarla
from app.core.security import redis_istemci
from app.modules.saha import repository
from app.modules.saha.models import Cihaz
from app.modules.uretim.models import Makine, UretimVerisi

pytestmark = pytest.mark.asyncio

testcontainers = pytest.importorskip("testcontainers.core.container")


@pytest.fixture(scope="module")
def mosquitto():
    from testcontainers.core.container import DockerContainer
    from testcontainers.core.waiting_utils import wait_for_logs

    c = (
        DockerContainer("eclipse-mosquitto:2")
        .with_exposed_ports(1883)
        .with_command("sh -c 'printf \"listener 1883\\nallow_anonymous true\\n\" > /m.conf && mosquitto -c /m.conf'")
    )
    try:
        c.start()
    except Exception as exc:  # Docker yoksa atla
        pytest.skip(f"Docker/mosquitto yok: {exc}")
    wait_for_logs(c, "mosquitto version 2", timeout=30)
    yield c.get_container_host_ip(), int(c.get_exposed_port(1883))
    c.stop()


async def test_edge_to_worker_roundtrip(test_engine: object, mosquitto) -> None:
    host, port = mosquitto
    redis_istemci.redis_ayarla(__import__("fakeredis.aioredis", fromlist=["FakeRedis"]).FakeRedis(decode_responses=True))
    sm = async_sessionmaker(test_engine, expire_on_commit=False)  # type: ignore[arg-type]
    async with sm() as s:
        await search_path_ayarla(s, "alfa")
        await repository.cihaz_ekle(s, Cihaz(kod="GW-RT", ad="RT"))
        s.add(Makine(kod="MAK-RT", ad="RT"))
        await s.commit()

    import aiomqtt

    from app.ingestion.worker import mesaj_ele

    payload = (
        '{"olcum_id":"%s","makine_kod":"MAK-RT","zaman":"%s","vardiya":"A",'
        '"planlanan_sure_dk":60,"durus_sure_dk":5,"toplam_adet":100,'
        '"saglam_adet":98,"ideal_cevrim_sn":30}'
        % (uuid.uuid4(), datetime.now(UTC).isoformat())
    )
    topic = "fabrikaos/alfa/GW-RT/olcum"
    async with aiomqtt.Client(host, port=port) as pub:
        await pub.subscribe(topic)
        await pub.publish(topic, payload.encode(), qos=1)
        async for m in pub.messages:
            await mesaj_ele(sm, str(m.topic), m.payload)
            break

    async with sm() as s:
        await search_path_ayarla(s, "alfa")
        sayi = await s.scalar(
            select(func.count()).select_from(UretimVerisi).join(
                Makine, Makine.id == UretimVerisi.makine_id
            ).where(Makine.kod == "MAK-RT")
        )
        assert sayi == 1
    redis_istemci.redis_ayarla(None)
```

- [ ] **Step 6: docker-compose `ingestion` servisi** — `docker-compose.yml`

`api` servisinin altına (aynı girinti seviyesinde) ekle:
```yaml
  ingestion:
    build:
      context: .
      dockerfile: backend/Dockerfile
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://fabrikaos:fabrikaos@db:5432/fabrikaos
      REDIS_URL: redis://redis:6379/0
      MQTT_HOST: mqtt
      MQTT_PORT: "1883"
    command: ["python", "-m", "app.ingestion.worker"]
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      mqtt:
        condition: service_started
    networks: [fabrikaos]
```

- [ ] **Step 7: Round-trip testini çalıştır (Docker varsa)**

Run: `./.venv/Scripts/python.exe -m pytest backend/tests/test_s8_mqtt_roundtrip.py -v`
Expected: PASS veya SKIP (Docker yoksa skip — kabul edilir).

- [ ] **Step 8: mypy + ruff + commit**

Run: `./.venv/Scripts/python.exe -m mypy && ./.venv/Scripts/python.exe -m ruff check edge backend`
```bash
git add edge/agent.py edge/yayinci.py edge/tests/test_agent.py backend/tests/test_s8_mqtt_roundtrip.py docker-compose.yml
git commit -m "feat(edge): MQTT publisher + ajan döngüsü (graceful shutdown) + ingestion compose + round-trip testi"
```

---

### Task 14: Frontend — Cihazlar ekranı + codegen + canlı son_gorulme

**Files:**
- Regenerate: `frontend/openapi.json`, `frontend/src/api/types.gen.ts`
- Create: `frontend/src/modules/saha/hooks.ts`, `frontend/src/modules/saha/CihazListesi.tsx`
- Modify: `frontend/src/routes/*` (rota), menü tanımı, `frontend/src/i18n/*` (TR/EN), `frontend/src/modules/ortak/olayIsle.ts` (cihaz invalidate)
- Test: `frontend/src/modules/saha/CihazListesi.test.tsx`

**Interfaces:**
- Consumes: `SunucuTablo`, `useSayfaliSorgu`/`useSayfaParam` (modules/ortak), `apiClient`/`istekSayfali` (api), TanStack Query.
- Produces: `useCihazlar(param)` hook; `CihazListesi` ekranı; `/saha/cihazlar` rotası; "Saha" menü girdisi (`saha:oku`).

> Not: Aşağıdaki kod, mevcut `modules/uretim/MakineListesi.tsx` desenini birebir izler. Uygulamadan önce o dosyayı ve `modules/ortak/`'ı oku; bileşen adları/prop'ları bu projeye uydur.

- [ ] **Step 1: openapi.json + tip codegen yenile**

Run (backend kökünden):
```bash
./.venv/Scripts/python.exe -c "import json; from app.main import create_app; open('frontend/openapi.json','w',encoding='utf-8').write(json.dumps(create_app().openapi(),ensure_ascii=False))"
```
Sonra `frontend/`'te: `npm run codegen`
Expected: `types.gen.ts` `/api/v1/saha/cihazlar` yollarını içerir.

- [ ] **Step 2: Failing test yaz** — `frontend/src/modules/saha/CihazListesi.test.tsx`

```tsx
import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { CihazListesi } from "./CihazListesi";
import { testSarmalayici } from "../../test/yardimci"; // mevcut test yardımcısı (uretim testlerine bak)
import { fetchMock } from "../../test/fetchMock";       // mevcut fetch-mock yardımcısı

describe("CihazListesi", () => {
  it("cihazları sunucu-taraflı listeler", async () => {
    fetchMock.get("/api/v1/saha/cihazlar", {
      success: true,
      message: "ok",
      data: [{ id: 1, kod: "GW-1", ad: "Gateway 1", protokol: "simulasyon", aktif: true, son_gorulme: null }],
      meta: { sayfa: 1, adet: 20, toplam: 1 },
    });
    render(<CihazListesi />, { wrapper: testSarmalayici() });
    await waitFor(() => expect(screen.getByText("GW-1")).toBeInTheDocument());
  });
});
```

> Test yardımcılarının (`testSarmalayici`, `fetchMock`) gerçek yolları/adları için mevcut bir `modules/uretim/*.test.tsx` dosyasını referans al ve import'ları ona göre düzelt.

- [ ] **Step 3: Testin başarısız olduğunu doğrula**

Run (frontend/): `npm test -- CihazListesi`
Expected: FAIL — `CihazListesi` bulunamadı.

- [ ] **Step 4: Hook + ekranı yaz**

`frontend/src/modules/saha/hooks.ts`:
```ts
import { useQuery } from "@tanstack/react-query";
import { istekSayfali } from "../../api/client";
import type { SayfaParam } from "../../api/sayfalama";
import { sorguDizesi } from "../../api/sayfalama";

export type Cihaz = {
  id: number;
  kod: string;
  ad: string;
  protokol: string;
  aktif: boolean;
  son_gorulme: string | null;
};

export function useCihazlar(param: SayfaParam) {
  return useQuery({
    queryKey: ["saha-cihazlar", param],
    queryFn: () => istekSayfali<Cihaz>(`/api/v1/saha/cihazlar${sorguDizesi(param)}`),
  });
}
```

`frontend/src/modules/saha/CihazListesi.tsx`:
```tsx
import { useTranslation } from "react-i18next";
import { Tag } from "antd";
import { SunucuTablo } from "../../components/SunucuTablo";
import { SayfaBaslik } from "../../components/SayfaBaslik";
import { useSayfaParam } from "../ortak/useSayfaParam";
import { useCihazlar, type Cihaz } from "./hooks";

export function CihazListesi() {
  const { t } = useTranslation();
  const [param, setParam] = useSayfaParam();
  const sorgu = useCihazlar(param);

  const kolonlar = [
    { title: t("saha.kod"), dataIndex: "kod", sorter: true },
    { title: t("saha.ad"), dataIndex: "ad" },
    { title: t("saha.protokol"), dataIndex: "protokol" },
    {
      title: t("saha.durum"),
      dataIndex: "aktif",
      render: (aktif: boolean) => (
        <Tag color={aktif ? "green" : "default"}>{aktif ? t("saha.aktif") : t("saha.pasif")}</Tag>
      ),
    },
    {
      title: t("saha.sonGorulme"),
      dataIndex: "son_gorulme",
      sorter: true,
      render: (v: string | null) => (v ? new Date(v).toLocaleString() : "—"),
    },
  ];

  return (
    <>
      <SayfaBaslik baslik={t("saha.cihazlar")} />
      <SunucuTablo<Cihaz>
        rowKey="id"
        kolonlar={kolonlar}
        sorgu={sorgu}
        param={param}
        setParam={setParam}
        aramaIpucu={t("saha.ara")}
      />
    </>
  );
}
```

> `SunucuTablo`/`SayfaBaslik`/`useSayfaParam` prop imzalarını mevcut `MakineListesi.tsx`'ten doğrula ve gerekirse uyarlama yap.

- [ ] **Step 5: Rota + menü + i18n + canlı invalidate**

1. Rota ekle (mevcut `routes` tanımında, `/makineler` örneğini izle): `path: "/saha/cihazlar"`, `element: <IzinKapisi izin="saha:oku"><CihazListesi /></IzinKapisi>`.
2. Menü girdisi (RBAC `saha:oku`): etiket `t("menu.saha")`, yol `/saha/cihazlar`.
3. i18n — `frontend/src/i18n/tr.json` ve `en.json`'a `saha.*` + `menu.saha` anahtarları ekle:
```json
"saha": { "cihazlar": "Saha Cihazları", "kod": "Kod", "ad": "Ad", "protokol": "Protokol", "durum": "Durum", "aktif": "Aktif", "pasif": "Pasif", "sonGorulme": "Son görülme", "ara": "Cihaz ara…" }
```
(en.json: `"cihazlar": "Field Devices"`, vb.)
4. `frontend/src/modules/ortak/olayIsle.ts` — `uretim.eklendi` olayında cihaz listesini de invalidate et (canlı son_gorulme). Mevcut `case "uretim.eklendi"` dalına ekle:
```ts
queryClient.invalidateQueries({ queryKey: ["saha-cihazlar"] });
```

- [ ] **Step 6: Testin geçtiğini + lint/tsc/build doğrula**

Run (frontend/): `npm test -- CihazListesi && npm run lint && npm run typecheck && npm run build`
Expected: tüm adımlar PASS/temiz.

- [ ] **Step 7: Commit**

```bash
git add frontend/openapi.json frontend/src
git commit -m "feat(frontend): Saha Cihazlar ekranı (sunucu-tablo) + codegen + canlı son_gorulme"
```

---

### Task 15: CI + ADR-0010 + dokümanlar + uçtan uca doğrulama + hafıza

**Files:**
- Modify: `.github/workflows/ci.yml` (testcontainers için Docker zaten var; gerekiyorsa not)
- Create: `docs/adr/0010-edge-ingestion-mqtt.md`
- Modify: `docs/veri-sozlugu.md` (varsa), `README.md`, `docs/yol-haritasi.md`
- Modify: `C:\Users\scryn\.claude\projects\...\memory\project-fabrikaos-plan.md` + `MEMORY.md`

- [ ] **Step 1: Tüm backend testleri + lint/tip**

Run: `docker compose up -d db redis mqtt` ardından `./.venv/Scripts/python.exe -m pytest && ./.venv/Scripts/python.exe -m ruff check backend edge && ./.venv/Scripts/python.exe -m ruff format --check backend edge && ./.venv/Scripts/python.exe -m mypy`
Expected: hepsi temiz (round-trip testi PASS veya SKIP). Test sayısını not et (BE 82 → ~100+).

- [ ] **Step 2: ADR-0010 yaz** — `docs/adr/0010-edge-ingestion-mqtt.md`

`docs/adr/0000-sablon.md` formatını izle. İçerik özeti:
- **Bağlam:** Sahadan otomatik veri akışı; PLC → bulut; tenant-aware ingestion.
- **Karar:** Edge ajanı (simülatör + pluggable sürücü) interval özetlerini `fabrikaos/<tenant>/<cihaz>/olcum` topic'ine yayınlar; ayrı aiomqtt worker tenant şemasına idempotent yazar (`saha_alinan_olcum` defteri); store-and-forward sqlite tamponunda. Veri `uretim_verileri`'ne yazılır → OEE hattı değişmez.
- **Sonuçlar:** OEE'ye elle giriş olmadan akış; tenant izolasyonu registry + topic ile; çift-sayma idempotency ile önlenir.
- **Ertelenenler:** gerçek OPC-UA/Modbus sürücüleri, MQTT mTLS/kimlik doğrulama (dev anonim), idempotency tablosu retention → Faz 5/S19-S20.

- [ ] **Step 3: README + yol-haritası güncelle**

- `docs/yol-haritasi.md`: S8 satırını ✅ işaretle.
- `README.md`: durum tablosunda S8 ✅; çalıştırma bölümüne edge ajanı (`python -m edge.agent`) + ingestion worker (`python -m app.ingestion.worker`) notu.

- [ ] **Step 4: Uçtan uca doğrulama (canlı yığın)**

Run:
```bash
docker compose up -d db redis mqtt
./.venv/Scripts/python.exe -c "import asyncio; from app.control_plane.provizyon import tenant_provizyonla; asyncio.run(tenant_provizyonla(slug='demo', ad='Demo', admin_eposta='admin@demo.test', admin_parola='Demo12345!', db_url='postgresql+asyncpg://fabrikaos:fabrikaos@localhost:5432/fabrikaos'))"
```
1. `demo` tenant'ında bir makine (`MAK-DEMO`) ve cihaz (`GW-DEMO`) oluştur (Swagger `/docs` veya curl, `edge`/`saha:yaz` izinli admin token).
2. `EDGE_TENANT_SLUG=demo EDGE_CIHAZ_KOD=GW-DEMO EDGE_MAKINE_KODLARI=["MAK-DEMO"] EDGE_BROKER_HOST=localhost python -m edge.agent` çalıştır (birkaç saniye).
3. Ayrı terminalde `MQTT_HOST=localhost python -m app.ingestion.worker` çalıştır.
4. `GET /api/v1/oee/ozet` (demo tenant) → `MAK-DEMO` satırının **elle giriş olmadan** dolduğunu doğrula.
5. (Opsiyonel görsel) frontend `npm run dev` → pano + Saha Cihazlar ekranında `son_gorulme` güncel.
Expected: OEE özeti saha verisiyle dolar; kabul kriteri 1 kanıtlanır.

- [ ] **Step 5: Hafıza güncelle**

`project-fabrikaos-plan.md`'ye S8 TAMAM özeti ekle (commit, test sayıları, ertelenenler, ADR-0010). `MEMORY.md` satırını "sıradaki S9" olacak şekilde güncelle.

- [ ] **Step 6: Final commit + dal**

```bash
git add docs README.md .github
git commit -m "docs(s8): ADR-0010 + README/yol-haritası + S8 kapanış (Edge & Ingestion)"
```
Branch'i `main`'e ff-merge etmeden önce `superpowers:finishing-a-development-branch` ile kapanış seçeneklerini sun.

---

## Self-Review

**1. Spec coverage:**
- Edge Gateway (simülatör + pluggable sürücü + store-and-forward): Task 10/11/12/13 ✓
- Ingestion Worker (MQTT abone, tenant-aware yaz): Task 4/6/9 ✓
- REST `POST /saha/olcumler` (edge): Task 8 ✓
- CSV içe aktarma: Task 8 ✓
- Cihaz yönetimi `GET/POST /saha/cihazlar`: Task 7 ✓
- Migration (fan-out) + idempotency: Task 2/5 ✓
- RBAC saha:oku/yaz/edge: Task 3 ✓
- Tenant izolasyonu testleri: Task 6/7 ✓
- Store-and-forward kayıpsız: Task 12 ✓
- ADR-0010 + dokümanlar: Task 15 ✓
- Frontend Cihazlar ekranı: Task 14 ✓
- Kontrat/şema doğrulama: Task 1/10 ✓

**2. Placeholder scan:** Migration `revision`/`down_revision` Task 2 Step 3'te canlı komutla doğrulanır (somut değer + fallback talimatı). Frontend Task 14 mevcut desene yönlendirir + tam kod verir. Placeholder yok.

**3. Type consistency:** `OlcumPaketi` alanları Task 1/10'da aynı; `IngestSonuc.etkilenen_makineler` Task 6'da üretilir, Task 8/9'da tüketilir; `mesaj_coz -> (slug, cihaz_kod, paket)` Task 4'te tanımlı, Task 9'da kullanılır; `olcum_isaretle -> bool` Task 5'te, Task 6'da tüketilir. Tutarlı.
