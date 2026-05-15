"""Initial schema with all tables including committee_rooms

Revision ID: 001_initial
Revises:
Create Date: 2026-05-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('organization_name', sa.String(255)),
        sa.Column('subscription_tier', sa.String(50), server_default='free'),
        sa.Column('subscription_status', sa.String(50), server_default='active'),
        sa.Column('simulations_remaining', sa.Integer, server_default='5'),
        sa.Column('api_key', sa.String(500), unique=True),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
    )

    # Personas
    op.create_table(
        'personas',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('industry', sa.String(100), nullable=False, index=True),
        sa.Column('company_size', sa.String(50), nullable=False),
        sa.Column('personality_traits', sa.JSON, nullable=False, server_default='{}'),
        sa.Column('buying_style', sa.String(100), nullable=False),
        sa.Column('pain_points', postgresql.ARRAY(sa.Text), server_default='{}'),
        sa.Column('objection_patterns', postgresql.ARRAY(sa.Text), server_default='{}'),
        sa.Column('decision_process', sa.String(255)),
        sa.Column('budget_authority', sa.String(100)),
        sa.Column('success_criteria', sa.JSON, server_default='{}'),
        sa.Column('bio', sa.Text),
        sa.Column('avatar_url', sa.String(500)),
        sa.Column('is_public', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
    )

    # Simulations
    op.create_table(
        'simulations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('pitch_title', sa.String(500), nullable=False),
        sa.Column('pitch_content', sa.Text, nullable=False),
        sa.Column('company_name', sa.String(255)),
        sa.Column('industry', sa.String(100)),
        sa.Column('target_audience', sa.String(500)),
        sa.Column('num_personas', sa.Integer, server_default='10'),
        sa.Column('status', sa.String(50), server_default='pending', index=True),
        sa.Column('progress_pct', sa.Integer, server_default='0'),
        sa.Column('started_at', sa.DateTime),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
        sa.Column('config', sa.JSON, server_default='{}'),
    )

    # Simulation Results
    op.create_table(
        'simulation_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('simulation_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('simulations.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('overall_engagement_score', sa.Float),
        sa.Column('overall_sentiment_score', sa.Float),
        sa.Column('sentiment_breakdown', sa.JSON),
        sa.Column('key_objections', postgresql.ARRAY(sa.Text)),
        sa.Column('objection_frequency', sa.JSON),
        sa.Column('key_recommendations', postgresql.ARRAY(sa.Text)),
        sa.Column('strongest_segments', sa.JSON),
        sa.Column('weakest_segments', sa.JSON),
        sa.Column('engagement_by_industry', sa.JSON),
        sa.Column('next_steps_suggested', sa.Text),
        sa.Column('created_at', sa.DateTime),
    )

    # Persona Responses
    op.create_table(
        'persona_responses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('simulation_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('simulations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('persona_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('personas.id'), nullable=False),
        sa.Column('initial_reaction', sa.Text),
        sa.Column('sentiment', sa.String(50)),
        sa.Column('engagement_score', sa.Float),
        sa.Column('questions_raised', postgresql.ARRAY(sa.Text)),
        sa.Column('objections', postgresql.ARRAY(sa.Text)),
        sa.Column('objection_categories', postgresql.ARRAY(sa.String(100))),
        sa.Column('buying_confidence_shift', sa.Float),
        sa.Column('likely_decision', sa.String(50)),
        sa.Column('internal_monologue', sa.Text),
        sa.Column('created_at', sa.DateTime),
    )

    # Persona Conversations
    op.create_table(
        'persona_conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('simulation_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('simulations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('persona_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('personas.id'), nullable=False),
        sa.Column('conversation_history', sa.JSON, server_default='[]'),
        sa.Column('last_message_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime),
    )

    # Committee Rooms
    op.create_table(
        'committee_rooms',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('simulation_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('simulations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('room_type', sa.String(50), nullable=False),
        sa.Column('role_filter', sa.String(255), nullable=True),
        sa.Column('table_index', sa.Integer, nullable=True),
        sa.Column('room_name', sa.String(500), nullable=False),
        sa.Column('participant_ids', sa.JSON, server_default='[]'),
        sa.Column('conversation_history', sa.JSON, server_default='[]'),
        sa.Column('voice_config', sa.JSON, server_default='{}'),
        sa.Column('last_message_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime),
    )


def downgrade() -> None:
    op.drop_table('committee_rooms')
    op.drop_table('persona_conversations')
    op.drop_table('persona_responses')
    op.drop_table('simulation_results')
    op.drop_table('simulations')
    op.drop_table('personas')
    op.drop_table('users')
