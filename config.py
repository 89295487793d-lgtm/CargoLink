from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    bot_token: str = ""
    webapp_url: str = "https://example.com"
    database_url: str = "sqlite:///./cargolink.db"
    admin_ids: str = ""
    app_name: str = "CargoLink"
    log_level: str = "INFO"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

def settings() -> Settings:
    return Settings()
