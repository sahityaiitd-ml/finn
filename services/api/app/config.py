from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(ROOT_ENV, ".env"), extra="ignore")

    job_secret: str = "change-me"
    cors_origins: str = "http://localhost:3000"
    supabase_url: str = ""
    supabase_service_key: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"  # 2.5 is closed to new users
    gemini_api_keys: str = ""  # optional, comma-separated; rotated on rate limits


settings = Settings()
