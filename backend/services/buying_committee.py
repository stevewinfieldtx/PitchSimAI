import json
import random
from typing import Optional, Dict, List, Any
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy import select

from config import get_settings
from database import async_session
from models import Persona

settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url) if settings.openai_api_key else None


# Typical buying committee roles by deal type
COMMITTEE_STRUCTURES = {
    "small": {
        "roles": [
            {"title": "CEO / Founder", "authority": "full", "influence": "high"},
            {"title": "Head of Operations", "authority": "partial", "influence": "high"},
            {"title": "Lead Developer / Technical Lead", "authority": "none", "influence": "medium"},
        ]
    },
    "mid-market": {
        "roles": [
            {"title": "VP of {department}", "authority": "partial", "influence": "high"},
            {"title": "Director of {department}", "authority": "partial", "influence": "high"},
            {"title": "CFO", "authority": "full", "influence": "medium"},
            {"title": "IT Security Lead", "authority": "none", "influence": "medium"},
            {"title": "End User / Team Lead", "authority": "none", "influence": "low"},
        ]
    },
    "enterprise": {
        "roles": [
            {"title": "C-Suite Sponsor (CTO/CRO/COO)", "authority": "full", "influence": "high"},
            {"title": "VP of {department}", "authority": "partial", "influence": "high"},
            {"title": "Director of {department}", "authority": "partial", "influence": "high"},
            {"title": "Procurement Manager", "authority": "partial", "influence": "medium"},
            {"title": "CISO / Compliance Officer", "authority": "partial", "influence": "medium"},
            {"title": "IT Architecture Lead", "authority": "none", "influence": "medium"},
            {"title": "End User Champion", "authority": "none", "influence": "low"},
        ]
    },
}

# Warmth profiles control trait distributions
WARMTH_PROFILES = {
    "friendly": {
        "skepticism_range": (0.1, 0.4),
        "openness_range": (0.7, 0.95),
        "detail_range": (0.4, 0.8),
        "sentiment_bias": "positive",
        "description": "Actively looking for solutions, open to new vendors, positive buying signals",
    },
    "mixed": {
        "skepticism_range": (0.3, 0.7),
        "openness_range": (0.4, 0.7),
        "detail_range": (0.5, 0.9),
        "sentiment_bias": "neutral",
        "description": "Standard evaluation process, some champions and some skeptics",
    },
    "hostile": {
        "skepticism_range": (0.7, 0.95),
        "openness_range": (0.1, 0.4),
        "detail_range": (0.7, 0.95),
        "sentiment_bias": "negative",
        "description": "Resistant to change, incumbent vendor loyalty, budget-constrained, political dynamics",
    },
}

# Industry-specific departments and concerns
INDUSTRY_CONTEXT = {
    "SaaS": {
        "departments": ["Engineering", "Product", "Sales", "Marketing", "Customer Success"],
        "key_concerns": ["integration complexity", "API reliability", "data migration", "vendor lock-in", "scalability"],
    },
    "Financial Services": {
        "departments": ["Technology", "Risk Management", "Operations", "Compliance", "Trading"],
        "key_concerns": ["regulatory compliance", "data sovereignty", "audit trails", "SOC 2", "penetration testing"],
    },
    "Healthcare": {
        "departments": ["Clinical Operations", "Health IT", "Patient Experience", "Compliance", "Research"],
        "key_concerns": ["HIPAA compliance", "EHR integration", "patient data privacy", "clinical workflow disruption", "FDA regulations"],
    },
    "Retail": {
        "departments": ["E-Commerce", "Store Operations", "Supply Chain", "Marketing", "Customer Experience"],
        "key_concerns": ["omnichannel integration", "POS compatibility", "seasonal scalability", "customer data", "ROI timeline"],
    },
    "Manufacturing": {
        "departments": ["Operations", "Supply Chain", "Quality", "Engineering", "Maintenance"],
        "key_concerns": ["production downtime", "legacy system integration", "shop floor adoption", "total cost of ownership", "supply chain visibility"],
    },
    "Education": {
        "departments": ["Academic Affairs", "IT Services", "Student Success", "Administration", "Research"],
        "key_concerns": ["FERPA compliance", "LMS integration", "accessibility", "budget constraints", "faculty adoption"],
    },
    "Real Estate": {
        "departments": ["Property Management", "Acquisitions", "Asset Management", "Leasing", "Development"],
        "key_concerns": ["portfolio visibility", "tenant experience", "lease management", "capital planning", "market analytics"],
    },
}

