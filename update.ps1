cd "C:\Users\SteveWinfiel_12vs805\Documents\PitchSimAI"

@'
from fastapi import APIRouter
from services.channel_sim import ChannelMotionRequest, run_channel_sim

router = APIRouter()

@router.post("/analyze")
async def analyze_channel(req: ChannelMotionRequest):
    return await run_channel_sim(req)
'@ | Set-Content -Encoding UTF8 backend\routers\channel.py

@'
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import json

from services.model_pool import get_model_pool


class ChannelMotionRequest(BaseModel):
    actor_a: str
    motion: str
    actor_b: str
    industry: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    person: Optional[str] = None
    competitors: Optional[str] = None
    current_stack: Optional[str] = None
    notes: Optional[str] = None
    iterations: int = Field(default=1, ge=1, le=3)


def get_specificity(req: ChannelMotionRequest) -> int:
    if req.person:
        return 5
    if req.title:
        return 4
    if req.company:
        return 3
    if req.industry:
        return 2
    return 1


def build_motion(req: ChannelMotionRequest) -> str:
    parts = [req.actor_a, req.motion, req.actor_b]
    if req.industry:
        parts.append(f"into {req.industry}")
    if req.company:
        parts.append(f"at {req.company}")
    if req.title:
        parts.append(f"to {req.title}")
    if req.person:
        parts.append(f"involving {req.person}")
    return " ".join(parts)


def context_block(req: ChannelMotionRequest) -> str:
    data = {
        "Industry": req.industry,
        "Company": req.company,
        "Title": req.title,
        "Person": req.person,
        "Competitors": req.competitors,
        "Current Stack": req.current_stack,
        "Notes": req.notes,
    }
    return "\n".join(f"- {k}: {v}" for k, v in data.items() if v)


async def call_model(prompt: str) -> Dict[str, Any]:
    pool = get_model_pool()

    if not pool.is_available:
        return {
            "mock": True,
            "message": "No model pool configured. Endpoint is wired correctly, but OPENROUTER_API_KEY is needed for live results.",
            "prompt_preview": prompt[:1000],
        }

    content, model = await pool.call_with_failover(
        tier="premium",
        messages=[
            {
                "role": "system",
                "content": "You are ChannelSim, a strategic channel-analysis council. Be direct. Do not invent missing facts. Return valid JSON only."
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )

    try:
        parsed = json.loads(content)
    except Exception:
        parsed = {"raw": content}

    parsed["_model"] = model
    return parsed


def win_prompt(req, motion, level):
    return f"""
Run a 12-Month WIN Backcast.

Motion:
{motion}

Specificity level:
{level}

Context:
{context_block(req)}

Assume this worked extremely well 12 months from now.

Return JSON with:
- executive_summary
- success_levers
- why_partners_or_buyers_actually_moved
- friction_removed
- what_made_this_repeatable
- assumptions
- evidence_needed
"""


def loss_prompt(req, motion, level):
    return f"""
Run a 12-Month FAILURE Autopsy.

Motion:
{motion}

Specificity level:
{level}

Context:
{context_block(req)}

Assume this disappointed or failed 12 months from now.

Return JSON with:
- executive_summary
- root_causes
- false_signals
- incentive_misalignment
- competitor_impact
- assumptions_that_broke
- early_warning_signs
"""


def fight_prompt(motion, win, loss):
    return f"""
Cross-examine these two timelines.

Motion:
{motion}

WIN:
{json.dumps(win)}

LOSS:
{json.dumps(loss)}

Return JSON with:
- contradictions
- strongest_claims
- weakest_claims
- what_actually_matters
- what_needs_validation
"""


def synthesis_prompt(motion, win, loss, fight):
    return f"""
Create the final ChannelSim recommendation.

Motion:
{motion}

WIN:
{json.dumps(win)}

LOSS:
{json.dumps(loss)}

FIGHT:
{json.dumps(fight)}

Return JSON with:
- verdict
- most_likely_outcome
- recommended_action
- confidence_score_0_to_100
- key_variables
- next_best_questions
"""


async def run_channel_sim(req: ChannelMotionRequest):
    level = get_specificity(req)
    motion = build_motion(req)

    win_results = []
    loss_results = []

    for _ in range(req.iterations):
        win_results.append(await call_model(win_prompt(req, motion, level)))
        loss_results.append(await call_model(loss_prompt(req, motion, level)))

    win = win_results if req.iterations > 1 else win_results[0]
    loss = loss_results if req.iterations > 1 else loss_results[0]

    fight = await call_model(fight_prompt(motion, win, loss))
    final = await call_model(synthesis_prompt(motion, win, loss, fight))

    return {
        "engine": "ChannelSim",
        "motion": motion,
        "specificity_level": level,
        "win": win,
        "loss": loss,
        "fight": fight,
        "final": final,
    }
'@ | Set-Content -Encoding UTF8 backend\services\channel_sim.py

$main = Get-Content backend\main.py -Raw
$main = $main -replace 'from routers import simulations, personas, chat, committee, optimizer', 'from routers import simulations, personas, chat, committee, optimizer, channel'

if ($main -notmatch 'app\.include_router\(channel\.router') {
    $main = $main -replace 'app\.include_router\(optimizer\.router, prefix="/api/optimizer", tags=\["AutoOptimizer"\]\)', 'app.include_router(optimizer.router, prefix="/api/optimizer", tags=["AutoOptimizer"])' + "`r`n" + 'app.include_router(channel.router, prefix="/api/channel", tags=["ChannelSim"])'
}

Set-Content -Encoding UTF8 backend\main.py $main

Write-Host "ChannelSim files added. Now run: docker-compose up --build"