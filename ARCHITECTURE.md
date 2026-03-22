# PitchSimAI Architecture — MiroFish Integration

## Overview

PitchSimAI is an AI-powered sales pitch simulation platform that uses **MiroFish** (an open-source swarm intelligence engine) as its core simulation backend. Users paste a sales pitch, configure a buying committee, and MiroFish spawns thousands of autonomous AI buyer agents that interact with each other in a realistic social simulation — producing engagement scores, sentiment analysis, objections, and actionable recommendations.

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    PitchSimAI Frontend                    │
│              React 18 + Vite + Tailwind CSS              │
│                    (Port 3000)                            │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────────────┐
│                   PitchSimAI Backend                      │
│                FastAPI + SQLAlchemy                        │
│                    (Port 8000)                             │
│                                                           │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  Simulation  │  │   Buying     │  │   LinkedIn     │  │
│  │   Router     │  │  Committee   │  │  Enrichment    │  │
│  └──────┬───┬──┘  │  Generator   │  │   Service      │  │
│         │   │     └──────────────┘  └────────────────┘  │
│         │   │                                            │
│  ┌──────▼───▼─────────────────────────────────────────┐  │
│  │           MiroFish Service Layer                    │  │
│  │  MiroFishClient → MiroFishOrchestrator             │  │
│  │  (backend/services/mirofish.py)                    │  │
│  └──────────────────┬─────────────────────────────────┘  │
│                     │                                     │
│  ┌──────────────────▼─────────────────────────────────┐  │
│  │         Model Pool (Fallback Engine)                │  │
│  │  Direct LLM calls via OpenRouter if MiroFish       │  │
│  │  is unavailable (backend/services/model_pool.py)   │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────┬───────────────────────────────────┘
                       │ REST API (port 5001)
┌──────────────────────▼──────────────────────────────────┐
│                    MiroFish Engine                        │
│          Swarm Intelligence Simulation                    │
│              Flask + OASIS + Zep Cloud                    │
│                    (Port 5001)                            │
│                                                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │
│  │  Graph     │  │ Simulation │  │  Report Agent      │ │
│  │  Builder   │  │  Runner    │  │  (ReACT reasoning) │ │
│  └────────────┘  └────────────┘  └────────────────────┘ │
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │  OASIS Engine (CAMEL-AI) — Up to 1M Agents        │  │
│  │  23 social actions · Long-term memory · GraphRAG   │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Simulation Pipeline

### MiroFish Flow (Primary)

1. **Pitch Upload** → User pastes pitch text in the frontend
2. **Ontology Generation** → `POST /api/graph/ontology/generate` — MiroFish extracts entities from the pitch
3. **Graph Construction** → `POST /api/graph/build` — Builds a knowledge graph via Zep Cloud
4. **Simulation Creation** → `POST /api/simulation/create` — Creates sim with buyer persona seeds
5. **Agent Preparation** → `POST /api/simulation/prepare` — Generates agent profiles with buyer personas
6. **Swarm Execution** → `POST /api/simulation/start` — Agents interact across simulated platforms
7. **Report Generation** → `POST /api/report/generate` — ReportAgent analyzes all interactions
8. **Deep Interaction** → `GET /api/simulation/chat` — Chat with any simulated buyer

### Fallback Flow (Model Pool)

If MiroFish is unavailable, simulations fall back to direct LLM calls via OpenRouter:
- Each persona gets an individual LLM prompt
- Multi-model pool distributes calls across configured models
- Premium tier for C-suite, volume tier for bulk
- Results are still scored and aggregated

## Key Integration Points

### MiroFish Service Layer (`backend/services/mirofish.py`)

- **MiroFishClient** — Async HTTP client wrapping all MiroFish REST endpoints
- **MiroFishOrchestrator** — Manages the full 5-stage pipeline with polling and progress callbacks
- **Simulation Requirement Builder** — Translates PitchSimAI buyer personas into MiroFish agent seeds
- **Score Extractor** — Maps MiroFish social metrics to sales-relevant scores

### How Buyer Personas Become MiroFish Agents

PitchSimAI's Buying Committee Generator creates persona definitions (title, industry, traits, pain points). These are passed to MiroFish as "agent seeds" that influence how MiroFish generates its autonomous agents. The simulation requirement prompt frames the entire simulation as a B2B buying decision, so agents behave as buyers evaluating a pitch — not generic social media users.

## Services

| Service | Port | Purpose |
|---------|------|---------|
| Frontend | 3000 | React SPA |
| Backend | 8000 | FastAPI orchestration layer |
| MiroFish | 5001 | Swarm simulation engine |
| PostgreSQL | 5432 | Simulation data, personas, results |
| Redis | 6379 | Task queue (Celery) |

## Configuration

### Backend Environment Variables

| Variable | Description |
|----------|-------------|
| `MIROFISH_API_URL` | MiroFish service URL (default: `http://mirofish:5001`) |
| `MIROFISH_NUM_AGENTS` | Default agents per simulation (default: 50) |
| `MIROFISH_NUM_ROUNDS` | Default interaction rounds (default: 20) |
| `OPENROUTER_API_KEY` | LLM API key (shared with MiroFish) |
| `OPENROUTER_BASE_URL` | LLM endpoint (shared with MiroFish) |
| `OPENROUTER_MODEL*_ID` | Multi-model pool configuration |
| `ZEP_API_KEY` | Zep Cloud key for MiroFish memory layer |

### MiroFish Environment Variables (passed via Docker)

| Variable | Description |
|----------|-------------|
| `LLM_API_KEY` | Mapped from `OPENROUTER_API_KEY` |
| `LLM_BASE_URL` | Mapped from `OPENROUTER_BASE_URL` |
| `LLM_MODEL_NAME` | Mapped from `OPENROUTER_DEFAULT_MODEL` |
| `ZEP_API_KEY` | Zep Cloud for GraphRAG memory |

## Deployment

### Docker Compose (Local)

```bash
cp .env.example .env
# Fill in OPENROUTER_API_KEY and optionally ZEP_API_KEY
docker compose up -d
```

### Railway (Production)

- **Backend** → Dockerfile at `backend/Dockerfile`
- **Frontend** → Dockerfile at `frontend/Dockerfile`
- **MiroFish** → Dockerfile at `mirofish/Dockerfile`
- **PostgreSQL** → Railway managed service
- **Redis** → Railway managed service

## Monetization Paths

1. **SaaS** — Subscription tiers based on simulation volume (agents × rounds)
2. **API/Skill** — OpenClaw integration for other AI tools to call PitchSimAI
3. **Enterprise** — Self-hosted MiroFish with custom persona libraries
4. **Persona Library** — Curated, validated buyer persona databases by industry

## Tech Stack

- **Frontend**: React 18, Vite, Tailwind CSS, Recharts, Lucide React
- **Backend**: FastAPI, SQLAlchemy, asyncpg, httpx, Pydantic
- **Simulation Engine**: MiroFish (OASIS + Zep Cloud + GraphRAG)
- **LLM Gateway**: OpenRouter (multi-model pool)
- **Database**: PostgreSQL 16
- **Queue**: Redis + Celery
- **Deployment**: Docker, Railway
