"""LLM model pricing information for cost calculation."""

from typing import TypedDict, cast


class Pricing(TypedDict):
    """Pricing for a single model."""

    input: float
    output: float
    thinking: float
    pricing_unit: int


model_pricing = [
    {
        "gemini": {
            "gemini_3_flash": {
                "input": 0.50,
                "output": 3.00,
                "thinking": 3.00,
                "pricing_unit": 1_000_000,
            },
            "gemini_3_pro": {
                "input": 2.00,
                "output": 12.00,
                "thinking": 12.00,
                "pricing_unit": 1_000_000,
            },
        }
    },
    {
        "openai": {
            "gpt_5_2": {
                "input": 1.75,
                "output": 14.00,
                "thinking": 14.00,
                "pricing_unit": 1_000_000,
            },
            "gpt_5_mini": {
                "input": 0.25,
                "output": 2.00,
                "thinking": 2.00,
                "pricing_unit": 1_000_000,
            },
        }
    },
]


def get_model_pricing(model_id: str) -> dict | None:
    """Get pricing information for a specific model.

    Args:
        model_id: Model identifier (e.g., 'gemini-3-flash-preview')

    Returns:
        Pricing dictionary or None if not found
    """
    model_map = {
        "gemini-3-flash-preview": ("gemini", "gemini_3_flash"),
        "gemini-3-pro-preview": ("gemini", "gemini_3_pro"),
        "gpt-5.2": ("openai", "gpt_5_2"),
        "gpt-5-mini": ("openai", "gpt_5_mini"),
    }

    if model_id not in model_map:
        return None

    provider, model_key = model_map[model_id]

    for provider_dict in model_pricing:
        if provider in provider_dict:
            return provider_dict[provider].get(model_key)

    return None


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

    pricing_typed = cast(Pricing, pricing)

    unit = pricing_typed["pricing_unit"]

    cost: float = (
        (input_tokens * pricing_typed["input"] / unit)
        + (output_tokens * pricing_typed["output"] / unit)
        + (thinking_tokens * pricing_typed["thinking"] / unit)
    )

    return round(cost, 6)
