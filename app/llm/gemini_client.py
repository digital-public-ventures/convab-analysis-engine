"""Gemini API client utilities for structured generation."""

import json
import logging
import random
import string
from datetime import UTC, datetime
from typing import Literal, overload

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .model_config import MODELS, ModelProfile
from .rate_limiter import AsyncRateLimiter
from .token_tracking import record_token_usage

load_dotenv()

logger = logging.getLogger(__name__)

# Model ID mappings
MODEL_IDS = {
    "flash": "gemini-3-flash-preview",
    "pro": "gemini-3-pro-preview",
}


def validate_model_config(model_key: str, thinking_level: str, models_dict: dict | None = None) -> ModelProfile:
    """Validate model key and thinking level configuration.

    Args:
        model_key: Model key to validate ('flash' or 'pro')
        thinking_level: Thinking level to validate (MINIMAL, LOW, MEDIUM, HIGH)
        models_dict: Optional dictionary mapping model keys to ModelProfile objects.
                    If None, uses default MODELS dict.

    Returns:
        ModelProfile object if validation succeeds

    Raises:
        ValueError: If model_key is invalid or thinking_level not supported by model
    """
    if models_dict is None:
        models_dict = MODELS

    if model_key not in models_dict:
        available_keys = list(models_dict.keys())
        msg = f"Invalid model key. Choose from: {available_keys}"
        raise ValueError(msg)

    profile = models_dict[model_key]

    if thinking_level not in profile.allowed_thinking:
        msg = (
            f"Model {profile.model_id} does not support thinking level '{thinking_level}'. "
            f"Allowed: {profile.allowed_thinking}"
        )
        raise ValueError(msg)

    return profile


@overload
async def generate_structured_content(
    client: genai.Client,
    prompt_text: str,
    model_id: str = "flash",
    json_schema: dict | None = None,
    system_instruction: str | None = None,
    thinking_level: str | None = None,
    token_usage_file: str = "temp/token_usage.jsonl",
    rate_limiter: AsyncRateLimiter | None = None,
    batch_size: int = 1,
    include_thoughts: bool = False,
    *,
    return_full_response: Literal[True],
) -> tuple[dict | None, dict | None, object]:
    ...


@overload
async def generate_structured_content(
    client: genai.Client,
    prompt_text: str,
    model_id: str = "flash",
    json_schema: dict | None = None,
    system_instruction: str | None = None,
    thinking_level: str | None = None,
    token_usage_file: str = "temp/token_usage.jsonl",
    rate_limiter: AsyncRateLimiter | None = None,
    batch_size: int = 1,
    include_thoughts: bool = False,
    return_full_response: Literal[False] = False,
) -> tuple[dict | None, dict | None]:
    ...


async def generate_structured_content(
    client: genai.Client,
    prompt_text: str,
    model_id: str = "flash",
    json_schema: dict | None = None,
    system_instruction: str | None = None,
    thinking_level: str | None = None,
    token_usage_file: str = "temp/token_usage.jsonl",
    rate_limiter: AsyncRateLimiter | None = None,
    batch_size: int = 1,
    include_thoughts: bool = False,
    return_full_response: bool = False,
) -> tuple[dict | None, dict | None] | tuple[dict | None, dict | None, object]:
    """Generate structured content using Gemini API with automatic token tracking and rate limiting.

    Args:
        client: Gemini API client instance
        prompt_text: User prompt text
        model_id: Model identifier ('flash' or 'pro') or full model ID (default: 'flash')
        json_schema: Optional JSON schema for structured output
        system_instruction: Optional system instruction to guide model behavior
        thinking_level: Optional thinking level (MINIMAL, LOW, MEDIUM, HIGH)
        token_usage_file: Path to token usage tracking file (default: temp/token_usage.jsonl)
        rate_limiter: Optional AsyncRateLimiter instance for rate limiting
        batch_size: Number of items being processed (for token estimation, default: 1)
        include_thoughts: Whether to include thinking process in response (default: False)
        return_full_response: Whether to return full API response object (default: False)

    Returns:
        If return_full_response=False: Tuple of (response_data, usage_metadata)
        If return_full_response=True: Tuple of (response_data, usage_metadata, full_response)
        - response_data: Parsed JSON response or None if error
        - usage_metadata: Dict with token counts or None if error
        - full_response: Full Gemini API response object (only if return_full_response=True)
    """
    # Map short model names to full IDs
    resolved_model_id = MODEL_IDS.get(model_id, model_id)

    # If rate limiter provided, count tokens and wait for rate limits
    acquired = False
    if rate_limiter:
        await rate_limiter.acquire_concurrency()
        acquired = True
        estimated_input_tokens = await rate_limiter.count_tokens_and_acquire(
            client=client,
            model_id=resolved_model_id,
            prompt_text=prompt_text,
            system_instruction=system_instruction,
            batch_size=batch_size,
        )
        logger.debug("Sending request (%d input tokens)...", estimated_input_tokens)

    # Build config
    config_params: dict = {}

    config_params["automatic_function_calling"] = types.AutomaticFunctionCallingConfig(disable=True)

    if json_schema:
        config_params["response_mime_type"] = "application/json"
        config_params["response_schema"] = json_schema

    if system_instruction:
        config_params["system_instruction"] = system_instruction

    if thinking_level:
        thinking_level_enum = types.ThinkingLevel[thinking_level.upper()]
        config_params["thinking_config"] = types.ThinkingConfig(
            thinking_level=thinking_level_enum, include_thoughts=include_thoughts
        )

    config = types.GenerateContentConfig(**config_params)

    try:
        gen_unique_id = "".join(random.choices(string.ascii_letters, k=8))
        gen_start = datetime.now(tz=UTC)
        logger.debug("Generating %s at %s", gen_unique_id, gen_start.isoformat())

        response = await client.aio.models.generate_content(
            model=resolved_model_id,
            contents=prompt_text,
            config=config,
        )

        response_data = None
        if response.text:
            if json_schema:
                try:
                    response_data = json.loads(response.text)
                except json.JSONDecodeError:
                    if return_full_response:
                        return None, None, None
                    return None, None
            else:
                response_data = {"text": response.text}

        gen_end = datetime.now(tz=UTC)
        ms = (gen_end - gen_start).total_seconds() * 1000
        logger.debug("Content %s received in %.1f ms", gen_unique_id, ms)

        # Track token usage
        usage_metadata = None
        if response.usage_metadata:
            total_tokens = response.usage_metadata.total_token_count or 0
            input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
            thinking_tokens = total_tokens - input_tokens - output_tokens

            record_token_usage(
                total_tokens=total_tokens,
                model=resolved_model_id,
                input_tokens=input_tokens,
                thinking_tokens=thinking_tokens,
                output_tokens=output_tokens,
                token_usage_file=token_usage_file,
            )

            usage_metadata = {
                "total_tokens": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "thinking_tokens": thinking_tokens,
            }

        if return_full_response:
            return response_data, usage_metadata, response
        return response_data, usage_metadata

    except Exception as e:
        logger.error("API Error: %s", e)
        if return_full_response:
            return None, None, None
        return None, None
    finally:
        if acquired and rate_limiter:
            rate_limiter.release_concurrency()
