"""
Committee Room Engine
=====================
Orchestrates live group chat in a Committee Room.

When the user sends a message, the engine:
1. Decides which personas should respond (relevance + personality)
2. Generates responses in parallel, each persona aware of the others
3. Optionally triggers inter-persona reactions (one persona reacts to another)
4. Returns ordered responses for the frontend to render sequentially
"""

import json
import asyncio
import logging
import random
from datetime import datetime
from typing import List, Dict, Any, Optional

from services.model_pool import get_model_pool

logger = logging.getLogger(__name__)


def _build_room_system_prompt(
    persona: Dict[str, Any],
    all_participants: List[Dict[str, Any]],
    pitch_content: str,
    room_context: str,
) -> str:
    """Build the system prompt for a persona in a group room setting."""

    other_names = [
        f"{p['name']} ({p['title']})"
        for p in all_participants
        if str(p["id"]) != str(persona["id"])
    ]

    return f"""You are {persona['name']}, {persona['title']} in the {persona.get('industry', 'technology')} industry.

ABOUT YOU:
- Company Size: {persona.get('company_size', 'mid-market')}
- Buying Style: {persona.get('buying_style', 'analytical')}
- Personality: {json.dumps(persona.get('personality_traits', {}))}
- Pain Points: {', '.join(persona.get('pain_points', []))}
- Common Objections: {', '.join(persona.get('objection_patterns', []))}
- Bio: {persona.get('bio', 'N/A')}

ROOM CONTEXT:
You are in a committee room with other stakeholders evaluating a sales pitch.
Other people in the room: {', '.join(other_names)}
{room_context}

THE PITCH BEING EVALUATED:
{pitch_content[:2000]}

INSTRUCTIONS:
- Stay fully in character as {persona['name']}.
- You are in a live group discussion. Keep responses conversational — 2-4 sentences max.
- You can agree or disagree with others in the room. Reference them by name if relevant.
- Ask follow-up questions if the pitch doesn't address your concerns.
- Be authentic to your personality traits (skepticism: {persona.get('personality_traits', {}).get('skepticism', 0.5)})
- Don't repeat what others have already said — build on it or challenge it."""


async def decide_responders(
    user_message: str,
    participants: List[Dict[str, Any]],
    recent_history: List[Dict[str, Any]],
    max_responders: int = 4,
) -> List[Dict[str, Any]]:
    """
    Decide which personas should respond to the user's message.
    Uses heuristics + optional LLM call for smarter selection.
    """
    pool = get_model_pool()

    # If few participants, everyone responds
    if len(participants) <= 3:
        return participants

    # Try LLM-based selection for smarter routing
    if pool.is_available:
        try:
            participant_list = "\n".join(
                f"- {p['name']} ({p['title']}, {p.get('industry', '?')}): "
                f"pain points = {', '.join(p.get('pain_points', [])[:3])}"
                for p in participants
            )

            prompt = f"""Given this user message in a buying committee discussion:
"{user_message}"

These people are in the room:
{participant_list}

Which 2-{max_responders} people should respond? Pick the ones most relevant to the topic.
Also pick at least one skeptic or dissenter for balance.
Return a JSON array of their exact names, e.g. ["Sarah Chen", "Marcus Johnson"]"""

            content, _ = await pool.call_with_failover(
                tier="volume",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200,
                response_format={"type": "json_object"},
            )

            # Parse the response — might be {"names": [...]} or just [...]
            parsed = json.loads(content)
            names = parsed if isinstance(parsed, list) else parsed.get("names", parsed.get("responders", []))

            selected = [p for p in participants if p["name"] in names]
            if selected:
                return selected[:max_responders]
        except Exception as e:
            logger.warning(f"LLM responder selection failed, using fallback: {e}")

    # Fallback: random selection weighted by relevance heuristics
    msg_lower = user_message.lower()
    scored = []
    for p in participants:
        score = random.uniform(0.3, 0.7)
        # Boost if message touches their pain points
        for pp in p.get("pain_points", []):
            if any(word in msg_lower for word in pp.lower().split()):
                score += 0.3
        # Boost if message touches their objection patterns
        for obj in p.get("objection_patterns", []):
            if any(word in msg_lower for word in obj.lower().split()[:3]):
                score += 0.2
        # High-skepticism personas chime in more on pushback topics
        skepticism = p.get("personality_traits", {}).get("skepticism", 0.5)
        if any(word in msg_lower for word in ["cost", "price", "risk", "concern", "worry", "expensive"]):
            score += skepticism * 0.3
        scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    count = min(max_responders, max(2, len(participants) // 2))
    return [p for _, p in scored[:count]]


async def generate_room_response(
    persona: Dict[str, Any],
    user_message: str,
    all_participants: List[Dict[str, Any]],
    conversation_history: List[Dict[str, Any]],
    pitch_content: str,
    room_context: str = "",
) -> Dict[str, Any]:
    """Generate a single persona's response in the room context."""
    pool = get_model_pool()

    system_prompt = _build_room_system_prompt(
        persona, all_participants, pitch_content, room_context
    )

    # Build message history (keep last 20 messages for context window)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in conversation_history[-20:]:
        if msg.get("role") == "user":
            messages.append({"role": "user", "content": msg["content"]})
        elif msg.get("persona_name"):
            # Other personas' messages appear as user messages with attribution
            messages.append({
                "role": "user",
                "content": f"[{msg['persona_name']}]: {msg['content']}"
            })

    messages.append({"role": "user", "content": user_message})

    if pool.is_available:
        try:
            content, model_used = await pool.call_with_failover(
                tier="premium",
                messages=messages,
                temperature=0.85,
                max_tokens=250,
            )
            return {
                "persona_id": str(persona["id"]),
                "persona_name": persona["name"],
                "persona_title": persona["title"],
                "content": content.strip(),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Room response failed for {persona['name']}: {e}")

    # Mock fallback
    reactions = [
        f"That's an interesting point. From my perspective as {persona['title']}, I'd want to understand the impact on {(persona.get('pain_points') or ['our operations'])[0]}.",
        f"I appreciate you raising that. My main concern remains {(persona.get('objection_patterns') or ['the implementation timeline'])[0].lower()}.",
        f"Building on what was just said — in {persona.get('industry', 'our industry')}, we'd need to see concrete evidence before moving forward.",
    ]
    return {
        "persona_id": str(persona["id"]),
        "persona_name": persona["name"],
        "persona_title": persona["title"],
        "content": random.choice(reactions),
        "timestamp": datetime.utcnow().isoformat(),
    }


async def generate_room_responses(
    user_message: str,
    participants: List[Dict[str, Any]],
    conversation_history: List[Dict[str, Any]],
    pitch_content: str,
    room_context: str = "",
    max_responders: int = 4,
) -> List[Dict[str, Any]]:
    """
    Main entry point: generate all persona responses to a user message.
    Returns a list of response dicts ordered by a slight random delay
    to feel natural (not everyone answers at the exact same time).
    """
    # 1. Decide who responds
    responders = await decide_responders(
        user_message, participants, conversation_history, max_responders
    )

    # 2. Generate responses in parallel
    tasks = [
        generate_room_response(
            persona=p,
            user_message=user_message,
            all_participants=participants,
            conversation_history=conversation_history,
            pitch_content=pitch_content,
            room_context=room_context,
        )
        for p in responders
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 3. Filter out failures, shuffle slightly for natural feel
    responses = [r for r in results if isinstance(r, dict)]
    random.shuffle(responses)

    return responses
