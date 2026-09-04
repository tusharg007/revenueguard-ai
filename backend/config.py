from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM Configuration (Groq primary, OpenRouter fallback)
    GROQ_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    LLM_PROVIDER: str = "groq"  # "groq" or "openrouter"
    LLM_MODEL: str = "llama-3.3-70b-versatile"

    # Razorpay
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./revenueguard.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Policy
    HIGH_VALUE_THRESHOLD: int = 5_000_000  # ₹50K in paise
    MAX_RETRY_ATTEMPTS: int = 3
    COOLDOWN_HOURS: int = 24
    QUIET_HOURS_START: int = 21  # 9 PM IST
    QUIET_HOURS_END: int = 9  # 9 AM IST

    # Experiments
    EXPERIMENT_VARIANT_PCT: int = 20

    # n8n
    N8N_APPROVAL_WEBHOOK_URL: str = ""

    # App
    APP_ENV: str = "development"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
