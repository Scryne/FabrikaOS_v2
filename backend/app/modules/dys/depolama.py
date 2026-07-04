"""DYS nesne depolama soyutlaması (pluggable).

``NesneDepo`` protokolü içerik yüklemeyi/indirmeyi soyutlar. İki uygulama:

- ``MinioNesneDepo`` — MinIO/S3 (``minio`` SDK). Dev + üretim; ``.env`` ``MINIO_*``.
- ``BellekNesneDepo`` — bellek-içi sözlük; testler için (altyapısız).

**Tenant izolasyonu** anahtar önekiyle sağlanır: çağıran katman anahtarı
``tenant_<slug>/belge/...`` biçiminde üretir; bir bucket paylaşılsa bile tenant'lar önekle
ayrışır (bkz. ``belge_nesne_anahtari``). SDK çağrıları senkrondur; async uçlar
``asyncio.to_thread`` ile sarar (provizyon deseni).

Fabrika (``nesne_depo_al``) ayarlardan bir singleton kurar; ``nesne_depo_ayarla`` testlerde
sahte depoyu enjekte eder (``redis_ayarla`` deseni).
"""

from __future__ import annotations

import io
import logging
from typing import Protocol, runtime_checkable

from app.core.config import get_settings

logger = logging.getLogger("app.dys.depolama")


@runtime_checkable
class NesneDepo(Protocol):
    """Nesne depolama arabirimi (yükle/indir/sil/var-mı)."""

    def yukle(self, anahtar: str, veri: bytes, icerik_tipi: str) -> None: ...

    def indir(self, anahtar: str) -> bytes: ...

    def sil(self, anahtar: str) -> None: ...

    def var_mi(self, anahtar: str) -> bool: ...


def belge_nesne_anahtari(slug: str, belge_id: int, surum_no: int, dosya_adi: str) -> str:
    """Tenant-izole nesne anahtarı: ``tenant_<slug>/belge/<id>/<surum>/<dosya>``."""
    return f"tenant_{slug}/belge/{belge_id}/{surum_no}/{dosya_adi}"


class BellekNesneDepo:
    """Bellek-içi (test/dev) nesne deposu — süreç ömrü boyunca kalıcı."""

    def __init__(self) -> None:
        self._veri: dict[str, bytes] = {}

    def yukle(self, anahtar: str, veri: bytes, icerik_tipi: str) -> None:
        self._veri[anahtar] = bytes(veri)

    def indir(self, anahtar: str) -> bytes:
        if anahtar not in self._veri:
            raise KeyError(anahtar)
        return self._veri[anahtar]

    def sil(self, anahtar: str) -> None:
        self._veri.pop(anahtar, None)

    def var_mi(self, anahtar: str) -> bool:
        return anahtar in self._veri


class MinioNesneDepo:
    """MinIO/S3 uyumlu nesne deposu (``minio`` SDK; ilk kullanımda bucket'ı oluşturur)."""

    def __init__(
        self, *, endpoint: str, access_key: str, secret_key: str, secure: bool, bucket: str
    ) -> None:
        from minio import Minio  # lazy import: dep yalnız gerçek depo kullanılırsa gerekir

        self._bucket = bucket
        self._istemci = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        self._bucket_hazir = False

    def _bucket_sagla(self) -> None:
        if not self._bucket_hazir:
            if not self._istemci.bucket_exists(self._bucket):
                self._istemci.make_bucket(self._bucket)
            self._bucket_hazir = True

    def yukle(self, anahtar: str, veri: bytes, icerik_tipi: str) -> None:
        self._bucket_sagla()
        self._istemci.put_object(
            self._bucket,
            anahtar,
            io.BytesIO(veri),
            length=len(veri),
            content_type=icerik_tipi or "application/octet-stream",
        )

    def indir(self, anahtar: str) -> bytes:
        self._bucket_sagla()
        yanit = self._istemci.get_object(self._bucket, anahtar)
        try:
            return yanit.read()
        finally:
            yanit.close()
            yanit.release_conn()

    def sil(self, anahtar: str) -> None:
        self._bucket_sagla()
        self._istemci.remove_object(self._bucket, anahtar)

    def var_mi(self, anahtar: str) -> bool:
        from minio.error import S3Error

        self._bucket_sagla()
        try:
            self._istemci.stat_object(self._bucket, anahtar)
            return True
        except S3Error:
            return False


_depo: NesneDepo | None = None


def nesne_depo_ayarla(depo: NesneDepo | None) -> None:
    """Aktif nesne deposunu enjekte eder (testlerde sahte depo için)."""
    global _depo
    _depo = depo


def nesne_depo_al() -> NesneDepo:
    """Aktif nesne deposunu döndürür (yoksa ayarlardan MinIO deposunu kurar)."""
    global _depo
    if _depo is None:
        ayar = get_settings()
        _depo = MinioNesneDepo(
            endpoint=ayar.minio_endpoint,
            access_key=ayar.minio_access_key,
            secret_key=ayar.minio_secret_key,
            secure=ayar.minio_secure,
            bucket=ayar.minio_bucket,
        )
        logger.info("MinIO nesne deposu kuruldu (endpoint=%s)", ayar.minio_endpoint)
    return _depo
