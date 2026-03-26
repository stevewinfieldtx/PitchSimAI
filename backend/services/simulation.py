"""
Simulation Service
===================
Orchestrates pitch simulations using the PitchSim Swarm Engine.

The Swarm Engine creates multiple buying committee "tables", runs them through
multi-round deliberation (react → debate → cross-table → consensus), and
produces rich, actionable feedback.
"""

import json
import logging
import random
import asyncio
from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, List, Any

from sqlalchemy import select

from config import get_settings
from database import async_session
from models import Simulation, Persona, SimulationResult, PersonaResponse
from services.model_pool import get_model_pool
from services.swarm_engine import get_swarm_engine

settings = get_settings()
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Swarm Engine Simulation (Primary)
# ──────────────────────────────────────────────


async def run_swarm_simulation(
    simulation_id: str,
    pitch_content: str,
    industry: str = "technology",
    company_name: str = "",
    company_size: str = "mid-market",
    target_audience: str = "",
    num_tables: int = 3,
    personas_per_table: int = 5,
    debate_rounds: int = 2,
    personas: Optional[List[Dict[str, Any]]] = None,
):
    """
    Run a pitch simulation using the PitchSim Swarm Engine.

    This is the PRIMARY simulation method. It creates multiple buying
    committees that debate the pitch and reach consensus.
    """
    engine = get_swarm_engine()

    async with async_session() as db:
        try:
            # Update simulation status
            result = await db.execute(
                select(Simulation).where(Simulation.id == UUID(simulation_id))
            )
            sim = result.scalar_one()
            sim.status = "running"
            sim.started_at = datetime.utcnow()
            sim.config = {
                **(sim.config or {}),
                "engine": "pitchsim_swarm",
                "num_tables": num_tables,
                "personas_per_table": personas_per_table,
                "debate_rounds": debate_rounds,
            }
            await db.commit()

            # Use sim fields if not provided
            industry = sim.industry or industry
            company_name = sim.company_name or company_name
            target_audience = sim.target_audience or target_audience

            # Progress callback to update DB
            async def update_progress(stage: str, detail: str = "", pct: int = 0):
                async with async_session() as progress_db:
                    r = await progress_db.execute(
                        select(Simulation).where(Simulation.id == UUID(simulation_id))
                    )
                    s = r.scalar_one()
                    s.progress_pct = pct
                    s.config = {
                        **(s.config or {}),
                        "swarm_stage": stage,
                        "swarm_detail": detail,
                    }
                    await progress_db.commit()

            # Run the swarm deliberation
            swarm_result = await engine.run(
                pitch_content=pitch_content,
                industry=industry,
                company_name=company_name,
                company_size=company_size,
                target_audience=target_audience,
                num_tables=num_tables,
                personas_per_table=personas_per_table,
                debate_rounds=debate_rounds,
                existing_personas=personas,
                progress_callback=update_progress,
            )

            # Extract scores from consensus
            consensus = swarm_result.get("consensus", {})
            scores = consensus.get("scores", {})

            # Extract objections and recommendations
            top_objections = [
                obj.get("objection", str(obj)) if isinstance(obj, dict) else str(obj)
                for obj in consensus.get("top_objections", [])
            ]
            recommendations = [
                rec.get("action", str(rec)) if isinstance(rec, dict) else str(rec)
                for rec in consensus.get("recommendations", [])
            ]
            strengths = [
                s.get("strength", str(s)) if isinstance(s, dict) else str(s)
                for s in consensus.get("top_strengths", [])
            ]

            # Build sentiment breakdown from table scores
            sentiment_breakdown = {}
            for table_data in swarm_result.get("tables", []):
                table_scores = table_data.get("scores", {})
                verdict = "positive" if table_scores.get("sentiment", 50) > 60 else (
                    "negative" if table_scores.get("sentiment", 50) < 40 else "neutral"
                )
                sentiment_breakdown[table_data.get("variant", "unknown")] = {
                    "verdict": verdict,
                    "engagement": table_scores.get("engagement", 0),
                    "sentiment": table_scores.get("sentiment", 0),
                    "deal_probability": table_scores.get("deal_probability", 0),
                }

            # Store results
            sim_result = SimulationResult(
                simulation_id=UUID(simulation_id),
                overall_engagement_score=scores.get("overall_engagement", 0),
                overall_sentiment_score=scores.get("overall_sentiment", 0),
                sentiment_breakdown=sentiment_breakdown,
                key_objections=top_objections[:10],
                objection_frequency={
                    "total": len(top_objections),
                    "cross_table": len(swarm_result.get("cross_table_insights", {}).get("universal_objections", [])),
                },
                key_recommendations=recommendations[:10],
                strongest_segments=strengths[:5],
                weakest_segments=[],
                engagement_by_industry={industry: scores.get("overall_engagement", 0)},
                next_steps_suggested=consensus.get("executive_summary", ""),
            )
            db.add(sim_result)

            # Update simulation with full results
            r2 = await db.execute(
                select(Simulation).where(Simulation.id == UUID(simulation_id))
            )
            sim = r2.scalar_one()
            sim.config = {
                **(sim.config or {}),
                "engine": "pitchsim_swarm",
                "swarm_scores": scores,
                "consensus": consensus,  # Full consensus with structured data
                "deal_prediction": consensus.get("deal_prediction", {}),
                "best_pitch_approach": consensus.get("best_pitch_approach", ""),
                "cross_table_insights": swarm_result.get("cross_table_insights", {}),
                "metadata": swarm_result.get("metadata", {}),
                # Store full debate for the UI to render
                "debate_transcript": swarm_result.get("tables", []),
            }
            sim.status = "completed"
            sim.completed_at = datetime.utcnow()
            sim.progress_pct = 100
            await db.commit()

            dp = consensus.get("deal_prediction", {})
            logger.info(
                f"Swarm simulation {simulation_id} completed — "
                f"deal prediction: {dp.get('outcome', 'unknown')} "
                f"({dp.get('confidence', 0)}% confidence)"
            )

        except Exception as e:
            logger.error(f"Swarm simulation {simulation_id} failed: {e}", exc_info=True)
            async with async_session() as error_db:
                r = await error_db.execute(
                    select(Simulation).where(Simulation.id == UUID(simulation_id))
                )
                sim = r.scalar_one()
                sim.status = "failed"
                sim.completed_at = datetime.utcnow()
                sim.config = {**(sim.config or {}), "error": str(e)}
                await error_db.commit()


