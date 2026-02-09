"""LLM model configuration profiles and rate limits."""

import math
from typing import TypedDict


class Pricing(TypedDict):
    """Pricing for a single model."""

    input: float
    output: float
    thinking: float
    pricing_unit: int


class ModelProfile:
    """Model configuration profile with rate limits and capabilities."""

    def __init__(
        self,
        model_id: str,
        rpm: int,
        tpm: int,
        rpd: int,
        allowed_thinking: list[str],
        max_concurrency: int,
        pricing: Pricing | None = None,
    ):
        """Initialize a model profile.

        Args:
            model_id: Full model identifier
            rpm: Requests per minute limit
            tpm: Tokens per minute limit
            rpd: Requests per day limit
            allowed_thinking: List of allowed thinking levels
            max_concurrency: Max in-flight requests allowed by config
            pricing: Optional pricing metadata for token cost calculation
        """
        self.model_id = model_id
        self.rpm = rpm
        self.tpm = tpm
        self.rpd = rpd
        self.allowed_thinking = allowed_thinking
        self.max_concurrency = max_concurrency
        self.pricing = pricing


RPM_SAFETY_MARGIN = 0.30
AVG_REQUEST_SECONDS = 10.0


def _max_concurrency_from_rpm(rpm: int, safety_margin: float = RPM_SAFETY_MARGIN, request_seconds: float = AVG_REQUEST_SECONDS) -> int:
    """Derive max safe concurrency from RPM budget and average request duration."""
    effective_rpm = max(1, math.floor(rpm * (1 - safety_margin)))
    requests_per_worker_per_minute = max(1.0, 60.0 / max(request_seconds, 0.1))
    return max(1, int(effective_rpm // requests_per_worker_per_minute))


MODELS = {
    'flash': ModelProfile(
        model_id='gemini-3-flash-preview',
        rpm=1000,
        tpm=1_000_000,
        rpd=10_000,
        allowed_thinking=['MINIMAL', 'LOW', 'MEDIUM', 'HIGH'],
        max_concurrency=_max_concurrency_from_rpm(1000),
        pricing={
            'input': 0.50,
            'output': 3.00,
            'thinking': 3.00,
            'pricing_unit': 1_000_000,
        },
    ),
    'lite': ModelProfile(
        model_id='gemini-2.5-flash-lite-preview-09-2025',
        rpm=1000,
        tpm=1_000_000,
        rpd=10_000,
        allowed_thinking=['NONE'],
        max_concurrency=_max_concurrency_from_rpm(1000),
        pricing={
            'input': 0.50,
            'output': 3.00,
            'thinking': 3.00,
            'pricing_unit': 1_000_000,
        },
    ),
    'pro': ModelProfile(
        model_id='gemini-3-pro-preview',
        rpm=25,
        tpm=1_000_000,
        rpd=250,
        allowed_thinking=['LOW', 'MEDIUM', 'HIGH'],  # Pro does NOT support MINIMAL
        max_concurrency=_max_concurrency_from_rpm(25),
        pricing={
            'input': 2.00,
            'output': 12.00,
            'thinking': 12.00,
            'pricing_unit': 1_000_000,
        },
    ),
    'pro_2_5': ModelProfile(
        model_id='gemini-2.5-pro',
        rpm=150,
        tpm=2_000_000,
        rpd=1000,
        allowed_thinking=['LOW', 'HIGH'],
        max_concurrency=_max_concurrency_from_rpm(150),
    ),
    # OpenAI GPT models use tier-based limits. These are conservative Tier 1 defaults.
    'gpt_5_2': ModelProfile(
        model_id='gpt-5.2',
        rpm=500,
        tpm=500_000,
        rpd=1_000_000,
        allowed_thinking=['NONE', 'LOW', 'MEDIUM', 'HIGH', 'XHIGH'],
        max_concurrency=_max_concurrency_from_rpm(500),
        pricing={
            'input': 1.75,
            'output': 14.00,
            'thinking': 14.00,
            'pricing_unit': 1_000_000,
        },
    ),
    'gpt_5_2_codex': ModelProfile(
        model_id='gpt-5.2-codex',
        rpm=500,
        tpm=500_000,
        rpd=1_000_000,
        allowed_thinking=['LOW', 'MEDIUM', 'HIGH', 'XHIGH'],
        max_concurrency=_max_concurrency_from_rpm(500),
        pricing={
            'input': 1.75,
            'output': 14.00,
            'thinking': 14.00,
            'pricing_unit': 1_000_000,
        },
    ),
    'gpt_5_1': ModelProfile(
        model_id='gpt-5.1',
        rpm=500,
        tpm=500_000,
        rpd=1_000_000,
        allowed_thinking=['NONE', 'LOW', 'MEDIUM', 'HIGH'],
        max_concurrency=_max_concurrency_from_rpm(500),
        pricing={
            'input': 1.25,
            'output': 10.00,
            'thinking': 10.00,
            'pricing_unit': 1_000_000,
        },
    ),
    'gpt_5_mini': ModelProfile(
        model_id='gpt-5-mini',
        rpm=500,
        tpm=500_000,
        rpd=1_000_000,
        allowed_thinking=['NONE', 'MINIMAL', 'LOW', 'MEDIUM', 'HIGH'],
        max_concurrency=_max_concurrency_from_rpm(500),
        pricing={
            'input': 0.25,
            'output': 2.00,
            'thinking': 2.00,
            'pricing_unit': 1_000_000,
        },
    ),
    'gpt_5_nano': ModelProfile(
        model_id='gpt-5-nano',
        rpm=500,
        tpm=200_000,
        rpd=1_000_000,
        allowed_thinking=['NONE', 'MINIMAL', 'LOW', 'MEDIUM', 'HIGH'],
        max_concurrency=_max_concurrency_from_rpm(500),
        pricing={
            'input': 0.05,
            'output': 0.40,
            'thinking': 0.40,
            'pricing_unit': 1_000_000,
        },
    ),
}

MODEL_ALIASES = {
    'gemini-pro': 'pro',
    'gemini-flash': 'flash',
    'gemini-lite': 'lite',
    'gemini-2.5-pro': 'pro_2_5',
    'gpt-5.2': 'gpt_5_2',
    'gpt-5.2-2025-12-11': 'gpt_5_2',
    'gpt-5.2-chat-latest': 'gpt_5_2',
    'gpt-5.2-codex': 'gpt_5_2_codex',
    'gpt-5.2-codex-2025-12-11': 'gpt_5_2_codex',
    'gpt-5.1': 'gpt_5_1',
    'gpt-5.1-2025-11-13': 'gpt_5_1',
    'gpt-5.1-chat-latest': 'gpt_5_1',
    'gpt-5-mini': 'gpt_5_mini',
    'gpt-5-mini-2025-08-07': 'gpt_5_mini',
    'gpt-5-nano': 'gpt_5_nano',
    'gpt-5-nano-2025-08-07': 'gpt_5_nano',
}


def get_model_profile(model_id_or_key: str, models_dict: dict[str, ModelProfile] | None = None) -> ModelProfile | None:
    """Resolve a ModelProfile by key, alias, or full model ID."""
    if models_dict is None:
        models_dict = MODELS

    if model_id_or_key in models_dict:
        return models_dict[model_id_or_key]

    alias = MODEL_ALIASES.get(model_id_or_key)
    if alias and alias in models_dict:
        return models_dict[alias]

    for profile in models_dict.values():
        if profile.model_id == model_id_or_key:
            return profile

    return None


def resolve_model_id(model_id_or_key: str, models_dict: dict[str, ModelProfile] | None = None) -> str:
    """Resolve a full model ID from a key or alias."""
    profile = get_model_profile(model_id_or_key, models_dict=models_dict)
    return profile.model_id if profile else model_id_or_key
