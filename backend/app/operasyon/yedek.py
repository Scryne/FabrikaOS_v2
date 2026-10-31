"""Tenant-farkında mantıksal yedek ve geri yükleme (S20, ADR-0041).

Neden ``pg_dump --schema=tenant_<slug>`` değil: TimescaleDB hypertable verisi tenant şemasında
değil ``_timescaledb_internal`` şemasındaki chunk'larda durur; şema bazlı döküm hypertable'ları
(``uretim_verileri``, ``enerji_tuketim``) **boş** yedekler. Bu modül bu yüzden:

- **Yapıyı** yedeklemez, göçlerden yeniden kurar: yedek, şemanın Alembic revizyonunu kaydeder;
  geri yüklemede boş bir şema aynı revizyona yükseltilir (hypertable'lar göçte oluşur).
- **Veriyi** tablo tablo ``COPY ... (FORMAT binary)`` ile alır. Hypertable'a yapılan COPY
  chunk'lara kendiliğinden dağılır; sürekli toplulaştırmalar (CAGG) veri değil türevdir,
  geri yüklemeden sonra yeniden hesaplanır.
- Bütün tablolar **tek bir REPEATABLE READ anlık görüntüsünde** okunur: yedek, aynı ana ait
  tutarlı bir kesittir (sipariş ile kalemi arasında yarım kalmaz).

Bütünlük üç katmanlıdır: dosya başına SHA-256 (taşıma bozulması), satır sayısı, ve sıra
bağımsız içerik parmak izi (her satırın metin hâlinin md5'leri sıralanıp tekrar özetlenir).
Geri yükleme, parmak izi yedektekiyle birebir tutmadan canlı şemaya dokunmaz.

Geri yükleme önce geçici bir şemaya kurar, doğrular, sonra tek işlemde yer değiştirir:
``tenant_<slug>`` → ``eski_<slug>_<zaman>`` (geri dönüş için saklanır), geçici → ``tenant_<slug>``.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import tempfile
import time
import zipfile
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import asyncpg

from app.core.db.tenancy import sema_adi

BICIM = 1
_MANIFEST = "manifest.json"
_KONTROL_DUZLEMI = "kontrol-duzlemi.json"
# Göçlerin ürettiği, yedeklenmeyen tablolar (yapı göçten gelir).
_ATLANAN = frozenset({"alembic_version"})
# Tenant'a ait control-plane satırları (bilgi amaçlı yedeklenir; geri yükleme tenant şemasını
# kurar, public kayıtlar hedef tenant'ta zaten vardır).
_PUBLIC_SORGULAR = {
    "tenant": "SELECT * FROM public.tenant WHERE id = $1",
    "abonelik": "SELECT * FROM public.abonelik WHERE tenant_id = $1",
    "modul_haklari": "SELECT * FROM public.modul_haklari WHERE tenant_id = $1",
    "ozellik_bayraklari": "SELECT * FROM public.ozellik_bayraklari WHERE tenant_id = $1",
}


class YedekHatasi(RuntimeError):
    """Yedek alınamadı ya da geri yükleme güvenle yapılamaz (canlı şemaya dokunulmadı)."""


@dataclass
class TabloOzeti:
    ad: str
    sutunlar: list[str]
    satir: int
    sha256: str
    parmak_izi: str


@dataclass
class Manifest:
    bicim: int
    slug: str
    sema: str
    alembic_revizyonu: str
    pg_ana_surum: int
    timescale_surumu: str | None
    alindi: str
    sure_sn: float
    tablolar: list[TabloOzeti] = field(default_factory=list)

    @property
    def toplam_satir(self) -> int:
        return sum(t.satir for t in self.tablolar)


@dataclass
class GeriYuklemeRaporu:
    slug: str
    hedef_sema: str
    eski_sema: str | None
    revizyon: str
    tablo: int
    satir: int
    sure_sn: float
    adimlar: dict[str, float]
    degistirildi: bool


def asyncpg_dsn(sqlalchemy_url: str) -> str:
    """``postgresql+asyncpg://`` → asyncpg'nin kabul ettiği ``postgresql://``."""
    return sqlalchemy_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _id(ad: str) -> str:
    return '"' + ad.replace('"', '""') + '"'


