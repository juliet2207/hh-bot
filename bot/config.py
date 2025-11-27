from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Telegram Bot ---
    TG_BOT_API_KEY: str

    # --- Database (Neon PostgreSQL) ---
    # Пример:
    # postgres://user:pass@ep-calm-darkness-123456.us-east-2.aws.neon.tech/neondb
    DATABASE_URL: str

    # --- LLM / OpenAI-compatible ---
    LLM_API_KEY: str | None = None
    LLM_API_URL: str = Field(
        default="https://api.openai.com/v1",
        description="Any OpenAI-compatible endpoint",
    )
    LLM_MODEL: str = "gpt-4o-mini"

    # --- App Settings ---
    LOG_LEVEL: str = "DEBUG"
    ENV: str = Field(default="dev")  # dev / prod / staging

    # --- Webhook (prod only) ---
    WEBHOOK_URL: str | None = None
    WEBHOOK_SECRET: str | None = None
    WEBAPP_HOST: str = "127.0.0.1"
    WEBAPP_PORT: int = 8271

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
