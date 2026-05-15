"""
ElevenLabs Voice Service
========================
Assigns distinct voices to personas and generates TTS audio.
Uses ElevenLabs API for high-quality, natural-sounding speech.
"""

import base64
import logging
import httpx
from typing import Optional, Dict

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ──────────────────────────────────────────────
# Voice Pool — distinct ElevenLabs voices
# mapped to persona archetypes by gender/style
# ──────────────────────────────────────────────

VOICE_POOL = [
    {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "gender": "female", "style": "calm"},
    {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi", "gender": "female", "style": "assertive"},
    {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "gender": "female", "style": "warm"},
    {"id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli", "gender": "female", "style": "young"},
    {"id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh", "gender": "male", "style": "deep"},
    {"id": "VR6AewLTigWG4xSOukaG", "name": "Arnold", "gender": "male", "style": "authoritative"},
    {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "gender": "male", "style": "warm"},
    {"id": "yoZ06aMxZJJ28mfd3POQ", "name": "Sam", "gender": "male", "style": "professional"},
    {"id": "onwK4e9ZLuTAKqWW03F9", "name": "Daniel", "gender": "male", "style": "british"},
    {"id": "XB0fDUnXU5powFXDhCwa", "name": "Charlotte", "gender": "female", "style": "professional"},
]


def assign_voices(participant_personas: list) -> Dict[str, dict]:
    """
    Assign a unique ElevenLabs voice to each persona in a room.
    Tries to vary gender and style for distinctiveness.
    Returns {persona_id_str: {voice_id, voice_name, gender, style}}
    """
    assignments = {}
    pool = list(VOICE_POOL)  # copy so we can pop

    for i, persona in enumerate(participant_personas):
        voice = pool[i % len(pool)]
        assignments[str(persona["id"])] = {
            "voice_id": voice["id"],
            "voice_name": voice["name"],
            "gender": voice["gender"],
            "style": voice["style"],
        }

    return assignments


async def text_to_speech(
    text: str,
    voice_id: str,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.3,
) -> Optional[bytes]:
    """
    Generate speech audio from text using ElevenLabs API.
    Returns raw mp3 bytes, or None if the API key isn't configured.
    """
    if not settings.elevenlabs_api_key:
        logger.warning("ElevenLabs API key not configured — skipping TTS")
        return None

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": settings.elevenlabs_model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": True,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.content
    except httpx.HTTPStatusError as e:
        logger.error(f"ElevenLabs API error: {e.response.status_code} — {e.response.text[:200]}")
        return None
    except Exception as e:
        logger.error(f"ElevenLabs TTS failed: {e}")
        return None


async def text_to_speech_base64(
    text: str,
    voice_id: str,
    **kwargs,
) -> Optional[str]:
    """Generate TTS and return as base64-encoded mp3 string for WebSocket transport."""
    audio_bytes = await text_to_speech(text, voice_id, **kwargs)
    if audio_bytes:
        return base64.b64encode(audio_bytes).decode("utf-8")
    return None
