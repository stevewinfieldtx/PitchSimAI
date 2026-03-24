"""
PitchSim Swarm Engine
======================
Multi-agent deliberation system for evaluating sales pitches.

Instead of asking individual personas for isolated reactions, the Swarm Engine
creates multiple buying committee "tables" — each a full committee of 5-7
personas — and runs them through a multi-round deliberation:

  Round 1 — INITIAL REACTION
    Each persona reads the pitch independently and gives their gut reaction.

  Round 2 — COMMITTEE DEBATE (2-3 sub-rounds)
    Personas within each table read each other's reactions and debate.
    Champions defend, skeptics challenge, decision-makers weigh in.
    Opinions shift as the group dynamics play out.

  Round 3 — CROSS-TABLE SYNTHESIS
    Each table summarizes their verdict. All tables see each other's conclusions.
    Tables react to perspectives they hadn't considered.

  Round 4 — CONSENSUS & RECOMMENDATIONS
    A synthesis agent aggregates all debate history and produces:
    - Final pitch score
    - Ranked objections
    - Specific recommendations to improve the pitch
    - Predicted deal outcome

This produces far richer results than individual evaluations because:
- Agents influence each other (a CFO's budget concern shifts a CTO's enthusiasm)
- Group dynamics emerge naturally (champions vs. blockers)
- Different committee compositions surface different insights
- Cross-table comparison catches blind spots
"""

import json
import asyncio
import logging
import random
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime

from services.model_pool import ModelPool, get_model_pool

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Data Structures
# ──────────────────────────────────────────────


class AgentPersona:
    """A single buyer persona that participates in the deliberation."""

    def __init__(
        self,
        name: str,
        title: str,
        role_in_committee: str,
        industry: str,
        company_size: str,
        personality: Dict[str, Any],
        pain_points: List[str],
        buying_style: str,
        budget_authority: str = "influence",
        bio: str = "",
        cultural_context: Optional[Dict[str, str]] = None,
    ):
        self.name = name
        self.title = title
        self.role_in_committee = role_in_committee  # champion, skeptic, blocker, decision_maker, influencer
        self.industry = industry
        self.company_size = company_size
        self.personality = personality
        self.pain_points = pain_points
        self.buying_style = buying_style
        self.budget_authority = budget_authority
        self.bio = bio
        self.cultural_context = cultural_context
        self.messages: List[Dict[str, str]] = []  # conversation history

    def system_prompt(self) -> str:
        traits = ", ".join(f"{k}: {v}" for k, v in self.personality.items())
        pains = ", ".join(self.pain_points) if self.pain_points else "general efficiency"
        prompt = f"""You are {self.name}, {self.title} at a {self.company_size} {self.industry} company.

ROLE IN BUYING COMMITTEE: {self.role_in_committee}
PERSONALITY: {traits}
KEY PAIN POINTS: {pains}
BUYING STYLE: {self.buying_style}
BUDGET AUTHORITY: {self.budget_authority}
BACKGROUND: {self.bio}"""

        if self.cultural_context:
            seller_region = self.cultural_context.get("seller_region", "")
            buyer_region = self.cultural_context.get("buyer_region", "")
            cultural_notes = self.cultural_context.get("cultural_notes", "")
            cultural_block = f"""
CULTURAL CONTEXT:
The seller is based in {seller_region}. Your organization is in {buyer_region}."""
            if cultural_notes:
                cultural_block += f"\n{cultural_notes}"
            cultural_block += f"""
Consider cultural norms around business communication, decision-making hierarchy,
relationship-building expectations, and negotiation styles typical of {buyer_region}.
Your reactions should reflect your region's cultural business norms."""
            prompt += cultural_block

        prompt += """

You are evaluating a sales pitch as part of a buying committee. Stay fully in character.
Be specific about YOUR concerns from YOUR role's perspective. Reference real business
scenarios. Don't be generic — think about what {title} at a {company_size}
{industry} company actually worries about day to day.

When you agree with someone, say why specifically. When you disagree, push back with
concrete reasoning. You have real opinions shaped by your experience."""
        return prompt.format(title=self.title, company_size=self.company_size, industry=self.industry)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "role_in_committee": self.role_in_committee,
            "industry": self.industry,
            "company_size": self.company_size,
            "personality": self.personality,
            "pain_points": self.pain_points,
            "buying_style": self.buying_style,
            "budget_authority": self.budget_authority,
        }


