from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


# ---- Personas ----
class PersonaCreate(BaseModel):
    name: str
    title: str
    industry: str
    company_size: str
    personality_traits: Dict[str, float] = {}
    buying_style: str
    pain_points: List[str] = []
    objection_patterns: List[str] = []
    decision_process: Optional[str] = None
    budget_authority: Optional[str] = None
    success_criteria: Dict[str, Any] = {}
    bio: Optional[str] = None
    is_public: bool = True

class PersonaResponse(BaseModel):
    id: UUID
    name: str
    title: str
    industry: str
    company_size: str
    personality_traits: Dict[str, float]
    buying_style: str
    pain_points: List[str]
    objection_patterns: List[str]
    decision_process: Optional[str]
    budget_authority: Optional[str]
    bio: Optional[str]
    is_public: bool
    created_at: datetime

    class Config:
        from_attributes = True

class PersonaFilter(BaseModel):
    industries: Optional[List[str]] = None
    company_sizes: Optional[List[str]] = None
    buying_styles: Optional[List[str]] = None


# ---- Simulations ----
class SimulationCreate(BaseModel):
    pitch_title: str
    pitch_content: str
    company_name: Optional[str] = None
    industry: Optional[str] = None
    target_audience: Optional[str] = None
    num_personas: int = Field(default=10, ge=1, le=100)
    persona_filters: Optional[PersonaFilter] = None
    persona_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Optional: specific persona IDs to use in this simulation (ignores num_personas if provided)"
    )
    config: Dict[str, Any] = {}

class SimulationResponse(BaseModel):
    id: UUID
    pitch_title: str
    status: str
    progress_pct: int
    num_personas: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

class SimulationDetailResponse(SimulationResponse):
    pitch_content: str
    company_name: Optional[str]
    industry: Optional[str]
    target_audience: Optional[str]
    results: Optional[Dict[str, Any]] = None
    persona_responses: Optional[List[Dict[str, Any]]] = None

class SimulationResultResponse(BaseModel):
    overall_engagement_score: Optional[float]
    overall_sentiment_score: Optional[float]
    sentiment_breakdown: Optional[Dict[str, int]]
    key_objections: Optional[List[str]]
    objection_frequency: Optional[Dict[str, int]]
    key_recommendations: Optional[List[str]]
    strongest_segments: Optional[List[Dict[str, Any]]]
    weakest_segments: Optional[List[Dict[str, Any]]]
    engagement_by_industry: Optional[Dict[str, float]]

    class Config:
        from_attributes = True


# ---- Chat ----
class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    persona_name: str
    persona_title: str
    response: str
    sentiment: Optional[str] = None
    timestamp: datetime


# ---- Committee Rooms ----
class RoomCreate(BaseModel):
    simulation_id: UUID
    room_type: str = Field(description="'role' to group by title/role, 'table' to group by deliberation table")
    role_filter: Optional[str] = Field(default=None, description="Role keyword to filter, e.g. 'CTO', 'CEO', 'VP'")
    table_index: Optional[int] = Field(default=None, description="Table index (0-based) for table-based rooms")

class RoomResponse(BaseModel):
    id: UUID
    simulation_id: UUID
    room_type: str
    room_name: str
    role_filter: Optional[str]
    table_index: Optional[int]
    participant_count: int
    participants: List[Dict[str, Any]]
    created_at: datetime

class RoomMessageOut(BaseModel):
    type: str = "message"  # message | typing | error | voice
    persona_id: Optional[str] = None
    persona_name: Optional[str] = None
    persona_title: Optional[str] = None
    content: str = ""
    audio_base64: Optional[str] = None
    timestamp: Optional[str] = None
