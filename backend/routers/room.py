"""
Committee Room Router
=====================
REST endpoints for creating/listing rooms + WebSocket for live group chat.
"""

import json
import asyncio
import hashlib
import logging
from uuid import UUID
from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Simulation, Persona, CommitteeRoom
from schemas import RoomCreate, RoomResponse
from services.room_engine import generate_room_responses
from services.voice import assign_voices, text_to_speech_base64

router = APIRouter()
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _extract_tables_from_sim(sim: Simulation) -> List[Dict[str, Any]]:
    """Pull the debate tables out of the simulation config."""
    config = sim.config or {}
    return config.get("debate_transcript", [])


def _extract_participants_by_role(tables: List[Dict], role_keyword: str) -> List[Dict[str, Any]]:
    """
    Gather all personas across tables whose title matches the role keyword.
    e.g. role_keyword="CTO" matches "Chief Technology Officer", "CTO", etc.
    """
    keyword = role_keyword.lower()
    participants = []
    seen_names = set()

    # Common title expansions
    TITLE_MAP = {
        "cto": ["chief technology officer", "cto"],
        "cfo": ["chief financial officer", "cfo"],
        "ceo": ["chief executive officer", "ceo"],
        "coo": ["chief operating officer", "coo"],
        "ciso": ["chief information security officer", "ciso"],
        "vp": ["vice president", "vp"],
        "director": ["director"],
        "head": ["head of"],
    }

    match_terms = TITLE_MAP.get(keyword, [keyword])

    for table_data in tables:
        for persona in table_data.get("personas", []):
            title_lower = persona.get("title", "").lower()
            name = persona.get("name", "")

            if name in seen_names:
                continue

            if any(term in title_lower for term in match_terms) or keyword in title_lower:
                # Generate a stable pseudo-ID from name if not present
                if "id" not in persona:
                    persona["id"] = hashlib.md5(f"{name}-{persona.get('title', '')}".encode()).hexdigest()[:16]
                participants.append(persona)
                seen_names.add(name)

    return participants


def _extract_participants_by_table(tables: List[Dict], table_index: int) -> List[Dict[str, Any]]:
    """Get all personas from a specific table."""
    if table_index < 0 or table_index >= len(tables):
        return []

    table = tables[table_index]
    participants = []
    for persona in table.get("personas", []):
        if "id" not in persona:
            persona["id"] = hashlib.md5(f"{persona.get('name', '')}-{persona.get('title', '')}".encode()).hexdigest()[:16]
        participants.append(persona)

    return participants


def _extract_debate_quotes(tables: List[Dict], participants: List[Dict], room_type: str, role_filter: str = None, table_index: int = None) -> List[Dict[str, Any]]:
    """
    Extract each participant's debate quotes from the original deliberation.
    Returns a list of {name, title, table_index, table_variant, quotes: [{round, text}]}
    """
    participant_names = {p.get("name", "") for p in participants}
    quotes_by_name: Dict[str, Dict] = {}

    for ti, table in enumerate(tables):
        # For table-based rooms, only pull from the specific table
        if room_type == "table" and table_index is not None and ti != table_index:
            continue

        variant = table.get("variant", f"table_{ti + 1}")
        for round_data in table.get("rounds", []):
            round_label = round_data.get("round", "")
            # Human-readable round names
            if round_label == "initial_reaction":
                round_display = "Initial reaction"
            elif round_label.startswith("debate_"):
                round_num = round_label.replace("debate_", "")
                round_display = f"Debate round {round_num}"
            elif round_label == "cross_table":
                round_display = "Cross-table discussion"
            elif round_label == "consensus":
                round_display = "Final consensus"
            else:
                round_display = round_label.replace("_", " ").title()

            for resp in round_data.get("responses", []):
                name = resp.get("persona", "")
                if name not in participant_names:
                    continue

                if name not in quotes_by_name:
                    quotes_by_name[name] = {
                        "name": name,
                        "title": resp.get("title", ""),
                        "table_index": ti,
                        "table_variant": variant,
                        "quotes": [],
                    }

                text = resp.get("response", "")
                # Keep quotes manageable — truncate very long ones
                if len(text) > 400:
                    text = text[:397] + "..."

                quotes_by_name[name]["quotes"].append({
                    "round": round_display,
                    "text": text,
                })

    return list(quotes_by_name.values())


# ──────────────────────────────────────────────
# REST Endpoints
# ──────────────────────────────────────────────


