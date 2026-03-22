from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User, Simulation, PersonaConversation, PersonaResponse as PersonaResponseModel, Persona
from schemas import ChatMessage, ChatResponse
from auth import get_current_user
from services.simulation import generate_persona_chat_response

router = APIRouter()


@router.post("/{simulation_id}/{persona_id}")
async def chat_with_persona(
    simulation_id: UUID,
    persona_id: UUID,
    message: ChatMessage,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify simulation ownership and completion
    sim_result = await db.execute(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.user_id == current_user.id,
            Simulation.status == "completed"
        )
    )
    sim = sim_result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Completed simulation not found")

    # Get persona
    persona_result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = persona_result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    # Get or create conversation
    conv_result = await db.execute(
        select(PersonaConversation).where(
            PersonaConversation.simulation_id == simulation_id,
            PersonaConversation.persona_id == persona_id,
        )
    )
    conversation = conv_result.scalar_one_or_none()

    if not conversation:
        # Get persona's initial response from simulation
        pr_result = await db.execute(
            select(PersonaResponseModel).where(
                PersonaResponseModel.simulation_id == simulation_id,
                PersonaResponseModel.persona_id == persona_id,
            )
        )
        persona_response = pr_result.scalar_one_or_none()

        initial_context = persona_response.initial_reaction if persona_response else ""

        conversation = PersonaConversation(
            simulation_id=simulation_id,
            persona_id=persona_id,
            conversation_history=[
                {"role": "system", "content": f"Initial reaction to pitch: {initial_context}"}
            ],
        )
        db.add(conversation)

    # Add user message
    history = conversation.conversation_history or []
    history.append({
        "role": "user",
        "content": message.message,
        "timestamp": datetime.utcnow().isoformat()
    })

    # Generate response
    ai_response = await generate_persona_chat_response(
        persona=persona,
        pitch_content=sim.pitch_content,
        conversation_history=history,
    )

    history.append({
        "role": "assistant",
        "content": ai_response,
        "timestamp": datetime.utcnow().isoformat()
    })

    conversation.conversation_history = history
    conversation.last_message_at = datetime.utcnow()

    await db.commit()

    return {
        "persona_name": persona.name,
        "persona_title": persona.title,
        "response": ai_response,
        "timestamp": datetime.utcnow(),
    }


@router.get("/{simulation_id}/{persona_id}/history")
async def get_chat_history(
    simulation_id: UUID,
    persona_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify ownership
    sim_result = await db.execute(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.user_id == current_user.id,
        )
    )
    if not sim_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Simulation not found")

    conv_result = await db.execute(
        select(PersonaConversation).where(
            PersonaConversation.simulation_id == simulation_id,
            PersonaConversation.persona_id == persona_id,
        )
    )
    conversation = conv_result.scalar_one_or_none()

    if not conversation:
        return {"messages": []}

    return {
        "messages": [
            msg for msg in (conversation.conversation_history or [])
            if msg.get("role") != "system"
        ]
    }
