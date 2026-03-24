"""
PitchSim AutoOptimizer
=======================
Inspired by Karpathy's AutoResearch loop: give an AI agent a pitch and a
measurable metric, and let it autonomously rewrite → evaluate → keep/revert
until the pitch is as strong as possible.

The Loop:
  1. Run the Swarm Engine on the current pitch → get scores + objections
  2. An optimizer agent reads the scores, objections, and recommendations
  3. It rewrites the pitch, targeting specific weaknesses
  4. Run the Swarm Engine on the new pitch → get new scores
  5. If scores improved → keep the new pitch. If not → revert.
  6. Repeat for N iterations (or until target score reached)

At the end, the user gets:
  - Original pitch vs. optimized pitch (side-by-side)
  - Score progression across iterations
  - What changed and why at each step
  - The final consensus from the committees

This is the "Karpathy Loop" applied to sales — not just evaluating pitches,
but autonomously improving them.
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable

from services.model_pool import ModelPool, get_model_pool
from services.swarm_engine import SwarmEngine, get_swarm_engine

logger = logging.getLogger(__name__)


class OptimizationIteration:
    """One cycle of the optimization loop."""

    def __init__(
        self,
        iteration: int,
        pitch_content: str,
        scores: Dict[str, Any],
        changes_made: str,
        kept: bool,
        consensus: Dict[str, Any] = None,
        objections: List[str] = None,
        recommendations: List[str] = None,
    ):
        self.iteration = iteration
        self.pitch_content = pitch_content
        self.scores = scores
        self.changes_made = changes_made
        self.kept = kept
        self.consensus = consensus or {}
        self.objections = objections or []
        self.recommendations = recommendations or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iteration": self.iteration,
            "pitch_content": self.pitch_content,
            "scores": self.scores,
            "changes_made": self.changes_made,
            "kept": self.kept,
            "objections": self.objections,
            "recommendations": self.recommendations,
        }


class PitchOptimizer:
    """
    Autonomous pitch optimization loop.

    Wraps the Swarm Engine in a Karpathy-style experiment loop:
    evaluate → rewrite → evaluate → keep/revert → repeat.
    """

    def __init__(
        self,
        pool: Optional[ModelPool] = None,
        engine: Optional[SwarmEngine] = None,
    ):
        self.pool = pool or get_model_pool()
        self.engine = engine or get_swarm_engine()

    async def optimize(
        self,
        pitch_content: str,
        industry: str = "technology",
        company_name: str = "",
        company_size: str = "mid-market",
        target_audience: str = "",
        max_iterations: int = 5,
        target_score: int = 85,
        num_tables: int = 2,
        personas_per_table: int = 4,
        debate_rounds: int = 1,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Run the autonomous pitch optimization loop.

        Uses fewer tables/personas/rounds per iteration than a full sim
        to keep each cycle fast (~30-60 seconds instead of 2-3 minutes).

        Args:
            pitch_content: The original pitch to optimize
            max_iterations: Maximum optimization cycles (default 5)
            target_score: Stop early if overall_engagement hits this (default 85)
            num_tables/personas_per_table/debate_rounds: Lighter config for speed

        Returns:
            Complete optimization history with original and best pitch
        """
        started_at = datetime.utcnow()
        iterations: List[OptimizationIteration] = []
        current_pitch = pitch_content
        best_pitch = pitch_content
        best_scores = {}
        best_score_value = 0

        async def _progress(msg: str, pct: int):
            logger.info(f"[Optimizer] {msg}")
            if progress_callback:
                await progress_callback("optimizing", msg, pct)

        # ── Iteration 0: Baseline evaluation ──
        await _progress("Evaluating original pitch...", 5)

        baseline_result = await self.engine.run(
            pitch_content=current_pitch,
            industry=industry,
            company_name=company_name,
            company_size=company_size,
            target_audience=target_audience,
            num_tables=num_tables,
            personas_per_table=personas_per_table,
            debate_rounds=debate_rounds,
        )

        baseline_consensus = baseline_result.get("consensus", {})
        baseline_scores = baseline_consensus.get("scores", {})
        baseline_engagement = baseline_scores.get("overall_engagement", 0)

        baseline_objections = [
            obj.get("objection", str(obj)) if isinstance(obj, dict) else str(obj)
            for obj in baseline_consensus.get("top_objections", [])
        ]
        baseline_recommendations = [
            rec.get("action", str(rec)) if isinstance(rec, dict) else str(rec)
            for rec in baseline_consensus.get("recommendations", [])
        ]

        iterations.append(OptimizationIteration(
            iteration=0,
            pitch_content=current_pitch,
            scores=baseline_scores,
            changes_made="Original pitch — no changes",
            kept=True,
            consensus=baseline_consensus,
            objections=baseline_objections,
            recommendations=baseline_recommendations,
        ))

        best_scores = baseline_scores
        best_score_value = baseline_engagement
        logger.info(f"Baseline score: engagement={baseline_engagement}")

        # ── Optimization Loop ──
        for i in range(1, max_iterations + 1):
            pct = 5 + int((i / max_iterations) * 85)
            await _progress(
                f"Iteration {i}/{max_iterations} — rewriting pitch based on committee feedback...",
                pct,
            )

            # Check if we've hit the target
            if best_score_value >= target_score:
                await _progress(
                    f"Target score {target_score} reached at iteration {i-1}! Stopping.",
                    pct,
                )
                break

            # Get the last iteration's feedback
            last = iterations[-1]

            # ── Rewrite the pitch ──
            new_pitch = await self._rewrite_pitch(
                current_pitch=current_pitch,
                original_pitch=pitch_content,
                scores=last.scores,
                objections=last.objections,
                recommendations=last.recommendations,
                iteration=i,
                industry=industry,
                company_name=company_name,
                target_audience=target_audience,
            )

            # ── Evaluate the rewrite ──
            await _progress(
                f"Iteration {i}/{max_iterations} — committees evaluating rewritten pitch...",
                pct + 5,
            )

            eval_result = await self.engine.run(
                pitch_content=new_pitch,
                industry=industry,
                company_name=company_name,
                company_size=company_size,
                target_audience=target_audience,
                num_tables=num_tables,
                personas_per_table=personas_per_table,
                debate_rounds=debate_rounds,
            )

            eval_consensus = eval_result.get("consensus", {})
            eval_scores = eval_consensus.get("scores", {})
            eval_engagement = eval_scores.get("overall_engagement", 0)

            eval_objections = [
                obj.get("objection", str(obj)) if isinstance(obj, dict) else str(obj)
                for obj in eval_consensus.get("top_objections", [])
            ]
            eval_recommendations = [
                rec.get("action", str(rec)) if isinstance(rec, dict) else str(rec)
                for rec in eval_consensus.get("recommendations", [])
            ]

            # ── Keep or revert? ──
            # Calculate composite improvement score
            prev_engagement = last.scores.get("overall_engagement", 0)
            prev_sentiment = last.scores.get("overall_sentiment", 0)
            prev_deal = last.scores.get("deal_probability", 0)

            new_engagement = eval_scores.get("overall_engagement", 0)
            new_sentiment = eval_scores.get("overall_sentiment", 0)
            new_deal = eval_scores.get("deal_probability", 0)

            # Weighted composite: engagement 40%, sentiment 30%, deal prob 30%
            prev_composite = prev_engagement * 0.4 + prev_sentiment * 0.3 + prev_deal * 0.3
            new_composite = new_engagement * 0.4 + new_sentiment * 0.3 + new_deal * 0.3

            kept = new_composite > prev_composite

            changes_description = await self._describe_changes(
                current_pitch, new_pitch, kept, eval_scores, last.scores
            )

            iteration_record = OptimizationIteration(
                iteration=i,
                pitch_content=new_pitch,
                scores=eval_scores,
                changes_made=changes_description,
                kept=kept,
                consensus=eval_consensus,
                objections=eval_objections,
                recommendations=eval_recommendations,
            )
            iterations.append(iteration_record)

            if kept:
                current_pitch = new_pitch
                if new_composite > best_score_value:
                    best_pitch = new_pitch
                    best_scores = eval_scores
                    best_score_value = new_engagement
                logger.info(
                    f"Iteration {i}: KEPT — engagement {prev_engagement} → {new_engagement} "
                    f"(composite {prev_composite:.1f} → {new_composite:.1f})"
                )
            else:
                logger.info(
                    f"Iteration {i}: REVERTED — engagement {prev_engagement} → {new_engagement} "
                    f"(composite {prev_composite:.1f} → {new_composite:.1f})"
                )

        # ── Final Summary ──
        await _progress("Optimization complete! Generating summary...", 95)

        elapsed = (datetime.utcnow() - started_at).total_seconds()

        summary = await self._generate_summary(
            original_pitch=pitch_content,
            optimized_pitch=best_pitch,
            iterations=iterations,
            industry=industry,
            company_name=company_name,
        )

        await _progress("Done!", 100)

        return {
            "original_pitch": pitch_content,
            "optimized_pitch": best_pitch,
            "original_scores": iterations[0].scores,
            "optimized_scores": best_scores,
            "iterations": [it.to_dict() for it in iterations],
            "total_iterations": len(iterations) - 1,  # exclude baseline
            "kept_count": sum(1 for it in iterations[1:] if it.kept),
            "reverted_count": sum(1 for it in iterations[1:] if not it.kept),
            "summary": summary,
            "elapsed_seconds": round(elapsed, 1),
            "score_progression": [
                {
                    "iteration": it.iteration,
                    "engagement": it.scores.get("overall_engagement", 0),
                    "sentiment": it.scores.get("overall_sentiment", 0),
                    "deal_probability": it.scores.get("deal_probability", 0),
                    "kept": it.kept,
                }
                for it in iterations
            ],
        }

    async def _rewrite_pitch(
        self,
        current_pitch: str,
        original_pitch: str,
        scores: Dict[str, Any],
        objections: List[str],
        recommendations: List[str],
        iteration: int,
        industry: str,
        company_name: str,
        target_audience: str,
    ) -> str:
        """
        The optimizer agent rewrites the pitch based on committee feedback.
        This is the "hypothesis + code edit" step of the Karpathy loop.
        """
        objection_text = "\n".join(f"  - {obj}" for obj in objections[:5])
        recommendation_text = "\n".join(f"  - {rec}" for rec in recommendations[:5])

        prompt = f"""You are an elite sales pitch optimizer. You've received feedback from buying
committees who evaluated this pitch. Your job: rewrite the pitch to address their
specific concerns while preserving its strengths.

CURRENT SCORES:
  Engagement: {scores.get('overall_engagement', 0)}/100
  Sentiment: {scores.get('overall_sentiment', 0)}/100
  Deal Probability: {scores.get('deal_probability', 0)}/100
  Pitch Clarity: {scores.get('pitch_clarity', 0)}/100
  Objection Vulnerability: {scores.get('objection_vulnerability', 0)}/100

TOP OBJECTIONS FROM BUYING COMMITTEES:
{objection_text}

RECOMMENDED CHANGES:
{recommendation_text}

CONTEXT:
  Company: {company_name}
  Industry: {industry}
  Target Audience: {target_audience}
  Optimization Iteration: {iteration}

CURRENT PITCH:
{current_pitch}

RULES:
1. Address the TOP objections directly — add proof points, counter-arguments, or reframe
2. Follow the recommendations but use your judgment on implementation
3. Keep the pitch roughly the same length (±20%)
4. Maintain the pitch's voice and style — don't make it generic
5. Preserve what's already working (high-scoring elements)
6. Be specific and concrete — no filler phrases like "industry-leading" without backing
7. If objection vulnerability is high, preemptively address likely concerns
8. Think about what a {target_audience} actually cares about day-to-day

Return ONLY the rewritten pitch text. No commentary, no explanation, no markdown headers.
Just the pitch."""

        content, _ = await self.pool.call_with_failover(
            tier="premium",
            messages=[
                {
                    "role": "system",
                    "content": "You are a world-class B2B sales copywriter who optimizes pitches "
                    "based on real buyer committee feedback. Return only the rewritten pitch.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=3000,
        )
        return content.strip()

    async def _describe_changes(
        self,
        old_pitch: str,
        new_pitch: str,
        kept: bool,
        new_scores: Dict[str, Any],
        old_scores: Dict[str, Any],
    ) -> str:
        """Generate a concise description of what changed and the impact."""
        prompt = f"""Compare these two versions of a sales pitch and describe what changed in 2-3 sentences.
Focus on the strategic changes, not word-level edits.

SCORE CHANGES:
  Engagement: {old_scores.get('overall_engagement', 0)} → {new_scores.get('overall_engagement', 0)}
  Sentiment: {old_scores.get('overall_sentiment', 0)} → {new_scores.get('overall_sentiment', 0)}
  Deal Probability: {old_scores.get('deal_probability', 0)} → {new_scores.get('deal_probability', 0)}

RESULT: {"KEPT — scores improved" if kept else "REVERTED — scores declined"}

OLD VERSION (first 500 chars):
{old_pitch[:500]}

NEW VERSION (first 500 chars):
{new_pitch[:500]}

Describe the key changes in 2-3 sentences. Be specific."""

        content, _ = await self.pool.call_with_failover(
            tier="volume",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
        )
        return content.strip()

    async def _generate_summary(
        self,
        original_pitch: str,
        optimized_pitch: str,
        iterations: List[OptimizationIteration],
        industry: str,
        company_name: str,
    ) -> Dict[str, Any]:
        """Generate a final optimization summary."""
        iteration_log = ""
        for it in iterations:
            status = "BASELINE" if it.iteration == 0 else ("KEPT" if it.kept else "REVERTED")
            iteration_log += (
                f"\nIteration {it.iteration} [{status}]: "
                f"engagement={it.scores.get('overall_engagement', 0)}, "
                f"sentiment={it.scores.get('overall_sentiment', 0)}, "
                f"deal_prob={it.scores.get('deal_probability', 0)}\n"
                f"  Changes: {it.changes_made}\n"
            )

        prompt = f"""You ran an autonomous pitch optimization loop for {company_name or 'a company'} in {industry}.
Here's the full experiment log:

{iteration_log}

ORIGINAL SCORE: engagement={iterations[0].scores.get('overall_engagement', 0)}
FINAL SCORE: engagement={iterations[-1].scores.get('overall_engagement', 0) if iterations[-1].kept else iterations[-2].scores.get('overall_engagement', 0)}

Produce a JSON summary:
{{
  "headline": "One sentence summary of the optimization result",
  "total_improvement": "X% improvement in engagement (or whatever the actual number is)",
  "key_changes_that_worked": ["list of 3-5 specific changes that improved scores"],
  "changes_that_backfired": ["list of changes that were tried but reverted"],
  "remaining_weaknesses": ["1-3 areas that still need human attention"],
  "confidence": "high|medium|low — how confident are you the optimized pitch is better"
}}"""

        content, _ = await self.pool.call_with_failover(
            tier="premium",
            messages=[
                {"role": "system", "content": "Expert sales strategist. Respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=600,
            response_format={"type": "json_object"},
        )
        return json.loads(content)


# ──────────────────────────────────────────────
# Singleton
# ──────────────────────────────────────────────

_optimizer: Optional[PitchOptimizer] = None


def get_pitch_optimizer() -> PitchOptimizer:
    global _optimizer
    if _optimizer is None:
        _optimizer = PitchOptimizer()
    return _optimizer
