import asyncio
from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db, async_session
from models import User, Simulation, SimulationResult, PersonaResponse as PersonaResponseModel
from schemas import SimulationCreate, SimulationResponse, SimulationDetailResponse
from auth import get_current_user
from services.simulation import run_simulation

router = APIRouter()


@router.post("", response_model=SimulationResponse, status_code=202)
async def create_simulation(
    sim_data: SimulationCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check sim limit
    if current_user.simulations_remaining is not None and current_user.simulations_remaining <= 0:
        raise HTTPException(status_code=403, detail="No simulations remaining. Please upgrade your plan.")

    # Determine number of personas to use
    num_personas = len(sim_data.persona_ids) if sim_data.persona_ids else sim_data.num_personas

    sim = Simulation(
        user_id=current_user.id,
        pitch_title=sim_data.pitch_title,
        pitch_content=sim_data.pitch_content,
        company_name=sim_data.company_name,
        industry=sim_data.industry,
        target_audience=sim_data.target_audience,
        num_personas=num_personas,
        config=sim_data.config if sim_data.config else {},
        status="pending",
    )
    db.add(sim)

    # Decrement remaining simulations
    if current_user.simulations_remaining is not None:
        current_user.simulations_remaining -= 1

    await db.commit()
    await db.refresh(sim)

    # Launch simulation in background
    background_tasks.add_task(
        run_simulation,
        str(sim.id),
        sim_data.pitch_content,
        sim_data.persona_filters.model_dump() if sim_data.persona_filters else None,
        sim_data.num_personas,
        persona_ids=[str(pid) for pid in sim_data.persona_ids] if sim_data.persona_ids else None,
    )

    return sim


@router.get("", response_model=List[SimulationResponse])
async def list_simulations(
    status: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Simulation).where(Simulation.user_id == current_user.id)
    if status:
        query = query.where(Simulation.status == status)
    query = query.order_by(desc(Simulation.created_at)).limit(limit).offset(offset)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{simulation_id}")
async def get_simulation(
    simulation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.results))
        .where(Simulation.id == simulation_id, Simulation.user_id == current_user.id)
    )
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    response = {
        "id": sim.id,
        "pitch_title": sim.pitch_title,
        "pitch_content": sim.pitch_content,
        "company_name": sim.company_name,
        "industry": sim.industry,
        "target_audience": sim.target_audience,
        "num_personas": sim.num_personas,
        "status": sim.status,
        "progress_pct": sim.progress_pct,
        "created_at": sim.created_at,
        "started_at": sim.started_at,
        "completed_at": sim.completed_at,
    }

    if sim.results:
        r = sim.results
        response["results"] = {
            "overall_engagement_score": r.overall_engagement_score,
            "overall_sentiment_score": r.overall_sentiment_score,
            "sentiment_breakdown": r.sentiment_breakdown,
            "key_objections": r.key_objections,
            "objection_frequency": r.objection_frequency,
            "key_recommendations": r.key_recommendations,
            "strongest_segments": r.strongest_segments,
            "weakest_segments": r.weakest_segments,
            "engagement_by_industry": r.engagement_by_industry,
        }

    return response


@router.get("/{simulation_id}/responses")
async def get_simulation_responses(
    simulation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify ownership
    sim_result = await db.execute(
        select(Simulation).where(Simulation.id == simulation_id, Simulation.user_id == current_user.id)
    )
    if not sim_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Simulation not found")

    result = await db.execute(
        select(PersonaResponseModel)
        .options(selectinload(PersonaResponseModel.persona))
        .where(PersonaResponseModel.simulation_id == simulation_id)
    )
    responses = result.scalars().all()

    return [
        {
            "id": r.id,
            "persona_id": r.persona_id,
            "persona_name": r.persona.name if r.persona else "Unknown",
            "persona_title": r.persona.title if r.persona else "",
            "industry": r.persona.industry if r.persona else "",
            "company_size": r.persona.company_size if r.persona else "",
            "initial_reaction": r.initial_reaction,
            "sentiment": r.sentiment,
            "engagement_score": r.engagement_score,
            "questions_raised": r.questions_raised or [],
            "objections": r.objections or [],
            "likely_decision": r.likely_decision,
            "buying_confidence_shift": r.buying_confidence_shift,
        }
        for r in responses
    ]
