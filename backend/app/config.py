from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./edutrack.db"
    redis_url: str | None = None
    jwt_secret: str = "change-me-in-production"
    jwt_expire_minutes: int = 60 * 8
    cors_origins: str = "http://localhost:5173"
    seed_demo_users: bool = True

    # optional, any OpenAI-compatible endpoint (Groq, Ollama)
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "llama-3.1-8b-instant"


settings = Settings()