# Realistic first/last name pools
FIRST_NAMES = [
    "Sarah", "Marcus", "Priya", "Tom", "Jennifer", "Robert", "Alex", "Diana",
    "Wei", "Linda", "James", "Maria", "David", "Kenji", "Fatima", "Carlos",
    "Olivia", "Andre", "Mei", "Hassan", "Rachel", "Dmitri", "Aisha", "Patrick",
    "Yuki", "Sofia", "Brian", "Nadia", "Tyler", "Inga", "Raj", "Elena",
]
LAST_NAMES = [
    "Chen", "Johnson", "Patel", "Williams", "Martinez", "Kim", "Rivera", "Okonkwo",
    "Zhang", "Nakamura", "Thompson", "Garcia", "Anderson", "Tanaka", "Hassan", "Santos",
    "O'Brien", "Volkov", "Johannsen", "Park", "Nguyen", "Kowalski", "Adebayo", "Fischer",
    "Sharma", "Moreau", "Campbell", "Reyes", "Larsson", "Dubois", "Watanabe", "Okafor",
]

BUYING_STYLES = ["early-adopter", "consensus-builder", "risk-averse", "analytical"]


def _generate_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def _generate_traits(warmth: str, role_influence: str) -> Dict[str, float]:
    """Generate personality traits based on warmth profile and role influence."""
    profile = WARMTH_PROFILES[warmth]

    # Higher influence roles tend to be more skeptical (they have more at stake)
    influence_modifier = {"high": 0.1, "medium": 0.0, "low": -0.1}[role_influence]

    skepticism = random.uniform(*profile["skepticism_range"]) + influence_modifier
    openness = random.uniform(*profile["openness_range"]) - influence_modifier
    detail = random.uniform(*profile["detail_range"])

    # Add some individual variance (±0.1) to avoid everyone feeling identical
    skepticism = max(0.05, min(0.95, skepticism + random.gauss(0, 0.05)))
    openness = max(0.05, min(0.95, openness + random.gauss(0, 0.05)))
    detail = max(0.05, min(0.95, detail + random.gauss(0, 0.05)))

    return {
        "skepticism": round(skepticism, 2),
        "innovation_openness": round(openness, 2),
        "detail_orientation": round(detail, 2),
        "assertiveness": round(random.uniform(0.3, 0.9), 2),
        "risk_tolerance": round(1.0 - skepticism + random.gauss(0, 0.1), 2),
    }


def _pick_buying_style(traits: Dict[str, float]) -> str:
    """Select buying style based on personality traits."""
    if traits["innovation_openness"] > 0.7 and traits["skepticism"] < 0.4:
        return "early-adopter"
    elif traits["skepticism"] > 0.7:
        return "risk-averse"
    elif traits["detail_orientation"] > 0.7:
        return "analytical"
    else:
        return "consensus-builder"


