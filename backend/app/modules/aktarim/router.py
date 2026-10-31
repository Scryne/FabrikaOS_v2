"""Veri içe aktarma uçları (S21, ADR-0042): tür listesi, şablon, önizleme, uygulama.

Her tür kendi alt yoluna sahiptir (``/ice-aktarma/makine/...``); yetki ve modül kapısı türün
izni ve modülüyle router düzeyinde bağlanır: personel yükleme ``ik:yaz`` + ``ik`` modülü ister.
"""

# ``from __future__ import annotations`` bilerek yok: tür uçları fabrika içinde tanımlanıyor ve
# ``Depends(izin_gerekli(t.izin))`` kapanıştaki ``t``'ye bakıyor. Ertelenmiş (metin) açıklamalar
# FastAPI'de modül globalleriyle çözülür; ``t`` orada olmadığı için parametreler sessizce sorgu
# parametresine dönüşüp her istek 422 alıyordu.
import csv
import io
from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane import entitlement_service
from app.control_plane.models import Tenant
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, mevcut_kullanici, modul_gerekli, tenant_cozumle
from app.core.exceptions import DogrulamaHatasi
from app.core.responses import Zarf, basari
from app.kimlik.models import Kullanici
from app.modules.aktarim import service
from app.modules.aktarim.ayristir import DosyaGecersiz, dosya_oku
from app.modules.aktarim.schemas import OnizlemeDTO, TurDTO
from app.modules.aktarim.tanimlar import TURLER, Tur

router = APIRouter(prefix="/ice-aktarma", tags=["İçe Aktarma"])


@router.get("/turler", response_model=Zarf[list[TurDTO]], summary="İçe aktarma türleri")
async def turler(
    kullanici: Annotated[Kullanici, Depends(mevcut_kullanici)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    sonuc = []
    for t in sorted(TURLER.values(), key=lambda t: t.sira):
        modul_acik = await entitlement_service.tenant_modul_acik_mi(db, tenant, t.modul)
        sonuc.append(
            {
                "kod": t.kod,
                "baslik": t.baslik,
                "aciklama": t.aciklama,
                "anahtar": list(t.anahtar),
                "yetkili": modul_acik and kullanici.izin_var(t.izin),
                "alanlar": [
                    {"ad": a.ad, "zorunlu": a.zorunlu, "aciklama": a.aciklama, "ornek": a.ornek}
                    for a in t.alanlar
                ],
            }
        )
    return basari(sonuc)


async def _satirlar(dosya: UploadFile) -> list[dict[str, str]]:
    try:
        return dosya_oku(dosya.filename or "", await dosya.read())
    except DosyaGecersiz as exc:
        raise DogrulamaHatasi(str(exc), hata_kodu="DOSYA_GECERSIZ") from exc


def _onizleme_dto(o: service.Onizleme) -> dict[str, Any]:
    return asdict(o)


def _tur_router(t: Tur) -> APIRouter:
    r = APIRouter(prefix=f"/{t.kod}", dependencies=[Depends(modul_gerekli(t.modul))])

    @r.get("/sablon", summary=f"{t.baslik}: CSV şablonu", response_class=Response)
    async def sablon(_k: Annotated[Kullanici, Depends(izin_gerekli(t.izin))]) -> Response:
        tampon = io.StringIO()
        yazici = csv.writer(tampon, delimiter=";")
        yazici.writerow([a.ad for a in t.alanlar])
        yazici.writerow([a.ornek for a in t.alanlar])
        # BOM + ";": Türkçe Excel dosyayı çift tıkla doğru kodlama ve kolonlarla açar.
        return Response(
            content=("﻿" + tampon.getvalue()).encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="fabrikaos-{t.kod}-sablon.csv"'},
        )

    @r.post("/onizle", response_model=Zarf[OnizlemeDTO], summary=f"{t.baslik}: önizle (yazmaz)")
    async def onizle(
        _k: Annotated[Kullanici, Depends(izin_gerekli(t.izin))],
        db: Annotated[AsyncSession, Depends(get_session)],
        dosya: Annotated[UploadFile, File()],
    ) -> dict[str, Any]:
        o = await service.onizle(db, t, await _satirlar(dosya))
        return basari(_onizleme_dto(o))

    @r.post(
        "/uygula",
        response_model=Zarf[OnizlemeDTO],
        summary=f"{t.baslik}: uygula (hepsi ya da hiçbiri)",
    )
    async def uygula(
        kullanici: Annotated[Kullanici, Depends(izin_gerekli(t.izin))],
        db: Annotated[AsyncSession, Depends(get_session)],
        dosya: Annotated[UploadFile, File()],
    ) -> dict[str, Any]:
        o = await service.uygula(db, t, await _satirlar(dosya), kullanici, dosya.filename or "")
        return basari(
            _onizleme_dto(o), mesaj=f"{o.yeni} yeni, {o.guncelle} güncellendi, {o.ayni} değişmedi"
        )

    return r


for _tur in TURLER.values():
    router.include_router(_tur_router(_tur))