# ──────────────────────────────────────────────
# Legacy: Individual Persona Simulation (Fallback)
# ──────────────────────────────────────────────


def _is_high_value_persona(persona: Persona) -> bool:
    """Determine if a persona warrants a premium model."""
    high_value_signals = [
        persona.budget_authority == "full",
        persona.title and any(t in persona.title.lower() for t in ["ceo", "cfo", "cto", "cro", "coo", "ciso", "chief", "president", "founder", "owner"]),
        persona.personality_traits and persona.personality_traits.get("skepticism", 0) > 0.7,
    ]
    return sum(high_value_signals) >= 2


async def run_simulation(
    simulation_id: str,
    pitch_content: str,
    persona_filters: Optional[Dict] = None,
    num_personas: int = 10,
    persona_ids: Optional[List[str]] = None,
):
    """Run a pitch simulation against individual personas (legacy fallback)."""
    async with async_session() as db:
        try:
            result = await db.execute(select(Simulation).where(Simulation.id == UUID(simulation_id)))
            sim = result.scalar_one()
            sim.status = "running"
            sim.started_at = datetime.utcnow()
            await db.commit()

            if persona_ids:
                persona_uuids = [UUID(pid) for pid in persona_ids]
                query = select(Persona).where(Persona.id.in_(persona_uuids))
            else:
                query = select(Persona).where(Persona.is_public == True)
                if persona_filters:
                    if persona_filters.get("industries"):
                        query = query.where(Persona.industry.in_(persona_filters["industries"]))
                    if persona_filters.get("company_sizes"):
                        query = query.where(Persona.company_size.in_(persona_filters["company_sizes"]))
                    if persona_filters.get("buying_styles"):
                        query = query.where(Persona.buying_style.in_(persona_filters["buying_styles"]))
                query = query.limit(num_personas)

            persona_result = await db.execute(query)
            personas = persona_result.scalars().all()

            if not personas:
                sim.status = "failed"
                sim.completed_at = datetime.utcnow()
                await db.commit()
                return

            pool = get_model_pool()
            total = len(personas)
            completed = 0
            lock = asyncio.Lock()

            async def process_persona(persona: Persona) -> tuple[Persona, Dict[str, Any]]:
                nonlocal completed
                response_data = await simulate_persona_response(persona, pitch_content, pool)
                async with lock:
                    completed += 1
                    sim.progress_pct = int((completed / total) * 100)
                    await db.commit()
                return persona, response_data

            tasks = [process_persona(p) for p in personas]
            results_list = await asyncio.gather(*tasks, return_exceptions=True)

            all_responses = []
            ordered_personas = []

            for item in results_list:
                if isinstance(item, Exception):
                    logger.error(f"Persona simulation failed: {item}")
                    continue
                persona, response_data = item

                pr = PersonaResponse(
                    simulation_id=UUID(simulation_id),
                    persona_id=persona.id,
                    initial_reaction=response_data["initial_reaction"],
                    sentiment=response_data["sentiment"],
                    engagement_score=response_data["engagement_score"],
                    questions_raised=response_data.get("questions_raised", []),
                    objections=response_data.get("objections", []),
                    objection_categories=response_data.get("objection_categories", []),
                    buying_confidence_shift=response_data.get("buying_confidence_shift", 0),
                    likely_decision=response_data["likely_decision"],
                    internal_monologue=response_data.get("internal_monologue", ""),
                )
                db.add(pr)
                all_responses.append(response_data)
                ordered_personas.append(persona)

            agg = aggregate_results(all_responses, ordered_personas)

            sim_result = SimulationResult(
                simulation_id=UUID(simulation_id),
                overall_engagement_score=agg["overall_engagement_score"],
                overall_sentiment_score=agg["overall_sentiment_score"],
                sentiment_breakdown=agg["sentiment_breakdown"],
                key_objections=agg["key_objections"],
                objection_frequency=agg["objection_frequency"],
                key_recommendations=agg["key_recommendations"],
                strongest_segments=agg["strongest_segments"],
                weakest_segments=agg["weakest_segments"],
                engagement_by_industry=agg["engagement_by_industry"],
                next_steps_suggested=agg.get("next_steps_suggested", ""),
            )
            db.add(sim_result)

            sim.config = {**(sim.config or {}), "engine": "legacy_pool", "model_stats": pool.get_stats()}
            sim.status = "completed"
            sim.completed_at = datetime.utcnow()
            sim.progress_pct = 100
            await db.commit()

        except Exception as e:
            logger.error(f"Simulation {simulation_id} failed: {e}", exc_info=True)
            async with async_session() as error_db:
                result = await error_db.execute(select(Simulation).where(Simulation.id == UUID(simulation_id)))
                sim = result.scalar_one()
                sim.status = "failed"
                sim.completed_at = datetime.utcnow()
                await error_db.commit()


