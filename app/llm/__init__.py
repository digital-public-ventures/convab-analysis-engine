"""LLM utilities with provider-aware routing."""

from __future__ import annotations

from typing import Any

from . import gemini_client, openai_client
from .model_config import MODELS, ModelProfile, validate_model_config as validate_model_profile
from .provider import get_llm_provider
from .rate_limiter import AsyncRateLimiter
from .response_parser import extract_json_from_response


def _resolve_client_module(model_id_or_key: str | None = None) -> Any:
    """Resolve provider-specific client module."""
    provider = get_llm_provider(model_id_or_key=model_id_or_key)
    if provider == 'openai':
        return openai_client
    return gemini_client


def validate_model_config(model_id_or_key: str, thinking_level: str, models_dict: dict | None = None) -> ModelProfile:
    """Validate model configuration against resolved provider."""
    provider = get_llm_provider(model_id_or_key=model_id_or_key)
    return validate_model_profile(
        model_id_or_key=model_id_or_key,
        thinking_level=thinking_level,
        models_dict=models_dict,
        provider=provider,
    )


async def generate_structured_content(*args: Any, **kwargs: Any) -> Any:
    """Generate structured content via active provider."""
    model_id = kwargs.get('model_id')
    model_id_or_key = model_id if isinstance(model_id, str) else None
    module = _resolve_client_module(model_id_or_key=model_id_or_key)
    return await module.generate_structured_content(*args, **kwargs)


__all__ = [
    "generate_structured_content",
    "validate_model_config",
    "AsyncRateLimiter",
    "MODELS",
    "ModelProfile",
    "extract_json_from_response",
]