@router.post("", response_model=RoomResponse)
async def create_room(body: RoomCreate, db: AsyncSession = Depends(get_db)):
    """Create a Committee Room from a completed simulation."""

    # Load simulation
    result = await db.execute(
        select(Simulation).where(
            Simulation.id == body.simulation_id,
            Simulation.status == "completed",
        )
    )
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(404, "Completed simulation not found")

    tables = _extract_tables_from_sim(sim)
    if not tables:
        raise HTTPException(400, "Simulation has no debate table data — run a swarm simulation first")

    # Determine participants
    if body.room_type == "role":
        if not body.role_filter:
            raise HTTPException(400, "role_filter is required for role-based rooms")
        participants = _extract_participants_by_role(tables, body.role_filter)
        room_name = f"{body.role_filter.upper()}s Room"
    elif body.room_type == "table":
        if body.table_index is None:
            raise HTTPException(400, "table_index is required for table-based rooms")
        participants = _extract_participants_by_table(tables, body.table_index)
        variant = tables[body.table_index].get("variant", f"Table {body.table_index + 1}")
        room_name = f"Table: {variant.replace('-', ' ').title()}"
    else:
        raise HTTPException(400, "room_type must be 'role' or 'table'")

    if not participants:
        raise HTTPException(400, f"No matching personas found for {body.room_type} filter")

    # Assign voices
    voice_config = assign_voices(participants)

    # Create room
    room = CommitteeRoom(
        simulation_id=body.simulation_id,
        room_type=body.room_type,
        role_filter=body.role_filter,
        table_index=body.table_index,
        room_name=room_name,
        participant_ids=[str(p.get("id", "")) for p in participants],
        conversation_history=[],
        voice_config=voice_config,
    )
    db.add(room)
    await db.commit()
    await db.refresh(room)

    return RoomResponse(
        id=room.id,
        simulation_id=room.simulation_id,
        room_type=room.room_type,
        room_name=room.room_name,
        role_filter=room.role_filter,
        table_index=room.table_index,
        participant_count=len(participants),
        participants=[
            {
                "id": str(p.get("id", "")),
                "name": p.get("name", ""),
                "title": p.get("title", ""),
                "industry": p.get("industry", ""),
                "role_in_committee": p.get("role_in_committee", ""),
                "voice": voice_config.get(str(p.get("id", "")), {}),
            }
            for p in participants
        ],
        created_at=room.created_at,
    )


