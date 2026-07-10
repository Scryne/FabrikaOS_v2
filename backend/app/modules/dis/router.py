"""Dış self-servis portal uçları (``/api/v1/dis/*``) — S18 / ADR-0020.

Skill sözleşmesi (tenant-rbac-conventions / Dış panel): dış kullanıcı **yalnızca kendi
firmasının** kayıtlarını görür; firma süzgeci ``dis_firma_kullanici`` dependency'sinde
ZORLANIR, controller'a bırakılmaz. Rol ``dis-panel`` = yalnız ``dis:erisim`` — iç uçların
tamamı başka izin istediğinden dış kullanıcı yapısal olarak içeride yetkisizdir; iç
kullanıcılar da (admin dahil) firma bağlantısı olmadığından bu yüzeye giremez.

Modül kapısı: ``dis-portal`` (üst-segment eklenti; ADR-0020). Talep verisi iç ``talep``
modülüyle AYNI tablodur — portal talebi iç ekranlarda anında görünür (tek doğruluk
kaynağı; ``talep.olusturuldu`` gerçek-zaman sinyali de aynıdır).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.exceptions import DogrulamaHatasi, KaynakBulunamadi, YetkiHatasi
from app.core.gercekzaman import yayinla
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.crm import repository as crm_repo
from app.modules.dis.schemas import (
    DisDurumDTO,
    DisDurumSayiDTO,
    DisTalepCevapDTO,
    DisTalepOlusturDTO,
)
from app.modules.talep import repository as talep_repo
from app.modules.talep import service as talep_service
from app.modules.talep.birimler import ONCELIKLER, TALEP_TURLERI
from app.modules.talep.models import Talep

router = APIRouter(
    prefix="/dis", tags=["Dış Portal"], dependencies=[Depends(modul_gerekli("dis-portal"))]
)


async def dis_firma_kullanici(
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("dis:erisim"))],
) -> Kullanici:
    """Dış portal kimliği: ``dis:erisim`` izni + zorunlu firma bağlantısı.

    Firma süzgeci burada zorlanır — ``firma_id`` boş olan (ör. admin) 403 alır.
    """
    if kullanici.firma_id is None:
        raise YetkiHatasi("Dış portal için firma bağlantısı gerekli")
    return kullanici


def _cevap(t: Talep) -> dict[str, Any]:
    return DisTalepCevapDTO(
        id=t.id,
        kod=t.kod,
        baslik=t.baslik,
        aciklama=t.aciklama,
        tur=t.tur,
        oncelik=t.oncelik,
        durum=t.durum,
        olusturma_tarihi=t.olusturma_tarihi,
        guncelleme_tarihi=t.guncelleme_tarihi,
    ).model_dump()


@router.get(
    "/talepler",
    response_model=Zarf[list[DisTalepCevapDTO]],
    summary="Taleplerim (yalnız kendi firmam)",
)
async def dis_talep_listele(
    kullanici: Annotated[Kullanici, Depends(dis_firma_kullanici)],
    db: Annotated[AsyncSession, Depends(get_session)],
    sayfa: int = 1,
    adet: int = 20,
    durum: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await talep_repo.listele(
        db, sayfa=sayfa, adet=adet, firma_id=kullanici.firma_id, durum=durum
    )
    return sayfali([_cevap(t) for t in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.post(
    "/talepler",
    response_model=Zarf[DisTalepCevapDTO],
    status_code=201,
    summary="Yeni talep aç (firma sunucuda atanır)",
)
async def dis_talep_olustur(
    govde: DisTalepOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(dis_firma_kullanici)],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    if govde.tur not in TALEP_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz talep türü",
            detaylar=[{"alan": "tur", "mesaj": f"Geçerli: {', '.join(sorted(TALEP_TURLERI))}"}],
        )
    if govde.oncelik not in ONCELIKLER:
        raise DogrulamaHatasi(
            "Geçersiz öncelik",
            detaylar=[{"alan": "oncelik", "mesaj": f"Geçerli: {', '.join(sorted(ONCELIKLER))}"}],
        )
    talep = Talep(
        kod=talep_service.talep_gecici_kod(),
        # Firma İSTEMCİDEN ALINMAZ — oturumdaki dış kullanıcının firmasıdır.
        firma_id=kullanici.firma_id,
        baslik=govde.baslik,
        aciklama=govde.aciklama,
        tur=govde.tur,
        oncelik=govde.oncelik,
        talep_eden_kullanici_id=kullanici.id,
        talep_eden_ad=kullanici.ad_soyad,
    )
    await talep_repo.ekle(db, talep)
    talep.kod = talep_service.talep_kalici_kod(talep.id)
    await db.flush()
    # Kod UPDATE'i sunucu-tarafı onupdate'i tetikler → guncelleme_tarihi expire olur;
    # DTO'ya girmeden yenile (async oturumda tembel yükleme MissingGreenlet fırlatır).
    await db.refresh(talep)
    await denetim_yaz(
        db, eylem="olustur", kaynak="dis_talep", kaynak_id=str(talep.id), kullanici=kullanici
    )
    await yayinla(tenant.slug, {"tur": "talep.olusturuldu", "id": talep.id})
    return basari(_cevap(talep), mesaj="Talebiniz alındı")


@router.get(
    "/talepler/{talep_id}",
    response_model=Zarf[DisTalepCevapDTO],
    summary="Talep detayı (başka firmanınki görünmez)",
)
async def dis_talep_detay(
    talep_id: int,
    kullanici: Annotated[Kullanici, Depends(dis_firma_kullanici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    talep = await talep_repo.getir(db, talep_id)
    # Başka firmanın talebi YOKMUŞ gibi davranır (404 — görünmez kalır).
    if talep is None or talep.firma_id != kullanici.firma_id:
        raise KaynakBulunamadi("Talep bulunamadı")
    return basari(_cevap(talep), mesaj="Talep detayı")


@router.get("/durum", response_model=Zarf[DisDurumDTO], summary="Portal özeti (firma bağlamı)")
async def dis_durum(
    kullanici: Annotated[Kullanici, Depends(dis_firma_kullanici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    firma = await crm_repo.firma_getir(db, kullanici.firma_id or 0)
    if firma is None:
        raise KaynakBulunamadi("Firma bulunamadı")

    durum_sonuc = await db.execute(
        select(Talep.durum, func.count())
        .where(Talep.firma_id == kullanici.firma_id)
        .group_by(Talep.durum)
    )
    sayac = {d: int(a) for d, a in durum_sonuc.all()}

    son = await db.execute(
        select(Talep).where(Talep.firma_id == kullanici.firma_id).order_by(Talep.id.desc()).limit(5)
    )

    ozet = DisDurumDTO(
        firma_ad=firma.ad,
        toplam=sum(sayac.values()),
        acik=sayac.get("acik", 0) + sayac.get("inceleniyor", 0),
        durum_dagilimi=[DisDurumSayiDTO(durum=d, adet=a) for d, a in sorted(sayac.items())],
        son_talepler=[DisTalepCevapDTO(**_cevap(t)) for t in son.scalars()],
    )
    return basari(ozet.model_dump(), mesaj="Portal özeti")
