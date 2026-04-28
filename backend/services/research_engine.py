"""
Pre-Simulation Research Engine
===============================
Inspired by MiroThinker's deep research tool stack (Serper + Jina + LLM summary),
adapted for PitchSimAI's sales simulation context.

WHAT IT DOES:
  Before the swarm engine runs its buying committee deliberation, this module
  performs automated web research on the target company/industry and produces
  a structured "Company Intel Brief" that gets injected into every persona's
  system prompt. This transforms generic buyer personas into context-aware
  evaluators who debate with real-world knowledge.

TOOL STACK (borrowed from MiroThinker):
  1. Serper API — Google search for company news, competitors, challenges
  2. Jina Reader API — Clean web page scraping and text extraction
  3. OpenRouter LLM — Synthesize raw research into structured intel brief

COST:
  - Serper: ~$0.001 per search (1,000 free credits on signup)
  - Jina: Free tier available, ~$0.001 per page
  - LLM summary: One OpenRouter call (~$0.002-0.01 depending on model)
  - Total per simulation: ~$0.01-0.03

USAGE:
  research = await research_engine.research_target(
      company_name="Acme Corp",
      industry="Financial Services — Banking",
      target_audience="VP of Operations",
      pitch_content="Our platform helps..."
  )
  # research.context_block → inject into persona system prompts
  # research.enriched_pain_points → override generic pain points
"""

import json
import asyncio
import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Data Structures
# ──────────────────────────────────────────────


@dataclass
class ResearchResult:
    """Structured output from pre-simulation research."""

    company_name: str
    industry: str

    # Raw search results (for debugging/transparency)
    search_hits: List[Dict[str, str]] = field(default_factory=list)
    scraped_pages: List[Dict[str, str]] = field(default_factory=list)

    # Synthesized intel
    company_overview: str = ""
    recent_news: List[str] = field(default_factory=list)
    known_challenges: List[str] = field(default_factory=list)
    competitive_landscape: str = ""
    industry_trends: List[str] = field(default_factory=list)
    enriched_pain_points: List[str] = field(default_factory=list)
    key_stakeholder_concerns: Dict[str, List[str]] = field(default_factory=dict)

    # Metadata
    research_elapsed_seconds: float = 0.0
    sources_used: int = 0
    research_quality: str = "none"  # none, basic, good, deep

    @property
    def context_block(self) -> str:
        """
        Formatted context block ready to inject into persona system prompts.
        This is the key output — it transforms generic personas into
        context-aware evaluators.
        """
        if self.research_quality == "none":
            return ""

        sections = []

        if self.company_overview:
            sections.append(f"COMPANY INTELLIGENCE:\n{self.company_overview}")

        if self.recent_news:
            news_str = "\n".join(f"  - {n}" for n in self.recent_news[:5])
            sections.append(f"RECENT NEWS & DEVELOPMENTS:\n{news_str}")

        if self.known_challenges:
            challenges_str = "\n".join(f"  - {c}" for c in self.known_challenges[:5])
            sections.append(f"KNOWN CHALLENGES & PAIN POINTS:\n{challenges_str}")

        if self.competitive_landscape:
            sections.append(f"COMPETITIVE CONTEXT:\n{self.competitive_landscape}")

        if self.industry_trends:
            trends_str = "\n".join(f"  - {t}" for t in self.industry_trends[:4])
            sections.append(f"INDUSTRY TRENDS:\n{trends_str}")

        return "\n\n".join(sections)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company_name": self.company_name,
            "industry": self.industry,
            "company_overview": self.company_overview,
            "recent_news": self.recent_news,
            "known_challenges": self.known_challenges,
            "competitive_landscape": self.competitive_landscape,
            "industry_trends": self.industry_trends,
            "enriched_pain_points": self.enriched_pain_points,
            "key_stakeholder_concerns": self.key_stakeholder_concerns,
            "research_elapsed_seconds": self.research_elapsed_seconds,
            "sources_used": self.sources_used,
            "research_quality": self.research_quality,
        }


