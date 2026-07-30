"""İzin/rol kataloğu ↔ tenant şemaları uzlaştırması (idempotent).

**Neden var:** izin kataloğu (`IZIN_KATALOGU`) ve varsayılan roller (`VARSAYILAN_ROLLER`)
kod tarafında yaşar; tenant şemasındaki `izin`/`rol` tabloları ise provizyon anında
tohumlanır. Her sprint yeni izin kodu eklediğinde (`denetim:oku`, `stok:duzeltme`,
`finans:onay`…) **mevcut tenant'lar bu kodu almaz**: uç 403 döner, rol matrisinde satır
eksik kalır. S16 ve S23'te bu elle yeniden provizyonlamayla kapatıldı — elle adım
kaçınılmaz olarak unutulur ve sessiz sürüklenme (drift) üretir.

**Çözüm:** migration fan-out'unun ardından her tenant şeması katalogla uzlaştırılır.
İşlem idempotenttir ve yalnızca **eklemeli**dir:

- Katalogda olup şemada olmayan izinler eklenir. Şemada olup katalogda olmayan izin
  **silinmez** (elle tanımlanmış/eski kodlar korunur; silme ayrı ve bilinçli bir karar).
- `VARSAYILAN_ROLLER`'daki roller yoksa oluşturulur. Var olan rollere yalnız **daha önce
  hiç tohumlanmamış** katalog izinleri eklenir. Katalog dışı **özel roller hiç ellenmez**.

**Yetki restorasyonu yasağı (kritik).** Uzlaştırma, rol izin kümesini katalogla
*eşitlemez*. "Katalogda var ama rolde yok" iki farklı şey demek olabilir:

1. **Yeni sprintin eklediği izin** — role eklenmeli (bu modülün varlık sebebi).
2. **Tenant'ın bilinçli olarak kaldırdığı izin** — asla geri verilmemeli; aksi hâlde
   yönetici bir yetkiyi kaldırır, bir sonraki dağıtım onu sessizce geri açar. Bu
   denetlenemeyen bir yetki yükseltmesidir.

İkisi `rol_izin_tohumu` köken defteriyle ayrılır: katalogdan eklenen her bağ oraya
yazılır. Defterde kayıtlı ama rolde bulunmayan bir izin = bilinçli kaldırma → korunur
ve sonuçta ``korunan_kaldirma`` olarak raporlanır (sessiz kalmaz).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.control_plane.models import Tenant
from app.core.config import get_settings
from app.core.db.tenancy import search_path_ayarla
from app.kimlik.izinler import IZIN_KATALOGU, VARSAYILAN_ROLLER
from app.kimlik.models import Izin, Rol, RolIzinTohumu

logger = logging.getLogger("app.uzlastirma")


@dataclass(frozen=True, slots=True)
class UzlastirmaSonucu:
    """Bir tenant için uzlaştırma çıktısı (idempotent koşuda değişiklik alanları boş olur)."""

    slug: str
    eklenen_izin: tuple[str, ...] = ()
    eklenen_rol: tuple[str, ...] = ()
    guncellenen_rol: tuple[str, ...] = ()
    # Katalogda olan ama tenant'ın kaldırdığı için GERİ VERİLMEYEN bağlar ("rol:izin").
    # Değişiklik değildir — görünürlük içindir (sessiz atlama olmasın).
    korunan_kaldirma: tuple[str, ...] = ()

    @property
    def degisti(self) -> bool:
        return bool(self.eklenen_izin or self.eklenen_rol or self.guncellenen_rol)


async def izin_rol_uzlastir(s: AsyncSession, slug: str) -> UzlastirmaSonucu:
    """Tek tenant şemasını katalogla uzlaştırır. Çağıran commit'ten sorumludur.

    ``search_path`` bu fonksiyon içinde ayarlanır (tenant-rbac-conventions: şema
    çözümlemesi tek noktadan).
    """
    await search_path_ayarla(s, slug)

    # 1) İzinler — eksikleri ekle (fazlaları KORU).
    izin_haritasi = {i.kod: i for i in (await s.execute(select(Izin))).scalars()}
    eklenen_izin: list[str] = []
    for kod, aciklama in IZIN_KATALOGU.items():
        if kod not in izin_haritasi:
            izin = Izin(kod=kod, aciklama=aciklama)
            s.add(izin)
            izin_haritasi[kod] = izin
            eklenen_izin.append(kod)
    await s.flush()

    # 2) Varsayılan roller — yoksa oluştur; VAR OLANLARA yalnız hiç tohumlanmamış
    #    katalog izinlerini ekle (tenant'ın kaldırdıklarını geri verme).
    rol_haritasi = {r.ad: r for r in (await s.execute(select(Rol))).scalars()}
    tohumlu: dict[str, set[str]] = {}
    for t in (await s.execute(select(RolIzinTohumu))).scalars():
        tohumlu.setdefault(t.rol_ad, set()).add(t.izin_kod)

    eklenen_rol: list[str] = []
    guncellenen_rol: list[str] = []
    korunan_kaldirma: list[str] = []

    for ad, kodlar in VARSAYILAN_ROLLER.items():
        rol = rol_haritasi.get(ad)
        yeni_rol = rol is None
        if rol is None:
            rol = Rol(ad=ad, aciklama=f"Varsayılan {ad} rolü")
            s.add(rol)
            rol_haritasi[ad] = rol
            eklenen_rol.append(ad)

        mevcut_kodlar = set() if yeni_rol else {i.kod for i in rol.izinler}
        defterdeki = tohumlu.get(ad, set())
        # İZİN SATIRI bu koşuda yeniden oluşturulduysa, o izne ait rol bağının yokluğu
        # "bilinçli kaldırma" olamaz: izin hiç yokken rolden kaldırılmış olamazdı. Bu bir
        # şema sürüklenmesidir (izin satırı silinmiş) → köken defteri es geçilir, bağ onarılır.
        engelleyen = defterdeki - set(eklenen_izin)

        # Yeni rolde her şey eklenir; var olan rolde YALNIZ hiç tohumlanmamış olanlar.
        eklenecek = {k for k in kodlar if k not in mevcut_kodlar and k not in engelleyen}
        # Defterde var, rolde yok, izin satırı da duruyor → bilinçli kaldırma; dokunma.
        korunan = {k for k in kodlar if k not in mevcut_kodlar and k in engelleyen}
        korunan_kaldirma.extend(f"{ad}:{k}" for k in sorted(korunan))

        if eklenecek:
            rol.izinler = list(rol.izinler) + [izin_haritasi[k] for k in sorted(eklenecek)]
            if not yeni_rol:
                guncellenen_rol.append(ad)

        # Köken defterine yaz — YALNIZ gerçekten kayıtlı olmayanlar (onarılan bağlar
        # zaten defterde; yeniden eklemek UNIQUE kısıtını ihlal ederdi).
        for kod in sorted(eklenecek - defterdeki):
            s.add(RolIzinTohumu(rol_ad=ad, izin_kod=kod))
    await s.flush()

    if korunan_kaldirma:
        logger.info(
            "izin uzlastirma: tenant=%s bilincli kaldirmalar korundu: %s",
            slug,
            korunan_kaldirma,
        )

    return UzlastirmaSonucu(
        slug=slug,
        eklenen_izin=tuple(eklenen_izin),
        eklenen_rol=tuple(eklenen_rol),
        guncellenen_rol=tuple(guncellenen_rol),
        korunan_kaldirma=tuple(korunan_kaldirma),
    )


async def tum_tenantlari_uzlastir(*, db_url: str | None = None) -> list[UzlastirmaSonucu]:
    """Tüm (askıdakiler dahil) tenant şemalarını katalogla uzlaştırır.

    Askıya alınmış tenant da uzlaştırılır: askıdan döndüğünde izin tablosu eksik olmasın.
    Bir tenant hata verirse diğerleri etkilenmez — hata loglanır ve döngü sürer
    (yarım provizyonlanmış bir şema tüm dağıtımı durdurmamalı).
    """
    url = db_url or get_settings().database_url
    engine = create_async_engine(url, poolclass=NullPool)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    sonuclar: list[UzlastirmaSonucu] = []
    try:
        async with sm() as s:
            sluglar = [t.slug for t in (await s.execute(select(Tenant))).scalars()]

        for slug in sluglar:
            try:
                async with sm() as s, s.begin():
                    sonuc = await izin_rol_uzlastir(s, slug)
                sonuclar.append(sonuc)
                if sonuc.degisti:
                    logger.info(
                        "izin uzlastirma: tenant=%s yeni_izin=%s yeni_rol=%s guncellenen_rol=%s",
                        slug,
                        list(sonuc.eklenen_izin),
                        list(sonuc.eklenen_rol),
                        list(sonuc.guncellenen_rol),
                    )
            except Exception as exc:  # noqa: BLE001 — tek tenant tüm dağıtımı durdurmamalı
                logger.warning("izin uzlastirma basarisiz (tenant=%s): %s", slug, exc)
    finally:
        await engine.dispose()
    return sonuclar
