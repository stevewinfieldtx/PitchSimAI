"""
PitchProof Swarm Engine
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
# Famous Guides — optional strategic advisor for committees
# ──────────────────────────────────────────────

FAMOUS_GUIDES = [
    {
        "id": "guide_jobs",
        "name": "Steve Jobs",
        "title": "Legendary Product Visionary",
        "persona": "You are Steve Jobs. You think in terms of simplicity, design, and the customer experience above all. "
                   "You challenge the committee to think about what the CUSTOMER actually feels, not just features and specs. "
                   "You ask: Is this pitch simple enough? Does it make the customer feel something? "
                   "You push back on complexity, on feature-dumping, on anything that obscures the core value proposition. "
                   "You speak with absolute conviction. You believe the best products sell themselves when positioned correctly.",
        "focus": "product vision, simplicity, customer experience, positioning",
        "style": "visionary, demanding, cuts through noise",
    },
    {
        "id": "guide_buffett",
        "name": "Warren Buffett",
        "title": "Legendary Value Investor",
        "persona": "You are Warren Buffett. You evaluate everything through the lens of long-term value and economic moats. "
                   "You ask the committee: What is the durable competitive advantage here? Is the ROI real or imagined? "
                   "What happens in year 3, year 5? You are skeptical of hype and buzzwords. "
                   "You trust numbers, not narratives. You push the committee to think about what they are giving up, not just what they are getting. "
                   "You speak plainly, use folksy wisdom, and make complex ideas simple.",
        "focus": "value, ROI, competitive moats, long-term thinking",
        "style": "analytical, patient, skeptical of hype, plain-spoken",
    },
    {
        "id": "guide_gates",
        "name": "Bill Gates",
        "title": "Technology and Systems Thinker",
        "persona": "You are Bill Gates. You think in systems and platforms. "
                   "You ask: How does this integrate with what we already have? What is the platform play? "
                   "You care about adoption curves, ecosystem effects, and technical debt. "
                   "You push the committee to think about scalability, interoperability, and the total cost of the technology stack. "
                   "You are deeply analytical but also understand that technology only matters if people actually use it.",
        "focus": "systems thinking, platform strategy, adoption, integration",
        "style": "analytical, systematic, practical, forward-looking",
    },
    {
        "id": "guide_oprah",
        "name": "Oprah Winfrey",
        "title": "Master Communicator and People Leader",
        "persona": "You are Oprah Winfrey. You focus on the HUMAN side of every decision. "
                   "You ask: How will the people who use this actually feel? What is the story here? "
                   "You push the committee to consider organizational change, team buy-in, and the emotional journey of adoption. "
                   "You know that the best technology in the world fails if the people reject it. "
                   "You speak from the heart but with business acumen.",
        "focus": "people, change management, storytelling, organizational buy-in",
        "style": "empathetic, persuasive, people-first, authentic",
    },
    {
        "id": "guide_musk",
        "name": "Elon Musk",
        "title": "First Principles Innovator",
        "persona": "You are Elon Musk. You think from first principles and challenge every assumption. "
                   "You ask: Why are we doing it this way? What if we removed 80 percent of the complexity? "
                   "You push the committee to think 10x bigger but also to question whether the pitch is solving the RIGHT problem. "
                   "You are impatient with incremental thinking. You want to know what the most ambitious version looks like.",
        "focus": "first principles, 10x thinking, challenging assumptions, bold moves",
        "style": "contrarian, bold, impatient with mediocrity, first-principles",
    },
    {
        "id": "guide_bezos",
        "name": "Jeff Bezos",
        "title": "Customer Obsession and Scale Master",
        "persona": "You are Jeff Bezos. Everything starts with the customer and works backwards. "
                   "You ask: What does the customer actually need? What is the Day 1 mindset here? "
                   "You push the committee to write the press release before building the product. "
                   "You care about flywheel effects, operational excellence, and relentless optimization. "
                   "You think long-term and are willing to be misunderstood for extended periods.",
        "focus": "customer obsession, operational excellence, flywheel thinking, long-term",
        "style": "methodical, customer-first, long-horizon, data-driven",
    },
    {
        "id": "guide_suntzu",
        "name": "Sun Tzu",
        "title": "Master Strategist",
        "persona": "You are Sun Tzu, the ancient military strategist. You see business as war conducted through other means. "
                   "You ask: What is the competitive landscape? Where is the opponents weakness? "
                   "You push the committee to think about positioning, timing, and the art of winning without direct confrontation. "
                   "You evaluate whether the pitch creates strategic advantage or merely reacts to competitors. "
                   "You speak in strategic principles that cut through tactical noise.",
        "focus": "competitive strategy, positioning, timing, strategic advantage",
        "style": "strategic, indirect, wisdom-based, sees the whole battlefield",
    },
]


def get_guide_by_id(guide_id: str) -> Optional[Dict[str, Any]]:
    """Look up a famous guide by ID."""
    if not guide_id:
        return None
    for g in FAMOUS_GUIDES:
        if g["id"] == guide_id:
            return g
    return None




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
        self.messages: List[Dict[str, str]] = []  # conversation history

    def system_prompt(self) -> str:
        # Use custom guide prompt if this is a famous guide
        if hasattr(self, '_guide_system_prompt') and self._guide_system_prompt:
            return self._guide_system_prompt + f"\n\nYou are advising a buying committee at a {self.company_size} {self.industry} company. Stay in character."
        traits = ", ".join(f"{k}: {v}" for k, v in self.personality.items())
        pains = ", ".join(self.pain_points) if self.pain_points else "general efficiency"
        return f"""You are {self.name}, {self.title} at a {self.company_size} {self.industry} company.