async def simulate_persona_response(
    persona: Persona,
    pitch_content: str,
    pool=None,
) -> Dict[str, Any]:
    """Simulate a single persona's response using the model pool."""
    if pool is None:
        pool = get_model_pool()

    if pool.is_available:
        return await _llm_simulate(persona, pitch_content, pool)
    else:
        return _mock_simulate(persona, pitch_content)


async def _llm_simulate(persona: Persona, pitch_content: str, pool) -> Dict[str, Any]:
    """Use the model pool to generate a realistic persona response."""
    tier = "premium" if _is_high_value_persona(persona) else "volume"

    system_prompt = f"""You are simulating a buyer persona for a sales pitch evaluation.

PERSONA:
- Name: {persona.name}
- Title: {persona.title}
- Industry: {persona.industry}
- Company Size: {persona.company_size}
- Buying Style: {persona.buying_style}
- Personality Traits: {json.dumps(persona.personality_traits)}
- Pain Points: {', '.join(persona.pain_points or [])}
- Common Objections: {', '.join(persona.objection_patterns or [])}
- Decision Process: {persona.decision_process or 'Unknown'}
- Budget Authority: {persona.budget_authority or 'Unknown'}
- Bio: {persona.bio or 'N/A'}

Evaluate the following sales pitch AS THIS PERSONA. Respond with valid JSON only:
{{
  "initial_reaction": "Your authentic first reaction (2-4 sentences)",
  "sentiment": "very_positive|positive|neutral|negative|very_negative",
  "engagement_score": <0-100 number>,
  "questions_raised": ["question 1", "question 2"],
  "objections": ["objection 1", "objection 2"],
  "objection_categories": ["pricing|technical|roi|competitive|security|implementation"],
  "buying_confidence_shift": <-50 to +50 number>,
  "likely_decision": "would_advance|needs_clarification|would_decline",
  "internal_monologue": "What you're really thinking (1-2 sentences)"
}}"""

    try:
        content, model_used = await pool.call_with_failover(
            tier=tier,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"PITCH:\n\n{pitch_content}"},
            ],
            temperature=0.8,
            response_format={"type": "json_object"},
        )
        result = json.loads(content)
        result["_model_used"] = model_used
        result["_tier"] = tier
        return result
    except Exception as e:
        logger.error(f"LLM simulation failed for {persona.name}: {e}")
        return _mock_simulate(persona, pitch_content)


