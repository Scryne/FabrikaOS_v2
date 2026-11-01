"""S27-A platform deneyimi (ADR-0045): birleşik onay kutusu ve içerik araması.

**Onaylarım** modüllerin kendi onay akışlarını değiştirmez; yalnız "bu kullanıcının onaylayabileceği
bekleyen işler"i tek listede toplar ve her kalemin **mevcut** onay/red ucunu gösterir. Bir kaynak
listeye ancak iki koşulda girer: kullanıcının o onay izni var **ve** modül aboneliği açık. Görev
ayrımı korunur: kullanıcının kendi açtığı sayım onaylayamayacağı için listede değil, sayısı ayrıca
döner (ekran "başka biri onaylamalı" der).

**Arama** her kaynak için aynı iki kapıyı uygular (okuma izni + modül); RBAC dışı kayıt sonuç
olarak hiç dönmez. Kaynak başına en çok ``limit`` kayıt, kod ve ad üzerinde ``ILIKE``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane import entitlement_service
from app.control_plane.models import Tenant
from app.kimlik.models import Kullanici
from app.modules.crm.models import Firma
from app.modules.dys.models import Belge
from app.modules.ik.models import FazlaMesai, IzinTalebi, Personel
from app.modules.isemri.models import IsEmri
from app.modules.stok.models import Malzeme, SatinalmaTalebi, SayimOturumu
from app.modules.uretim.models import Makine


@dataclass
class OnayKalemi:
    tur: str
    id: int
    kod: str
    baslik: str
    ozet: str
    talep_eden: str | None
    tarih: Any
    onay_yolu: str
    red_yolu: str | None
    red_gerekce_zorunlu: bool
    detay_yolu: str


@dataclass
class OnayKutusu:
    kalemler: list[OnayKalemi] = field(default_factory=list)
    # Görev ayrımı: kullanıcının kendi açtığı, onayını bekleyen kayıtlar (listede değil).
    kendi_kayitlarim: int = 0


async def _ad(db: AsyncSession, kullanici_id: int | None) -> str | None:
    if kullanici_id is None:
        return None
    k = await db.get(Kullanici, kullanici_id)
    return (k.ad_soyad or k.eposta) if k else None


async def _acik(db: AsyncSession, tenant: Tenant, modul: str) -> bool:
    return await entitlement_service.tenant_modul_acik_mi(db, tenant, modul)


async def onay_kutusu(db: AsyncSession, tenant: Tenant, kullanici: Kullanici) -> OnayKutusu:
    kutu = OnayKutusu()
    if kullanici.izin_var("satinalma:onay") and await _acik(db, tenant, "stok"):
        talepler = (
            await db.execute(
                select(SatinalmaTalebi)
                .where(SatinalmaTalebi.durum == "onay_bekliyor")
                .order_by(SatinalmaTalebi.olusturma_tarihi)
            )
        ).scalars()
        for t in talepler:
            if t.talep_eden_kullanici_id == kullanici.id:
                kutu.kendi_kayitlarim += 1
                continue
            kutu.kalemler.append(
                OnayKalemi(
                    tur="satinalma_talebi",
                    id=t.id,
                    kod=t.kod,
                    baslik=t.baslik,
                    ozet=t.aciklama[:200],
                    talep_eden=await _ad(db, t.talep_eden_kullanici_id),
                    tarih=t.olusturma_tarihi,
                    onay_yolu=f"/satinalma-talepleri/{t.id}/onayla",
                    red_yolu=f"/satinalma-talepleri/{t.id}/reddet",
                    red_gerekce_zorunlu=False,
                    detay_yolu=f"/satinalma-talepleri?kayit={t.id}",
                )
            )
    if kullanici.izin_var("ik:onay") and await _acik(db, tenant, "ik"):
        izinler = (
            await db.execute(
                select(IzinTalebi, Personel)
                .join(Personel, Personel.id == IzinTalebi.personel_id)
                .where(IzinTalebi.durum == "onay_bekliyor")
                .order_by(IzinTalebi.baslangic_tarihi)
            )
        ).all()
        for i, p in izinler:
            if i.talep_eden_kullanici_id == kullanici.id:
                kutu.kendi_kayitlarim += 1
                continue
            kutu.kalemler.append(
                OnayKalemi(
                    tur="izin_talebi",
                    id=i.id,
                    kod=i.kod,
                    baslik=f"{p.ad} {p.soyad} · {i.izin_turu}",
                    ozet=(
                        f"{i.baslangic_tarihi:%d.%m.%Y} – {i.bitis_tarihi:%d.%m.%Y}"
                        f" · {i.gun_sayisi} gün"
                    ),
                    talep_eden=await _ad(db, i.talep_eden_kullanici_id),
                    tarih=i.olusturma_tarihi,
                    onay_yolu=f"/izin-talepleri/{i.id}/onayla",
                    red_yolu=f"/izin-talepleri/{i.id}/reddet",
                    red_gerekce_zorunlu=True,
                    detay_yolu=f"/izin-talepleri?kayit={i.id}",
                )
            )
        mesailer = (
            await db.execute(
                select(FazlaMesai, Personel)
                .join(Personel, Personel.id == FazlaMesai.personel_id)
                .where(FazlaMesai.onayli.is_(False))
                .order_by(FazlaMesai.tarih)
            )
        ).all()
        for m, p in mesailer:
            if m.olusturan_kullanici_id == kullanici.id:
                kutu.kendi_kayitlarim += 1
                continue
            kutu.kalemler.append(
                OnayKalemi(
                    tur="fazla_mesai",
                    id=m.id,
                    kod=f"FM-{m.id}",
                    baslik=f"{p.ad} {p.soyad} · fazla mesai",
                    ozet=f"{m.tarih:%d.%m.%Y} · {float(m.saat):g} saat",
                    talep_eden=await _ad(db, m.olusturan_kullanici_id),
                    tarih=m.olusturma_tarihi,
                    onay_yolu=f"/fazla-mesailer/{m.id}/onayla",
                    red_yolu=None,
                    red_gerekce_zorunlu=False,
                    detay_yolu=f"/personeller/{p.id}",
                )
            )
    if kullanici.izin_var("stok:duzeltme") and await _acik(db, tenant, "stok"):
        sayimlar = (
            await db.execute(
                select(SayimOturumu)
                .where(SayimOturumu.durum == "onay_bekliyor")
                .order_by(SayimOturumu.olusturma_tarihi)
            )
        ).scalars()
        for s in sayimlar:
            if s.olusturan_kullanici_id == kullanici.id:
                kutu.kendi_kayitlarim += 1
                continue
            kutu.kalemler.append(
                OnayKalemi(
                    tur="sayim",
                    id=s.id,
                    kod=s.kod,
                    baslik=f"Sayım farkları · {s.kod}",
                    ozet=s.aciklama[:200],
                    talep_eden=await _ad(db, s.olusturan_kullanici_id),
                    tarih=s.olusturma_tarihi,
                    onay_yolu=f"/sayimlar/{s.id}/onayla",
                    red_yolu=None,
                    red_gerekce_zorunlu=False,
                    detay_yolu=f"/sayimlar/{s.id}",
                )
            )
    kutu.kalemler.sort(key=lambda k: k.tarih)
    return kutu


# ── Arama ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class AramaKaynagi:
    tur: str
    izin: str
    modul: str
    sorgu: Callable[[AsyncSession, str, int], Awaitable[list[dict[str, Any]]]]


def _kalip(q: str) -> str:
    kacis = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{kacis}%"


async def _makine(db: AsyncSession, q: str, n: int) -> list[dict[str, Any]]:
    k = _kalip(q)
    rows = (
        await db.execute(
            select(Makine.id, Makine.kod, Makine.ad)
            .where(or_(Makine.kod.ilike(k), Makine.ad.ilike(k)))
            .order_by(Makine.kod)
            .limit(n)
        )
    ).all()
    return [{"id": i, "baslik": ad, "alt": kod, "yol": f"/makineler/{i}"} for i, kod, ad in rows]


async def _malzeme(db: AsyncSession, q: str, n: int) -> list[dict[str, Any]]:
    k = _kalip(q)
    rows = (
        await db.execute(
            select(Malzeme.id, Malzeme.kod, Malzeme.ad)
            .where(or_(Malzeme.kod.ilike(k), Malzeme.ad.ilike(k)))
            .order_by(Malzeme.kod)
            .limit(n)
        )
    ).all()
    return [{"id": i, "baslik": ad, "alt": kod, "yol": f"/malzemeler/{i}"} for i, kod, ad in rows]


async def _firma(db: AsyncSession, q: str, n: int) -> list[dict[str, Any]]:
    k = _kalip(q)
    rows = (
        await db.execute(
            select(Firma.id, Firma.ad, Firma.vergi_no)
            .where(or_(Firma.ad.ilike(k), Firma.vergi_no.ilike(k)))
            .order_by(Firma.ad)
            .limit(n)
        )
    ).all()
    return [
        {"id": i, "baslik": ad, "alt": vn or "", "yol": f"/firmalar?firma={i}"}
        for i, ad, vn in rows
    ]


async def _belge(db: AsyncSession, q: str, n: int) -> list[dict[str, Any]]:
    k = _kalip(q)
    rows = (
        await db.execute(
            select(Belge.id, Belge.kod, Belge.ad)
            .where(or_(Belge.kod.ilike(k), Belge.ad.ilike(k)))
            .order_by(Belge.kod)
            .limit(n)
        )
    ).all()
    return [
        {"id": i, "baslik": ad, "alt": kod, "yol": f"/belgeler?kayit={i}"} for i, kod, ad in rows
    ]


async def _is_emri(db: AsyncSession, q: str, n: int) -> list[dict[str, Any]]:
    k = _kalip(q)
    rows = (
        await db.execute(
            select(IsEmri.id, IsEmri.kod, IsEmri.baslik)
            .where(or_(IsEmri.kod.ilike(k), IsEmri.baslik.ilike(k)))
            .order_by(IsEmri.id.desc())
            .limit(n)
        )
    ).all()
    return [
        {"id": i, "baslik": b, "alt": kod, "yol": f"/is-emirleri?kayit={i}"} for i, kod, b in rows
    ]


async def _personel(db: AsyncSession, q: str, n: int) -> list[dict[str, Any]]:
    k = _kalip(q)
    tam_ad = func.concat(Personel.ad, " ", Personel.soyad)
    rows = (
        await db.execute(
            select(Personel.id, Personel.sicil_no, Personel.ad, Personel.soyad, Personel.unvan)
            .where(or_(Personel.sicil_no.ilike(k), tam_ad.ilike(k)))
            .order_by(Personel.ad, Personel.soyad)
            .limit(n)
        )
    ).all()
    return [
        {
            "id": i,
            "baslik": f"{a} {s}",
            "alt": " · ".join(x for x in (sicil, u) if x),
            "yol": f"/personeller/{i}",
        }
        for i, sicil, a, s, u in rows
    ]


KAYNAKLAR: tuple[AramaKaynagi, ...] = (
    AramaKaynagi("makine", "uretim:oku", "uretim", _makine),
    AramaKaynagi("malzeme", "stok:oku", "stok", _malzeme),
    AramaKaynagi("is_emri", "isemri:oku", "isemri", _is_emri),
    AramaKaynagi("firma", "crm:oku", "crm", _firma),
    AramaKaynagi("belge", "dys:oku", "dys", _belge),
    AramaKaynagi("personel", "ik:oku", "ik", _personel),
)


async def ara(
    db: AsyncSession, tenant: Tenant, kullanici: Kullanici, q: str, limit: int = 5
) -> list[dict[str, Any]]:
    sonuc: list[dict[str, Any]] = []
    for kaynak in KAYNAKLAR:
        if not kullanici.izin_var(kaynak.izin) or not await _acik(db, tenant, kaynak.modul):
            continue
        kayitlar = await kaynak.sorgu(db, q, limit)
        if kayitlar:
            sonuc.append({"tur": kaynak.tur, "kayitlar": kayitlar})
    return sonuc