async def generate_buying_committee(
    industry: str,
    company_size: str,  # "small", "mid-market", "enterprise"
    warmth: str,  # "friendly", "mixed", "hostile"
    company_name: Optional[str] = None,
    product_context: Optional[str] = None,
    user_id: Optional[str] = None,
    save_to_db: bool = True,
) -> List[Dict[str, Any]]:
    """
    Generate a full buying committee with contextually appropriate personas.

    This is the primary way users create persona groups — zero manual entry.
    """

    # Normalize inputs
    size_key = company_size.lower().replace("-", "-").replace(" ", "-")
    if size_key in ("early-stage", "startup", "small"):
        size_key = "small"
    elif size_key in ("mid-market", "midmarket", "medium"):
        size_key = "mid-market"
    elif size_key in ("enterprise", "large"):
        size_key = "enterprise"
    else:
        size_key = "mid-market"

    warmth_key = warmth.lower()
    if warmth_key not in WARMTH_PROFILES:
        warmth_key = "mixed"

    structure = COMMITTEE_STRUCTURES.get(size_key, COMMITTEE_STRUCTURES["mid-market"])
    industry_ctx = INDUSTRY_CONTEXT.get(industry, INDUSTRY_CONTEXT.get("SaaS"))
    warmth_profile = WARMTH_PROFILES[warmth_key]

    # If we have an LLM, use it for richer persona generation
    if client and settings.openai_api_key:
        return await _llm_generate_committee(
            industry=industry,
            company_size=size_key,
            warmth=warmth_key,
            structure=structure,
            industry_ctx=industry_ctx,
            warmth_profile=warmth_profile,
            company_name=company_name,
            product_context=product_context,
            user_id=user_id,
            save_to_db=save_to_db,
        )
    else:
        return await _mock_generate_committee(
            industry=industry,
            company_size=size_key,
            warmth=warmth_key,
            structure=structure,
            industry_ctx=industry_ctx,
            warmth_profile=warmth_profile,
            company_name=company_name,
            user_id=user_id,
            save_to_db=save_to_db,
        )


async def _llm_generate_committee(
    industry: str,
    company_size: str,
    warmth: str,
    structure: Dict,
    industry_ctx: Dict,
    warmth_profile: Dict,
    company_name: Optional[str],
    product_context: Optional[str],
    user_id: Optional[str],
    save_to_db: bool,
) -> List[Dict[str, Any]]:
    """Use LLM to generate rich, contextual buying committee personas."""

    num_members = len(structure["roles"])
    departments = industry_ctx["departments"]
    concerns = industry_ctx["key_concerns"]

    system_prompt = f"""You are generating a realistic B2B buying committee for a sales simulation.

CONTEXT:
- Industry: {industry}
- Company Size: {company_size}
- Company Name: {company_name or 'Generic ' + industry + ' company'}
- Committee Warmth: {warmth} — {warmth_profile['description']}
- Product Being Evaluated: {product_context or 'A B2B SaaS product'}
- Relevant Departments: {', '.join(departments)}
- Industry Concerns: {', '.join(concerns)}

Generate {num_members} committee members. Each person should feel like a real individual with:
- A realistic name
- A specific title (not generic — e.g., "VP of Revenue Operations" not just "VP")
- A 2-3 sentence bio that explains their background, what they care about, and how they'll evaluate this purchase
- 2-4 specific pain points relevant to their role AND industry
- 2-3 specific objection patterns they'd raise (things they'd actually say in a meeting)
- A decision process description
- Budget authority level

The committee warmth of "{warmth}" means:
- friendly: Most members are open to change, actively looking for solutions
- mixed: Some champions, some neutral, maybe one skeptic
- hostile: Most are resistant, loyal to incumbents, budget-protective, politically motivated

IMPORTANT: Each person should have a DISTINCT personality. Don't make everyone the same. Even in a "friendly" committee, someone should be more cautious. Even in a "hostile" one, there might be one secret champion.

Respond with valid JSON array:
[
  {{
    "name": "Full Name",
    "title": "Specific Title",
    "bio": "2-3 sentence background",
    "buying_style": "early-adopter|consensus-builder|risk-averse|analytical",
    "pain_points": ["specific pain 1", "specific pain 2"],
    "objection_patterns": ["What they'd actually say in a meeting"],
    "decision_process": "How they make decisions",
    "budget_authority": "full|partial|none",
    "personality_traits": {{
      "skepticism": 0.0-1.0,
      "innovation_openness": 0.0-1.0,
      "detail_orientation": 0.0-1.0,
      "assertiveness": 0.0-1.0,
      "risk_tolerance": 0.0-1.0
    }}
  }}
]"""

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate the buying committee now."},
            ],
            temperature=0.9,
            response_format={"type": "json_object"},
        )

        raw = json.loads(response.choices[0].message.content)
        # Handle both {"committee": [...]} and [...] formats
        members = raw if isinstance(raw, list) else raw.get("committee", raw.get("members", []))

    except Exception as e:
        print(f"LLM committee generation failed: {e}")
        return await _mock_generate_committee(
            industry, company_size, warmth, structure,
            INDUSTRY_CONTEXT.get(industry, INDUSTRY_CONTEXT["SaaS"]),
            warmth_profile, company_name, user_id, save_to_db
        )

    # Save to database
    created_personas = []
    if save_to_db:
        async with async_session() as db:
            for member in members:
                persona = Persona(
                    name=member["name"],
                    title=member["title"],
                    industry=industry,
                    company_size=company_size,
                    personality_traits=member.get("personality_traits", {}),
                    buying_style=member.get("buying_style", "analytical"),
                    pain_points=member.get("pain_points", []),
                    objection_patterns=member.get("objection_patterns", []),
                    decision_process=member.get("decision_process"),
                    budget_authority=member.get("budget_authority", "partial"),
                    bio=member.get("bio"),
                    is_public=False,
                    created_by=UUID(user_id) if user_id else None,
                )
                db.add(persona)
                await db.flush()

                created_personas.append({
                    "id": str(persona.id),
                    "name": persona.name,
                    "title": persona.title,
                    "industry": persona.industry,
                    "company_size": persona.company_size,
                    "personality_traits": persona.personality_traits,
                    "buying_style": persona.buying_style,
                    "pain_points": persona.pain_points,
                    "objection_patterns": persona.objection_patterns,
                    "decision_process": persona.decision_process,
                    "budget_authority": persona.budget_authority,
                    "bio": persona.bio,
                })

            await db.commit()
    else:
        created_personas = members

    return created_personas


