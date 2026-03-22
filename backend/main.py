from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import init_db
from routers import simulations, personas, chat, committee

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    await init_db()
    # Seed default personas if empty
    from services.persona import seed_default_personas
    await seed_default_personas()
    yield
    # Shutdown


app = FastAPI(
    title=settings.app_name,
    description="AI-powered sales pitch simulation platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulations.router, prefix="/api/simulations", tags=["Simulations"])
app.include_router(personas.router, prefix="/api/personas", tags=["Personas"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(committee.router, prefix="/api/committee", tags=["Buying Committee"])


@app.get("/api/health")
async def health_check():
    """
    Health check endpoint. Must respond FAST — Railway uses this to determine
    if the service is alive. MiroFish status is checked separately.
    """
    from services.model_pool import get_model_pool
    pool = get_model_pool()

    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "0.2.0",
        "models_configured": len(pool.models),
        "model_ids": list(pool.models.keys()),
    }


@app.get("/api/health/full")
async def health_check_full():
    """Extended health check including MiroFish status (may take 2-3s)."""
    from services.model_pool import get_model_pool
    from services.mirofish import get_mirofish_client

    pool = get_model_pool()
    mf_client = get_mirofish_client()
    mf_healthy = await mf_client.health_check()

    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "0.2.0",
        "engine": "mirofish" if mf_healthy else "model_pool_fallback",
        "mirofish_available": mf_healthy,
        "mirofish_url": settings.mirofish_api_url,
        "models_configured": len(pool.models),
        "model_ids": list(pool.models.keys()),
    }


@app.get("/api/models/stats")
async def model_stats():
    """Live stats for all models in the pool — calls, errors, latency, distribution."""
    from services.model_pool import get_model_pool
    return get_model_pool().get_stats()


@app.get("/api/models/pool")
async def model_pool_info():
    """Show the configured model pool with tiers."""
    from services.model_pool import get_model_pool
    pool = get_model_pool()
    return {
        "premium_models": [m.model_id for m in pool.premium_models],
        "volume_models": [m.model_id for m in pool.volume_models],
        "concurrency_per_model": settings.openrouter_concurrency_per_model,
        "total_models": len(pool.models),
    }
