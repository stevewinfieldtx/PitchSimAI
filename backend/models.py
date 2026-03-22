import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255))
    organization_name = Column(String(255))
    subscription_tier = Column(String(50), default="free")
    subscription_status = Column(String(50), default="active")
    simulations_remaining = Column(Integer, default=5)
    api_key = Column(String(500), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    simulations = relationship("Simulation", back_populates="user")
    personas = relationship("Persona", back_populates="created_by_user")


class Persona(Base):
    __tablename__ = "personas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    industry = Column(String(100), nullable=False, index=True)
    company_size = Column(String(50), nullable=False)
    personality_traits = Column(JSON, nullable=False, default={})
    buying_style = Column(String(100), nullable=False)
    pain_points = Column(ARRAY(Text), default=[])
    objection_patterns = Column(ARRAY(Text), default=[])
    decision_process = Column(String(255))
    budget_authority = Column(String(100))
    success_criteria = Column(JSON, default={})
    bio = Column(Text)
    avatar_url = Column(String(500))
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    created_by_user = relationship("User", back_populates="personas")
    responses = relationship("PersonaResponse", back_populates="persona")


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    pitch_title = Column(String(500), nullable=False)
    pitch_content = Column(Text, nullable=False)
    company_name = Column(String(255))
    industry = Column(String(100))
    target_audience = Column(String(500))
    num_personas = Column(Integer, default=10)
    status = Column(String(50), default="pending", index=True)
    progress_pct = Column(Integer, default=0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    config = Column(JSON, default={})

    user = relationship("User", back_populates="simulations")
    results = relationship("SimulationResult", back_populates="simulation", uselist=False)
    persona_responses = relationship("PersonaResponse", back_populates="simulation")
    conversations = relationship("PersonaConversation", back_populates="simulation")


class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id", ondelete="CASCADE"), unique=True, nullable=False)
    overall_engagement_score = Column(Float)
    overall_sentiment_score = Column(Float)
    sentiment_breakdown = Column(JSON)
    key_objections = Column(ARRAY(Text))
    objection_frequency = Column(JSON)
    key_recommendations = Column(ARRAY(Text))
    strongest_segments = Column(JSON)
    weakest_segments = Column(JSON)
    engagement_by_industry = Column(JSON)
    next_steps_suggested = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    simulation = relationship("Simulation", back_populates="results")


class PersonaResponse(Base):
    __tablename__ = "persona_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    initial_reaction = Column(Text)
    sentiment = Column(String(50))
    engagement_score = Column(Float)
    questions_raised = Column(ARRAY(Text))
    objections = Column(ARRAY(Text))
    objection_categories = Column(ARRAY(String(100)))
    buying_confidence_shift = Column(Float)
    likely_decision = Column(String(50))
    internal_monologue = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    simulation = relationship("Simulation", back_populates="persona_responses")
    persona = relationship("Persona", back_populates="responses")


class PersonaConversation(Base):
    __tablename__ = "persona_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    conversation_history = Column(JSON, default=[])
    last_message_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    simulation = relationship("Simulation", back_populates="conversations")
    persona = relationship("Persona")