async def _mock_generate_committee(
    industry: str,
    company_size: str,
    warmth: str,
    structure: Dict,
    industry_ctx: Dict,
    warmth_profile: Dict,
    company_name: Optional[str],
    user_id: Optional[str],
    save_to_db: bool,
) -> List[Dict[str, Any]]:
    """Generate committee without LLM using intelligent randomization."""

    departments = industry_ctx["departments"]
    concerns = industry_ctx["key_concerns"]
    roles = structure["roles"]

    created_personas = []
    used_names = set()

    async with async_session() as db:
        for i, role in enumerate(roles):
            # Generate unique name
            name = _generate_name()
            while name in used_names:
                name = _generate_name()
            used_names.add(name)

            # Pick department for templated titles
            dept = departments[i % len(departments)]
            title = role["title"].replace("{department}", dept)

            # Generate traits based on warmth and role
            traits = _generate_traits(warmth, role["influence"])
            buying_style = _pick_buying_style(traits)

            # Generate contextual pain points
            role_pain_points = random.sample(concerns, k=min(3, len(concerns)))

            # Generate contextual objection patterns
            objection_templates = {
                "friendly": [
                    f"I'm excited about this, but how does it handle {random.choice(concerns)}?",
                    "What does the implementation timeline look like for our size?",
                    "Can you walk me through a success story in our industry?",
                ],
                "mixed": [
                    f"I need to understand how this addresses {random.choice(concerns)}",
                    "What's the total cost of ownership over 3 years?",
                    f"How does this integrate with our existing {dept.lower()} tools?",
                    "Who else in {industry} is using this successfully?",
                ],
                "hostile": [
                    f"We tried something similar before and it failed. Why is this different?",
                    f"Our current solution handles {random.choice(concerns)} just fine",
                    "I don't see how this justifies pulling budget from other priorities",
                    "The switching costs alone would eat any ROI for 18+ months",
                ],
            }

            objections = random.sample(
                objection_templates.get(warmth, objection_templates["mixed"]),
                k=min(2, len(objection_templates[warmth]))
            )

            # Generate bio
            years_exp = random.randint(8, 25)
            bio_templates = {
                "friendly": f"{years_exp} years in {industry}. Actively looking for ways to modernize the {dept.lower()} function. Known for championing new tools that deliver measurable results.",
                "mixed": f"{years_exp} years in {industry}. Methodical evaluator who wants to see clear evidence before committing. Values thorough vendor assessments but open to innovation.",
                "hostile": f"{years_exp} years in {industry}. Has been burned by vendor promises before. Deeply protective of current workflows and team stability. Every dollar must be justified three times over.",
            }

            persona_data = {
                "name": name,
                "title": title,
                "industry": industry,
                "company_size": company_size,
                "personality_traits": traits,
                "buying_style": buying_style,
                "pain_points": role_pain_points,
                "objection_patterns": objections,
                "decision_process": f"{'Quick decision maker' if traits['skepticism'] < 0.4 else 'Thorough evaluation process'} — {role['influence']} influence on final decision",
                "budget_authority": role["authority"],
                "bio": bio_templates.get(warmth, bio_templates["mixed"]),
                "is_public": False,
            }

            if save_to_db:
                persona = Persona(
                    **persona_data,
                    created_by=UUID(user_id) if user_id else None,
                )
                db.add(persona)
                await db.flush()
                persona_data["id"] = str(persona.id)

            created_personas.append(persona_data)

        if save_to_db:
            await db.commit()

    return created_personas


