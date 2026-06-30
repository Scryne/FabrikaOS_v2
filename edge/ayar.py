"""Edge ajanı yapılandırması (env / .env)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class EdgeAyar(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EDGE_", env_file=".env", extra="ignore")

    broker_host: str = "localhost"
    broker_port: int = 1883
    tenant_slug: str = "alfa"
    cihaz_kod: str = "GW-1"
    surucu: str = "simulasyon"
    makine_kodlari: list[str] = ["MAK-1"]
    aralik_sn: float = 2.0
    tohum: int = 0
    tampon_yolu: str = "edge_tampon.sqlite"