# ──────────────────────────────────────────────
# Serper Search (Google via API)
# ──────────────────────────────────────────────


async def _serper_search(query: str, num_results: int = 8) -> List[Dict[str, str]]:
    """
    Search Google via Serper API.
    Returns list of {title, link, snippet} dicts.
    """
    if not settings.serper_api_key:
        logger.warning("SERPER_API_KEY not configured — skipping web search")
        return []

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{settings.serper_base_url}/search",
                headers={
                    "X-API-KEY": settings.serper_api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "q": query,
                    "num": num_results,
                },
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("organic", []):
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                })
            return results

    except Exception as e:
        logger.error(f"Serper search failed for '{query}': {e}")
        return []


# ──────────────────────────────────────────────
# Jina Reader (Web Scraping)
# ──────────────────────────────────────────────


async def _jina_scrape(url: str, max_chars: int = 5000) -> str:
    """
    Scrape a web page using Jina Reader API.
    Returns clean text content, truncated to max_chars.
    """
    if not settings.jina_api_key:
        logger.warning("JINA_API_KEY not configured — skipping page scrape")
        return ""

    try:
        jina_url = f"{settings.jina_base_url}/{url}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                jina_url,
                headers={
                    "Authorization": f"Bearer {settings.jina_api_key}",
                    "Accept": "text/plain",
                    "X-Return-Format": "text",
                },
            )
            response.raise_for_status()
            text = response.text[:max_chars]
            return text

    except Exception as e:
        logger.error(f"Jina scrape failed for '{url}': {e}")
        return ""


# ──────────────────────────────────────────────
# LLM Synthesis (via OpenRouter)
# ──────────────────────────────────────────────


