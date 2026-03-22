from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "PitchSim AI"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pitchsim"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/pitchsim"

    # Auth
    secret_key: str = "change-me-in-production-use-a-real-secret"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # LLM via OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_default_model: str = "openai/gpt-4o-mini"

    # Multi-model pool — add as many as you want
    # Models are distributed across simulations round-robin
    # Premium models (tier1) get high-value personas (C-suite, budget holders)
    # Volume models (tier2) handle the bulk
    openrouter_model1_id: str = ""  # tier1 premium (e.g. anthropic/claude-sonnet-4)
    openrouter_model2_id: str = ""  # tier1 premium (e.g. openai/gpt-4o)
    openrouter_model3_id: str = ""  # tier2 volume  (e.g. openai/gpt-4o-mini)
    openrouter_model4_id: str = ""  # tier2 volume  (e.g. meta-llama/llama-3.1-70b-instruct)
    openrouter_model5_id: str = ""  # tier2 volume  (e.g. google/gemini-flash-1.5)

    # Concurrency per model (stay under rate limits)
    openrouter_concurrency_per_model: int = 10

    # Redis (for Celery task queue)
    redis_url: str = "redis://localhost:6379/0"

    # MiroFish
    mirofish_api_url: str = "http://localhost:8080"

    # Simulation defaults
    default_num_personas: int = 10
    max_personas_per_sim: int = 100

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
