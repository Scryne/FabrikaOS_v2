"""API anahtarı kimlik doğrulaması (``X-API-Anahtar``) — dış veri yüzeyinin girişi.

JWT ``Authorization`` başlığıyla karışmaz. Akış: ``tenant_cozumle`` (X-Tenant/subdomain;
anahtar tenant şemasında yaşadığı için arama yapısal olarak izole) → SHA-256 özet
eşleşmesi → aktif + geçerlilik kontrolü → kapsam (``izinler``) kontrolü →
``son_kullanim_tarihi`` güncelle.

Başarısız her kimlik dalı **401** döner — anahtarın var/pasif/süresi-dolmuş ayrımı
sızdırılmaz. Kapsam yetersizse (geçerli anahtar, eksik izin) **403**.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.db.session import get_session
from app.core.deps import tenant_cozumle
from app.core.exceptions import KimlikHatasi, YetkiHatasi
from app.modules.entegrasyon.models import ApiAnahtari
from app.modules.entegrasyon.service import anahtar_ozetle

API_ANAHTAR_BASLIGI = "X-API-Anahtar"


def api_izin_gerekli(kapsam: str) -> Callable[..., Awaitable[ApiAnahtari]]:
    """``kapsam`` iznini taşıyan geçerli bir API anahtarı şart koşan dependency üretir."""

    async def kontrol(
        request: Request,
        _tenant: Annotated[Tenant, Depends(tenant_cozumle)],
        db: Annotated[AsyncSession, Depends(get_session)],
    ) -> ApiAnahtari:
        ham = request.headers.get(API_ANAHTAR_BASLIGI.lower())
        if not ham:
            raise KimlikHatasi("API anahtarı gerekli")
        sonuc = await db.execute(
            select(ApiAnahtari).where(ApiAnahtari.anahtar_ozet == anahtar_ozetle(ham))
        )
        anahtar = sonuc.scalar_one_or_none()
        simdi = datetime.now(UTC)
        if (
            anahtar is None
            or not anahtar.aktif
            or (anahtar.gecerlilik_tarihi is not None and anahtar.gecerlilik_tarihi < simdi)
        ):
            raise KimlikHatasi("Geçersiz API anahtarı")
        if kapsam not in (anahtar.izinler or []):
            raise YetkiHatasi(f"Anahtar kapsamı yetersiz: {kapsam}")
        anahtar.son_kullanim_tarihi = simdi
        await db.flush()
        return anahtar

    return kontrol