ROLE IN BUYING COMMITTEE: {self.role_in_committee}
PERSONALITY: {traits}
KEY PAIN POINTS: {pains}
BUYING STYLE: {self.buying_style}
BUDGET AUTHORITY: {self.budget_authority}
BACKGROUND: {self.bio}

You are evaluating a sales pitch as part of a buying committee. Stay fully in character.
Be specific about YOUR concerns from YOUR role's perspective. Reference real business
scenarios. Don't be generic — think about what {self.title} at a {self.company_size}
{self.industry} company actually worries about day to day.

When you agree with someone, say why specifically. When you disagree, push back with
concrete reasoning. You have real opinions shaped by your experience."""

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


COMPANY_SIZE_LABELS = {
    "general": "mid-market",
    "smb": "small business (10-50 employees)",
    "mid-market": "mid-market (50-500 employees)",
    "small-enterprise": "small enterprise (500-2,000 employees)",
    "medium-enterprise": "medium enterprise (2,000-10,000 employees)",
    "large-enterprise": "large enterprise (10,000+ employees)",
}


def generate_committee_tables(
    industry: str,
    company_size: str,
    company_name: str = "",
    num_tables: int = 3,
    personas_per_table: int = 5,
    existing_personas: Optional[List[Dict[str, Any]]] = None,
    seed: Optional[int] = None,
    guide_id: Optional[str] = None,
) -> List[CommitteeTable]:
    """
    Generate multiple buying committee tables for deliberation.

    Each table is a different "flavor" of committee (conservative, innovative, etc.)
    to surface different perspectives on the same pitch.

    If seed is provided, committee composition is deterministic — the same seed
    always produces the same committees. This is critical for the optimizer,
    which needs to compare scores across iterations with identical committees.
    """
    rng = random.Random(seed) if seed is not None else random

    # Resolve audience segment to a human-readable label
    company_size_label = COMPANY_SIZE_LABELS.get(company_size, company_size)

    tables = []
    selected_variants = rng.sample(
        COMMITTEE_VARIANTS, min(num_tables, len(COMMITTEE_VARIANTS))
    )

    for i, variant_config in enumerate(selected_variants):
        # Pick roles for this table
        selected_roles = rng.sample(
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
                name = f"{rng.choice(first_names)} {rng.choice(last_names)}"
                if name not in used_names:
                    used_names.add(name)
                    break

            # Merge variant bias into personality
            personality = {
                "skepticism": round(rng.uniform(0.3, 0.8), 2),
                "innovation_openness": round(rng.uniform(0.3, 0.8), 2),
                "risk_tolerance": round(rng.uniform(0.3, 0.7), 2),
                "detail_orientation": round(rng.uniform(0.4, 0.9), 2),
            }
            # Apply variant bias
            for key, value in variant_config["bias"].items():
                personality[key] = round(value + rng.uniform(-0.1, 0.1), 2)

            # Industry-specific pain points
            pain_points = _get_industry_pain_points(industry, role_config["focus"])

            # Parse the industry string which may be "Industry — Sub-Industry"
            display_industry = industry.split(" — ")[0] if " — " in industry else industry

            persona = AgentPersona(
                name=name,
                title=role_config["title"],
                role_in_committee=role_config["role"],
                industry=industry,
                company_size=company_size_label,
                personality=personality,
                pain_points=pain_points,
                buying_style=role_config["buying_style"],
                budget_authority=role_config["budget_authority"],
                bio=f"15+ years in {display_industry}. Currently at {'a ' + company_size_label + ' company' if not company_name else company_name}. "
                    f"Focused on {role_config['focus']}.",
            )
            personas.append(persona)

        table = CommitteeTable(
            table_id=f"table_{i+1}_{variant_config['variant']}",
            personas=personas,
            variant=variant_config["variant"],
        )
        tables.append(table)

    # Add famous guide to each table if specified
    guide = get_guide_by_id(guide_id) if guide_id else None
    if guide:
        for table in tables:
            guide_persona = AgentPersona(
                name=guide["name"],
                title=guide["title"],
                role_in_committee="advisor",  # special role — advises but has unique weight
                industry=industry,
                company_size=company_size_label,
                personality={"skepticism": 0.5, "innovation_openness": 0.7, "risk_tolerance": 0.6, "detail_orientation": 0.8},
                pain_points=["strategic clarity", "competitive positioning"],
                buying_style="visionary",
                budget_authority="influence",
                bio=guide.get("persona", f"Legendary advisor. Focus: {guide.get('focus', 'strategy')}"),
            )
            # The guide persona uses custom system prompt from the guide data
            guide_persona._guide_system_prompt = guide.get("persona", "")
            table.personas.append(guide_persona)
        logger.info(f"Added famous guide '{guide['name']}' to all {len(tables)} tables")

    return tables


def _get_industry_pain_points(industry: str, focus: str) -> List[str]:
    """Generate relevant pain points based on industry (including sub-industry) and role focus.

    The `industry` parameter may be a plain industry name or a composite like
    "Financial Services — Banking & Credit Unions".  We match against both the
    big-bucket industry AND the sub-industry for maximum specificity.
    """
    industry_lower = industry.lower()

    # ── Big-bucket industry pain points ──
    base_pains = {
        "financial": ["regulatory compliance (SOX, Dodd-Frank)", "fraud prevention", "real-time transaction processing", "audit trail requirements"],
        "technology": ["integration with legacy systems", "developer productivity", "technical debt", "cloud cost management"],
        "software": ["integration with legacy systems", "developer productivity", "technical debt", "cloud cost management"],
        "healthcare": ["HIPAA compliance", "EHR integration", "patient data security", "clinician burnout"],
        "manufacturing": ["supply chain visibility", "unplanned downtime", "quality control automation", "IoT sensor integration"],
        "engineering": ["supply chain visibility", "unplanned downtime", "quality control automation", "project cost overruns"],
        "retail": ["omnichannel consistency", "inventory optimization", "customer retention", "seasonal scaling"],
        "consumer": ["omnichannel consistency", "inventory optimization", "customer retention", "seasonal scaling"],
        "professional services": ["billable utilization tracking", "talent retention", "project margin erosion", "client satisfaction measurement"],
        "education": ["enrollment management", "student engagement tracking", "LMS integration", "budget constraints"],
        "government": ["FedRAMP / StateRAMP compliance", "procurement cycle length", "legacy modernization", "citizen experience"],
        "public sector": ["FedRAMP / StateRAMP compliance", "procurement cycle length", "legacy modernization", "citizen experience"],
        "energy": ["grid reliability", "regulatory compliance", "asset lifecycle management", "renewable integration"],
        "utilities": ["grid reliability", "regulatory compliance", "asset lifecycle management", "renewable integration"],
        "transportation": ["fleet optimization", "real-time tracking", "fuel cost management", "driver safety compliance"],
        "logistics": ["last-mile delivery costs", "warehouse throughput", "carrier management", "demand forecasting"],
        "media": ["content monetization", "audience engagement", "ad-tech integration", "content piracy"],
        "entertainment": ["content monetization", "audience engagement", "ad-tech integration", "content piracy"],
        "hospitality": ["guest experience personalization", "occupancy optimization", "labor scheduling", "OTA dependency"],
    }

    # ── Sub-industry specific pain points ──
    sub_industry_pains = {
        "banking": ["core banking modernization", "KYC/AML automation", "branch digital transformation", "open banking APIs"],
        "credit union": ["member engagement", "core system vendor lock-in", "digital banking parity with big banks"],
        "insurance": ["claims processing speed", "underwriting automation", "policyholder retention", "InsurTech competition"],
        "investment": ["portfolio risk analytics", "trade execution speed", "regulatory reporting (MiFID II, SEC)", "ESG data integration"],
        "fintech": ["payment gateway reliability", "PCI-DSS compliance", "interchange fee optimization", "fraud detection ML"],
        "real estate": ["property management automation", "tenant communication", "maintenance request tracking", "lease lifecycle management"],
        "accounting": ["tax regulation changes", "audit workflow automation", "client portal experience", "multi-entity consolidation"],
        "saas": ["churn reduction", "feature adoption tracking", "usage-based billing complexity", "API reliability at scale"],
        "cloud": ["multi-cloud cost optimization", "Kubernetes management overhead", "cloud security posture", "vendor lock-in risk"],
        "cybersecurity": ["threat detection speed", "false positive reduction", "SOC analyst fatigue", "compliance reporting automation"],
        "it services": ["managed service margin pressure", "SLA adherence", "multi-tenant management", "talent shortage"],
        "telecom": ["5G infrastructure ROI", "network capacity planning", "subscriber churn", "billing system complexity"],
        "hospital": ["nurse staffing optimization", "revenue cycle management", "interoperability mandates", "patient throughput"],
        "physician": ["practice management efficiency", "prior authorization burden", "patient no-show reduction", "value-based care transition"],
        "pharma": ["clinical trial acceleration", "drug safety monitoring", "supply chain cold-chain integrity", "patent cliff planning"],
        "biotech": ["clinical trial acceleration", "drug safety monitoring", "supply chain cold-chain integrity", "patent cliff planning"],
        "medical device": ["FDA 510(k) pathway management", "post-market surveillance", "field service optimization", "UDI compliance"],
        "health insurance": ["claims adjudication speed", "provider network adequacy", "member experience digital", "Star rating improvement"],
        "healthcare it": ["HL7/FHIR interoperability", "telehealth platform reliability", "data warehouse integration", "security incident response"],
        "e-commerce": ["cart abandonment reduction", "marketplace fee optimization", "returns logistics", "personalization at scale"],
        "food": ["supply chain traceability", "food safety compliance", "seasonal demand forecasting", "delivery logistics"],
        "automotive": ["EV supply chain transition", "connected vehicle data", "dealer network management", "IATF 16949 compliance"],
        "aerospace": ["DO-178C compliance", "supply chain single-source risk", "MRO optimization", "export control (ITAR/EAR)"],
        "defense": ["CMMC compliance", "supply chain security", "system integration complexity", "acquisition cycle time"],
        "construction": ["project schedule adherence", "material cost volatility", "worker safety compliance", "BIM adoption"],
        "consulting": ["utilization rate optimization", "knowledge management", "client delivery quality", "bench time reduction"],
        "legal": ["matter lifecycle management", "e-discovery costs", "billing transparency", "client communication"],
        "marketing": ["campaign ROI attribution", "martech stack sprawl", "data privacy compliance", "creative production speed"],
        "hr": ["time-to-fill reduction", "candidate experience", "compliance with labor laws", "employee engagement measurement"],
        "higher education": ["enrollment funnel optimization", "research grant management", "campus IT security", "student success analytics"],
        "k-12": ["classroom technology integration", "student safety systems", "teacher workload reduction", "parental engagement"],
        "edtech": ["content engagement metrics", "learning outcome measurement", "platform scalability during peak", "accessibility compliance"],
        "oil": ["drilling efficiency optimization", "environmental compliance", "asset integrity management", "commodity price hedging"],
        "gas": ["drilling efficiency optimization", "environmental compliance", "asset integrity management", "commodity price hedging"],
        "renewable": ["intermittency management", "PPA optimization", "grid interconnection queues", "ESG reporting"],
        "gaming": ["player retention/LTV", "anti-cheat systems", "monetization balance", "cross-platform parity"],
        "digital media": ["programmatic ad yield", "content recommendation", "paywall optimization", "creator economics"],
        "hotel": ["revenue management optimization", "loyalty program ROI", "direct booking growth", "labor scheduling"],
        "restaurant": ["order accuracy and speed", "food cost management", "delivery platform margins", "workforce retention"],
        "travel": ["dynamic pricing optimization", "booking abandonment", "traveler personalization", "disruption management"],
    }

    # Match big-bucket industry
    pains = []
    for key, values in base_pains.items():
        if key in industry_lower:
            pains = values[:3]
            break

    # Match sub-industry for more specific pains (check for keywords in the full industry string)
    for key, values in sub_industry_pains.items():
        if key in industry_lower:
            # Add up to 2 sub-industry pains, avoiding duplicates
            for p in values[:2]:
                if p not in pains:
                    pains.append(p)
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
        num_tables: int = 3,
        personas_per_table: int = 5,
        debate_rounds: int = 5,
        existing_personas: Optional[List[Dict[str, Any]]] = None,
        progress_callback: Optional[Callable] = None,
        seed: Optional[int] = None,
        guide_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run a full swarm deliberation on a sales pitch.

        Returns comprehensive results including per-table debates,
        cross-table synthesis, and final consensus.
        """
        started_at = datetime.utcnow()

        self._progress_fn = None
        async def _progress(stage: str, detail: str = "", pct: int = 0, extra: dict = None):
            logger.info(f"[SwarmEngine] {stage}: {detail}")
            if progress_callback:
                if extra:
                    await progress_callback(stage, detail, pct, extra)
                else:
                    await progress_callback(stage, detail, pct)
        self._progress_fn = _progress

        # ── Stage 1: Generate Committees ──
        await _progress("initializing", "Assembling buying committees...", 5)

        tables = generate_committee_tables(
            industry=industry,
            company_size=company_size,
            company_name=company_name,
            num_tables=num_tables,
            personas_per_table=personas_per_table,
            existing_personas=existing_personas,
            seed=seed,
            guide_id=guide_id,
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
        consensus = await self._generate_consensus(tables, cross_table_insights, pitch_content, industry, company_name)

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
                "guide": guide_id,
                "guide_name": (get_guide_by_id(guide_id) or {}).get("name"),
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
            # Emit per-table detail for live visibility
            if hasattr(self, '_progress_fn') and self._progress_fn:
                await self._progress_fn(
                    "initial_reaction_detail",
                    f"Table {table.table_id}: {len(round_data['responses'])} responses collected",
                    0,
                    {"table_id": table.table_id, "responses": round_data["responses"]}
                )

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
            # Emit per-table detail for live visibility
            if hasattr(self, '_progress_fn') and self._progress_fn:
                await self._progress_fn(
                    "initial_reaction_detail",
                    f"Table {table.table_id}: {len(round_data['responses'])} responses collected",
                    0,
                    {"table_id": table.table_id, "responses": round_data["responses"]}
                )

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
{pitch}

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
