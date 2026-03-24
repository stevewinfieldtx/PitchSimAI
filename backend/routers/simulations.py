import asyncio
from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db, async_session
from models import Simulation, SimulationResult, PersonaResponse as PersonaResponseModel
from schemas import SimulationCreate, SimulationResponse
from services.simulation import run_simulation, run_swarm_simulation

router = APIRouter()


@router.post("", response_model=SimulationResponse, status_code=202)
async def create_simulation(
    sim_data: SimulationCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    num_personas = len(sim_data.persona_ids) if sim_data.persona_ids else sim_data.num_personas
    config = sim_data.config or {}

    # Extract cultural context from config
    seller_region = config.get("seller_region", "")
    buyer_region = config.get("buyer_region", "")
    cultural_notes = config.get("cultural_notes", "")

    sim = Simulation(
        pitch_title=sim_data.pitch_title,
        pitch_content=sim_data.pitch_content,
        company_name=sim_data.company_name,
        industry=sim_data.industry,
        target_audience=sim_data.target_audience,
        num_personas=num_personas,
        config=config,
        status="pending",
    )
    db.add(sim)
    await db.commit()
    await db.refresh(sim)

    # Swarm Engine config (defaults are sensible for most pitches)
    num_tables = config.get("num_tables", 3)
    personas_per_table = config.get("personas_per_table", 5)
    debate_rounds = config.get("debate_rounds", 2)

    # Optional: convert persona_ids to dicts for seeding
    personas = None
    if sim_data.persona_ids:
        from models import Persona
        persona_result = await db.execute(
            select(Persona).where(Persona.id.in_(sim_data.persona_ids))
        )
        db_personas = persona_result.scalars().all()
        personas = [
            {
                "id": str(p.id),
                "name": p.name,
                "title": p.title,
                "industry": p.industry,
                "company_size": p.company_size,
                "traits": list((p.personality_traits or {}).keys()),
                "pain_points": p.pain_points or [],
                "priorities": [],
                "background": p.bio or "",
                "communication_style": p.buying_style or "professional",
            }
            for p in db_personas
        ]

    # Primary: Swarm Engine (multi-agent deliberation)
    background_tasks.add_task(
        run_swarm_simulation,
        str(sim.id),
        sim_data.pitch_content,
        industry=sim_data.industry or "technology",
        company_name=sim_data.company_name or "",
        company_size=config.get("company_size", "mid-market"),
        target_audience=sim_data.target_audience or "",
        sub_industry=sim_data.sub_industry,
        seller_region=seller_region,
        buyer_region=buyer_region,
        cultural_notes=cultural_notes,
        num_tables=num_tables,
        personas_per_table=personas_per_table,
        debate_rounds=debate_rounds,
        personas=personas,
    )

    return sim


@router.get("", response_model=List[SimulationResponse])
async def list_simulations(
    status: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Simulation)
    if status:
        query = query.where(Simulation.status == status)
    query = query.order_by(desc(Simulation.created_at)).limit(limit).offset(offset)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{simulation_id}")
async def get_simulation(
    simulation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Simulation)
        .options(selectinload(Simulation.results))
        .where(Simulation.id == simulation_id)
    )
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    config = sim.config or {}
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
        "engine": config.get("engine", "unknown"),
        "config": {
            "num_tables": config.get("num_tables", 3),
            "personas_per_table": config.get("personas_per_table", 5),
            "debate_rounds": config.get("debate_rounds", 2),
        },
        "progress_stage": config.get("swarm_stage", ""),
        "progress_detail": config.get("swarm_detail", ""),
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
            "next_steps_suggested": r.next_steps_suggested,
        }

    # Include swarm-specific data if available
    if config.get("engine") == "pitchsim_swarm":
        response["swarm_scores"] = config.get("swarm_scores", {})
        response["consensus"] = config.get("consensus", {})
        response["deal_prediction"] = config.get("deal_prediction", {})
        response["best_pitch_approach"] = config.get("best_pitch_approach", "")
        response["cross_table_insights"] = config.get("cross_table_insights", {})
        response["debate_transcript"] = config.get("debate_transcript", [])
        response["metadata"] = config.get("metadata", {})

    return response


@router.get("/{simulation_id}/responses")
async def get_simulation_responses(
    simulation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    sim_result = await db.execute(
        select(Simulation).where(Simulation.id == simulation_id)
    )
    sim = sim_result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # For swarm simulations, return the debate transcript from config
    config = sim.config or {}
    if config.get("engine") == "pitchsim_swarm":
        tables = config.get("debate_transcript", [])
        return {
            "engine": "pitchsim_swarm",
            "tables": tables,
            "cross_table_insights": config.get("cross_table_insights", {}),
            "deal_prediction": config.get("deal_prediction", {}),
        }

    # For legacy simulations, return individual persona responses
    result = await db.execute(
        select(PersonaResponseModel)
        .options(selectinload(PersonaResponseModel.persona))
        .where(PersonaResponseModel.simulation_id == simulation_id)
    )
    responses = result.scalars().all()

    return {
        "engine": "legacy_pool",
        "responses": [
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
        ],
    }
