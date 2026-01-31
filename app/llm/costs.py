"""LLM model pricing information for cost calculation."""

from typing import cast

from .model_config import MODELS, Pricing, get_model_profile

PRICING_BY_MODEL_ID: dict[str, Pricing] = {
    "gpt-5.2": {
        "input": 1.75,
        "output": 14.00,
        "thinking": 14.00,
        "pricing_unit": 1_000_000,
    },
    "gpt-5-mini": {
        "input": 0.25,
        "output": 2.00,
        "thinking": 2.00,
        "pricing_unit": 1_000_000,
    },
}


def get_model_pricing(model_id: str) -> Pricing | None:
    """Get pricing information for a specific model.

    Args:
        model_id: Model identifier (e.g., 'gemini-3-flash-preview')

    Returns:
        Pricing dictionary or None if not found
    """
    profile = get_model_profile(model_id, models_dict=MODELS)
    if profile and profile.pricing:
        return cast(Pricing, profile.pricing)

    return PRICING_BY_MODEL_ID.get(model_id)


def calculate_cost(input_tokens: int, output_tokens: int, thinking_tokens: int, model_id: str) -> float:
    """Calculate the total cost for a model invocation.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        thinking_tokens: Number of thinking tokens
        model_id: Model identifier

    Returns:
        Total cost in USD, or 0.0 if pricing not found
    """
    pricing = get_model_pricing(model_id)
    if not pricing:
        return 0.0

    unit = pricing["pricing_unit"]

    cost = (
        (input_tokens * pricing["input"] / unit)
        + (output_tokens * pricing["output"] / unit)
        + (thinking_tokens * pricing["thinking"] / unit)
    )

    return round(cost, 6)