class CommitteeTable:
    """A buying committee — a group of personas who deliberate together."""

    def __init__(self, table_id: str, personas: List[AgentPersona], variant: str = ""):
        self.table_id = table_id
        self.personas = personas
        self.variant = variant  # e.g. "conservative", "innovation-forward", "cost-conscious"
        self.rounds: List[Dict[str, Any]] = []  # full debate history
        self.summary: str = ""
        self.scores: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_id": self.table_id,
            "variant": self.variant,
            "personas": [p.to_dict() for p in self.personas],
            "rounds": self.rounds,
            "summary": self.summary,
            "scores": self.scores,
        }


# ──────────────────────────────────────────────
# Committee Generator
# ──────────────────────────────────────────────


COMMITTEE_VARIANTS = [
    {
        "variant": "conservative",
        "description": "Risk-averse, cost-conscious committee that prioritizes proven solutions",
        "bias": {"skepticism": 0.7, "risk_tolerance": 0.3, "innovation_openness": 0.4},
    },
    {
        "variant": "innovation-forward",
        "description": "Tech-forward committee eager to adopt cutting-edge solutions",
        "bias": {"skepticism": 0.3, "risk_tolerance": 0.7, "innovation_openness": 0.9},
    },
    {
        "variant": "cost-conscious",
        "description": "Budget-tight committee where every dollar needs clear ROI",
        "bias": {"skepticism": 0.6, "risk_tolerance": 0.4, "innovation_openness": 0.5, "price_sensitivity": 0.9},
    },
    {
        "variant": "enterprise-cautious",
        "description": "Large enterprise committee with compliance, security, and integration concerns",
        "bias": {"skepticism": 0.6, "risk_tolerance": 0.3, "innovation_openness": 0.5, "security_focus": 0.9},
    },
    {
        "variant": "growth-stage",
        "description": "Fast-growing company that needs solutions that scale with them",
        "bias": {"skepticism": 0.4, "risk_tolerance": 0.6, "innovation_openness": 0.7, "scalability_focus": 0.8},
    },
]

COMMITTEE_ROLES = [
    {
        "title": "Chief Technology Officer",
        "role": "decision_maker",
        "focus": "technical fit, integration complexity, scalability, security architecture",
        "budget_authority": "full",
        "buying_style": "analytical",
    },
    {
        "title": "Chief Financial Officer",
        "role": "blocker",
        "focus": "total cost of ownership, ROI timeline, budget impact, vendor financial stability",
        "budget_authority": "full",
        "buying_style": "methodical",
    },
    {
        "title": "VP of Operations",
        "role": "influencer",
        "focus": "implementation disruption, team adoption, workflow changes, training requirements",
        "budget_authority": "influence",
        "buying_style": "collaborative",
    },
    {
        "title": "Director of Engineering",
        "role": "champion",
        "focus": "developer experience, API quality, documentation, maintenance overhead",
        "budget_authority": "recommend",
        "buying_style": "analytical",
    },
    {
        "title": "Head of Security",
        "role": "skeptic",
        "focus": "data handling, compliance, access controls, audit trails, vendor security posture",
        "budget_authority": "veto",
        "buying_style": "methodical",
    },
    {
        "title": "VP of Sales / Revenue",
        "role": "champion",
        "focus": "revenue impact, competitive advantage, customer-facing value, speed to value",
        "budget_authority": "influence",
        "buying_style": "driver",
    },
    {
        "title": "End User / Team Lead",
        "role": "influencer",
        "focus": "daily usability, learning curve, pain point relief, feature gaps vs current tool",
        "budget_authority": "none",
        "buying_style": "expressive",
    },
]


