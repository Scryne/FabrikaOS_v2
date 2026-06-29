"""Uygulama yapılandırması (Pydantic Settings).

Ortam değişkenlerinden veya `.env` dosyasından okur. `get_settings()` önbelleklidir.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Uygulama ---
    app_env: str = "dev"  # dev | staging | prod
    app_name: str = "FabrikaOS"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # Üretimde MUTLAKA override edilir.
    secret_key: str = "degistir-bu-degeri-uretimde"

    cors_origins: list[str] = Field(default_factory=list)

    # --- Veri/cache ---
    database_url: str = "postgresql+asyncpg://fabrikaos:fabrikaos@db:5432/fabrikaos"
    redis_url: str = "redis://redis:6379/0"

    # --- Kimlik / JWT (S2) ---
    jwt_algoritma: str = "HS256"
    access_token_dakika: int = 15  # kısa ömürlü access token
    refresh_token_gun: int = 7  # rotasyonlu refresh token

    # --- Rate limit (S2) ---
    rate_limit_istek: int = 100  # pencere başına izinli istek
    rate_limit_pencere_sn: int = 60  # pencere süresi (saniye)

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
