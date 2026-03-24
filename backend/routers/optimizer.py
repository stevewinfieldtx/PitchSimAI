"""
AutoOptimizer Router
=====================
Karpathy-loop style autonomous pitch optimization.
Runs the Swarm Engine in a loop, rewriting the pitch after each evaluation.
"""

from uuid import UUID, uuid4
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from database import get_db, async_session
from models import Simulation, SimulationResult
from services.pitch_optimizer import get_pitch_optimizer

router = APIRouter()


# ── In-memory store for optimization jobs ──
# (For MVP. Move to Redis/DB if needed later.)
_optimization_jobs: dict = {}


class OptimizeRequest(BaseModel):
    pitch_content: str
    pitch_title: str = "Pitch Optimization"
    company_name: str = ""
    industry: str = "technology"
    target_audience: str = ""
    company_size: str = "mid-market"
    max_iterations: int = Field(default=5, ge=1, le=10)
    target_score: int = Field(default=85, ge=50, le=100)


class OptimizeFromSimRequest(BaseModel):
    """Optimize a pitch that was already simulated."""
    simulation_id: UUID
    max_iterations: int = Field(default=5, ge=1, le=10)
    target_score: int = Field(default=85, ge=50, le=100)


@router.post("/start")
async def start_optimization(
    req: OptimizeRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start an autonomous pitch optimization loop.

    The optimizer will:
    1. Evaluate the pitch with buying committees
    2. Rewrite the pitch based on committee feedback
    3. Re-evaluate the rewrite
    4. Keep improvements, revert regressions
    5. Repeat for max_iterations or until target_score is reached

    Returns a job_id to poll for results.
    """
    job_id = str(uuid4())

    _optimization_jobs[job_id] = {
        "status": "running",
        "progress_pct": 0,
        "stage": "starting",
        "detail": "Initializing optimizer...",
        "result": None,
    }

    async def run_optimization():
        optimizer = get_pitch_optimizer()
        try:
            async def progress_cb(stage: str, detail: str, pct: int):
                _optimization_jobs[job_id]["stage"] = stage
                _optimization_jobs[job_id]["detail"] = detail
                _optimization_jobs[job_id]["progress_pct"] = pct

            result = await optimizer.optimize(
                pitch_content=req.pitch_content,
                industry=req.industry,
                company_name=req.company_name,
                company_size=req.company_size,
                target_audience=req.target_audience,
                max_iterations=req.max_iterations,
                target_score=req.target_score,
                num_tables=2,
                personas_per_table=4,
                debate_rounds=1,
                progress_callback=progress_cb,
            )

            _optimization_jobs[job_id]["status"] = "completed"
            _optimization_jobs[job_id]["progress_pct"] = 100
            _optimization_jobs[job_id]["result"] = result

        except Exception as e:
            _optimization_jobs[job_id]["status"] = "failed"
            _optimization_jobs[job_id]["detail"] = str(e)

    background_tasks.add_task(run_optimization)

    return {"job_id": job_id, "status": "running"}


@router.post("/from-simulation")
async def optimize_from_simulation(
    req: OptimizeFromSimRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Optimize a pitch that was already run through a simulation.
    Pulls the pitch content, industry, etc. from the existing simulation.
    """
    result = await db.execute(
        select(Simulation).where(Simulation.id == req.simulation_id)
    )
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    job_id = str(uuid4())
    _optimization_jobs[job_id] = {
        "status": "running",
        "progress_pct": 0,
        "stage": "starting",
        "detail": "Loading simulation data...",
        "result": None,
        "source_simulation_id": str(req.simulation_id),
    }

    async def run_optimization():
        optimizer = get_pitch_optimizer()
        try:
            async def progress_cb(stage: str, detail: str, pct: int):
                _optimization_jobs[job_id]["stage"] = stage
                _optimization_jobs[job_id]["detail"] = detail
                _optimization_jobs[job_id]["progress_pct"] = pct

            result = await optimizer.optimize(
                pitch_content=sim.pitch_content,
                industry=sim.industry or "technology",
                company_name=sim.company_name or "",
                company_size=(sim.config or {}).get("company_size", "mid-market"),
                target_audience=sim.target_audience or "",
                max_iterations=req.max_iterations,
                target_score=req.target_score,
                num_tables=2,
                personas_per_table=4,
                debate_rounds=1,
                progress_callback=progress_cb,
            )

            _optimization_jobs[job_id]["status"] = "completed"
            _optimization_jobs[job_id]["progress_pct"] = 100
            _optimization_jobs[job_id]["result"] = result

        except Exception as e:
            _optimization_jobs[job_id]["status"] = "failed"
            _optimization_jobs[job_id]["detail"] = str(e)

    background_tasks.add_task(run_optimization)

    return {"job_id": job_id, "status": "running", "pitch_title": sim.pitch_title}


@router.get("/status/{job_id}")
async def get_optimization_status(job_id: str):
    """Poll optimization progress."""
    job = _optimization_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Optimization job not found")

    response = {
        "job_id": job_id,
        "status": job["status"],
        "progress_pct": job["progress_pct"],
        "stage": job["stage"],
        "detail": job["detail"],
    }

    # Include results if complete
    if job["status"] == "completed" and job["result"]:
        result = job["result"]
        response["result"] = {
            "original_pitch": result["original_pitch"],
            "optimized_pitch": result["optimized_pitch"],
            "original_scores": result["original_scores"],
            "optimized_scores": result["optimized_scores"],
            "total_iterations": result["total_iterations"],
            "kept_count": result["kept_count"],
            "reverted_count": result["reverted_count"],
            "summary": result["summary"],
            "elapsed_seconds": result["elapsed_seconds"],
            "score_progression": result["score_progression"],
            "iterations": result["iterations"],
        }

    return response


@router.get("/jobs")
async def list_optimization_jobs():
    """List all optimization jobs (most recent first)."""
    return [
        {
            "job_id": jid,
            "status": job["status"],
            "progress_pct": job["progress_pct"],
            "stage": job["stage"],
        }
        for jid, job in reversed(list(_optimization_jobs.items()))
    ]
