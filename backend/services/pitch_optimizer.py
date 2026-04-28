"""
PitchProof AutoOptimizer
=======================
Karpathy AutoResearch loop applied to sales pitch optimization.

The methodology:
  1. MEASURE: Run the full Swarm Engine on the current pitch → scores + objections
  2. HYPOTHESIZE: An optimizer agent reviews ALL prior experiments (not just the last)
     and forms an explicit hypothesis about what to change and why
  3. EDIT: Rewrite the pitch to test the hypothesis
  4. RE-MEASURE: Run the Swarm Engine on the new pitch → new scores
  5. ACCEPT/REJECT: If scores improved → keep. If not → revert.
     The agent sees which hypotheses worked and which didn't.
  6. REPEAT: Loop until target score reached or max iterations exhausted.

Key principles:
  - Full experiment history is available to the agent at every step
  - Each change has an explicit hypothesis (not blind rewriting)
  - Accept/reject is based on composite score across all metrics
  - After a revert, the agent uses feedback from the last ACCEPTED state
  - Evaluation uses full simulation config (not lightweight) for accuracy
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable

from services.model_pool import ModelPool, get_model_pool
from services.swarm_engine import SwarmEngine, get_swarm_engine

logger = logging.getLogger(__name__)


def _compute_composite(scores: Dict[str, Any]) -> float:
    """Weighted composite: engagement 40%, sentiment 30%, deal prob 30%."""
    return (
        scores.get("overall_engagement", 0) * 0.4
        + scores.get("overall_sentiment", 0) * 0.3
        + scores.get("deal_probability", 0) * 0.3
    )


class OptimizationIteration:
    """One cycle of the optimization loop."""

    def __init__(
        self,
        iteration: int,
        pitch_content: str,
        scores: Dict[str, Any],
        composite_score: float,
        hypothesis: str,
        changes_made: str,
        kept: bool,
        consensus: Dict[str, Any] = None,
        objections: List[str] = None,
        recommendations: List[str] = None,
    ):
        self.iteration = iteration
        self.pitch_content = pitch_content
        self.scores = scores
        self.composite_score = composite_score
        self.hypothesis = hypothesis
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
            "composite_score": round(self.composite_score, 1),
            "hypothesis": self.hypothesis,
            "changes_made": self.changes_made,
            "kept": self.kept,
            "objections": self.objections,
            "recommendations": self.recommendations,
        }


class PitchOptimizer:
    """
    Autonomous pitch optimization loop.

    Implements Karpathy's AutoResearch methodology:
    measure → hypothesize → edit → re-measure → accept/reject → repeat.

    Each iteration has access to the FULL experiment history, not just the
    last round. This lets the optimizer learn from what worked and what didn't.
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
        num_tables: int = 3,
        personas_per_table: int = 5,
        debate_rounds: int = 2,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Run the autonomous pitch optimization loop.

        Uses full simulation config for accurate evaluation at each step.
        Accuracy > speed — each cycle runs a real committee deliberation.

        Args:
            pitch_content: The original pitch to optimize
            max_iterations: Maximum optimization cycles (default 5)
            target_score: Stop early if composite score hits this (default 85)
            num_tables/personas_per_table/debate_rounds: Full sim config

        Returns:
            Complete optimization history with original and best pitch
        """
        started_at = datetime.utcnow()
        iterations: List[OptimizationIteration] = []
        current_pitch = pitch_content
        best_pitch = pitch_content
        best_scores = {}
        best_composite = 0.0

        # Generate a fixed seed for committee composition. Every evaluation
        # in this optimization run uses the SAME committees, so score
        # differences reflect pitch quality, not committee randomness.
        committee_seed = hash(pitch_content[:200]) & 0x7FFFFFFF

        async def _progress(msg: str, pct: int):
            logger.info(f"[Optimizer] {msg}")
            if progress_callback:
                await progress_callback("optimizing", msg, pct)

        # ── Step 1: MEASURE baseline ──
        await _progress("Evaluating original pitch with full buying committees...", 5)

        baseline_result = await self.engine.run(
            pitch_content=current_pitch,
            industry=industry,
            company_name=company_name,
            company_size=company_size,
            target_audience=target_audience,
            num_tables=num_tables,
            personas_per_table=personas_per_table,
            debate_rounds=debate_rounds,
            seed=committee_seed,
        )

        baseline_consensus = baseline_result.get("consensus", {})
        baseline_scores = baseline_consensus.get("scores", {})
        baseline_composite = _compute_composite(baseline_scores)

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
            composite_score=baseline_composite,
            hypothesis="N/A — baseline measurement",
            changes_made="Original pitch — no changes",
            kept=True,
            consensus=baseline_consensus,
            objections=baseline_objections,
            recommendations=baseline_recommendations,
        ))

        best_scores = dict(baseline_scores)  # copy, don't alias with iterations[0]
        best_composite = baseline_composite
        logger.info(
            f"Baseline: composite={baseline_composite:.1f}, "
            f"engagement={baseline_scores.get('overall_engagement', 0)}"
        )

        # ── Optimization Loop ──
        for i in range(1, max_iterations + 1):
            pct = 5 + int((i / max_iterations) * 85)

            # Check if we've hit the target
            if best_composite >= target_score:
                await _progress(
                    f"Target composite score {target_score} reached! Stopping after iteration {i-1}.",
                    pct,
                )
                break

            # ── Get feedback from the last ACCEPTED iteration ──
            # After a revert, we don't want the failed experiment's feedback
            # poisoning the next hypothesis. Use the last kept iteration.
            last_kept = None
            for it in reversed(iterations):
                if it.kept:
                    last_kept = it
                    break

            # ── Step 2: HYPOTHESIZE ──
            await _progress(
                f"Iteration {i}/{max_iterations} — analyzing experiment history and forming hypothesis...",
                pct,
            )

            hypothesis = await self._form_hypothesis(
                current_pitch=current_pitch,
                original_pitch=pitch_content,
                iterations=iterations,
                last_kept=last_kept,
                iteration=i,
                industry=industry,
                company_name=company_name,
                target_audience=target_audience,
            )
            logger.info(f"Iteration {i} hypothesis: {hypothesis[:200]}")

            # ── Step 3: EDIT — rewrite the pitch to test the hypothesis ──
            await _progress(
                f"Iteration {i}/{max_iterations} — rewriting pitch to test hypothesis...",
                pct + 2,
            )

            new_pitch = await self._rewrite_pitch(
                current_pitch=current_pitch,
                original_pitch=pitch_content,
                hypothesis=hypothesis,
                scores=last_kept.scores,
                objections=last_kept.objections,
                recommendations=last_kept.recommendations,
                iteration=i,
                industry=industry,
                company_name=company_name,
                target_audience=target_audience,
            )

            # ── Step 4: RE-MEASURE ──
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
                seed=committee_seed,
            )

            eval_consensus = eval_result.get("consensus", {})
            eval_scores = eval_consensus.get("scores", {})
            eval_composite = _compute_composite(eval_scores)

            eval_objections = [
                obj.get("objection", str(obj)) if isinstance(obj, dict) else str(obj)
                for obj in eval_consensus.get("top_objections", [])
            ]
            eval_recommendations = [
                rec.get("action", str(rec)) if isinstance(rec, dict) else str(rec)
                for rec in eval_consensus.get("recommendations", [])
            ]

            # ── Step 5: ACCEPT or REJECT ──
            prev_composite = last_kept.composite_score

            # Noise margin: with full-size committees the scores are more stable,
            # but still allow a small margin (2 points) to avoid rejecting
            # rewrites that address real objections but get unlucky on re-eval.
            noise_margin = 2.0
            kept = eval_composite >= (prev_composite - noise_margin)

            changes_description = await self._describe_changes(
                current_pitch, new_pitch, kept, eval_scores, last_kept.scores
            )

            iteration_record = OptimizationIteration(
                iteration=i,
                pitch_content=new_pitch,
                scores=eval_scores,
                composite_score=eval_composite,
                hypothesis=hypothesis,
                changes_made=changes_description,
                kept=kept,
                consensus=eval_consensus,
                objections=eval_objections,
                recommendations=eval_recommendations,
            )
            iterations.append(iteration_record)

            if kept:
                current_pitch = new_pitch
                # Always update best to the latest accepted iteration.
                # With seeded committees, accepted means genuinely better
                # (or at worst within noise margin of previous).
                best_pitch = new_pitch
                best_scores = dict(eval_scores)  # copy, don't alias
                best_composite = eval_composite
                logger.info(
                    f"Iteration {i}: ACCEPTED — composite {prev_composite:.1f} → {eval_composite:.1f} "
                    f"(Δ{eval_composite - prev_composite:+.1f})"
                )
            else:
                logger.info(
                    f"Iteration {i}: REJECTED — composite {prev_composite:.1f} → {eval_composite:.1f} "
                    f"(Δ{eval_composite - prev_composite:+.1f})"
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
                    "composite": round(it.composite_score, 1),
                    "kept": it.kept,
                }
                for it in iterations
            ],
        }

    async def _form_hypothesis(
        self,
        current_pitch: str,
        original_pitch: str,
        iterations: List[OptimizationIteration],
        last_kept: OptimizationIteration,
        iteration: int,
        industry: str,
        company_name: str,
        target_audience: str,
    ) -> str:
        """
        The HYPOTHESIS step of the Karpathy loop.

        The agent reviews the FULL experiment history — what was tried, what
        scores resulted, what was accepted/rejected — and forms a specific
        hypothesis about what change will improve the pitch.

        This is what distinguishes Karpathy's approach from blind trial-and-error:
        each edit is informed by the cumulative learnings from all prior experiments.
        """
        # Build the full experiment log
        experiment_log = ""
        for it in iterations:
            status = "BASELINE" if it.iteration == 0 else ("ACCEPTED ✓" if it.kept else "REJECTED ✗")
            experiment_log += (
                f"\n--- Iteration {it.iteration} [{status}] ---\n"
                f"Composite Score: {it.composite_score:.1f} "
                f"(engagement={it.scores.get('overall_engagement', 0)}, "
                f"sentiment={it.scores.get('overall_sentiment', 0)}, "
                f"deal_prob={it.scores.get('deal_probability', 0)})\n"
            )
            if it.hypothesis and it.hypothesis != "N/A — baseline measurement":
                experiment_log += f"Hypothesis: {it.hypothesis}\n"
            if it.changes_made:
                experiment_log += f"Changes: {it.changes_made}\n"
            if it.objections:
                experiment_log += f"Top Objections: {'; '.join(it.objections[:3])}\n"
            if it.recommendations:
                experiment_log += f"Recommendations: {'; '.join(it.recommendations[:3])}\n"

        objection_text = "\n".join(f"  - {obj}" for obj in last_kept.objections[:5])
        recommendation_text = "\n".join(f"  - {rec}" for rec in last_kept.recommendations[:5])

        prompt = f"""You are a pitch optimization researcher running an experiment loop.