async def generate_persona_from_context(
    title: str,
    industry: str,
    company_size: str,
    company_name: Optional[str] = None,
    warmth: str = "mixed",
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a single persona dynamically from title + industry + company size.
    No templates — every persona is unique to its context.
    """

    if client and settings.openai_api_key:
        warmth_profile = WARMTH_PROFILES.get(warmth, WARMTH_PROFILES["mixed"])

        prompt = f"""Generate a single realistic buyer persona for a sales simulation based on:
- Title: {title}
- Industry: {industry}
- Company Size: {company_size}
- Company: {company_name or 'Not specified'}
- Disposition: {warmth} — {warmth_profile['description']}

A {title} at a {company_size} {industry} company has VERY different priorities than the same title at a different company type. Make this persona specific to their context.

Respond with valid JSON:
{{
  "name": "Full Name",
  "title": "{title}",
  "bio": "2-3 sentences",
  "buying_style": "early-adopter|consensus-builder|risk-averse|analytical",
  "pain_points": ["specific to role+industry+size"],
  "objection_patterns": ["what they'd actually say"],
  "decision_process": "description",
  "budget_authority": "full|partial|none",
  "personality_traits": {{
    "skepticism": 0.0-1.0,
    "innovation_openness": 0.0-1.0,
    "detail_orientation": 0.0-1.0,
    "assertiveness": 0.0-1.0,
    "risk_tolerance": 0.0-1.0
  }}
}}"""

        try:
            response = await client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "system", "content": prompt}],
                temperature=0.9,
                response_format={"type": "json_object"},
            )
            persona_data = json.loads(response.choices[0].message.content)
            persona_data["industry"] = industry
            persona_data["company_size"] = company_size
            return persona_data
        except Exception:
            pass

    # Fallback: generate without LLM
    traits = _generate_traits(warmth, "medium")
    return {
        "name": _generate_name(),
        "title": title,
        "industry": industry,
        "company_size": company_size,
        "personality_traits": traits,
        "buying_style": _pick_buying_style(traits),
        "pain_points": random.sample(
            INDUSTRY_CONTEXT.get(industry, INDUSTRY_CONTEXT["SaaS"])["key_concerns"],
            k=2
        ),
        "objection_patterns": [f"How does this work for {industry} specifically?"],
        "decision_process": "Standard evaluation",
        "budget_authority": "partial",
        "bio": f"Experienced {title} in the {industry} sector.",
    }
