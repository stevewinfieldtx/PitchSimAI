"""
Multi-model pool for distributing LLM calls across OpenRouter models.

Supports:
- Round-robin distribution across all configured models
- Tiered routing: premium models for high-value personas, volume models for bulk
- Per-model concurrency limits to respect rate limits
- Automatic failover if a model errors out
- Real-time stats tracking per model
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from openai import AsyncOpenAI

from config import get_settings

settings = get_settings()


@dataclass
class ModelStats:
    """Track per-model performance."""
    calls: int = 0
    errors: int = 0
    total_latency_ms: float = 0
    last_error: Optional[str] = None

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.calls if self.calls else 0

    @property
    def error_rate(self) -> float:
        return self.errors / self.calls if self.calls else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "calls": self.calls,
            "errors": self.errors,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "error_rate": round(self.error_rate, 3),
            "last_error": self.last_error,
        }


@dataclass
class PooledModel:
    """A model in the pool with its own semaphore and stats."""
    model_id: str
    tier: str  # "premium" or "volume"
    semaphore: asyncio.Semaphore = field(default_factory=lambda: asyncio.Semaphore(10))
    stats: ModelStats = field(default_factory=ModelStats)


class ModelPool:
    """
    Manages a pool of LLM models for distributed simulation.

    Usage:
        pool = ModelPool()
        model_id = pool.pick(tier="premium")
        async with pool.acquire(model_id):
            response = await pool.call(model_id, messages=[...])
    """

    def __init__(self):
        self.client = (
            AsyncOpenAI(api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url)
            if settings.openrouter_api_key else None
        )
        self.models: Dict[str, PooledModel] = {}
        self._robin_premium = 0
        self._robin_volume = 0
        self._robin_all = 0
        self._lock = asyncio.Lock()

        # Load models from env vars
        model_vars = [
            (settings.openrouter_model1_id, "premium"),
            (settings.openrouter_model2_id, "premium"),
            (settings.openrouter_model3_id, "volume"),
            (settings.openrouter_model4_id, "volume"),
            (settings.openrouter_model5_id, "volume"),
        ]

        concurrency = settings.openrouter_concurrency_per_model

        for model_id, tier in model_vars:
            if model_id:
                self.models[model_id] = PooledModel(
                    model_id=model_id,
                    tier=tier,
                    semaphore=asyncio.Semaphore(concurrency),
                )

        # If no models configured, fall back to the single default model
        if not self.models and settings.openrouter_default_model:
            self.models[settings.openrouter_default_model] = PooledModel(
                model_id=settings.openrouter_default_model,
                tier="volume",
                semaphore=asyncio.Semaphore(concurrency),
            )

    @property
    def is_available(self) -> bool:
        return self.client is not None and len(self.models) > 0

    @property
    def premium_models(self) -> List[PooledModel]:
        return [m for m in self.models.values() if m.tier == "premium"]

    @property
    def volume_models(self) -> List[PooledModel]:
        return [m for m in self.models.values() if m.tier == "volume"]

    @property
    def all_models(self) -> List[PooledModel]:
        return list(self.models.values())

    async def pick(self, tier: Optional[str] = None) -> str:
        """
        Pick the next model via round-robin.

        tier="premium" → only premium models (falls back to volume if none)
        tier="volume"  → only volume models (falls back to premium if none)
        tier=None      → round-robin across all models
        """
        async with self._lock:
            if tier == "premium":
                pool = self.premium_models or self.volume_models or self.all_models
                self._robin_premium = (self._robin_premium + 1) % len(pool)
                return pool[self._robin_premium - 1].model_id
            elif tier == "volume":
                pool = self.volume_models or self.premium_models or self.all_models
                self._robin_volume = (self._robin_volume + 1) % len(pool)
                return pool[self._robin_volume - 1].model_id
            else:
                pool = self.all_models
                self._robin_all = (self._robin_all + 1) % len(pool)
                return pool[self._robin_all - 1].model_id

    async def call(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        timeout: float = 90.0,
    ) -> str:
        """
        Make an LLM call with semaphore-controlled concurrency, timeout, and stats tracking.
        Returns the response content string.
        Raises on failure (caller should handle failover).
        """
        if not self.client:
            raise RuntimeError("No OpenRouter API key configured")

        model = self.models.get(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not in pool")

        async with model.semaphore:
            start = time.monotonic()
            try:
                kwargs = {
                    "model": model_id,
                    "messages": messages,
                    "temperature": temperature,
                    "timeout": timeout,
                }
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens
                if response_format:
                    kwargs["response_format"] = response_format

                response = await asyncio.wait_for(
                    self.client.chat.completions.create(**kwargs),
                    timeout=timeout,
                )
                content = response.choices[0].message.content

                elapsed = (time.monotonic() - start) * 1000
                model.stats.calls += 1
                model.stats.total_latency_ms += elapsed

                return content

            except asyncio.TimeoutError:
                elapsed = (time.monotonic() - start) * 1000
                model.stats.calls += 1
                model.stats.errors += 1
                model.stats.total_latency_ms += elapsed
                model.stats.last_error = f"Timeout after {timeout}s"
                raise TimeoutError(f"LLM call to {model_id} timed out after {timeout}s")

            except Exception as e:
                elapsed = (time.monotonic() - start) * 1000
                model.stats.calls += 1
                model.stats.errors += 1
                model.stats.total_latency_ms += elapsed
                model.stats.last_error = str(e)
                raise

    async def call_with_failover(
        self,
        tier: Optional[str],
        messages: List[Dict[str, str]],
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        timeout: float = 90.0,
        retries: int = 2,
    ) -> tuple[str, str]:
        """
        Pick a model, call it, failover to another model if it fails.
        Retries each model up to `retries` times before moving on.
        Returns (response_content, model_id_used).
        """
        tried = set()
        last_error = None

        for _ in range(min(3, len(self.models))):
            model_id = await self.pick(tier)
            if model_id in tried:
                continue
            tried.add(model_id)

            for attempt in range(retries):
                try:
                    content = await self.call(
                        model_id=model_id,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format=response_format,
                        timeout=timeout,
                    )
                    return content, model_id
                except (TimeoutError, asyncio.TimeoutError) as e:
                    last_error = e
                    print(f"Model {model_id} timeout (attempt {attempt + 1}/{retries}): {e}")
                    if attempt < retries - 1:
                        await asyncio.sleep(1)  # Brief pause before retry
                    continue
                except Exception as e:
                    last_error = e
                    print(f"Model {model_id} failed (attempt {attempt + 1}/{retries}): {e}")
                    break  # Don't retry non-timeout errors, try next model

        raise last_error or RuntimeError("All models failed")

    def get_stats(self) -> Dict[str, Any]:
        """Get per-model and aggregate stats."""
        model_stats = {}
        total_calls = 0
        total_errors = 0

        for model_id, model in self.models.items():
            model_stats[model_id] = {
                "tier": model.tier,
                **model.stats.to_dict(),
            }
            total_calls += model.stats.calls
            total_errors += model.stats.errors

        return {
            "models": model_stats,
            "total_calls": total_calls,
            "total_errors": total_errors,
            "overall_error_rate": round(total_errors / total_calls, 3) if total_calls else 0,
        }


# Singleton pool instance
_pool: Optional[ModelPool] = None


def get_model_pool() -> ModelPool:
    """Get or create the global model pool singleton."""
    global _pool
    if _pool is None:
        _pool = ModelPool()
    return _pool
