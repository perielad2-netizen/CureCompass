"""Shared OpenAI Responses API defaults for CureCompass.

Builds ``client.responses.create`` kwargs with model-aware reasoning:

- ``gpt-6-luna`` (and snapshots): include ``reasoning.effort`` from
  ``OPENAI_REASONING_EFFORT`` (default ``none``), validated against Luna's
  supported efforts.
- ``gpt-4.1-mini`` (legacy rollback): omit ``reasoning`` entirely — it is a
  non-reasoning model and may reject the parameter.
- Unknown / other overrides: omit ``reasoning`` (do not assume support).

Strict JSON Schema structured outputs (``text.format``) are unchanged.
Embeddings stay on ``OPENAI_EMBEDDING_MODEL`` and are not handled here.
"""

from __future__ import annotations

from typing import Any

from app.core.config import settings

# gpt-6-luna documented efforts (Responses API reasoning.effort).
_GPT6_LUNA_EFFORTS = frozenset({"none", "low", "medium", "high", "xhigh", "max"})


def _normalize_model_id(model: str) -> str:
    return (model or "").strip().lower()


def model_supports_responses_reasoning(model: str) -> bool:
    """Return True only for models known to accept Responses ``reasoning``."""
    m = _normalize_model_id(model)
    if not m:
        return False
    # Snapshots look like gpt-6-luna or gpt-6-luna-YYYY-MM-DD.
    if m == "gpt-6-luna" or m.startswith("gpt-6-luna-"):
        return True
    return False


def model_is_legacy_non_reasoning(model: str) -> bool:
    """True for gpt-4.1-mini rollback IDs (base or dated snapshot)."""
    m = _normalize_model_id(model)
    return m == "gpt-4.1-mini" or m.startswith("gpt-4.1-mini-")


def supported_reasoning_efforts(model: str) -> frozenset[str] | None:
    """Supported effort values for ``model``, or None if reasoning is unsupported."""
    if not model_supports_responses_reasoning(model):
        return None
    m = _normalize_model_id(model)
    if m == "gpt-6-luna" or m.startswith("gpt-6-luna-"):
        return _GPT6_LUNA_EFFORTS
    return None


def responses_reasoning_param(
    *,
    model: str | None = None,
    effort: str | None = None,
) -> dict[str, str] | None:
    """Return ``reasoning`` kwarg, or None when the model must not receive it.

    Validates configured effort against the selected model's capabilities.
    Raises ``ValueError`` if reasoning is supported but the effort is invalid.
    """
    model_id = model if model is not None else settings.openai_responses_model
    allowed = supported_reasoning_efforts(model_id)
    if allowed is None:
        return None

    raw = effort if effort is not None else settings.openai_reasoning_effort
    normalized = (raw or "none").strip().lower() or "none"
    if normalized not in allowed:
        raise ValueError(
            f"Unsupported OPENAI_REASONING_EFFORT={normalized!r} for model "
            f"{model_id!r}; allowed: {sorted(allowed)}"
        )
    return {"effort": normalized}


def responses_create_kwargs(
    *,
    input: Any,
    text: dict[str, Any],
    timeout: float | int,
    **extra: Any,
) -> dict[str, Any]:
    """Build kwargs for Responses create: model, optional reasoning, structured text, timeout."""
    model_id = settings.openai_responses_model
    kwargs: dict[str, Any] = {
        "model": model_id,
        "input": input,
        "text": text,
        "timeout": timeout,
    }
    reasoning = responses_reasoning_param(model=model_id)
    if reasoning is not None:
        kwargs["reasoning"] = reasoning
    kwargs.update(extra)
    return kwargs
