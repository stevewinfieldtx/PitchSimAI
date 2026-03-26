from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "PitchSim AI"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pitchsim"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/pitchsim"

    # LLM via OpenRouter — single model
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_default_model: str = "google/gemini-2.5-flash"
    openrouter_concurrency_per_model: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Swarm Engine defaults
    swarm_default_tables: int = 3
    swarm_default_personas_per_table: int = 5
    swarm_default_debate_rounds: int = 2

    # Simulation defaults
    default_num_personas: int = 10
    max_personas_per_sim: int = 100

    class Config:
        env_file = "../.env"

@lru_cache()
def get_settings():
    return Settings()