def generate_committee_tables(
    industry: str,
    company_size: str,
    company_name: str = "",
    sub_industry: Optional[str] = None,
    num_tables: int = 3,
    personas_per_table: int = 5,
    existing_personas: Optional[List[Dict[str, Any]]] = None,
    cultural_context: Optional[Dict[str, str]] = None,
) -> List[CommitteeTable]:
    """
    Generate multiple buying committee tables for deliberation.

    Each table is a different "flavor" of committee (conservative, innovative, etc.)
    to surface different perspectives on the same pitch.
    """
    tables = []
    selected_variants = random.sample(
        COMMITTEE_VARIANTS, min(num_tables, len(COMMITTEE_VARIANTS))
    )

    for i, variant_config in enumerate(selected_variants):
        # Pick roles for this table
        selected_roles = random.sample(
            COMMITTEE_ROLES, min(personas_per_table, len(COMMITTEE_ROLES))
        )

        personas = []
        # Use names that feel real
        first_names = ["Sarah", "Marcus", "Priya", "James", "Wei", "Elena", "David", "Aisha", "Tom", "Nina",
                       "Carlos", "Megan", "Raj", "Olivia", "Chen", "Fatima", "Alex", "Yuki", "Robert", "Amara"]
        last_names = ["Chen", "Patel", "Williams", "Kim", "Rodriguez", "Okafor", "Thompson", "Mueller",
                      "Singh", "Johnson", "Park", "Anderson", "Gupta", "Taylor", "Nakamura", "Brown"]

        used_names = set()
        for role_config in selected_roles:
            # Generate a unique name
            while True:
                name = f"{random.choice(first_names)} {random.choice(last_names)}"
                if name not in used_names:
                    used_names.add(name)
                    break

            # Merge variant bias into personality
            personality = {
                "skepticism": round(random.uniform(0.3, 0.8), 2),
                "innovation_openness": round(random.uniform(0.3, 0.8), 2),
                "risk_tolerance": round(random.uniform(0.3, 0.7), 2),
                "detail_orientation": round(random.uniform(0.4, 0.9), 2),
            }
            # Apply variant bias
            for key, value in variant_config["bias"].items():
                personality[key] = round(value + random.uniform(-0.1, 0.1), 2)

            # Industry-specific pain points
            pain_points = _get_industry_pain_points(industry, sub_industry, role_config["focus"])

            persona = AgentPersona(
                name=name,
                title=role_config["title"],
                role_in_committee=role_config["role"],
                industry=industry,
                company_size=company_size,
                personality=personality,
                pain_points=pain_points,
                buying_style=role_config["buying_style"],
                budget_authority=role_config["budget_authority"],
                bio=f"15+ years in {industry}. Currently at {'a ' + company_size + ' company' if not company_name else company_name}. "
                    f"Focused on {role_config['focus']}.",
                cultural_context=cultural_context,
            )
            personas.append(persona)

        table = CommitteeTable(
            table_id=f"table_{i+1}_{variant_config['variant']}",
            personas=personas,
            variant=variant_config["variant"],
        )
        tables.append(table)

    return tables


def _get_industry_pain_points(industry: str, sub_industry: Optional[str] = None, focus: str = "") -> List[str]:
    """Generate relevant pain points based on industry, sub-industry, and role focus."""
    industry_lower = industry.lower()

    # Sub-industry specific pain points for cybersecurity
    sub_industry_pains = {
        "penetration_testing": ["keeping up with evolving attack surfaces", "qualified pentester shortage", "retesting cadence vs budget"],
        "network_security": ["encrypted traffic blind spots", "east-west traffic monitoring gaps", "alert fatigue in SOC"],
        "email_security": ["BEC attacks bypassing native controls", "user click-through on phishing", "DLP for outbound sensitive data"],
        "cloud_security": ["misconfigured cloud resources", "identity and access management at scale", "multi-cloud visibility gaps"],
        "application_security": ["vulnerable dependencies in supply chain", "secure SDLC adoption", "addressing security debt in legacy code"],
        "incident_response": ["mean time to detect getting longer", "forensics and attribution challenges", "coordinating across tools"],
    }

    base_pains = {
        "technology": ["integration with legacy systems", "developer productivity", "technical debt", "cloud costs"],
        "healthcare": ["HIPAA compliance", "EHR integration", "patient data security", "clinician burnout"],
        "finance": ["regulatory compliance", "fraud prevention", "real-time processing", "audit requirements"],
        "manufacturing": ["supply chain visibility", "downtime reduction", "quality control", "IoT integration"],
        "retail": ["omnichannel experience", "inventory optimization", "customer retention", "seasonal scaling"],
        "cybersecurity": ["threat detection speed", "false positive reduction", "SOC analyst fatigue", "compliance reporting"],
        "saas": ["churn reduction", "feature adoption", "scalability", "API reliability"],
    }

    # Check for sub-industry specific pains first
    pains = []
    if sub_industry:
        sub_lower = sub_industry.lower().replace(" ", "_").replace("-", "_")
        for key, values in sub_industry_pains.items():
            if key in sub_lower or sub_lower in key:
                pains = values[:3]
                break

    # If no sub-industry match, find best match on industry
    if not pains:
        for key, values in base_pains.items():
            if key in industry_lower:
                pains = values[:3]
                break

    if not pains:
        pains = ["operational efficiency", "cost optimization", "competitive pressure"]

    # Add role-specific pain
    if "security" in focus.lower():
        pains.append("zero-trust architecture requirements")
    elif "cost" in focus.lower() or "budget" in focus.lower():
        pains.append("proving ROI within 12 months")
    elif "user" in focus.lower() or "usability" in focus.lower():
        pains.append("tool fatigue and adoption resistance")

    return pains