@router.get("/simulation/{simulation_id}/available")
async def get_available_rooms(simulation_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Show what rooms can be created from a simulation.
    Returns available roles and tables.
    """
    result = await db.execute(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.status == "completed",
        )
    )
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(404, "Completed simulation not found")

    tables = _extract_tables_from_sim(sim)
    if not tables:
        return {"roles": [], "tables": [], "existing_rooms": []}

    # Discover unique roles across all tables
    role_counts: Dict[str, int] = {}
    for table in tables:
        for persona in table.get("personas", []):
            title = persona.get("title", "Unknown")
            # Normalize to short role labels
            title_lower = title.lower()
            for label, keywords in {
                "CTO": ["chief technology", "cto"],
                "CFO": ["chief financial", "cfo"],
                "CEO": ["chief executive", "ceo"],
                "VP Ops": ["vp of operations", "vice president of operations"],
                "VP Sales": ["vp of sales", "vice president of sales"],
                "VP Eng": ["vp of engineering", "vice president of engineering"],
                "Dir. Engineering": ["director of engineering"],
                "Dir. Product": ["director of product"],
                "Security Lead": ["security", "ciso"],
                "Procurement": ["procurement"],
            }.items():
                if any(kw in title_lower for kw in keywords):
                    role_counts[label] = role_counts.get(label, 0) + 1
                    break
            else:
                role_counts[title] = role_counts.get(title, 0) + 1

    # Existing rooms for this simulation
    existing_result = await db.execute(
        select(CommitteeRoom).where(CommitteeRoom.simulation_id == simulation_id)
    )
    existing_rooms = existing_result.scalars().all()

    return {
        "roles": [
            {"role": role, "count": count}
            for role, count in sorted(role_counts.items(), key=lambda x: -x[1])
            if count > 0
        ],
        "tables": [
            {
                "index": i,
                "variant": t.get("variant", f"Table {i + 1}"),
                "persona_count": len(t.get("personas", [])),
            }
            for i, t in enumerate(tables)
        ],
        "existing_rooms": [
            {
                "id": str(r.id),
                "room_type": r.room_type,
                "room_name": r.room_name,
                "role_filter": r.role_filter,
                "table_index": r.table_index,
            }
            for r in existing_rooms
        ],
    }


@router.get("/{room_id}")
async def get_room(room_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get room details including participants and conversation history."""
    result = await db.execute(select(CommitteeRoom).where(CommitteeRoom.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(404, "Room not found")

    # Reload participant details from simulation
    sim_result = await db.execute(select(Simulation).where(Simulation.id == room.simulation_id))
    sim = sim_result.scalar_one_or_none()

    tables = _extract_tables_from_sim(sim) if sim else []
    if room.room_type == "role":
        participants = _extract_participants_by_role(tables, room.role_filter or "")
    else:
        participants = _extract_participants_by_table(tables, room.table_index or 0)

    # Extract what each participant said during the original deliberation
    debate_quotes = _extract_debate_quotes(
        tables, participants,
        room_type=room.room_type,
        role_filter=room.role_filter,
        table_index=room.table_index,
    )

    return {
        "id": str(room.id),
        "simulation_id": str(room.simulation_id),
        "room_type": room.room_type,
        "room_name": room.room_name,
        "role_filter": room.role_filter,
        "table_index": room.table_index,
        "participants": [
            {
                "id": str(p.get("id", "")),
                "name": p.get("name", ""),
                "title": p.get("title", ""),
                "industry": p.get("industry", ""),
                "role_in_committee": p.get("role_in_committee", ""),
                "voice": (room.voice_config or {}).get(str(p.get("id", "")), {}),
            }
            for p in participants
        ],
        "debate_quotes": debate_quotes,
        "conversation_history": [
            msg for msg in (room.conversation_history or [])
            if msg.get("role") != "system"
        ],
        "voice_config": room.voice_config,
        "created_at": room.created_at.isoformat() if room.created_at else None,
    }


# ──────────────────────────────────────────────
# WebSocket — Live Group Chat
# ──────────────────────────────────────────────


@router.websocket("/{room_id}/ws")
async def room_websocket(websocket: WebSocket, room_id: UUID):
    """
    WebSocket endpoint for real-time committee room chat.

    Client sends: {"type": "message", "content": "..."}
    Server sends:
      - {"type": "typing", "persona_name": "...", "persona_id": "..."}
      - {"type": "message", "persona_id": "...", "persona_name": "...",
         "persona_title": "...", "content": "...", "audio_base64": "..."}
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for room {room_id}")

    try:
        # Load room
        from database import async_session
        async with async_session() as db:
            result = await db.execute(select(CommitteeRoom).where(CommitteeRoom.id == room_id))
            room = result.scalar_one_or_none()
            if not room:
                await websocket.send_json({"type": "error", "content": "Room not found"})
                await websocket.close()
                return

            # Load simulation for pitch content
            sim_result = await db.execute(select(Simulation).where(Simulation.id == room.simulation_id))
            sim = sim_result.scalar_one_or_none()
            if not sim:
                await websocket.send_json({"type": "error", "content": "Simulation not found"})
                await websocket.close()
                return

            pitch_content = sim.pitch_content
            tables = _extract_tables_from_sim(sim)

            # Get participant details
            if room.room_type == "role":
                participants = _extract_participants_by_role(tables, room.role_filter or "")
            else:
                participants = _extract_participants_by_table(tables, room.table_index or 0)

            voice_config = room.voice_config or {}
            conversation_history = list(room.conversation_history or [])

        # Send room info to client
        await websocket.send_json({
            "type": "room_info",
            "room_name": room.room_name,
            "participants": [
                {
                    "id": str(p.get("id", "")),
                    "name": p.get("name", ""),
                    "title": p.get("title", ""),
                    "voice": voice_config.get(str(p.get("id", "")), {}),
                }
                for p in participants
            ],
        })

        # Chat loop
        while True:
            data = await websocket.receive_json()

            if data.get("type") != "message":
                continue

            user_content = data.get("content", "").strip()
            if not user_content:
                continue

            # Add user message to history
            user_msg = {
                "role": "user",
                "content": user_content,
                "timestamp": datetime.utcnow().isoformat(),
            }
            conversation_history.append(user_msg)

            # Generate persona responses
            room_context = f"Room type: {room.room_type}"
            if room.role_filter:
                room_context += f" — grouped by role: {room.role_filter}"

            responses = await generate_room_responses(
                user_message=user_content,
                participants=participants,
                conversation_history=conversation_history,
                pitch_content=pitch_content,
                room_context=room_context,
            )

            # Stream responses one at a time with typing indicators
            for resp in responses:
                # Send typing indicator
                await websocket.send_json({
                    "type": "typing",
                    "persona_id": resp["persona_id"],
                    "persona_name": resp["persona_name"],
                })

                # Small delay for natural feel
                await asyncio.sleep(0.5)

                # Generate voice audio if configured
                audio_b64 = None
                persona_voice = voice_config.get(resp["persona_id"], {})
                if persona_voice.get("voice_id"):
                    audio_b64 = await text_to_speech_base64(
                        text=resp["content"],
                        voice_id=persona_voice["voice_id"],
                    )

                # Send the message
                await websocket.send_json({
                    "type": "message",
                    "persona_id": resp["persona_id"],
                    "persona_name": resp["persona_name"],
                    "persona_title": resp.get("persona_title", ""),
                    "content": resp["content"],
                    "audio_base64": audio_b64,
                    "timestamp": resp["timestamp"],
                })

                # Add to history
                conversation_history.append({
                    "role": "assistant",
                    "persona_id": resp["persona_id"],
                    "persona_name": resp["persona_name"],
                    "content": resp["content"],
                    "timestamp": resp["timestamp"],
                })

                # Brief pause between personas
                await asyncio.sleep(0.3)

            # Persist conversation history periodically
            async with async_session() as db:
                result = await db.execute(select(CommitteeRoom).where(CommitteeRoom.id == room_id))
                room_record = result.scalar_one_or_none()
                if room_record:
                    room_record.conversation_history = conversation_history
                    room_record.last_message_at = datetime.utcnow()
                    await db.commit()

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for room {room_id}")
    except Exception as e:
        logger.error(f"WebSocket error in room {room_id}: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass
