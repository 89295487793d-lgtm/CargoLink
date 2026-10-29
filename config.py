import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    bot_token: str
    webapp_url: str
    database_url: str
    dev_auth: bool
    log_level: str

def settings() -> Settings:
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
        webapp_url=os.getenv("WEBAPP_URL", "https://example.invalid").strip(),
        database_url=os.getenv("DATABASE_URL", "postgresql+asyncpg://cargolink:cargolink_dev_password@db:5432/cargolink").strip(),
        dev_auth=os.getenv("DEV_AUTH", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
