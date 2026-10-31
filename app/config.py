import os

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = ""
    webapp_url: str = ""
    database_url: str = "postgresql+asyncpg://cargolink:cargolink_local_password@localhost:5432/cargolink"
    log_level: str = "INFO"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def infer_codespaces_webapp_url(self):
        if not self.webapp_url.startswith("https://"):
            codespace = os.getenv("CODESPACE_NAME", "").strip()
            domain = os.getenv("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "app.github.dev").strip()
            if codespace and domain:
                self.webapp_url = f"https://{codespace}-8000.{domain}"
        return self


def get_settings() -> Settings:
    return Settings()
