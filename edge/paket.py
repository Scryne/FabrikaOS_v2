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
