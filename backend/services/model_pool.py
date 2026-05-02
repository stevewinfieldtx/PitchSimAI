"""
OpenRouter LLM client for PitchProof AI.

Single model, configured via OPENROUTER_MODEL_ID env var.
All calls go through OpenRouter. Includes timeout, retry, concurrency
throttling, and basic stats tracking.
"""

import asyncio
import time
import logging
from typing import Optional, Dict, List, Any
from openai import AsyncOpenAI

from config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class ModelPool:
    """
    Single-model LLM client with retry and concurrency control.

    Keeps the same interface so swarm_engine, simulation, etc.
    don't need to change.
    """

    def __init__(self):
        self.model_id: str = settings.openrouter_model_id
        self.client = (
            AsyncOpenAI(
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
            )
            if settings.openrouter_api_key
            else None
        )
        self._semaphore = asyncio.Semaphore(settings.openrouter_concurrency_per_model)

        # Stats
        self.calls: int = 0
        self.errors: int = 0
        self.total_latency_ms: float = 0
        self.last_error: Optional[str] = None

    # ── Compatibility properties (used by health endpoints) ──

    @property
    def is_available(self) -> bool:
        return self.client is not None and bool(self.model_id)

    @property
    def models(self) -> Dict[str, Any]:
        return {self.model_id: {"tier": "default"}} if self.model_id else {}

    @property
    def premium_models(self) -> list:
        return [type("M", (), {"model_id": self.model_id})()] if self.model_id else []

    @property
    def volume_models(self) -> list:
        return self.premium_models

    # ── Core call ──

    async def call(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        timeout: float = 90.0,
    ) -> str:
        if not self.client:
            raise RuntimeError("No OpenRouter API key configured")

        async with self._semaphore:
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
                self.calls += 1
                self.total_latency_ms += elapsed
                return content

            except asyncio.TimeoutError:
                elapsed = (time.monotonic() - start) * 1000
                self.calls += 1
                self.errors += 1
                self.total_latency_ms += elapsed
                self.last_error = f"Timeout after {timeout}s"
                raise TimeoutError(f"LLM call timed out after {timeout}s")

            except Exception as e:
                elapsed = (time.monotonic() - start) * 1000
                self.calls += 1
                self.errors += 1
                self.total_latency_ms += elapsed
                self.last_error = str(e)
                raise

    async def call_with_failover(
        self,
        tier: Optional[str],
        messages: List[Dict[str, str]],
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        timeout: float = 90.0,
        retries: int = 3,
    ) -> tuple[str, str]:
        """
        Call the model with retries. tier is ignored (single model).
        Returns (response_content, model_id) for compatibility.
        """
        last_error = None

        for attempt in range(retries):
            try:
                content = await self.call(
                    model_id=self.model_id,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    timeout=timeout,
                )
                return content, self.model_id
            except (TimeoutError, asyncio.TimeoutError) as e:
                last_error = e
                logger.warning(f"Timeout attempt {attempt + 1}/{retries}: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                last_error = e
                logger.warning(f"Error attempt {attempt + 1}/{retries}: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(1)

        raise last_error or RuntimeError("LLM call failed after all retries")

    async def pick(self, tier: Optional[str] = None) -> str:
        return self.model_id

    def get_stats(self) -> Dict[str, Any]:
        avg_latency = self.total_latency_ms / self.calls if self.calls else 0
        error_rate = self.errors / self.calls if self.calls else 0
        return {
            "model": self.model_id,
            "total_calls": self.calls,
            "total_errors": self.errors,
            "avg_latency_ms": round(avg_latency, 1),
            "error_rate": round(error_rate, 3),
            "last_error": self.last_error,
        }


_pool: Optional[ModelPool] = None


def get_model_pool() -> ModelPool:
    global _pool
    if _pool is None:
        _pool = ModelPool()
    return _pool