You have run {len(iterations)} experiment(s) so far. Here is the FULL experiment log:

{experiment_log}

CURRENT BEST SCORES (from the last accepted iteration):
  Composite: {last_kept.composite_score:.1f}
  Engagement: {last_kept.scores.get('overall_engagement', 0)}/100
  Sentiment: {last_kept.scores.get('overall_sentiment', 0)}/100
  Deal Probability: {last_kept.scores.get('deal_probability', 0)}/100
  Pitch Clarity: {last_kept.scores.get('pitch_clarity', 0)}/100
  Objection Vulnerability: {last_kept.scores.get('objection_vulnerability', 0)}/100

CURRENT TOP OBJECTIONS:
{objection_text}

CURRENT RECOMMENDATIONS:
{recommendation_text}

CONTEXT:
  Company: {company_name}
  Industry: {industry}
  Target Audience: {target_audience}
  This is iteration {iteration}

Based on the FULL experiment history above:
1. What patterns do you see in what worked vs. what didn't?
2. What is the weakest area that hasn't been adequately addressed yet?
3. What SPECIFIC HYPOTHESIS do you want to test in this next iteration?

Your hypothesis should be:
- Specific ("Add a concrete ROI example to address the CFO's cost concern") not vague ("improve the pitch")
- Informed by prior experiments (don't repeat rejected approaches)
- Targeted at the lowest-scoring metric or most severe objection

Return your hypothesis in 2-3 sentences. Start with "HYPOTHESIS:" """

        content, _ = await self.pool.call_with_failover(
            tier="premium",
            messages=[
                {
                    "role": "system",
                    "content": "You are a rigorous optimization researcher. You form specific, "
                    "testable hypotheses based on experimental data. Be precise and strategic.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=300,
        )

        # Clean up the hypothesis text
        hypothesis = content.strip()
        if hypothesis.upper().startswith("HYPOTHESIS:"):
            hypothesis = hypothesis[len("HYPOTHESIS:"):].strip()
        return hypothesis

    async def _rewrite_pitch(
        self,
        current_pitch: str,
        original_pitch: str,
        hypothesis: str,
        scores: Dict[str, Any],
        objections: List[str],
        recommendations: List[str],
        iteration: int,
        industry: str,
        company_name: str,
        target_audience: str,
    ) -> str:
        """
        The EDIT step of the Karpathy loop.

        Rewrites the pitch to TEST a specific hypothesis. The rewrite is
        targeted and deliberate — not a generic "make it better" pass.
        """
        objection_text = "\n".join(f"  - {obj}" for obj in objections[:5])
        recommendation_text = "\n".join(f"  - {rec}" for rec in recommendations[:5])

        prompt = f"""You are an elite sales pitch optimizer. You are testing a SPECIFIC HYPOTHESIS
about how to improve this pitch. Your rewrite should be TARGETED at testing this hypothesis.

═══ YOUR HYPOTHESIS TO TEST ═══
{hypothesis}

═══ CURRENT SCORES ═══
  Engagement: {scores.get('overall_engagement', 0)}/100
  Sentiment: {scores.get('overall_sentiment', 0)}/100
  Deal Probability: {scores.get('deal_probability', 0)}/100
  Pitch Clarity: {scores.get('pitch_clarity', 0)}/100
  Objection Vulnerability: {scores.get('objection_vulnerability', 0)}/100

═══ TOP OBJECTIONS FROM BUYING COMMITTEES ═══
{objection_text}

═══ RECOMMENDED CHANGES ═══
{recommendation_text}

═══ CONTEXT ═══
  Company: {company_name}
  Industry: {industry}
  Target Audience: {target_audience}
  Optimization Iteration: {iteration}

═══ CURRENT PITCH ═══
{current_pitch}

═══ REWRITE RULES ═══
1. Focus your changes on TESTING THE HYPOTHESIS above — make targeted edits, not a full rewrite
2. Address the top objections directly with proof points, counter-arguments, or reframes
3. Keep the pitch roughly the same length (±20%)
4. Maintain the pitch's voice and style — don't make it generic
5. Preserve what's already working (don't touch high-scoring elements)
6. Be specific and concrete — no filler phrases like "industry-leading" without evidence
7. Think about what a {target_audience} actually cares about day-to-day
8. Each change you make should be traceable back to the hypothesis