async def _llm_synthesize(raw_research: str, company_name: str, industry: str) -> Dict[str, Any]:
    """
    Use OpenRouter LLM to synthesize raw research data into a structured
    intel brief. This is the "brain" that turns search snippets and scraped
    pages into actionable buyer committee context.
    """
    from services.model_pool import get_model_pool

    pool = get_model_pool()
    if not pool.is_available:
        logger.warning("Model pool unavailable — returning raw research only")
        return {}

    prompt = f"""You are a B2B sales intelligence analyst preparing a buyer committee simulation.

RESEARCH TARGET:
- Company: {company_name or 'Unknown (use industry context)'}
- Industry: {industry}

RAW RESEARCH DATA:
{raw_research}

Synthesize this into a structured intelligence brief. Be specific and factual.
Only include information that is supported by the research data.
If the research is thin, say so — don't fabricate.

Respond with valid JSON:
{{
  "company_overview": "2-3 sentence overview of the company, their market position, and what they do. If company unknown, describe the typical company profile in this industry segment.",
  "recent_news": ["up to 5 recent developments, press releases, or news items"],
  "known_challenges": ["up to 5 specific business challenges this company/industry faces"],
  "competitive_landscape": "1-2 sentences about key competitors and market dynamics",
  "industry_trends": ["up to 4 trends shaping this industry right now"],
  "enriched_pain_points": ["up to 6 specific, research-backed pain points that a vendor pitch should address"],
  "key_stakeholder_concerns": {{
    "CTO": ["2-3 concerns specific to this company/industry"],
    "CFO": ["2-3 concerns specific to this company/industry"],
    "VP Operations": ["2-3 concerns specific to this company/industry"],
    "Head of Security": ["2-3 concerns specific to this company/industry"]
  }},
  "research_quality": "basic|good|deep"
}}"""

    try:
        content, _ = await pool.call_with_failover(
            tier="premium",
            messages=[
                {"role": "system", "content": "You are a B2B sales intelligence analyst. Respond with valid JSON only. Be factual — never fabricate information."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )
        return json.loads(content)
    except Exception as e:
        logger.error(f"LLM synthesis failed: {e}")
        return {}


# ──────────────────────────────────────────────
# Research Engine (Orchestrator)
# ──────────────────────────────────────────────


class ResearchEngine:
    """
    Pre-simulation research engine.

    Runs automated web research on the target company/industry before the
    swarm engine deliberation begins. Produces a ResearchResult with a
    context_block that gets injected into buyer persona system prompts.

    The research is additive — if APIs aren't configured, the swarm still
    runs with generic personas. If APIs ARE configured, personas get
    real-world intelligence that makes their debates dramatically more
    realistic.
    """

    async def research_target(
        self,
        company_name: str = "",
        industry: str = "",
        target_audience: str = "",
        pitch_content: str = "",
        max_scrape_pages: int = 3,
    ) -> ResearchResult:
        """
        Run pre-simulation research. Gracefully degrades if APIs aren't available.

        Flow:
          1. Search Google for company + industry intelligence (Serper)
          2. Scrape top 2-3 most relevant pages (Jina)
          3. Synthesize findings into structured intel brief (OpenRouter LLM)
        """
        started = time.monotonic()
        result = ResearchResult(
            company_name=company_name,
            industry=industry,
        )

        # Quick exit if no research APIs configured
        if not settings.serper_api_key:
            logger.info("Research engine: No SERPER_API_KEY — skipping research")
            result.research_quality = "none"
            return result

        # ── Step 1: Parallel web searches ──
        search_queries = self._build_search_queries(company_name, industry, target_audience)
        logger.info(f"Research engine: Running {len(search_queries)} searches for '{company_name or industry}'")

        search_tasks = [_serper_search(q, num_results=5) for q in search_queries]
        search_results_list = await asyncio.gather(*search_tasks, return_exceptions=True)

        all_hits = []
        seen_urls = set()
        for search_results in search_results_list:
            if isinstance(search_results, Exception):
                continue
            for hit in search_results:
                url = hit.get("link", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_hits.append(hit)

        result.search_hits = all_hits
        logger.info(f"Research engine: Got {len(all_hits)} unique search results")

        if not all_hits:
            result.research_quality = "none"
            result.research_elapsed_seconds = round(time.monotonic() - started, 1)
            return result

        # ── Step 2: Scrape top pages (if Jina configured) ──
        scraped_content = []
        if settings.jina_api_key and all_hits:
            # Pick the most promising pages to scrape
            pages_to_scrape = self._select_pages_to_scrape(all_hits, max_pages=max_scrape_pages)
            scrape_tasks = [_jina_scrape(url, max_chars=4000) for url in pages_to_scrape]
            scrape_results = await asyncio.gather(*scrape_tasks, return_exceptions=True)

            for url, content in zip(pages_to_scrape, scrape_results):
                if isinstance(content, Exception) or not content:
                    continue
                scraped_content.append({"url": url, "content": content})
                result.scraped_pages.append({"url": url, "length": len(content)})

        # ── Step 3: Build raw research package ──
        raw_research = self._compile_raw_research(all_hits, scraped_content)
        result.sources_used = len(all_hits) + len(scraped_content)

        # ── Step 4: LLM synthesis ──
        synthesis = await _llm_synthesize(raw_research, company_name, industry)

        if synthesis:
            result.company_overview = synthesis.get("company_overview", "")
            result.recent_news = synthesis.get("recent_news", [])
            result.known_challenges = synthesis.get("known_challenges", [])
            result.competitive_landscape = synthesis.get("competitive_landscape", "")
            result.industry_trends = synthesis.get("industry_trends", [])
            result.enriched_pain_points = synthesis.get("enriched_pain_points", [])
            result.key_stakeholder_concerns = synthesis.get("key_stakeholder_concerns", {})
            result.research_quality = synthesis.get("research_quality", "basic")
        else:
            # Fallback: use search snippets directly
            result.recent_news = [h["snippet"] for h in all_hits[:5] if h.get("snippet")]
            result.research_quality = "basic"

        result.research_elapsed_seconds = round(time.monotonic() - started, 1)
        logger.info(
            f"Research engine: Completed in {result.research_elapsed_seconds}s — "
            f"quality={result.research_quality}, sources={result.sources_used}"
        )
        return result

    def _build_search_queries(
        self, company_name: str, industry: str, target_audience: str
    ) -> List[str]:
        """
        Build targeted search queries. If we know the company name, search
        for company-specific intel. If not, search for industry-level context.
        """
        queries = []

        if company_name:
            # Company-specific searches
            queries.append(f"{company_name} company overview")
            queries.append(f"{company_name} news {datetime.now().year}")
            queries.append(f"{company_name} challenges problems")
            if industry:
                queries.append(f"{company_name} competitors {industry.split(' — ')[0]}")
        else:
            # Industry-level searches (still very useful for realistic personas)
            base_industry = industry.split(" — ")[0] if " — " in industry else industry
            queries.append(f"{base_industry} industry challenges {datetime.now().year}")
            queries.append(f"{base_industry} market trends")
            queries.append(f"{base_industry} technology adoption priorities")

        # Always add industry trend search
        if industry:
            base = industry.split(" — ")[0] if " — " in industry else industry
            queries.append(f"{base} buying priorities enterprise software {datetime.now().year}")

        return queries[:4]  # Cap at 4 searches to keep costs < $0.01

    def _select_pages_to_scrape(self, hits: List[Dict], max_pages: int = 3) -> List[str]:
        """
        Pick the most information-dense pages to scrape.
        Prioritize company about pages, news articles, and industry reports.
        Skip social media, PDFs, and video platforms.
        """
        skip_domains = {"youtube.com", "twitter.com", "x.com", "facebook.com",
                        "linkedin.com", "instagram.com", "tiktok.com", "reddit.com"}
        skip_extensions = {".pdf", ".mp4", ".mp3", ".zip"}

        candidates = []
        for hit in hits:
            url = hit.get("link", "")
            if not url:
                continue

            # Skip social media and media files
            domain = url.split("/")[2] if len(url.split("/")) > 2 else ""
            if any(sd in domain for sd in skip_domains):
                continue
            if any(url.lower().endswith(ext) for ext in skip_extensions):
                continue

            # Score by relevance signals
            score = 0
            title_lower = hit.get("title", "").lower()
            if any(w in title_lower for w in ["about", "overview", "company", "who we are"]):
                score += 3
            if any(w in title_lower for w in ["news", "announce", "launch", "report"]):
                score += 2
            if any(w in title_lower for w in ["challenge", "trend", "forecast", "outlook"]):
                score += 2
            candidates.append((score, url))

        # Sort by score, take top N
        candidates.sort(key=lambda x: x[0], reverse=True)
        return [url for _, url in candidates[:max_pages]]

    def _compile_raw_research(
        self,
        search_hits: List[Dict],
        scraped_pages: List[Dict[str, str]],
    ) -> str:
        """Compile all raw research into a single text block for LLM synthesis."""
        sections = []

        # Search snippets
        if search_hits:
            snippets = []
            for hit in search_hits[:10]:
                snippets.append(f"- [{hit.get('title', 'No title')}] {hit.get('snippet', '')}")
            sections.append("SEARCH RESULTS:\n" + "\n".join(snippets))

        # Scraped page content
        if scraped_pages:
            for page in scraped_pages:
                # Truncate each page to keep total context manageable
                content = page.get("content", "")[:3000]
                sections.append(f"PAGE CONTENT ({page.get('url', 'unknown')}):\n{content}")

        return "\n\n---\n\n".join(sections) if sections else "No research data available."


# ──────────────────────────────────────────────
# Singleton
# ──────────────────────────────────────────────


_research_engine: Optional[ResearchEngine] = None


def get_research_engine() -> ResearchEngine:
    global _research_engine
    if _research_engine is None:
        _research_engine = ResearchEngine()
    return _research_engine
