from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_keys: str = ""
    app_secret_key: str = "dev-secret"
    debug_token: str = "dev-debug"
    database_url: str = "sqlite+aiosqlite:///./nyayra.db"
    storage_path: str = "./storage"

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""
    public_base_url: str = "http://localhost:8000"

    model_prep: str = "gemini-flash-lite-latest"
    model_act_select: str = "gemini-flash-lite-latest"
    model_council: str = "gemini-3.5-flash"
    model_verify: str = "gemini-3.5-flash"
    model_draft: str = "gemini-3.5-flash"
    model_unmask: str = "gemini-flash-lite-latest"
    model_audio: str = "gemini-2.5-flash-native-audio-latest"
    model_embed: str = "gemini-embedding-001"

    max_concurrent_calls: int = 8

    @property
    def key_list(self) -> list[str]:
        return [k.strip() for k in self.gemini_api_keys.split(",") if k.strip()]

    def model_for(self, stage: str) -> str:
        return getattr(self, f"model_{stage}")


@lru_cache
def get_settings() -> Settings:
    return Settings()
