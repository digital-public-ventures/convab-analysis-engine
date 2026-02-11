"""Provider selection and client factory utilities for LLM integrations."""

from __future__ import annotations

import os

from .model_config import LLMProvider, SUPPORTED_PROVIDERS, get_model_provider

_API_KEY_ENV_BY_PROVIDER: dict[LLMProvider, str] = {
    'gemini': 'GEMINI_API_KEY',
    'openai': 'OPENAI_API_KEY',
}


def _configured_provider() -> LLMProvider | None:
    configured = os.environ.get('LLM_PROVIDER')
    if configured is None or not configured.strip():
        return None
    normalized = configured.strip().lower()
    if normalized not in SUPPORTED_PROVIDERS:
        msg = f'Unsupported LLM_PROVIDER={normalized!r}. Expected one of {sorted(SUPPORTED_PROVIDERS)}.'
        raise ValueError(msg)
    return normalized  # type: ignore[return-value]


def get_llm_provider(model_id_or_key: str | None = None) -> LLMProvider:
    """Resolve active provider.

    Provider resolution precedence:
    1. If `model_id_or_key` resolves to a known model provider, use it.
       If `LLM_PROVIDER` is also set, it must match.
    2. Else use `LLM_PROVIDER` when set.
    3. Else default to `gemini`.
    """
    configured = _configured_provider()

    if model_id_or_key:
        inferred = get_model_provider(model_id_or_key)
        if inferred:
            if configured and configured != inferred:
                msg = (
                    f"LLM_PROVIDER={configured!r} conflicts with model {model_id_or_key!r} "
                    f"(provider={inferred!r})."
                )
                raise ValueError(msg)
            return inferred

    if configured:
        return configured
    return 'gemini'


def get_api_key_env_var(provider: LLMProvider | None = None, model_id_or_key: str | None = None) -> str:
    """Return API-key environment variable name for the selected provider."""
    resolved_provider = provider or get_llm_provider(model_id_or_key=model_id_or_key)
    return _API_KEY_ENV_BY_PROVIDER[resolved_provider]


def resolve_api_key(
    api_key: str | None = None,
    provider: LLMProvider | None = None,
    model_id_or_key: str | None = None,
) -> str:
    """Resolve API key from explicit value or provider-specific environment variable."""
    if api_key:
        return api_key
    env_var = get_api_key_env_var(provider=provider, model_id_or_key=model_id_or_key)
    resolved = os.environ.get(env_var)
    if not resolved:
        raise ValueError(f'{env_var} environment variable not set')
    return resolved


def create_llm_client(
    api_key: str | None = None,
    provider: LLMProvider | None = None,
    model_id_or_key: str | None = None,
) -> object:
    """Create provider-specific SDK client."""
    resolved_provider = provider or get_llm_provider(model_id_or_key=model_id_or_key)
    resolved_api_key = resolve_api_key(
        api_key=api_key,
        provider=resolved_provider,
        model_id_or_key=model_id_or_key,
    )

    if resolved_provider == 'gemini':
        from google import genai

        return genai.Client(api_key=resolved_api_key)

    from openai import OpenAI

    return OpenAI(api_key=resolved_api_key)
