from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "PitchSim AI"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pitchsim"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/pitchsim"

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

    # PitchSim Swarm Engine — Multi-Agent Deliberation
    # Creates multiple buying committees that debate pitches and reach consensus.
    # No external dependencies — runs entirely on the OpenRouter model pool.
    swarm_default_tables: int = 3           # Number of committee tables per simulation
    swarm_default_personas_per_table: int = 5  # Personas per committee
    swarm_default_debate_rounds: int = 2    # Debate rounds per committee

    # Simulation defaults
    default_num_personas: int = 10
    max_personas_per_sim: int = 100

    class Config:
        env_file = "../.env"  # root of repo

@lru_cache()
def get_settings():
    return Settings()
