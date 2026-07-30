"""Uyum uçları (``/api/v1``) — denetim kaydı görünürlüğü + KVKK paketi + consent (S23).

Modül kapısı YOK (güvenlik/uyum çekirdek haktır, satılabilir yetenek değil):
- ``GET /denetim-kayitlari`` → ``denetim:oku`` (append-only; trigger değişikliği engeller)
- ``/kvkk/*`` → ``kvkk:yonet`` (ihraç async, S14 deseni; anonimleştirme denetim izli)
- ``/consent`` → oturum yeterli (kişisel yüzey: kendi kaydını yazar/görür)
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import DenetimIzi, denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, mevcut_kullanici, tenant_cozumle
from app.core.exceptions import (
    CakismaHatasi,
    DogrulamaHatasi,
    KaynakBulunamadi,
    SureDoldu,
)
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.uyum import models, service
from app.modules.uyum.models import CONSENT_TURLERI, ConsentKaydi, KvkkIhraci

router = APIRouter(tags=["Uyum"])


# --- DTO'lar ---
class DenetimKaydiDTO(BaseModel):
    id: int
    kullanici_id: int | None = None
    kullanici_eposta: str | None = None
    eylem: str
    kaynak: str
    kaynak_id: str | None = None
    request_id: str | None = None
    ip_adresi: str | None = None
    detay: dict[str, Any] | None = None
    olusturma_tarihi: datetime


class KvkkIhracTalepDTO(BaseModel):
    kisi_turu: str = Field(min_length=1, max_length=20)
    kisi_id: int = Field(gt=0)


class KvkkIhracCevapDTO(BaseModel):
    id: int
    kod: str
    kisi_turu: str
    kisi_id: int
    durum: str
    dosya_adi: str
    boyut: int
    kayit_sayisi: int
    hata: str
    olusturma_tarihi: datetime


class AnonimlestirDTO(BaseModel):
    kisi_turu: str = Field(min_length=1, max_length=20)
    kisi_id: int = Field(gt=0)
    # Tehlikeli/geri alınamaz işlem: FE slug-yazarak-onay deseni (S17) — "ANONIM" yazılmalı.
    onay: str = Field(min_length=1)


class ConsentGirdiDTO(BaseModel):
    tur: str = Field(min_length=1, max_length=20)
    metin_surumu: str = Field(min_length=1, max_length=20)
    kabul: bool


class ConsentCevapDTO(BaseModel):
    id: int
    tur: str
    metin_surumu: str
    kabul: bool
    olusturma_tarihi: datetime


def _ihrac_cevap(k: KvkkIhraci) -> dict[str, Any]:
    return KvkkIhracCevapDTO(
        id=k.id,
        kod=k.kod,
        kisi_turu=k.kisi_turu,
        kisi_id=k.kisi_id,
        durum=k.durum,
        dosya_adi=k.dosya_adi,
        boyut=k.boyut,
        kayit_sayisi=k.kayit_sayisi,
        hata=k.hata,
        olusturma_tarihi=k.olusturma_tarihi,
    ).model_dump()


# --- Denetim kaydı görünürlüğü ---
@router.get(
    "/denetim-kayitlari",
    response_model=Zarf[list[DenetimKaydiDTO]],
    summary="Denetim kayıtları (append-only; kim-ne-ne zaman)",
)
async def denetim_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("denetim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    kullanici_eposta: Annotated[str | None, Query(max_length=255)] = None,
    kaynak: Annotated[str | None, Query(max_length=80)] = None,
    eylem: Annotated[str | None, Query(max_length=50)] = None,
    baslangic: Annotated[datetime | None, Query()] = None,
    bitis: Annotated[datetime | None, Query()] = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kosullar: list[Any] = []
    if kullanici_eposta:
        kosullar.append(DenetimIzi.kullanici_eposta.ilike(f"%{kullanici_eposta}%"))
    if kaynak:
        kosullar.append(DenetimIzi.kaynak == kaynak)
    if eylem:
        kosullar.append(DenetimIzi.eylem == eylem)
    if baslangic:
        kosullar.append(DenetimIzi.olusturma_tarihi >= baslangic)
    if bitis:
        kosullar.append(DenetimIzi.olusturma_tarihi <= bitis)
    toplam = (
        await db.execute(select(func.count()).select_from(DenetimIzi).where(*kosullar))
    ).scalar_one()
    kayitlar = (
        (
            await db.execute(
                select(DenetimIzi)
                .where(*kosullar)
                .order_by(DenetimIzi.id.desc())
                .offset((sayfa - 1) * adet)
                .limit(adet)
            )
        )
        .scalars()
        .all()
    )
    return sayfali(
        [
            DenetimKaydiDTO(
                id=k.id,
                kullanici_id=k.kullanici_id,
                kullanici_eposta=k.kullanici_eposta,
                eylem=k.eylem,
                kaynak=k.kaynak,
                kaynak_id=k.kaynak_id,
                request_id=k.request_id,
                ip_adresi=k.ip_adresi,
                detay=k.detay,
                olusturma_tarihi=k.olusturma_tarihi,
            ).model_dump()
            for k in kayitlar
        ],
        sayfa=sayfa,
        adet=adet,
        toplam=int(toplam),
    )


@router.get(
    "/denetim-kayitlari/kaynaklar",
    response_model=Zarf[list[str]],
    summary="Denetimde geçen kaynak adları (filtre seçenekleri)",
)
async def denetim_kaynaklari(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("denetim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    kaynaklar = (
        (await db.execute(select(DenetimIzi.kaynak).distinct().order_by(DenetimIzi.kaynak)))
        .scalars()
        .all()
    )
    return basari(list(kaynaklar), mesaj="Denetim kaynakları")


# --- KVKK: kişi bazlı ihraç ---
@router.get(
    "/kvkk/ihraclar",
    response_model=Zarf[list[KvkkIhracCevapDTO]],
    summary="KVKK ihraç talepleri",
)
async def ihrac_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("kvkk:yonet"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    toplam = (await db.execute(select(func.count()).select_from(KvkkIhraci))).scalar_one()
    kayitlar = (
        (
            await db.execute(
                select(KvkkIhraci)
                .order_by(KvkkIhraci.id.desc())
                .offset((sayfa - 1) * adet)
                .limit(adet)
            )
        )
        .scalars()
        .all()
    )
    return sayfali([_ihrac_cevap(k) for k in kayitlar], sayfa=sayfa, adet=adet, toplam=int(toplam))


@router.post(
    "/kvkk/ihrac",
    response_model=Zarf[KvkkIhracCevapDTO],
    status_code=202,
    summary="Kişi bazlı KVKK veri ihracı başlat (async)",
)
async def ihrac_baslat(
    govde: KvkkIhracTalepDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("kvkk:yonet"))],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    service.kisi_turu_dogrula(govde.kisi_turu)
    # Kişinin varlığı istek içinde doğrulanır (arka planda geç hata yerine erken 404).
    ana_tablo = Kullanici if govde.kisi_turu == "kullanici" else None
    if ana_tablo is not None:
        var = (
            await db.execute(select(Kullanici.id).where(Kullanici.id == govde.kisi_id))
        ).scalar_one_or_none()
    else:
        from app.modules.ik.models import Personel

        var = (
            await db.execute(select(Personel.id).where(Personel.id == govde.kisi_id))
        ).scalar_one_or_none()
    if var is None:
        raise KaynakBulunamadi("Kişi bulunamadı")

    kayit = KvkkIhraci(
        kod=f"GECICI-{datetime.now(UTC).timestamp()}",
        kisi_turu=govde.kisi_turu,
        kisi_id=govde.kisi_id,
        olusturan_kullanici_id=kullanici.id,
    )
    db.add(kayit)
    await db.flush()
    kayit.kod = f"KV-{datetime.now(UTC).year}-{kayit.id:06d}"
    await denetim_yaz(
        db,
        eylem="kvkk_ihrac",
        kaynak="uyum",
        kaynak_id=kayit.kod,
        kullanici=kullanici,
        detay={"kisi_turu": govde.kisi_turu, "kisi_id": govde.kisi_id},
    )
    await db.commit()
    await service.uretim_planla(kayit.id, tenant.slug)
    return basari(_ihrac_cevap(kayit), mesaj="İhraç kuyruğa alındı")


@router.get(
    "/kvkk/ihraclar/{ihrac_id}/indir",
    summary="Hazır KVKK ihracını indir (ZIP)",
    response_class=Response,
)
async def ihrac_indir(
    ihrac_id: int,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("kvkk:yonet"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> Response:
    """Hazır ihracı indirir. İçerik **kimlik doğrulamalı bu uçtan** akar: nesne deposuna
    önceden imzalı (presigned) URL üretilmez — tam kişisel veri dökümü için paylaşılabilir
    bir bağlantı en büyük sızıntı yüzeyidir. Her indirme denetim izine yazılır."""
    kayit = await db.get(KvkkIhraci, ihrac_id)
    if kayit is None:
        raise KaynakBulunamadi("İhraç kaydı bulunamadı")
    if service.suresi_doldu_mu(kayit) or kayit.durum == "suresi_doldu":
        # Süresi dolmuşsa artefaktı burada da temizle (tarama beklenmeden).
        await service.artefakti_sil(db, kayit)
        # AÇIK COMMIT ŞART: aşağıdaki istisna isteği rollback'e sürükler; nesne deposundan
        # silme ise transactional DEĞİL. Commit edilmezse dosya gider ama kayıt "hazir"
        # kalır — depo ile DB kalıcı olarak tutarsızlaşır.
        await db.commit()
        raise SureDoldu(
            f"İhraç artefaktının saklama süresi doldu ({models.IHRAC_SAKLAMA_GUN} gün); "
            "yeni bir ihraç talebi oluşturun"
        )
    if kayit.durum != "hazir":
        raise CakismaHatasi(f"İhraç henüz hazır değil (durum: {kayit.durum})")
    icerik = await service.ihrac_icerik_indir(kayit)
    kayit.indirme_sayisi += 1
    await denetim_yaz(
        db,
        eylem="kvkk_ihrac_indir",
        kaynak="uyum",
        kaynak_id=kayit.kod,
        kullanici=kullanici,
        # Kim (denetim izinin kendisi) + kimin verisi (aşağıdaki alanlar) + kaçıncı indirme.
        detay={
            "kisi_turu": kayit.kisi_turu,
            "kisi_id": kayit.kisi_id,
            "boyut": kayit.boyut,
            "indirme_sayisi": kayit.indirme_sayisi,
        },
    )
    guvenli_ad = re.sub(r"[^A-Za-z0-9._-]", "_", kayit.dosya_adi or f"{kayit.kod}.zip")
    return Response(
        content=icerik,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{guvenli_ad}"'},
    )


@router.post(
    "/kvkk/ihraclar/temizle",
    response_model=Zarf[dict[str, int]],
    summary="Saklama süresi dolan ihraç artefaktlarını sil (kenar-tetikli tarama)",
)
async def ihraclari_temizle(
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("kvkk:yonet"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    """Süresi dolan ZIP'leri nesne deposundan siler; kayıt satırları denetim için kalır.

    İdempotenttir (``suresi_doldu`` olanlar atlanır) — zamanlanmış görevden ya da elle
    çağrılabilir. İndirme ucu da süresi dolmuş artefaktı kendiliğinden temizler; bu uç
    hiç indirilmemiş artefaktların birikmesini engeller.
    """
    sayi = await service.suresi_dolanlari_temizle(db)
    if sayi:
        await denetim_yaz(
            db,
            eylem="kvkk_artefakt_temizle",
            kaynak="uyum",
            kullanici=kullanici,
            detay={"silinen": sayi, "saklama_gun": models.IHRAC_SAKLAMA_GUN},
        )
    return basari({"silinen": sayi}, mesaj=f"{sayi} artefakt temizlendi")


# --- KVKK: anonimleştirme ---
@router.post(
    "/kvkk/anonimlestir",
    response_model=Zarf[dict[str, Any]],
    summary="Kişisel veriyi anonimleştir (geri alınamaz; denetim izli)",
)
async def anonimlestir(
    govde: AnonimlestirDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("kvkk:yonet"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    if govde.onay != "ANONIM":
        raise DogrulamaHatasi(
            "Onay metni hatalı",
            detaylar=[{"alan": "onay", "mesaj": 'Geri alınamaz işlem için "ANONIM" yazın'}],
        )
    ozet = await service.anonimlestir(
        db, kisi_turu=govde.kisi_turu, kisi_id=govde.kisi_id, yapan=kullanici
    )
    return basari(ozet, mesaj="Kişisel veri anonimleştirildi")


# --- Consent (kişisel yüzey — oturum yeterli) ---
@router.get(
    "/consent",
    response_model=Zarf[list[ConsentCevapDTO]],
    summary="Kendi aydınlatma/rıza kayıtlarım",
)
async def consent_listele(
    kullanici: Annotated[Kullanici, Depends(mevcut_kullanici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    kayitlar = (
        (
            await db.execute(
                select(ConsentKaydi)
                .where(ConsentKaydi.kullanici_id == kullanici.id)
                .order_by(ConsentKaydi.id.desc())
            )
        )
        .scalars()
        .all()
    )
    return basari(
        [
            ConsentCevapDTO(
                id=k.id,
                tur=k.tur,
                metin_surumu=k.metin_surumu,
                kabul=k.kabul,
                olusturma_tarihi=k.olusturma_tarihi,
            ).model_dump()
            for k in kayitlar
        ],
        mesaj="Rıza kayıtları",
    )


@router.post(
    "/consent",
    response_model=Zarf[ConsentCevapDTO],
    status_code=201,
    summary="Aydınlatma/rıza kaydı ekle (geri çekme = kabul:false yeni satır)",
)
async def consent_ekle(
    govde: ConsentGirdiDTO,
    kullanici: Annotated[Kullanici, Depends(mevcut_kullanici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    if govde.tur not in CONSENT_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz rıza türü",
            detaylar=[{"alan": "tur", "mesaj": f"Geçerli: {', '.join(sorted(CONSENT_TURLERI))}"}],
        )
    from app.core.context import istemci_ip_ctx

    kayit = ConsentKaydi(
        kullanici_id=kullanici.id,
        tur=govde.tur,
        metin_surumu=govde.metin_surumu,
        kabul=govde.kabul,
        ip_adresi=istemci_ip_ctx.get(),
    )
    db.add(kayit)
    await db.flush()
    await denetim_yaz(
        db,
        eylem="consent",
        kaynak="uyum",
        kaynak_id=str(kayit.id),
        kullanici=kullanici,
        detay={"tur": govde.tur, "kabul": govde.kabul, "surum": govde.metin_surumu},
    )
    return basari(
        ConsentCevapDTO(
            id=kayit.id,
            tur=kayit.tur,
            metin_surumu=kayit.metin_surumu,
            kabul=kayit.kabul,
            olusturma_tarihi=kayit.olusturma_tarihi,
        ).model_dump(),
        mesaj="Rıza kaydı eklendi",
    )
