"""LLM utilities with provider-aware routing."""

from __future__ import annotations

from typing import Any

from . import gemini_client, openai_client
from .model_config import MODELS, ModelProfile
from .provider import get_llm_provider
from .rate_limiter import AsyncRateLimiter
from .response_parser import extract_json_from_response


def _resolve_client_module() -> Any:
    """Resolve provider-specific client module."""
    provider = get_llm_provider()
    if provider == 'openai':
        return openai_client
    return gemini_client


def validate_model_config(model_id_or_key: str, thinking_level: str, models_dict: dict | None = None) -> ModelProfile:
    """Validate model configuration against active provider."""
    module = _resolve_client_module()
    return module.validate_model_config(
        model_id_or_key=model_id_or_key,
        thinking_level=thinking_level,
        models_dict=models_dict,
    )


async def generate_structured_content(*args: Any, **kwargs: Any) -> Any:
    """Generate structured content via active provider."""
    module = _resolve_client_module()
    return await module.generate_structured_content(*args, **kwargs)


__all__ = [
    "generate_structured_content",
    "validate_model_config",
    "AsyncRateLimiter",
    "MODELS",
    "ModelProfile",
    "extract_json_from_response",
]
