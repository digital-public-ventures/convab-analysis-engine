"""LLM model pricing utilities.

This module provides convenience functions for cost calculation.
Pricing data is centralized in model_config.py.
"""

from .model_config import get_model_profile


def get_model_pricing(model_id: str) -> dict | None:
    """Get pricing information for a specific model.

    Args:
        model_id: Model identifier (short alias or full ID)

    Returns:
        Pricing dictionary with 'input', 'output', 'thinking', 'pricing_unit' keys,
        or None if model not found or has no pricing
    """
    profile = get_model_profile(model_id)
    if not profile or not profile.pricing:
        return None

    return {
        "input": profile.pricing.input,
        "output": profile.pricing.output,
        "thinking": profile.pricing.thinking,
        "pricing_unit": profile.pricing.pricing_unit,
    }


def calculate_cost(input_tokens: int, output_tokens: int, thinking_tokens: int, model_id: str) -> float:
    """Calculate the total cost for a model invocation.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        thinking_tokens: Number of thinking tokens
        model_id: Model identifier (short alias or full ID)

    Returns:
        Total cost in USD, or 0.0 if pricing not found
    """
    profile = get_model_profile(model_id)
    if not profile:
        return 0.0

    return profile.calculate_cost(input_tokens, output_tokens, thinking_tokens)
