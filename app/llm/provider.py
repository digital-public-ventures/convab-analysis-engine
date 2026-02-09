"""Provider selection and client factory utilities for LLM integrations."""

from __future__ import annotations

import os
from typing import Literal

LLMProvider = Literal['gemini', 'openai']

_SUPPORTED_PROVIDERS = {'gemini', 'openai'}
_API_KEY_ENV_BY_PROVIDER: dict[LLMProvider, str] = {
    'gemini': 'GEMINI_API_KEY',
    'openai': 'OPENAI_API_KEY',
}


def get_llm_provider() -> LLMProvider:
    """Resolve configured LLM provider from environment.

    Uses `LLM_PROVIDER` with a default of `gemini`.
    """
    configured = os.environ.get('LLM_PROVIDER', 'gemini').strip().lower()
    if configured not in _SUPPORTED_PROVIDERS:
        msg = f'Unsupported LLM_PROVIDER={configured!r}. Expected one of {sorted(_SUPPORTED_PROVIDERS)}.'
        raise ValueError(msg)
    return configured  # type: ignore[return-value]


def get_api_key_env_var(provider: LLMProvider | None = None) -> str:
    """Return API-key environment variable name for the selected provider."""
    resolved_provider = provider or get_llm_provider()
    return _API_KEY_ENV_BY_PROVIDER[resolved_provider]


def resolve_api_key(api_key: str | None = None, provider: LLMProvider | None = None) -> str:
    """Resolve API key from explicit value or provider-specific environment variable."""
    if api_key:
        return api_key
    env_var = get_api_key_env_var(provider=provider)
    resolved = os.environ.get(env_var)
    if not resolved:
        raise ValueError(f'{env_var} environment variable not set')
    return resolved


def create_llm_client(api_key: str | None = None, provider: LLMProvider | None = None) -> object:
    """Create provider-specific SDK client."""
    resolved_provider = provider or get_llm_provider()
    resolved_api_key = resolve_api_key(api_key=api_key, provider=resolved_provider)

    if resolved_provider == 'gemini':
        from google import genai

        return genai.Client(api_key=resolved_api_key)

    from openai import OpenAI

    return OpenAI(api_key=resolved_api_key)
