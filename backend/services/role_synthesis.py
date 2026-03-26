"""
Role Synthesis Service
=======================
On-demand LLM-powered synthesis of all feedback from a specific role/title
across committee tables. Produces:
  - A synthesized narrative of that role's perspective
  - Targeted bullet points the salesperson can use
  - A ready-to-use paragraph for pitch preparation
  - Key concerns that role raised

Results are cached in the simulation config so repeat requests are instant.
"""

import json
import logging
from typing import Dict, Any, List, Optional

from services.model_pool import get_model_pool

logger = logging.getLogger(__name__)

# Map common title variations to canonical roles
TITLE_CANONICAL = {
    "cto": "CTO",
    "chief technology officer": "CTO",
    "cfo": "CFO",
    "chief financial officer": "CFO",
    "vp operations": "VP Operations",
    "vp of operations": "VP Operations",
    "director of engineering": "Director of Engineering",
    "dir engineering": "Director of Engineering",
    "head of security": "Head of Security",
    "ciso": "Head of Security",
    "chief information security officer": "Head of Security",
    "vp sales": "VP Sales",
    "vp of sales": "VP Sales",
    "end user": "End User Champion",
    "end user champion": "End User Champion",
}


def normalize_title(title: str) -> str:
    """Normalize a title to a canonical form for grouping."""
    lower = title.lower().strip()
    return TITLE_CANONICAL.get(lower, title.strip())


def extract_role_quotes(debate_transcript: List[Dict], target_title: str) -> List[Dict[str, Any]]:
    """
    Extract all quotes from a specific title/role across all tables and rounds.
    Returns list of {persona, title, table_variant, round, response, role_in_committee}.
    """
    normalized_target = normalize_title(target_title)
    quotes = []

    for table in debate_transcript:
        variant = table.get("variant", "unknown")
        for round_data in table.get("rounds", []):
            round_name = round_data.get("round", "unknown")
            for resp in round_data.get("responses", []):
                resp_title = normalize_title(resp.get("title", ""))
                if resp_title == normalized_target:
                    quotes.append({
                        "persona": resp.get("persona", "Unknown"),
                        "title": resp.get("title", ""),
                        "role_in_committee": resp.get("role", ""),
                        "table_variant": variant,
                        "round": round_name,
                        "response": resp.get("response", ""),
                    })

    return quotes


def get_all_roles(debate_transcript: List[Dict]) -> List[Dict[str, Any]]:
    """
    Get a summary of all unique roles across the debate transcript.
    Returns list of {title, normalized_title, count, tables}.
    """
    role_map = {}  # normalized_title -> {count, tables set, original_title}

    for table in debate_transcript:
        variant = table.get("variant", "unknown")
        for round_data in table.get("rounds", []):
            for resp in round_data.get("responses", []):
                raw_title = resp.get("title", "Unknown")
                norm = normalize_title(raw_title)
                if norm not in role_map:
                    role_map[norm] = {
                        "title": raw_title,
                        "normalized_title": norm,
                        "count": 0,
                        "tables": set(),
                        "committee_roles": set(),
                    }
                role_map[norm]["count"] += 1
                role_map[norm]["tables"].add(variant)
                role_map[norm]["committee_roles"].add(resp.get("role", ""))

    # Convert sets to lists for JSON serialization
    result = []
    for norm, data in role_map.items():
        result.append({
            "title": data["title"],
            "normalized_title": data["normalized_title"],
            "count": data["count"],
            "tables": list(data["tables"]),
            "committee_roles": list(data["committee_roles"]),
        })

    # Sort by count (most quotes first)
    result.sort(key=lambda x: x["count"], reverse=True)
    return result