# ──────────────────────────────────────────────
# Swarm Engine
# ──────────────────────────────────────────────


class SwarmEngine:
    """
    Multi-agent deliberation engine for pitch evaluation.

    Runs buying committees through structured debate rounds and produces
    consensus results with specific, actionable feedback.
    """

    def __init__(self, pool: Optional[ModelPool] = None):
        self.pool = pool or get_model_pool()

    async def run(
        self,
        pitch_content: str,
        industry: str,
        company_name: str = "",
        company_size: str = "mid-market",
        target_audience: str = "",
        sub_industry: Optional[str] = None,
        seller_region: Optional[str] = None,
        buyer_region: Optional[str] = None,
        cultural_notes: Optional[str] = None,
        num_tables: int = 3,
        personas_per_table: int = 5,
        debate_rounds: int = 2,
        existing_personas: Optional[List[Dict[str, Any]]] = None,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Run a full swarm deliberation on a sales pitch.

        Returns comprehensive results including per-table debates,
        cross-table synthesis, and final consensus.
        """
        started_at = datetime.utcnow()

        async def _progress(stage: str, detail: str = "", pct: int = 0):
            logger.info(f"[SwarmEngine] {stage}: {detail}")
            if progress_callback:
                await progress_callback(stage, detail, pct)

        # ── Stage 1: Generate Committees ──
        await _progress("initializing", "Assembling buying committees...", 5)

        # Build cultural context dict if provided
        cultural_context = None
        if seller_region or buyer_region or cultural_notes:
            cultural_context = {
                "seller_region": seller_region or "",
                "buyer_region": buyer_region or "",
                "cultural_notes": cultural_notes or "",
            }

        tables = generate_committee_tables(
            industry=industry,
            company_size=company_size,
            company_name=company_name,
            sub_industry=sub_industry,
            num_tables=num_tables,
            personas_per_table=personas_per_table,
            existing_personas=existing_personas,
            cultural_context=cultural_context,
        )

        logger.info(f"Created {len(tables)} committee tables with {sum(len(t.personas) for t in tables)} total agents")

        # ── Stage 2: Initial Reactions ──
        await _progress("initial_reactions", "Each buyer reads the pitch independently...", 15)
        await self._run_initial_reactions(tables, pitch_content, company_name, target_audience)

        # ── Stage 3: Committee Debates ──
        for round_num in range(1, debate_rounds + 1):
            pct = 25 + int((round_num / debate_rounds) * 35)
            await _progress(
                "committee_debate",
                f"Committee debate round {round_num}/{debate_rounds}...",
                pct,
            )
            await self._run_debate_round(tables, pitch_content, round_num)

        # ── Stage 4: Table Summaries ──
        await _progress("summarizing", "Each committee reaches their verdict...", 70)
        await self._generate_table_summaries(tables, pitch_content)

        # ── Stage 5: Cross-Table Synthesis ──
        await _progress("cross_table", "Committees compare conclusions...", 80)
        cross_table_insights = await self._run_cross_table_synthesis(tables, pitch_content)

        # ── Stage 6: Final Consensus ──
        await _progress("consensus", "Building final consensus and recommendations...", 90)
        consensus = await self._generate_consensus(tables, cross_table_insights, pitch_content, industry, company_name, cultural_context)

        await _progress("completed", "Deliberation complete!", 100)

        elapsed = (datetime.utcnow() - started_at).total_seconds()

        return {
            "engine": "pitchsim_swarm",
            "tables": [t.to_dict() for t in tables],
            "cross_table_insights": cross_table_insights,
            "consensus": consensus,
            "metadata": {
                "num_tables": len(tables),
                "total_agents": sum(len(t.personas) for t in tables),
                "debate_rounds": debate_rounds,
                "elapsed_seconds": round(elapsed, 1),
                "industry": industry,
                "company_name": company_name,
                "sub_industry": sub_industry,
                "seller_region": seller_region,
                "buyer_region": buyer_region,
            },
            "scores": consensus.get("scores", {}),
        }

    # ──────────────────────────────────────────────
    # Round 1: Initial Reactions
    # ──────────────────────────────────────────────

    async def _run_initial_reactions(
        self,
        tables: List[CommitteeTable],
        pitch: str,
        company_name: str,
        target_audience: str,
    ):
        """Every persona reads the pitch and gives their independent first reaction."""
        tasks = []
        for table in tables:
            for persona in table.personas:
                tasks.append(self._get_initial_reaction(persona, pitch, company_name, target_audience))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Store results back into tables
        idx = 0
        for table in tables:
            round_data = {"round": "initial_reaction", "responses": []}
            for persona in table.personas:
                result = results[idx]
                idx += 1
                if isinstance(result, Exception):
                    response_text = f"[{persona.name} could not respond: {result}]"
                else:
                    response_text = result
                persona.messages.append({"role": "assistant", "content": response_text})
                round_data["responses"].append({
                    "persona": persona.name,
                    "title": persona.title,
                    "role": persona.role_in_committee,
                    "response": response_text,
                })
            table.rounds.append(round_data)

    async def _get_initial_reaction(
        self, persona: AgentPersona, pitch: str, company_name: str, target_audience: str
    ) -> str:
        """Get one persona's initial reaction to the pitch."""
        prompt = f"""Read this sales pitch and give your honest initial reaction.

PITCH FROM: {company_name or 'a vendor'}
TARGET AUDIENCE: {target_audience or 'business decision makers'}

--- PITCH ---
{pitch}
--- END PITCH ---

As {persona.title}, give your gut reaction in 3-5 sentences. Be specific:
- What catches your attention (positive or negative)?
- Does this address any of your actual pain points?
- What's your initial concern or question?
- Would you keep reading / take the meeting, or pass?

Respond in first person, as yourself. Be direct and honest."""

        if persona.cultural_context and (persona.cultural_context.get("seller_region") or persona.cultural_context.get("buyer_region")):
            seller_region = persona.cultural_context.get("seller_region", "")
            buyer_region = persona.cultural_context.get("buyer_region", "")
            prompt += f"\n\nNote: The vendor is from {seller_region}. Consider how that might influence communication and business approach."

        content, _ = await self.pool.call_with_failover(
            tier="premium" if persona.budget_authority in ("full", "veto") else "volume",
            messages=[
                {"role": "system", "content": persona.system_prompt()},
                {"role": "user", "content": prompt},
            ],
            temperature=0.85,
            max_tokens=400,
        )
        return content

    # ──────────────────────────────────────────────
    # Round 2: Committee Debate
    # ──────────────────────────────────────────────

    async def _run_debate_round(
        self,
        tables: List[CommitteeTable],
        pitch: str,
        round_num: int,
    ):
        """Each persona reads their committee's previous messages and responds."""
        tasks = []
        for table in tables:
            for persona in table.personas:
                # Build the conversation context — what others said
                others_said = self._build_committee_context(table, persona)
                tasks.append(
                    self._get_debate_response(persona, pitch, others_said, round_num)
                )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        idx = 0
        for table in tables:
            round_data = {"round": f"debate_{round_num}", "responses": []}
            for persona in table.personas:
                result = results[idx]
                idx += 1
                if isinstance(result, Exception):
                    response_text = f"[{persona.name} could not respond: {result}]"
                else:
                    response_text = result
                persona.messages.append({"role": "assistant", "content": response_text})
                round_data["responses"].append({
                    "persona": persona.name,
                    "title": persona.title,
                    "role": persona.role_in_committee,
                    "response": response_text,
                })
            table.rounds.append(round_data)

    def _build_committee_context(self, table: CommitteeTable, current_persona: AgentPersona) -> str:
        """Build a summary of what other committee members have said so far."""
        lines = []
        for persona in table.personas:
            if persona.name == current_persona.name:
                continue
            if persona.messages:
                last_msg = persona.messages[-1]["content"]
                lines.append(f"**{persona.name} ({persona.title}):**\n{last_msg}\n")
        return "\n".join(lines) if lines else "(No other committee members have spoken yet.)"

    async def _get_debate_response(
        self, persona: AgentPersona, pitch: str, others_context: str, round_num: int
    ) -> str:
        """Get a persona's debate response, reacting to what others said."""
        if round_num == 1:
            prompt = f"""Your buying committee has shared their initial reactions to the pitch.
Read what your colleagues said and respond. Do you agree? Disagree?
What did they miss? What concerns do you share?

YOUR COLLEAGUES' REACTIONS:
{others_context}

Respond in 3-5 sentences. Address specific points others raised.
Push back where you disagree. Support points you agree with.
Bring up anything the group hasn't mentioned yet that matters for YOUR role."""
        else:
            prompt = f"""The committee debate continues. Here's where everyone stands:

{others_context}

This is round {round_num} of discussion. The group needs to move toward a decision.
- Have any of your colleagues' points changed your mind?
- What's your updated position?
- What would YOU need to see from this vendor to move forward?
- Are there deal-breakers the group should acknowledge?

Respond in 3-5 sentences. Be decisive — you're trying to reach a conclusion."""

        content, _ = await self.pool.call_with_failover(
            tier="volume",
            messages=[
                {"role": "system", "content": persona.system_prompt()},
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=350,
        )
        return content

    # ──────────────────────────────────────────────
    # Round 3: Table Summaries
    # ──────────────────────────────────────────────

    async def _generate_table_summaries(self, tables: List[CommitteeTable], pitch: str):
        """Each table produces a verdict summary."""
        tasks = [self._summarize_table(table, pitch) for table in tables]
        summaries = await asyncio.gather(*tasks, return_exceptions=True)

        for table, summary in zip(tables, summaries):
            if isinstance(summary, Exception):
                table.summary = f"[Summary generation failed: {summary}]"
                table.scores = {"engagement": 50, "sentiment": 50, "deal_probability": 50}
            else:
                table.summary = summary.get("summary", "")
                table.scores = summary.get("scores", {})

    async def _summarize_table(self, table: CommitteeTable, pitch: str) -> Dict[str, Any]:
        """Generate a structured summary of one table's deliberation."""
        # Compile full debate history
        debate_log = ""
        for round_data in table.rounds:
            debate_log += f"\n--- {round_data['round'].upper()} ---\n"
            for resp in round_data["responses"]:
                debate_log += f"\n{resp['persona']} ({resp['title']}):\n{resp['response']}\n"

        prompt = f"""You are a neutral observer summarizing a buying committee's deliberation about a sales pitch.

COMMITTEE TYPE: {table.variant}
DEBATE TRANSCRIPT:
{debate_log}

Produce a JSON response with:
{{
  "summary": "2-3 paragraph summary of how the committee's discussion evolved, key points of agreement/disagreement, and their overall verdict",
  "champions": ["names of people who advocated for the purchase"],
  "blockers": ["names of people who would block or significantly delay"],
  "key_objections": ["the top 3-5 specific objections raised"],
  "key_positives": ["the top 3-5 specific things the committee liked"],
  "deal_breakers": ["any absolute deal-breakers mentioned"],
  "scores": {{
    "engagement": <0-100, how engaged/interested the committee was>,
    "sentiment": <0-100, overall positive vs negative>,
    "deal_probability": <0-100, likelihood they'd advance to next stage>,
    "urgency": <0-100, how urgently they'd want to act>
  }},
  "verdict": "advance|needs_work|decline"
}}

Respond with valid JSON only."""

        content, _ = await self.pool.call_with_failover(
            tier="premium",
            messages=[
                {"role": "system", "content": "You are an expert B2B sales analyst. Respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )
        return json.loads(content)

    # ──────────────────────────────────────────────
    # Round 4: Cross-Table Synthesis
    # ──────────────────────────────────────────────

    async def _run_cross_table_synthesis(
        self, tables: List[CommitteeTable], pitch: str
    ) -> Dict[str, Any]:
        """Compare conclusions across tables and find patterns."""
        table_summaries = ""
        for table in tables:
            table_summaries += f"\n--- COMMITTEE: {table.variant.upper()} ---\n"
            table_summaries += f"Scores: {json.dumps(table.scores)}\n"
            table_summaries += f"Summary: {table.summary}\n"

        prompt = f"""You've observed {len(tables)} different buying committees evaluate the same sales pitch.
Each committee had a different composition and risk profile.

{table_summaries}

Analyze the cross-committee patterns:
1. What objections came up across MULTIPLE committees? (These are real problems.)
2. What did only ONE committee catch? (These are blind spots worth noting.)
3. Where did committees disagree? (These reveal audience-dependent messaging.)
4. What was universally liked? (These are the pitch's real strengths.)

Respond with valid JSON:
{{
  "universal_objections": ["objections raised by 2+ committees"],
  "unique_insights": ["important points only one committee caught"],
  "disagreements": ["areas where committees reached opposite conclusions"],
  "universal_strengths": ["things all committees agreed were strong"],
  "audience_sensitivity": "which audience segments need different messaging and why",
  "biggest_risk": "the single biggest risk to this deal across all committees"
}}"""

        content, _ = await self.pool.call_with_failover(
            tier="premium",
            messages=[
                {"role": "system", "content": "You are a senior B2B sales strategist. Respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        return json.loads(content)

    # ──────────────────────────────────────────────
    # Round 5: Final Consensus
    # ──────────────────────────────────────────────

    async def _generate_consensus(
        self,
        tables: List[CommitteeTable],
        cross_insights: Dict[str, Any],
        pitch: str,
        industry: str,
        company_name: str,
        cultural_context: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Produce the final consensus: scores, objections, and specific recommendations."""
        # Build complete context
        all_debates = ""
        for table in tables:
            all_debates += f"\n{'='*40}\nCOMMITTEE: {table.variant}\n{'='*40}\n"
            all_debates += f"Verdict: {table.scores}\n"
            all_debates += f"Summary: {table.summary}\n"

        prompt = f"""You are the lead sales strategist synthesizing results from {len(tables)} buying committee simulations
that evaluated a pitch for {company_name or 'a solution'} targeting {industry}.

COMMITTEE RESULTS:
{all_debates}

CROSS-COMMITTEE ANALYSIS:
{json.dumps(cross_insights, indent=2)}

ORIGINAL PITCH:
{pitch[:2000]}"""

        if cultural_context and (cultural_context.get("seller_region") or cultural_context.get("buyer_region")):
            seller_region = cultural_context.get("seller_region", "")
            buyer_region = cultural_context.get("buyer_region", "")
            cultural_notes = cultural_context.get("cultural_notes", "")
            prompt += f"""

CULTURAL CONTEXT:
The seller is based in {seller_region}. The buyer organization is in {buyer_region}."""
            if cultural_notes:
                prompt += f"\n{cultural_notes}"
            prompt += f"""
Consider how cultural differences in business communication, decision-making, negotiation
styles, and relationship-building between {seller_region} and {buyer_region} may impact
this deal. Factor this into your final analysis and recommendations."""

        prompt += """

Produce the FINAL analysis. This is what the salesperson will use to improve their pitch.
Be specific, actionable, and brutally honest. No fluff.

Respond with valid JSON:
{{
  "scores": {{
    "overall_engagement": <0-100>,
    "overall_sentiment": <0-100>,
    "deal_probability": <0-100>,
    "pitch_clarity": <0-100>,
    "value_proposition_strength": <0-100>,
    "objection_vulnerability": <0-100, higher = more vulnerable to objections>
  }},
  "executive_summary": "3-4 sentence summary of how this pitch would land with real buyers",
  "top_objections": [
    {{"objection": "specific objection", "severity": "high|medium|low", "raised_by": "which roles raised this", "suggested_counter": "how to address it"}}
  ],
  "top_strengths": [
    {{"strength": "specific strength", "impact": "why this matters to buyers"}}
  ],
  "recommendations": [
    {{"priority": 1, "action": "specific thing to change in the pitch", "rationale": "why this would help", "expected_impact": "what improvement to expect"}}
  ],
  "best_pitch_approach": "2-3 sentences describing the optimal way to pitch this based on all committee feedback",
  "deal_prediction": {{
    "outcome": "likely_win|possible_win|needs_work|likely_loss",
    "confidence": <0-100>,
    "key_factor": "the single biggest factor that will determine the deal outcome",
    "timeline_estimate": "how long this deal would take to close"
  }}
}}"""

        content, _ = await self.pool.call_with_failover(
            tier="premium",
            messages=[
                {"role": "system", "content": "You are a world-class B2B sales strategist with 20 years of experience closing enterprise deals. Respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
        return json.loads(content)


# ──────────────────────────────────────────────
# Singleton
# ──────────────────────────────────────────────

_engine: Optional[SwarmEngine] = None


def get_swarm_engine() -> SwarmEngine:
    global _engine
    if _engine is None:
        _engine = SwarmEngine()
    return _engine