def _nitelikli(sema: str, tablo: str) -> str:
    return f"{_id(sema)}.{_id(tablo)}"


# --- Keşif ---------------------------------------------------------------------------------


async def tablolar(conn: asyncpg.Connection, sema: str) -> list[str]:
    """Şemanın gerçek tabloları (ada göre). Yükleme sırası önemsizdir: geri yükleme yabancı
    anahtarları kaldırıp veri yüklendikten sonra yeniden ekler (şemada FK döngüleri var:
    sıralı yükleme mümkün değil)."""
    satirlar = await conn.fetch(
        """SELECT table_name FROM information_schema.tables
           WHERE table_schema = $1 AND table_type = 'BASE TABLE' ORDER BY table_name""",
        sema,
    )
    return [r["table_name"] for r in satirlar if r["table_name"] not in _ATLANAN]


async def yazilabilir_sutunlar(conn: asyncpg.Connection, sema: str, tablo: str) -> list[str]:
    """Üretilmiş (GENERATED ... STORED) olmayan sütunlar, tablo sırasıyla."""
    satirlar = await conn.fetch(
        """SELECT a.attname FROM pg_attribute a
           JOIN pg_class c ON c.oid = a.attrelid
           JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = $1 AND c.relname = $2 AND a.attnum > 0
             AND NOT a.attisdropped AND a.attgenerated = ''
           ORDER BY a.attnum""",
        sema,
        tablo,
    )
    return [r["attname"] for r in satirlar]


async def parmak_izi(conn: asyncpg.Connection, sema: str, tablo: str, sutunlar: list[str]) -> str:
    """Sıra bağımsız içerik özeti: satır md5'leri sıralanıp birleştirilir ve yeniden özetlenir."""
    satir_ifadesi = "ROW(" + ", ".join(f"t.{_id(s)}" for s in sutunlar) + ")::text"
    deger = await conn.fetchval(
        f"""SELECT md5(coalesce(string_agg(h, '' ORDER BY h), ''))
            FROM (SELECT md5({satir_ifadesi}) AS h FROM {_nitelikli(sema, tablo)} t) x"""
    )
    return str(deger)


async def _sunucu_bilgisi(conn: asyncpg.Connection) -> tuple[int, str | None]:
    ana = int(await conn.fetchval("SHOW server_version_num")) // 10000
    ts = await conn.fetchval("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'")
    return ana, ts


# --- Yedek ---------------------------------------------------------------------------------


