"""Shared OpenAI Responses API defaults for CureCompass.

gpt-6-luna supports structured outputs on the Responses API and reasoning.effort
including ``none``. Latency-sensitive medical JSON workflows set effort to
``none`` (configurable via OPENAI_REASONING_EFFORT) so behavior stays closer to
the previous non-reasoning gpt-4.1-mini profile. Embeddings stay on
OPENAI_EMBEDDING_MODEL and are not handled here.
"""

from __future__ import annotations

from typing import Any

from app.core.config import settings


def responses_reasoning_param() -> dict[str, str]:
    """Return the ``reasoning`` kwarg for ``client.responses.create``."""
    effort = (settings.openai_reasoning_effort or "none").strip().lower() or "none"
    return {"effort": effort}


def responses_create_kwargs(
    *,
    input: Any,
    text: dict[str, Any],
    timeout: float | int,
    **extra: Any,
) -> dict[str, Any]:
    """Build kwargs for Responses create: model, reasoning, structured text, timeout."""
    return {
        "model": settings.openai_responses_model,
        "input": input,
        "text": text,
        "timeout": timeout,
        "reasoning": responses_reasoning_param(),
        **extra,
    }