def _mock_simulate(persona: Persona, pitch_content: str) -> Dict[str, Any]:
    """Generate a mock persona response for testing without an LLM API key."""
    skepticism = persona.personality_traits.get("skepticism", 0.5) if persona.personality_traits else 0.5
    openness = persona.personality_traits.get("innovation_openness", 0.5) if persona.personality_traits else 0.5
    engagement = max(10, min(100, int(60 + (openness - skepticism) * 40 + random.gauss(0, 10))))

    if engagement > 75:
        sentiment = random.choice(["very_positive", "positive"])
        decision = "would_advance"
    elif engagement > 50:
        sentiment = random.choice(["positive", "neutral"])
        decision = "needs_clarification"
    else:
        sentiment = random.choice(["neutral", "negative"])
        decision = random.choice(["needs_clarification", "would_decline"])

    objection_pool = [
        "Price point seems high for our segment",
        "Implementation timeline is concerning",
        "ROI isn't clearly demonstrated",
        "How does this compare to existing solutions?",
        "Security and compliance questions remain",
        "Need to see more case studies in our industry",
        "Integration with existing tools is unclear",
    ]
    question_pool = [
        f"How does this work for {persona.industry} specifically?",
        "What's the typical onboarding timeline?",
        "Can you share reference customers in our space?",
        "What's the pricing model for teams our size?",
        "How do you handle data security and compliance?",
        "What kind of support is included?",
    ]

    selected_objections = random.sample(objection_pool, k=random.randint(1, 3))
    selected_questions = random.sample(question_pool, k=random.randint(1, 3))
    categories = ["pricing", "technical", "roi", "competitive", "security", "implementation"]
    selected_categories = random.sample(categories, k=len(selected_objections))

    return {
        "initial_reaction": f"As a {persona.title} in {persona.industry}, my first impression is that this pitch {'shows promise' if engagement > 60 else 'needs more work'}.",
        "sentiment": sentiment,
        "engagement_score": engagement,
        "questions_raised": selected_questions,
        "objections": selected_objections,
        "objection_categories": selected_categories,
        "buying_confidence_shift": round(random.uniform(-20, 30) * (openness / (skepticism + 0.1)), 1),
        "likely_decision": decision,
        "internal_monologue": f"{'Interesting approach, worth exploring further.' if engagement > 60 else 'Not convinced yet, need more concrete evidence.'}",
        "_model_used": "mock",
        "_tier": "mock",
    }


