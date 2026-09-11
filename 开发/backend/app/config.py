from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "VibeCodingWiki"
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./data/vibecodingwiki.db"
    data_dir: Path = Path("./data")
    access_secret: str = "change-this-access-secret"
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    cookie_secure: bool = False
    admin_email: str = "admin@example.com"
    admin_password: str = "ChangeMe123!"
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost"])

    model_config = SettingsConfigDict(env_file=".env", env_prefix="VCW_", extra="ignore")

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("sqlite+aiosqlite", "sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
