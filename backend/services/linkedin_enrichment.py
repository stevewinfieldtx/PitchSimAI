"""
LinkedIn-based persona enrichment.

Approach: Users paste a LinkedIn profile URL or provide a name + company.
We use available data to build a realistic, calibrated persona.

Note: Direct LinkedIn scraping violates ToS. This module supports:
1. Manual paste of LinkedIn profile text (copy-paste from browser)
2. Integration with enrichment APIs (Apollo, Clearbit, etc.) when available
3. LLM-based inference from name + company + title
"""

import json
from typing import Optional, Dict, Any
from openai import AsyncOpenAI

from config import get_settings

settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url) if settings.openai_api_key else None


async def enrich_from_linkedin_text(
    profile_text: str,
    warmth: str = "mixed",
) -> Dict[str, Any]:
    """
    Generate a persona from pasted LinkedIn profile text.
    User copies the text content from a LinkedIn profile page and pastes it here.
    """

    if not client or not settings.openai_api_key:
        return {"error": "OpenAI API key required for LinkedIn enrichment"}

    prompt = f"""Analyze this LinkedIn profile text and create a buyer persona for a sales simulation.

LINKEDIN PROFILE:
{profile_text}

Based on their experience, industry, seniority, and career trajectory, create a realistic buyer persona.
Their general disposition should be: {warmth}

Key things to infer:
- What are they likely to care about based on their role and experience?
- What objections would they raise based on their background?
- How do they make decisions based on their seniority and company?
- What's their likely buying style given their career path?

Respond with valid JSON:
{{
  "name": "Their actual name from the profile",
  "title": "Their current title",
  "industry": "Their industry",
  "company_size": "early-stage|mid-market|enterprise",
  "company_name": "Their current company",
  "bio": "2-3 sentence summary of who they are as a buyer, based on their background",
  "buying_style": "early-adopter|consensus-builder|risk-averse|analytical",
  "pain_points": ["inferred from their role and industry"],
  "objection_patterns": ["what they'd likely say based on their background"],
  "decision_process": "inferred from seniority and company type",
  "budget_authority": "full|partial|none",
  "personality_traits": {{
    "skepticism": 0.0-1.0,
    "innovation_openness": 0.0-1.0,
    "detail_orientation": 0.0-1.0,
    "assertiveness": 0.0-1.0,
    "risk_tolerance": 0.0-1.0
  }},
  "linkedin_insights": "Brief note on what from their profile informed this persona"
}}"""

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"error": f"Enrichment failed: {str(e)}"}


async def enrich_from_name_and_company(
    name: str,
    company: str,
    title: Optional[str] = None,
    warmth: str = "mixed",
) -> Dict[str, Any]:
    """
    Generate a persona from just a name and company.
    Uses LLM's training data knowledge about the company and typical roles.
    """

    if not client or not settings.openai_api_key:
        return {"error": "OpenAI API key required for enrichment"}

    prompt = f"""Create a realistic buyer persona for a sales simulation based on:
- Name: {name}
- Company: {company}
- Title: {title or 'Unknown — infer likely title based on company'}
- Disposition: {warmth}

Use your knowledge of {company} to infer:
- The company's industry, size, and culture
- What someone in this role at this specific company would care about
- Their likely buying process and concerns
- Company-specific technology stack or vendor preferences if known

Be specific to THIS company — a buyer at {company} is different from a buyer at a competitor.

Respond with valid JSON:
{{
  "name": "{name}",
  "title": "Their likely title (use provided if given)",
  "industry": "Company's industry",
  "company_size": "early-stage|mid-market|enterprise",
  "company_name": "{company}",
  "bio": "2-3 sentences about who they are as a buyer at this specific company",
  "buying_style": "early-adopter|consensus-builder|risk-averse|analytical",
  "pain_points": ["specific to their role at this company"],
  "objection_patterns": ["company-specific objections they'd raise"],
  "decision_process": "How this company typically buys",
  "budget_authority": "full|partial|none",
  "personality_traits": {{
    "skepticism": 0.0-1.0,
    "innovation_openness": 0.0-1.0,
    "detail_orientation": 0.0-1.0,
    "assertiveness": 0.0-1.0,
    "risk_tolerance": 0.0-1.0
  }},
  "company_insights": "Brief note on what's known about this company's buying culture"
}}"""

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"error": f"Enrichment failed: {str(e)}"}