def aggregate_results(responses: List[Dict], personas: list) -> Dict[str, Any]:
    """Aggregate individual persona responses into simulation results."""
    if not responses:
        return {}

    engagement_scores = [r["engagement_score"] for r in responses]
    overall_engagement = sum(engagement_scores) / len(engagement_scores)

    sentiment_map = {"very_positive": 2, "positive": 1, "neutral": 0, "negative": -1, "very_negative": -2}
    sentiment_scores = [sentiment_map.get(r["sentiment"], 0) for r in responses]
    overall_sentiment = (sum(sentiment_scores) / len(sentiment_scores)) * 50

    sentiment_breakdown = {}
    for r in responses:
        s = r["sentiment"]
        sentiment_breakdown[s] = sentiment_breakdown.get(s, 0) + 1

    all_objections = []
    objection_freq = {}
    for r in responses:
        all_objections.extend(r.get("objections", []))
        for cat in r.get("objection_categories", []):
            objection_freq[cat] = objection_freq.get(cat, 0) + 1

    unique_objections = list(set(all_objections))[:10]

    industry_scores = {}
    industry_counts = {}
    for r, p in zip(responses, personas):
        ind = p.industry
        industry_scores[ind] = industry_scores.get(ind, 0) + r["engagement_score"]
        industry_counts[ind] = industry_counts.get(ind, 0) + 1

    engagement_by_industry = {
        ind: round(industry_scores[ind] / industry_counts[ind], 1)
        for ind in industry_scores
    }

    segments = [
        {"industry": ind, "engagement_score": engagement_by_industry[ind]}
        for ind in engagement_by_industry
    ]
    segments.sort(key=lambda x: x["engagement_score"], reverse=True)

    recommendations = []
    if objection_freq.get("pricing", 0) > len(responses) * 0.3:
        recommendations.append("Address pricing concerns upfront with ROI framework")
    if objection_freq.get("roi", 0) > len(responses) * 0.2:
        recommendations.append("Include concrete ROI metrics and case studies")
    if objection_freq.get("security", 0) > len(responses) * 0.2:
        recommendations.append("Lead with security and compliance credentials")
    if objection_freq.get("competitive", 0) > len(responses) * 0.2:
        recommendations.append("Add competitive differentiation section")
    if objection_freq.get("implementation", 0) > len(responses) * 0.2:
        recommendations.append("Provide clear implementation timeline with milestones")
    if overall_engagement < 60:
        recommendations.append("Consider restructuring the pitch opening for stronger hook")
    if not recommendations:
        recommendations.append("Pitch is performing well - consider A/B testing variations")

    return {
        "overall_engagement_score": round(overall_engagement, 1),
        "overall_sentiment_score": round(overall_sentiment, 1),
        "sentiment_breakdown": sentiment_breakdown,
        "key_objections": unique_objections[:5],
        "objection_frequency": objection_freq,
        "key_recommendations": recommendations,
        "strongest_segments": segments[:3],
        "weakest_segments": segments[-3:] if len(segments) > 3 else [],
        "engagement_by_industry": engagement_by_industry,
        "next_steps_suggested": "Review top objections and iterate on messaging for weakest segments.",
    }


async def generate_persona_chat_response(
    persona: Persona,
    pitch_content: str,
    conversation_history: List[Dict],
) -> str:
    """Generate a chat response as a specific persona."""
    pool = get_model_pool()

    if pool.is_available:
        system_prompt = f"""You are {persona.name}, {persona.title} in the {persona.industry} industry.
Company size: {persona.company_size}
Buying style: {persona.buying_style}
Pain points: {', '.join(persona.pain_points or [])}
Bio: {persona.bio or 'N/A'}

You were presented with this sales pitch and are now in a follow-up conversation.
Stay in character. Be authentic. Keep responses conversational (2-4 sentences).

ORIGINAL PITCH:
{pitch_content}"""

        messages = [{"role": "system", "content": system_prompt}]
        for msg in conversation_history:
            if msg["role"] in ("user", "assistant"):
                messages.append({"role": msg["role"], "content": msg["content"]})

        try:
            content, _ = await pool.call_with_failover(
                tier="premium",
                messages=messages,
                temperature=0.8,
                max_tokens=300,
            )
            return content
        except Exception:
            return f"I appreciate you reaching out. As a {persona.title}, I'd need to see more concrete evidence before moving forward."

    return f"That's an interesting point. As someone in {persona.industry}, I'm particularly focused on {(persona.pain_points or ['value delivery'])[0]}."
