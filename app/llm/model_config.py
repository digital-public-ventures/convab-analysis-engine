"""LLM model configuration profiles and rate limits."""

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
        pricing: Pricing | None = None,
    ):
        """Initialize a model profile.

        Args:
            model_id: Full model identifier
            rpm: Requests per minute limit
            tpm: Tokens per minute limit
            rpd: Requests per day limit
            allowed_thinking: List of allowed thinking levels
            pricing: Optional pricing metadata for token cost calculation
        """
        self.model_id = model_id
        self.rpm = rpm
        self.tpm = tpm
        self.rpd = rpd
        self.allowed_thinking = allowed_thinking
        self.pricing = pricing


MODELS = {
    "flash": ModelProfile(
        model_id="gemini-3-flash-preview",
        rpm=1000,
        tpm=1_000_000,
        rpd=10_000,
        allowed_thinking=["MINIMAL", "LOW", "MEDIUM", "HIGH"],
        pricing={
            "input": 0.50,
            "output": 3.00,
            "thinking": 3.00,
            "pricing_unit": 1_000_000,
        },
    ),
    "pro": ModelProfile(
        model_id="gemini-3-pro-preview",
        rpm=25,
        tpm=1_000_000,
        rpd=250,
        allowed_thinking=["LOW", "MEDIUM", "HIGH"],  # Pro does NOT support MINIMAL
        pricing={
            "input": 2.00,
            "output": 12.00,
            "thinking": 12.00,
            "pricing_unit": 1_000_000,
        },
    ),
}

MODEL_ALIASES = {
    "gemini-pro": "pro",
    "gemini-flash": "flash",
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
