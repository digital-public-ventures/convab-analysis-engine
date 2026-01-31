"""LLM model configuration profiles, rate limits, and pricing.

This module provides a unified registry for model configuration including:
- Model identifiers and short aliases
- Rate limits (RPM, TPM, RPD)
- Thinking level capabilities
- Pricing information
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    """Pricing information for a model.

    All prices are per 1 million tokens in USD.
    """

    input: float
    output: float
    thinking: float
    pricing_unit: int = 1_000_000


@dataclass
class ModelProfile:
    """Model configuration profile with rate limits, capabilities, and pricing."""

    model_id: str
    rpm: int
    tpm: int
    rpd: int
    allowed_thinking: list[str]
    pricing: ModelPricing | None = None

    def calculate_cost(self, input_tokens: int, output_tokens: int, thinking_tokens: int = 0) -> float:
        """Calculate the total cost for a model invocation.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            thinking_tokens: Number of thinking tokens (default: 0)

        Returns:
            Total cost in USD, or 0.0 if pricing not available
        """
        if not self.pricing:
            return 0.0

        unit = self.pricing.pricing_unit
        cost = (
            (input_tokens * self.pricing.input / unit)
            + (output_tokens * self.pricing.output / unit)
            + (thinking_tokens * self.pricing.thinking / unit)
        )
        return round(cost, 6)


# Unified model registry
# Keys are short aliases, values are complete ModelProfile objects
MODELS: dict[str, ModelProfile] = {
    # Gemini models
    "flash": ModelProfile(
        model_id="gemini-3-flash-preview",
        rpm=1000,
        tpm=1_000_000,
        rpd=10_000,
        allowed_thinking=["MINIMAL", "LOW", "MEDIUM", "HIGH"],
        pricing=ModelPricing(input=0.50, output=3.00, thinking=3.00),
    ),
    "pro": ModelProfile(
        model_id="gemini-3-pro-preview",
        rpm=25,
        tpm=1_000_000,
        rpd=250,
        allowed_thinking=["LOW", "MEDIUM", "HIGH"],  # Pro does NOT support MINIMAL
        pricing=ModelPricing(input=2.00, output=12.00, thinking=12.00),
    ),
    # OpenAI models (placeholders for future use)
    "gpt-5.2": ModelProfile(
        model_id="gpt-5.2",
        rpm=500,
        tpm=800_000,
        rpd=10_000,
        allowed_thinking=["LOW", "MEDIUM", "HIGH"],
        pricing=ModelPricing(input=1.75, output=14.00, thinking=14.00),
    ),
    "gpt-5-mini": ModelProfile(
        model_id="gpt-5-mini",
        rpm=1000,
        tpm=1_000_000,
        rpd=10_000,
        allowed_thinking=["LOW", "MEDIUM", "HIGH"],
        pricing=ModelPricing(input=0.25, output=2.00, thinking=2.00),
    ),
}

# Reverse lookup: full model ID -> short alias
MODEL_ID_TO_ALIAS: dict[str, str] = {profile.model_id: alias for alias, profile in MODELS.items()}


def get_model_profile(model_key: str) -> ModelProfile | None:
    """Get a model profile by short alias or full model ID.

    Args:
        model_key: Short alias (e.g., 'flash') or full model ID (e.g., 'gemini-3-flash-preview')

    Returns:
        ModelProfile if found, None otherwise
    """
    # Try direct lookup by alias
    if model_key in MODELS:
        return MODELS[model_key]

    # Try lookup by full model ID
    alias = MODEL_ID_TO_ALIAS.get(model_key)
    if alias:
        return MODELS[alias]

    return None


def resolve_model_id(model_key: str) -> str:
    """Resolve a short alias to a full model ID.

    Args:
        model_key: Short alias (e.g., 'flash') or full model ID

    Returns:
        Full model ID (returns input as-is if not in registry)
    """
    profile = get_model_profile(model_key)
    if profile:
        return profile.model_id

    # Return as-is if not in registry (allows custom model IDs)
    return model_key
