from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    job_secret: str = "change-me"
    cors_origins: str = "http://localhost:3000"
    supabase_url: str = ""
    supabase_service_key: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""


settings = Settings()