Return ONLY the rewritten pitch text. No commentary, no explanation, no markdown headers.
Just the pitch."""

        content, _ = await self.pool.call_with_failover(
            tier="premium",
            messages=[
                {
                    "role": "system",
                    "content": "You are a world-class B2B sales copywriter who optimizes pitches "
                    "based on real buyer committee feedback and specific hypotheses. "
                    "Make targeted, deliberate changes — not generic rewrites. "
                    "Return only the rewritten pitch.",
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

RESULT: {"ACCEPTED — scores improved or held" if kept else "REJECTED — scores declined significantly"}

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
        """Generate a final optimization summary with full experiment analysis."""
        iteration_log = ""
        for it in iterations:
            status = "BASELINE" if it.iteration == 0 else ("ACCEPTED" if it.kept else "REJECTED")
            iteration_log += (
                f"\nIteration {it.iteration} [{status}]: "
                f"composite={it.composite_score:.1f}, "
                f"engagement={it.scores.get('overall_engagement', 0)}, "
                f"sentiment={it.scores.get('overall_sentiment', 0)}, "
                f"deal_prob={it.scores.get('deal_probability', 0)}\n"
            )
            if it.hypothesis and it.hypothesis != "N/A — baseline measurement":
                iteration_log += f"  Hypothesis: {it.hypothesis}\n"
            iteration_log += f"  Changes: {it.changes_made}\n"

        baseline_composite = iterations[0].composite_score
        # Find best composite among kept iterations
        best_kept = max(
            (it for it in iterations if it.kept),
            key=lambda it: it.composite_score,
            default=iterations[0],
        )

        prompt = f"""You ran a Karpathy-style autonomous pitch optimization loop for {company_name or 'a company'} in {industry}.
Here's the full experiment log:

{iteration_log}

BASELINE COMPOSITE: {baseline_composite:.1f}
BEST COMPOSITE: {best_kept.composite_score:.1f}
IMPROVEMENT: {best_kept.composite_score - baseline_composite:+.1f} points

Produce a JSON summary:
{{
  "headline": "One sentence summary of the optimization result",
  "total_improvement": "X point improvement in composite score (from A to B)",
  "key_changes_that_worked": ["list of 3-5 specific changes that improved scores — reference the hypotheses"],
  "changes_that_backfired": ["list of hypotheses/changes that were tried but rejected"],
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
