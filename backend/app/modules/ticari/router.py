"""Ticari özet ucu (``/api/v1/ticari/ozet``) — odaklı pano verisi.

CRM/sözleşme/talep/duyuru sayaçları + yaklaşan sözleşmeler + son yayınlanan duyurular.
Tenant-kapsamlı + ``crm:oku`` korumalı.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.responses import Zarf, basari
from app.kimlik.models import Kullanici
from app.modules.crm.models import Firma
from app.modules.duyuru.models import Duyuru
from app.modules.sozlesme import repository as sozlesme_repo
from app.modules.sozlesme.hesap import kalan_gun
from app.modules.sozlesme.models import Sozlesme
from app.modules.talep.models import Talep
from app.modules.ticari.schemas import (
    SonDuyuruDTO,
    TicariOzetDTO,
    TicariSayaclarDTO,
    YaklasanSozlesmeDTO,
)

router = APIRouter(tags=["Ticari"], dependencies=[Depends(modul_gerekli("crm"))])

_YAKLASAN_ESIK_GUN = 30
_LISTE_SINIRI = 5


@router.get("/ticari/ozet", response_model=Zarf[TicariOzetDTO], summary="Ticari özet (pano)")
async def ticari_ozet(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("crm:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    bugun = datetime.now(UTC).date()
    sinir = bugun + timedelta(days=_YAKLASAN_ESIK_GUN)

    firma_sayisi = await db.scalar(select(func.count()).select_from(Firma)) or 0
    aktif_firma = (
        await db.scalar(select(func.count()).select_from(Firma).where(Firma.aktif.is_(True))) or 0
    )
    yaklasan = await sozlesme_repo.yaklasan_listele(db, bugun=bugun, sinir=sinir)
    aktif_sozlesme = (
        await db.scalar(select(func.count()).select_from(Sozlesme).where(Sozlesme.durum == "aktif"))
        or 0
    )
    acik_talep = (
        await db.scalar(
            select(func.count()).select_from(Talep).where(Talep.durum.in_(("acik", "inceleniyor")))
        )
        or 0
    )
    yayinli_duyuru = (
        await db.scalar(select(func.count()).select_from(Duyuru).where(Duyuru.yayinda.is_(True)))
        or 0
    )

    son_duyurular_sonuc = await db.execute(
        select(Duyuru)
        .where(Duyuru.yayinda.is_(True))
        .order_by(Duyuru.yayin_tarihi.desc())
        .limit(_LISTE_SINIRI)
    )
    son_duyurular = son_duyurular_sonuc.scalars().all()

    ozet = TicariOzetDTO(
        sayaclar=TicariSayaclarDTO(
            firma_sayisi=int(firma_sayisi),
            aktif_firma=int(aktif_firma),
            aktif_sozlesme=int(aktif_sozlesme),
            yaklasan_sozlesme=len(yaklasan),
            acik_talep=int(acik_talep),
            yayinli_duyuru=int(yayinli_duyuru),
        ),
        yaklasan_sozlesmeler=[
            YaklasanSozlesmeDTO(
                id=s.id,
                kod=s.kod,
                firma_id=s.firma_id,
                baslik=s.baslik,
                bitis_tarihi=s.bitis_tarihi,
                kalan_gun=kalan_gun(s.bitis_tarihi, bugun),
                tutar=float(s.tutar),
                para_birimi=s.para_birimi,
            )
            for s in yaklasan[:_LISTE_SINIRI]
        ],
        son_duyurular=[
            SonDuyuruDTO(
                id=d.id, kod=d.kod, baslik=d.baslik, onem=d.onem, yayin_tarihi=d.yayin_tarihi
            )
            for d in son_duyurular
        ],
    )
    return basari(ozet.model_dump(), mesaj="Ticari özet")
