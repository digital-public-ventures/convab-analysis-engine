"""LLM utilities package.

This package provides a unified interface for LLM interactions including:
- Model configuration and rate limiting
- Structured content generation
- Token tracking and cost calculation
"""

from .config import SCHEMA_OUTPUT_DIR, TOKEN_USAGE_FILE
from .costs import calculate_cost, get_model_pricing
from .gemini_client import generate_structured_content, validate_model_config
from .model_config import MODEL_ID_TO_ALIAS, MODELS, ModelPricing, ModelProfile, get_model_profile, resolve_model_id
from .rate_limiter import AsyncRateLimiter, RateLimitExceededError
from .response_parser import extract_json_from_response
from .token_tracking import record_token_usage

__all__ = [
    # Configuration
    "TOKEN_USAGE_FILE",
    "SCHEMA_OUTPUT_DIR",
    # Model configuration
    "MODELS",
    "MODEL_ID_TO_ALIAS",
    "ModelPricing",
    "ModelProfile",
    "get_model_profile",
    "resolve_model_id",
    # Rate limiting
    "AsyncRateLimiter",
    "RateLimitExceededError",
    # Content generation
    "generate_structured_content",
    "validate_model_config",
    # Response parsing
    "extract_json_from_response",
    # Token tracking and costs
    "record_token_usage",
    "calculate_cost",
    "get_model_pricing",
]