async def synthesize_role(
    debate_transcript: List[Dict],
    target_title: str,
    pitch_title: str = "",
    company_name: str = "",
    industry: str = "",
) -> Dict[str, Any]:
    """
    Synthesize all feedback from a specific role into actionable sales intelligence.

    Returns:
        {
            "role": str,
            "quote_count": int,
            "synthesis": str,          # Narrative synthesis
            "bullet_points": [str],    # Targeted talking points
            "paragraph": str,          # Ready-to-use paragraph
            "key_concerns": [str],     # Top concerns from this role
            "sentiment_leaning": str,  # positive/mixed/negative
            "quotes": [{persona, table_variant, excerpt}]  # Select quotes
        }
    """
    quotes = extract_role_quotes(debate_transcript, target_title)
    normalized = normalize_title(target_title)

    if not quotes:
        return {
            "role": normalized,
            "quote_count": 0,
            "synthesis": f"No feedback found from {normalized} personas.",
            "bullet_points": [],
            "paragraph": "",
            "key_concerns": [],
            "sentiment_leaning": "unknown",
            "quotes": [],
        }

    # Build the LLM prompt with all quotes
    quotes_text = ""
    for q in quotes:
        quotes_text += f"\n--- {q['persona']} ({q['title']}, {q['role_in_committee']}) | Table: {q['table_variant']} | Round: {q['round']} ---\n"
        quotes_text += q["response"] + "\n"

    pool = get_model_pool()

    prompt = f"""You are a senior sales strategist analyzing buyer committee feedback.

CONTEXT:
- Pitch: "{pitch_title}" by {company_name or 'the vendor'}
- Industry: {industry or 'Technology'}
- Target Role: {normalized}
- Number of {normalized} personas who evaluated: {len(quotes)} (across different committee table variants)

ALL FEEDBACK FROM {normalized.upper()} PERSONAS:
{quotes_text}

TASK: Synthesize all feedback from the {normalized} personas into actionable sales intelligence.

Return a JSON object with these fields:

1. "synthesis" — A 3-4 sentence narrative summarizing the {normalized}'s overall perspective on this pitch. What matters most to them? Where do they lean? What would tip them?

2. "bullet_points" — Array of 4-6 targeted talking points the salesperson should use WHEN PRESENTING TO A {normalized.upper()}. These should be specific, actionable, and directly address what the {normalized} personas cared about. Write them as things the salesperson should SAY, not observations. Each should be 1-2 sentences.

3. "paragraph" — A single, polished paragraph (4-6 sentences) the salesperson could use in an email or pitch document specifically tailored for a {normalized} audience. This should sound natural and persuasive, incorporating the insights from the simulation.

4. "key_concerns" — Array of 3-5 specific concerns the {normalized} personas raised, stated concisely (one line each).

5. "sentiment_leaning" — One of: "positive", "leaning_positive", "mixed", "leaning_negative", "negative"

6. "select_quotes" — Array of 2-3 of the most impactful/representative quotes (brief excerpts, not full responses) with the persona name and table variant.

Return ONLY valid JSON, no markdown.
"""

    try:
        response, _ = await pool.call_with_failover(
            tier="premium",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        result = json.loads(response)

        return {
            "role": normalized,
            "quote_count": len(quotes),
            "synthesis": result.get("synthesis", ""),
            "bullet_points": result.get("bullet_points", []),
            "paragraph": result.get("paragraph", ""),
            "key_concerns": result.get("key_concerns", []),
            "sentiment_leaning": result.get("sentiment_leaning", "mixed"),
            "quotes": result.get("select_quotes", []),
        }

    except Exception as e:
        logger.error(f"Role synthesis failed for {normalized}: {e}", exc_info=True)
        # Return a degraded response with just the raw data
        return {
            "role": normalized,
            "quote_count": len(quotes),
            "synthesis": f"Synthesis unavailable — {len(quotes)} responses from {normalized} personas were collected across {len(set(q['table_variant'] for q in quotes))} committee tables.",
            "bullet_points": [],
            "paragraph": "",
            "key_concerns": [],
            "sentiment_leaning": "unknown",
            "quotes": [
                {
                    "excerpt": q["response"][:200] + "..." if len(q["response"]) > 200 else q["response"],
                    "persona": q["persona"],
                    "table_variant": q["table_variant"],
                }
                for q in quotes[:3]
            ],
        }
