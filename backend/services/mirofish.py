"""
MiroFish Integration Service
=============================
Wraps MiroFish's REST API to orchestrate swarm-based pitch simulations.

MiroFish Pipeline:
  1. Upload pitch as seed document → /api/graph/ontology/generate
  2. Build knowledge graph         → /api/graph/build
  3. Create simulation             → /api/simulation/create
  4. Prepare agent profiles        → /api/simulation/prepare
  5. Start swarm simulation        → /api/simulation/start
  6. Poll for completion           → /api/simulation/run-status
  7. Pull results                  → /api/simulation/details
  8. Generate report               → /api/report/generate
  9. Chat with agents              → /api/simulation/chat
"""

import asyncio
import logging
import tempfile
import os
from typing import Optional, Dict, Any, List
from enum import Enum

import httpx

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SimulationStatus(str, Enum):
    INITIALIZING = "initializing"
    GRAPH_BUILDING = "graph_building"
    PREPARING_AGENTS = "preparing_agents"
    RUNNING = "running"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"
    FAILED = "failed"


class MiroFishClient:
    """
    Async HTTP client for MiroFish's REST API.

    MiroFish runs as a separate service (default: http://localhost:5001).
    All simulation orchestration goes through this client.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 300.0):
        self.base_url = (base_url or settings.mirofish_api_url).rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout, connect=30.0),
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ──────────────────────────────────────────────
    # Health & Status
    # ──────────────────────────────────────────────

    async def health_check(self) -> bool:
        """Check if MiroFish service is reachable. Fast-fail with 2s timeout."""
        try:
            # Use a short-lived client with aggressive timeouts
            # so we don't block Railway's health check endpoint
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(2.0, connect=2.0),
            ) as quick_client:
                resp = await quick_client.get("/api/graph/data/test")
                # Any response (even 404) means the service is up
                return resp.status_code < 500
        except Exception as e:
            logger.debug(f"MiroFish not available: {e}")
            return False

    # ──────────────────────────────────────────────
    # Stage 1: Graph Construction
    # ──────────────────────────────────────────────

    async def generate_ontology(
        self,
        pitch_text: str,
        simulation_requirement: str,
        personas: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Upload a pitch as seed material and generate the knowledge graph ontology.

        We create a temporary file from the pitch text since MiroFish expects
        file uploads. The simulation_requirement tells MiroFish what to predict —
        we frame it as buyer reaction analysis.

        Args:
            pitch_text: The sales pitch content
            simulation_requirement: What we want MiroFish to predict/simulate
            personas: Optional buyer persona definitions to inject into the requirement

        Returns:
            Dict with projectId and taskId for tracking
        """
        # Build a rich simulation requirement that tells MiroFish
        # to simulate buyer reactions, not generic public opinion
        requirement = self._build_simulation_requirement(
            pitch_text, simulation_requirement, personas
        )

        # MiroFish expects multipart file upload
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, prefix="pitch_"
        ) as f:
            f.write(pitch_text)
            temp_path = f.name

        try:
            client = await self._get_client()
            with open(temp_path, "rb") as file_obj:
                resp = await client.post(
                    "/api/graph/ontology/generate",
                    data={"simulationRequirement": requirement},
                    files={"files": ("pitch.txt", file_obj, "text/plain")},
                    headers={},  # Let httpx set multipart headers
                )
            resp.raise_for_status()
            result = resp.json()
            logger.info(
                f"Ontology generation started: project={result.get('projectId')}, "
                f"task={result.get('taskId')}"
            )
            return result
        finally:
            os.unlink(temp_path)

    async def build_graph(self, project_id: str) -> Dict[str, Any]:
        """Trigger Zep knowledge graph ingestion for a project."""
        client = await self._get_client()
        resp = await client.post(
            "/api/graph/build",
            json={"projectId": project_id},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Poll an async task (graph build, agent prep, etc.)."""
        client = await self._get_client()
        resp = await client.get(f"/api/graph/task/{task_id}")
        resp.raise_for_status()
        return resp.json()

    async def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        """Retrieve the constructed knowledge graph (nodes + edges)."""
        client = await self._get_client()
        resp = await client.get(f"/api/graph/data/{graph_id}")
        resp.raise_for_status()
        return resp.json()

    # ──────────────────────────────────────────────
    # Stage 2: Simulation Setup
    # ──────────────────────────────────────────────

    async def create_simulation(
        self,
        project_id: str,
        num_agents: int = 50,
        num_rounds: int = 20,
        persona_seeds: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new simulation instance.

        Args:
            project_id: From the graph construction step
            num_agents: Number of AI agents to spawn (buyer personas)
            num_rounds: Simulation rounds (interactions between agents)
            persona_seeds: Optional buyer persona data to influence agent generation

        Returns:
            Dict with simulationId
        """
        payload = {
            "projectId": project_id,
            "numAgents": num_agents,
            "numRounds": num_rounds,
        }
        if persona_seeds:
            payload["personaSeeds"] = persona_seeds

        client = await self._get_client()
        resp = await client.post("/api/simulation/create", json=payload)
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"Simulation created: {result.get('simulationId')}")
        return result

    async def prepare_simulation(
        self, simulation_id: str, prep_type: str = "profiles"
    ) -> Dict[str, Any]:
        """
        Generate agent profiles and simulation config.

        Args:
            simulation_id: From create_simulation
            prep_type: 'profiles' to generate agent personas, 'config' for sim params
        """
        client = await self._get_client()
        resp = await client.post(
            "/api/simulation/prepare",
            json={"simulationId": simulation_id, "type": prep_type},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_preparation_status(self, simulation_id: str) -> Dict[str, Any]:
        """Poll agent/config preparation progress."""
        client = await self._get_client()
        resp = await client.get(
            "/api/simulation/task-status",
            params={"simulationId": simulation_id},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_env_status(self, simulation_id: str) -> Dict[str, Any]:
        """Validate simulation environment is ready to run."""
        client = await self._get_client()
        resp = await client.get(
            "/api/simulation/env-status",
            params={"simulationId": simulation_id},
        )
        resp.raise_for_status()
        return resp.json()

    # ──────────────────────────────────────────────
    # Stage 3: Run Simulation
    # ──────────────────────────────────────────────

    async def start_simulation(self, simulation_id: str) -> Dict[str, Any]:
        """Begin parallel agent execution (the actual swarm simulation)."""
        client = await self._get_client()
        resp = await client.post(
            "/api/simulation/start",
            json={"simulationId": simulation_id},
        )
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"Simulation started: {simulation_id}")
        return result

    async def get_run_status(self, simulation_id: str) -> Dict[str, Any]:
        """Poll simulation execution progress."""
        client = await self._get_client()
        resp = await client.get(
            "/api/simulation/run-status",
            params={"simulationId": simulation_id},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_simulation_details(self, simulation_id: str) -> Dict[str, Any]:
        """Fetch complete agent action logs after simulation completes."""
        client = await self._get_client()
        resp = await client.get(
            "/api/simulation/details",
            params={"simulationId": simulation_id},
        )
        resp.raise_for_status()
        return resp.json()

    # ──────────────────────────────────────────────
    # Stage 4: Report Generation
    # ──────────────────────────────────────────────

    async def generate_report(self, simulation_id: str) -> Dict[str, Any]:
        """Trigger MiroFish's ReportAgent to analyze simulation results."""
        client = await self._get_client()
        resp = await client.post(
            "/api/report/generate",
            json={"simulationId": simulation_id},
        )
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"Report generation started: {result.get('reportId')}")
        return result

    async def get_report_status(self, report_id: str) -> Dict[str, Any]:
        """Poll report generation progress."""
        client = await self._get_client()
        resp = await client.get(f"/api/report/generate/status/{report_id}")
        resp.raise_for_status()
        return resp.json()

    async def get_report_agent_log(self, report_id: str) -> Dict[str, Any]:
        """Fetch the ReportAgent's reasoning steps."""
        client = await self._get_client()
        resp = await client.get(f"/api/report/{report_id}/agent-log")
        resp.raise_for_status()
        return resp.json()

    # ──────────────────────────────────────────────
    # Stage 5: Agent Chat (Deep Interaction)
    # ──────────────────────────────────────────────

    async def chat_with_agent(
        self, simulation_id: str, agent_id: str, message: str
    ) -> Dict[str, Any]:
        """Chat with a specific simulated buyer agent post-simulation."""
        client = await self._get_client()
        resp = await client.get(
            "/api/simulation/chat",
            params={
                "simulationId": simulation_id,
                "agentId": agent_id,
                "message": message,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def chat_with_report(
        self, report_id: str, message: str
    ) -> Dict[str, Any]:
        """Chat with the ReportAgent for deeper analysis."""
        client = await self._get_client()
        resp = await client.post(
            "/api/report/chat",
            json={"reportId": report_id, "message": message},
        )
        resp.raise_for_status()
        return resp.json()

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────

    def _build_simulation_requirement(
        self,
        pitch_text: str,
        user_requirement: str,
        personas: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Build a simulation requirement that frames the MiroFish simulation
        as a buyer reaction analysis rather than generic public opinion.

        This is the key integration point — we tell MiroFish HOW to simulate
        by crafting a requirement that describes the buyer committee, their
        roles, concerns, and what we want to measure.
        """
        persona_context = ""
        if personas:
            persona_lines = []
            for p in personas:
                name = p.get("name", "Unknown")
                title = p.get("title", "")
                industry = p.get("industry", "")
                traits = ", ".join(p.get("traits", []))
                persona_lines.append(
                    f"- {name} ({title}, {industry}): Traits: {traits}"
                )
            persona_context = (
                "\n\nBuyer Committee Members:\n" + "\n".join(persona_lines)
            )

        requirement = f"""Simulate how a buying committee would react to this sales pitch.
This is a B2B sales simulation where AI agents represent potential buyers with
distinct roles, priorities, and concerns.

Prediction Goal: {user_requirement}

Instructions for Agent Behavior:
- Each agent should evaluate the pitch from their professional perspective
- Agents should discuss among themselves (post, comment, reply) about:
  * Whether the pitch addresses their specific pain points
  * Objections they would raise in a real buying decision
  * How compelling the value proposition is for their role
  * Whether they would champion or block the purchase
  * Price sensitivity and ROI concerns relevant to their position
- Track sentiment evolution: initial reaction → discussion → final position
- Agents should represent realistic buyer dynamics:
  * Champions who see value and advocate internally
  * Skeptics who raise legitimate concerns
  * Blockers who have competing priorities or vendor preferences
  * Decision-makers who weigh the overall business case
{persona_context}

Measure:
1. Overall buying committee sentiment (positive/negative/neutral)
2. Key objections raised across the committee
3. Which roles are most/least receptive
4. Deal-breaker concerns that would kill the deal
5. Suggestions for improving the pitch
6. Predicted likelihood of advancing to next sales stage"""

        return requirement


# ──────────────────────────────────────────────
# High-Level Orchestration
# ──────────────────────────────────────────────


class MiroFishOrchestrator:
    """
    Orchestrates the full MiroFish simulation pipeline for PitchSimAI.

    This is the main entry point that the simulation router calls.
    It manages the entire lifecycle: graph → agents → simulation → report.
    """

    def __init__(self, client: Optional[MiroFishClient] = None):
        self.client = client or MiroFishClient()

    async def run_pitch_simulation(
        self,
        pitch_text: str,
        prediction_goal: str = "Predict buying committee reaction and deal outcome",
        personas: Optional[List[Dict[str, Any]]] = None,
        num_agents: int = 50,
        num_rounds: int = 20,
        poll_interval: float = 3.0,
        status_callback=None,
    ) -> Dict[str, Any]:
        """
        Run a complete pitch simulation through MiroFish.

        Args:
            pitch_text: The sales pitch to test
            prediction_goal: What to predict (default: buyer reaction)
            personas: Buyer persona definitions from our committee generator
            num_agents: Number of simulated buyers
            num_rounds: Simulation rounds (more = deeper interaction)
            poll_interval: Seconds between status polls
            status_callback: Optional async callable(status, detail) for progress updates

        Returns:
            Complete simulation results including agent logs, report, and scores
        """
        async def _update(status: SimulationStatus, detail: str = ""):
            logger.info(f"Simulation status: {status.value} - {detail}")
            if status_callback:
                await status_callback(status.value, detail)

        try:
            # ── Stage 1: Build Knowledge Graph ──
            await _update(SimulationStatus.GRAPH_BUILDING, "Uploading pitch and generating ontology...")

            ontology_result = await self.client.generate_ontology(
                pitch_text=pitch_text,
                simulation_requirement=prediction_goal,
                personas=personas,
            )
            project_id = ontology_result.get("projectId")
            task_id = ontology_result.get("taskId")

            # Poll until ontology is ready
            await self._poll_task(task_id, poll_interval)

            await _update(SimulationStatus.GRAPH_BUILDING, "Building knowledge graph...")
            graph_result = await self.client.build_graph(project_id)
            graph_task_id = graph_result.get("taskId")
            if graph_task_id:
                await self._poll_task(graph_task_id, poll_interval)

            # ── Stage 2: Create & Prepare Simulation ──
            await _update(SimulationStatus.PREPARING_AGENTS, "Creating simulation and generating agent profiles...")

            sim_result = await self.client.create_simulation(
                project_id=project_id,
                num_agents=num_agents,
                num_rounds=num_rounds,
                persona_seeds=self._convert_personas_to_seeds(personas),
            )
            simulation_id = sim_result.get("simulationId")

            # Generate agent profiles
            await self.client.prepare_simulation(simulation_id, "profiles")
            await self._poll_preparation(simulation_id, poll_interval)

            # Generate simulation config
            await self.client.prepare_simulation(simulation_id, "config")
            await self._poll_preparation(simulation_id, poll_interval)

            # Validate environment
            env_status = await self.client.get_env_status(simulation_id)
            if not env_status.get("ready", False):
                logger.warning(f"Environment not fully ready: {env_status}")

            # ── Stage 3: Run Swarm Simulation ──
            await _update(SimulationStatus.RUNNING, f"Running swarm simulation with {num_agents} agents for {num_rounds} rounds...")

            await self.client.start_simulation(simulation_id)
            await self._poll_simulation_run(simulation_id, poll_interval, _update)

            # Pull detailed results
            details = await self.client.get_simulation_details(simulation_id)

            # ── Stage 4: Generate Report ──
            await _update(SimulationStatus.GENERATING_REPORT, "Analyzing results with ReportAgent...")

            report_result = await self.client.generate_report(simulation_id)
            report_id = report_result.get("reportId")
            await self._poll_report(report_id, poll_interval)

            report_log = await self.client.get_report_agent_log(report_id)

            # ── Stage 5: Package Results ──
            await _update(SimulationStatus.COMPLETED, "Simulation complete!")

            return {
                "project_id": project_id,
                "simulation_id": simulation_id,
                "report_id": report_id,
                "num_agents": num_agents,
                "num_rounds": num_rounds,
                "agent_actions": details,
                "report": report_log,
                "scores": self._extract_scores(details, report_log),
                "status": SimulationStatus.COMPLETED.value,
            }

        except Exception as e:
            logger.error(f"MiroFish simulation failed: {e}", exc_info=True)
            await _update(SimulationStatus.FAILED, str(e))
            return {
                "status": SimulationStatus.FAILED.value,
                "error": str(e),
            }

    async def chat_with_buyer(
        self, simulation_id: str, agent_id: str, message: str
    ) -> Dict[str, Any]:
        """Chat with a specific simulated buyer after the simulation."""
        return await self.client.chat_with_agent(simulation_id, agent_id, message)

    async def chat_with_analyst(
        self, report_id: str, message: str
    ) -> Dict[str, Any]:
        """Chat with the ReportAgent for deeper deal analysis."""
        return await self.client.chat_with_report(report_id, message)

    # ──────────────────────────────────────────────
    # Polling Helpers
    # ──────────────────────────────────────────────

    async def _poll_task(self, task_id: str, interval: float, max_wait: float = 600):
        """Poll a generic async task until completion."""
        elapsed = 0.0
        while elapsed < max_wait:
            status = await self.client.get_task_status(task_id)
            state = status.get("status", "").lower()
            if state in ("completed", "done", "success"):
                return status
            if state in ("failed", "error"):
                raise RuntimeError(f"Task {task_id} failed: {status}")
            await asyncio.sleep(interval)
            elapsed += interval
        raise TimeoutError(f"Task {task_id} timed out after {max_wait}s")

    async def _poll_preparation(self, sim_id: str, interval: float, max_wait: float = 300):
        """Poll simulation preparation status."""
        elapsed = 0.0
        while elapsed < max_wait:
            status = await self.client.get_preparation_status(sim_id)
            state = status.get("status", "").lower()
            if state in ("completed", "done", "ready"):
                return status
            if state in ("failed", "error"):
                raise RuntimeError(f"Preparation failed: {status}")
            await asyncio.sleep(interval)
            elapsed += interval
        raise TimeoutError(f"Agent preparation timed out after {max_wait}s")

    async def _poll_simulation_run(self, sim_id: str, interval: float, update_fn=None, max_wait: float = 1800):
        """Poll simulation execution with progress updates."""
        elapsed = 0.0
        while elapsed < max_wait:
            status = await self.client.get_run_status(sim_id)
            state = status.get("status", "").lower()
            progress = status.get("progress", "")

            if update_fn and progress:
                await update_fn(SimulationStatus.RUNNING, f"Progress: {progress}")

            if state in ("completed", "done", "finished"):
                return status
            if state in ("failed", "error"):
                raise RuntimeError(f"Simulation run failed: {status}")

            await asyncio.sleep(interval)
            elapsed += interval
        raise TimeoutError(f"Simulation run timed out after {max_wait}s")

    async def _poll_report(self, report_id: str, interval: float, max_wait: float = 600):
        """Poll report generation status."""
        elapsed = 0.0
        while elapsed < max_wait:
            status = await self.client.get_report_status(report_id)
            state = status.get("status", "").lower()
            if state in ("completed", "done"):
                return status
            if state in ("failed", "error"):
                raise RuntimeError(f"Report generation failed: {status}")
            await asyncio.sleep(interval)
            elapsed += interval
        raise TimeoutError(f"Report generation timed out after {max_wait}s")

    # ──────────────────────────────────────────────
    # Data Conversion
    # ──────────────────────────────────────────────

    def _convert_personas_to_seeds(
        self, personas: Optional[List[Dict[str, Any]]]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Convert PitchSimAI personas into MiroFish agent seeds.

        MiroFish will use these as hints when generating agent profiles,
        ensuring the simulated agents match our buyer committee roles.
        """
        if not personas:
            return None

        seeds = []
        for p in personas:
            seed = {
                "name": p.get("name", "Buyer"),
                "bio": (
                    f"{p.get('title', 'Professional')} in the {p.get('industry', 'technology')} "
                    f"industry. {p.get('background', '')} "
                    f"Key concerns: {', '.join(p.get('pain_points', []))}. "
                    f"Communication style: {p.get('communication_style', 'professional')}."
                ),
                "interests": p.get("pain_points", []) + p.get("priorities", []),
                "personality_traits": p.get("traits", []),
            }
            seeds.append(seed)
        return seeds

    def _extract_scores(
        self, details: Dict[str, Any], report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract pitch simulation scores from MiroFish results.

        Maps MiroFish's social simulation metrics to sales-relevant scores:
        - Engagement score: How much agents discussed the pitch
        - Sentiment score: Overall positive/negative reaction
        - Objection count: Number of negative/blocking reactions
        - Champion count: Number of agents who advocated for the pitch
        - Deal probability: Estimated chance of advancing
        """
        # Parse agent actions to compute scores
        actions = details.get("actions", details.get("data", []))
        if not actions:
            return self._default_scores()

        total_actions = len(actions)
        positive_actions = 0
        negative_actions = 0
        neutral_actions = 0
        objections = []
        champions = set()

        for action in actions:
            sentiment = action.get("sentiment", "neutral").lower()
            action_type = action.get("action_type", action.get("type", ""))

            if sentiment in ("positive", "supportive"):
                positive_actions += 1
                if action_type in ("REPOST", "LIKE", "QUOTE"):
                    champions.add(action.get("agent_id", ""))
            elif sentiment in ("negative", "critical", "opposed"):
                negative_actions += 1
                content = action.get("content", "")
                if content:
                    objections.append(content)
            else:
                neutral_actions += 1

        # Calculate scores
        engagement = min(100, int((total_actions / max(1, len(set(
            a.get("agent_id", "") for a in actions
        )))) * 10))

        sentiment_ratio = (
            positive_actions / max(1, total_actions)
        ) * 100

        deal_probability = min(100, int(
            (sentiment_ratio * 0.4)
            + (len(champions) / max(1, total_actions) * 100 * 0.3)
            + (engagement * 0.3)
        ))

        return {
            "engagement_score": engagement,
            "sentiment_score": round(sentiment_ratio, 1),
            "objection_count": negative_actions,
            "champion_count": len(champions),
            "deal_probability": deal_probability,
            "total_interactions": total_actions,
            "top_objections": objections[:5],
        }

    def _default_scores(self) -> Dict[str, Any]:
        return {
            "engagement_score": 0,
            "sentiment_score": 0,
            "objection_count": 0,
            "champion_count": 0,
            "deal_probability": 0,
            "total_interactions": 0,
            "top_objections": [],
        }


# ──────────────────────────────────────────────
# Singleton Access
# ──────────────────────────────────────────────

_client: Optional[MiroFishClient] = None
_orchestrator: Optional[MiroFishOrchestrator] = None


def get_mirofish_client() -> MiroFishClient:
    global _client
    if _client is None:
        _client = MiroFishClient()
    return _client


def get_mirofish_orchestrator() -> MiroFishOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MiroFishOrchestrator(get_mirofish_client())
    return _orchestrator