async def tenant_yedekle(dsn: str, slug: str, hedef: Path) -> Manifest:
    """``tenant_<slug>`` şemasını tek anlık görüntüde ``hedef`` ZIP dosyasına yedekler."""
    sema = sema_adi(slug)  # slug doğrulanır (şema adı SQL'e girer)
    baslangic = time.perf_counter()
    conn = await asyncpg.connect(dsn)
    try:
        if not await conn.fetchval(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = $1", sema
        ):
            raise YedekHatasi(f"Şema yok: {sema}")
        ana, ts = await _sunucu_bilgisi(conn)
        hedef.parent.mkdir(parents=True, exist_ok=True)
        gecici_zip = hedef.with_suffix(hedef.suffix + ".yaziliyor")
        ozetler: list[TabloOzeti] = []
        async with conn.transaction(isolation="repeatable_read", readonly=True):
            revizyon = await conn.fetchval(f"SELECT version_num FROM {_id(sema)}.alembic_version")
            tenant_id = await conn.fetchval("SELECT id FROM public.tenant WHERE slug = $1", slug)
            kontrol = {
                ad: [dict(r) for r in await conn.fetch(sql, tenant_id)]
                for ad, sql in _PUBLIC_SORGULAR.items()
            }
            with (
                zipfile.ZipFile(gecici_zip, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as z,
                tempfile.TemporaryDirectory() as tmp,
            ):
                for tablo in await tablolar(conn, sema):
                    sutunlar = await yazilabilir_sutunlar(conn, sema, tablo)
                    dosya = Path(tmp) / f"{tablo}.bin"
                    secim = ", ".join(_id(s) for s in sutunlar)
                    await conn.copy_from_query(
                        f"SELECT {secim} FROM {_nitelikli(sema, tablo)}",
                        output=str(dosya),
                        format="binary",
                    )
                    satir = int(
                        await conn.fetchval(f"SELECT count(*) FROM {_nitelikli(sema, tablo)}")
                    )
                    ozetler.append(
                        TabloOzeti(
                            ad=tablo,
                            sutunlar=sutunlar,
                            satir=satir,
                            sha256=_dosya_ozeti(dosya),
                            parmak_izi=await parmak_izi(conn, sema, tablo, sutunlar),
                        )
                    )
                    z.write(dosya, f"veri/{tablo}.bin")
                    dosya.unlink()
                manifest = Manifest(
                    bicim=BICIM,
                    slug=slug,
                    sema=sema,
                    alembic_revizyonu=str(revizyon),
                    pg_ana_surum=ana,
                    timescale_surumu=ts,
                    alindi=datetime.now(UTC).isoformat(),
                    sure_sn=round(time.perf_counter() - baslangic, 3),
                    tablolar=ozetler,
                )
                z.writestr(_KONTROL_DUZLEMI, json.dumps(kontrol, ensure_ascii=False, default=str))
                z.writestr(_MANIFEST, json.dumps(asdict(manifest), ensure_ascii=False, indent=1))
        gecici_zip.replace(hedef)  # yarım dosya hiçbir zaman "yedek" adıyla görünmez
        return manifest
    finally:
        await conn.close()


def _dosya_ozeti(yol: Path) -> str:
    h = hashlib.sha256()
    with yol.open("rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def manifest_oku(dosya: Path) -> Manifest:
    with zipfile.ZipFile(dosya) as z:
        ham = json.loads(z.read(_MANIFEST))
    ham["tablolar"] = [TabloOzeti(**t) for t in ham["tablolar"]]
    return Manifest(**ham)


def yedek_dogrula(dosya: Path) -> Manifest:
    """Dosya bütünlüğü: biçim ve her tablo dosyasının SHA-256'sı manifestle tutmalı."""
    try:
        manifest = manifest_oku(dosya)
    except (KeyError, zipfile.BadZipFile, json.JSONDecodeError, TypeError) as exc:
        raise YedekHatasi(f"Yedek okunamadı: {exc}") from exc
    if manifest.bicim != BICIM:
        raise YedekHatasi(f"Desteklenmeyen yedek biçimi: {manifest.bicim}")
    with zipfile.ZipFile(dosya) as z:
        for t in manifest.tablolar:
            h = hashlib.sha256()
            with z.open(f"veri/{t.ad}.bin") as f:
                for parca in iter(lambda f=f: f.read(1 << 20), b""):  # type: ignore[misc]
                    h.update(parca)
            if h.hexdigest() != t.sha256:
                raise YedekHatasi(f"Bozuk yedek: {t.ad} özeti manifestle tutmuyor")
    return manifest


# --- Geri yükleme --------------------------------------------------------------------------

GocCalistirici = Callable[[str, str], None]
"""(şema, revizyon) → şemayı o revizyona yükselt. Varsayılan: Alembic tenant ağacı."""


def _alembic_goc(db_url: str) -> GocCalistirici:
    def calistir(sema: str, revizyon: str) -> None:
        from app.core.db.fanout import sema_yukselt

        sema_yukselt(sema, revizyon, db_url=db_url)

    return calistir


async def tenant_geri_yukle(
    db_url: str,
    dosya: Path,
    hedef_slug: str | None = None,
    *,
    yalniz_dogrula: bool = False,
    goc: GocCalistirici | None = None,
) -> GeriYuklemeRaporu:
    """Yedeği ``tenant_<hedef_slug>`` şemasına geri yükler.

    ``yalniz_dogrula=True`` (tatbikat): geçici şemaya kurar, doğrular, ölçer ve siler; canlı
    şemaya dokunmaz. Aksi hâlde doğrulanmış geçici şema canlıyla tek işlemde yer değiştirir.
    """
    adimlar: dict[str, float] = {}
    t0 = time.perf_counter()

    def adim(ad: str, bas: float) -> float:
        simdi = time.perf_counter()
        adimlar[ad] = round(simdi - bas, 3)
        return simdi

    manifest = await asyncio.to_thread(yedek_dogrula, dosya)
    t = adim("dosya_dogrulama", t0)
    slug = hedef_slug or manifest.slug
    hedef_sema = sema_adi(slug)
    damga = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    gecici = f"geri_{slug}_{damga}"[:63]
    dsn = asyncpg_dsn(db_url)
    goc = goc or _alembic_goc(db_url)

    conn = await asyncpg.connect(dsn)
    try:
        ana, _ts = await _sunucu_bilgisi(conn)
        if ana != manifest.pg_ana_surum:
            raise YedekHatasi(
                f"PostgreSQL ana sürümü farklı (yedek {manifest.pg_ana_surum}, sunucu {ana}); "
                "ikili COPY biçimi sürümler arası taşınmaz"
            )
        await conn.execute(f"CREATE SCHEMA {_id(gecici)}")
        try:
            await asyncio.to_thread(goc, gecici, manifest.alembic_revizyonu)
            t = adim("yapi_goc", t)
            await _veri_yukle(conn, dosya, manifest, gecici)
            t = adim("veri_yukleme", t)
            await _dogrula(conn, manifest, gecici)
            t = adim("icerik_dogrulama", t)
            await asyncio.to_thread(goc, gecici, "head")
            await _toplulastirmalari_yenile(conn, gecici)
            t = adim("head_ve_toplulastirma", t)
        except BaseException:
            await conn.execute(f"DROP SCHEMA IF EXISTS {_id(gecici)} CASCADE")
            raise

        eski: str | None = None
        if yalniz_dogrula:
            await conn.execute(f"DROP SCHEMA {_id(gecici)} CASCADE")
        else:
            async with conn.transaction():
                var = await conn.fetchval(
                    "SELECT 1 FROM information_schema.schemata WHERE schema_name = $1", hedef_sema
                )
                if var:
                    eski = f"eski_{slug}_{damga}"[:63]
                    await conn.execute(f"ALTER SCHEMA {_id(hedef_sema)} RENAME TO {_id(eski)}")
                await conn.execute(f"ALTER SCHEMA {_id(gecici)} RENAME TO {_id(hedef_sema)}")
        adim("yer_degistirme", t)
    finally:
        await conn.close()

    return GeriYuklemeRaporu(
        slug=slug,
        hedef_sema=hedef_sema,
        eski_sema=eski,
        revizyon=manifest.alembic_revizyonu,
        tablo=len(manifest.tablolar),
        satir=manifest.toplam_satir,
        sure_sn=round(time.perf_counter() - t0, 3),
        adimlar=adimlar,
        degistirildi=not yalniz_dogrula,
    )


async def _veri_yukle(conn: asyncpg.Connection, dosya: Path, manifest: Manifest, sema: str) -> None:
    beklenen = {t.ad for t in manifest.tablolar}
    mevcut = set(await tablolar(conn, sema))
    if beklenen - mevcut:
        raise YedekHatasi(f"Göç sonrası şemada olmayan tablolar: {sorted(beklenen - mevcut)}")
    async with conn.transaction():
        # Yabancı anahtarlar yükleme süresince kaldırılır ve sonra aynı tanımla yeniden eklenir:
        # şemada FK döngüleri var (sıralı yükleme imkânsız) ve yeniden ekleme, bütün satırların
        # referans bütünlüğünü bir kez daha doğrular. Süper kullanıcı gerektirmez.
        kisitlar = await conn.fetch(
            """SELECT c.relname AS tablo, k.conname AS ad, pg_get_constraintdef(k.oid) AS tanim
               FROM pg_constraint k
               JOIN pg_class c ON c.oid = k.conrelid
               JOIN pg_namespace n ON n.oid = c.relnamespace
               WHERE k.contype = 'f' AND n.nspname = $1""",
            sema,
        )
        for k in kisitlar:
            await conn.execute(
                f"ALTER TABLE {_nitelikli(sema, k['tablo'])} DROP CONSTRAINT {_id(k['ad'])}"
            )
        # Göçlerin tohumladığı satırlar (rol/izin, varsayılan depo) yedekteki veriyle çakışır.
        await conn.execute("TRUNCATE " + ", ".join(_nitelikli(sema, t) for t in sorted(mevcut)))
        with zipfile.ZipFile(dosya) as z, tempfile.TemporaryDirectory() as tmp:
            for t in manifest.tablolar:
                yol = Path(tmp) / f"{t.ad}.bin"
                with z.open(f"veri/{t.ad}.bin") as kaynak, yol.open("wb") as hedef:
                    for parca in iter(lambda k=kaynak: k.read(1 << 20), b""):  # type: ignore[misc]
                        hedef.write(parca)
                await conn.copy_to_table(
                    t.ad, source=str(yol), columns=t.sutunlar, schema_name=sema, format="binary"
                )
                yol.unlink()
        for k in kisitlar:
            try:
                await conn.execute(
                    f"ALTER TABLE {_nitelikli(sema, k['tablo'])} "
                    f"ADD CONSTRAINT {_id(k['ad'])} {k['tanim']}"
                )
            except asyncpg.ForeignKeyViolationError as exc:
                raise YedekHatasi(f"{k['tablo']}: referans bütünlüğü bozuk ({k['ad']})") from exc
        await _dizileri_ayarla(conn, sema)


async def _dizileri_ayarla(conn: asyncpg.Connection, sema: str) -> None:
    """Kimlik/serial dizilerini tablodaki en büyük değere getirir (yeni kayıt çakışmasın)."""
    satirlar = await conn.fetch(
        """SELECT c.relname AS tablo, a.attname AS sutun,
                  pg_get_serial_sequence(quote_ident(n.nspname) || '.' || quote_ident(c.relname),
                                         a.attname) AS dizi
           FROM pg_attribute a
           JOIN pg_class c ON c.oid = a.attrelid
           JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = $1 AND c.relkind IN ('r', 'p') AND a.attnum > 0
             AND NOT a.attisdropped""",
        sema,
    )
    for r in satirlar:
        if r["dizi"] is None:
            continue
        en_buyuk = await conn.fetchval(
            f"SELECT max({_id(r['sutun'])}) FROM {_nitelikli(sema, r['tablo'])}"
        )
        if en_buyuk is None:
            await conn.execute("SELECT setval($1, 1, false)", r["dizi"])
        else:
            await conn.execute("SELECT setval($1, $2, true)", r["dizi"], int(en_buyuk))


async def _dogrula(conn: asyncpg.Connection, manifest: Manifest, sema: str) -> None:
    for t in manifest.tablolar:
        satir = int(await conn.fetchval(f"SELECT count(*) FROM {_nitelikli(sema, t.ad)}"))
        if satir != t.satir:
            raise YedekHatasi(f"{t.ad}: satır sayısı tutmuyor (yedek {t.satir}, yüklenen {satir})")
        iz = await parmak_izi(conn, sema, t.ad, t.sutunlar)
        if iz != t.parmak_izi:
            raise YedekHatasi(f"{t.ad}: içerik parmak izi yedektekiyle tutmuyor")


async def _toplulastirmalari_yenile(conn: asyncpg.Connection, sema: str) -> None:
    var = await conn.fetchval("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")
    if not var:
        return
    gorunumler = await conn.fetch(
        """SELECT view_name FROM timescaledb_information.continuous_aggregates
           WHERE view_schema = $1""",
        sema,
    )
    for g in gorunumler:
        # İşlem dışında çağrılmalı (CALL refresh_continuous_aggregate işlem bloğunda çalışmaz).
        await conn.execute(
            f"CALL refresh_continuous_aggregate('{_nitelikli(sema, g['view_name'])}', NULL, NULL)"
        )


def manifest_sozluk(m: Manifest) -> dict[str, Any]:
    return asdict(m)
