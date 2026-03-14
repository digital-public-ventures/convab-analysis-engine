"""Gemini API client utilities for structured generation."""

import asyncio
import json
import logging
import random
import string
from datetime import UTC, datetime
from typing import Literal, overload

from google import genai
from google.genai import types

from app.config import TOKEN_USAGE_FILE
from app.text_normalization import normalize_text_for_llm

from .model_config import (
    ModelProfile,
    resolve_model_id,
)
from .model_config import (
    validate_model_config as validate_model_profile,
)
from .rate_limiter import AsyncRateLimiter
from .schema_validation import validate_response_against_schema as _validate_response_against_schema
from .token_tracking import record_token_usage

logger = logging.getLogger(__name__)


def validate_model_config(model_id_or_key: str, thinking_level: str, models_dict: dict | None = None) -> ModelProfile:
    """Validate model key and thinking level configuration.

    Args:
        model_id_or_key: Model key or full model ID to validate
        thinking_level: Thinking level to validate (MINIMAL, LOW, MEDIUM, HIGH)
        models_dict: Optional dictionary mapping model keys to ModelProfile objects.
                    If None, uses default MODELS dict.

    Returns:
        ModelProfile object if validation succeeds

    Raises:
        ValueError: If model is invalid or thinking_level not supported by model
    """
    return validate_model_profile(
        model_id_or_key=model_id_or_key,
        thinking_level=thinking_level,
        models_dict=models_dict,
        provider='gemini',
    )


@overload
async def generate_structured_content(
    client: genai.Client,
    prompt_text: str,
    model_id: str = 'flash',
    json_schema: dict | None = None,
    system_instruction: str | None = None,
    thinking_level: str | None = None,
    token_usage_file: str = str(TOKEN_USAGE_FILE),
    rate_limiter: AsyncRateLimiter | None = None,
    batch_size: int = 1,
    include_thoughts: bool = False,
    *,
    return_full_response: Literal[True],
) -> tuple[dict | None, dict | None, object]: ...


@overload
async def generate_structured_content(
    client: genai.Client,
    prompt_text: str,
    model_id: str = 'flash',
    json_schema: dict | None = None,
    system_instruction: str | None = None,
    thinking_level: str | None = None,
    token_usage_file: str = str(TOKEN_USAGE_FILE),
    rate_limiter: AsyncRateLimiter | None = None,
    batch_size: int = 1,
    include_thoughts: bool = False,
    return_full_response: Literal[False] = False,
) -> tuple[dict | None, dict | None]: ...


async def generate_structured_content(
    client: genai.Client,
    prompt_text: str,
    model_id: str = 'flash',
    json_schema: dict | None = None,
    system_instruction: str | None = None,
    thinking_level: str | None = None,
    token_usage_file: str = str(TOKEN_USAGE_FILE),
    rate_limiter: AsyncRateLimiter | None = None,
    batch_size: int = 1,
    include_thoughts: bool = False,
    return_full_response: bool = False,
    request_timeout: float = 120.0,
) -> tuple[dict | None, dict | None] | tuple[dict | None, dict | None, object]:
    """Generate structured content using Gemini API with automatic token tracking and rate limiting.

    Args:
        client: Gemini API client instance
        prompt_text: User prompt text
        model_id: Model identifier ('flash' or 'pro') or full model ID (default: 'flash')
        json_schema: Optional JSON schema for structured output
        system_instruction: Optional system instruction to guide model behavior
        thinking_level: Optional thinking level (MINIMAL, LOW, MEDIUM, HIGH)
        token_usage_file: Path to token usage tracking file (default: app.config.TOKEN_USAGE_FILE)
        rate_limiter: Optional AsyncRateLimiter instance for rate limiting
        batch_size: Number of items being processed (for token estimation, default: 1)
        include_thoughts: Whether to include thinking process in response (default: False)
        return_full_response: Whether to return full API response object (default: False)
        request_timeout: Timeout in seconds for the API call (default: 120.0)

    Returns:
        If return_full_response=False: Tuple of (response_data, usage_metadata)
        If return_full_response=True: Tuple of (response_data, usage_metadata, full_response)
        - response_data: Parsed JSON response or None if error
        - usage_metadata: Dict with token counts or None if error
        - full_response: Full Gemini API response object (only if return_full_response=True)
    """
    original_prompt_len = len(prompt_text)
    prompt_text = normalize_text_for_llm(prompt_text)
    normalized_prompt_len = len(prompt_text)

    normalized_system_instruction = None
    if system_instruction is not None:
        normalized_system_instruction = normalize_text_for_llm(system_instruction)

    if normalized_prompt_len != original_prompt_len:
        logger.debug(
            'Normalized prompt text before Gemini request: chars %d -> %d',
            original_prompt_len,
            normalized_prompt_len,
        )
    if system_instruction is not None and normalized_system_instruction != system_instruction:
        logger.debug(
            'Normalized system instruction before Gemini request: chars %d -> %d',
            len(system_instruction),
            len(normalized_system_instruction or ''),
        )

    # Map short model names to full IDs
    resolved_model_id = resolve_model_id(model_id, provider='gemini')

    # If rate limiter provided, count tokens and wait for rate limits
    acquired = False
    if rate_limiter:
        await rate_limiter.acquire_concurrency()
        acquired = True
        estimated_input_tokens = await rate_limiter.count_tokens_and_acquire(
            client=client,
            model_id=resolved_model_id,
            prompt_text=prompt_text,
            system_instruction=normalized_system_instruction,
            batch_size=batch_size,
        )
        logger.debug('Sending request (%d input tokens)...', estimated_input_tokens)

    # Build config
    config_params: dict = {}

    config_params['automatic_function_calling'] = types.AutomaticFunctionCallingConfig(disable=True)

    if thinking_level:
        normalized_thinking_level = thinking_level.upper()
        if normalized_thinking_level == 'NONE':
            config_params.pop('include_thoughts', None)
            config_params.pop('thinking_config', None)
        else:
            thinking_level_enum = types.ThinkingLevel[normalized_thinking_level]
            config_params['thinking_config'] = types.ThinkingConfig(
                thinking_level=thinking_level_enum, include_thoughts=include_thoughts
            )

    if json_schema:
        config_params['response_mime_type'] = 'application/json'
        config_params['response_json_schema'] = json_schema
        config_params.update(
            {
                'temperature': 0,
                'top_k': 1,
                'top_p': 0,
                'candidate_count': 1,
            }
        )
        config_params.pop('include_thoughts', None)
        config_params.pop('thinking_config', None)

    if system_instruction:
        config_params['system_instruction'] = normalized_system_instruction

    config = types.GenerateContentConfig(**config_params)
    request_log = {
        'model': resolved_model_id,
        'prompt_text': prompt_text,
        'system_instruction': system_instruction,
        'response_json_schema': json_schema,
        'thinking_level': thinking_level,
        'include_thoughts': include_thoughts,
        'config_params': config_params,
    }
    logger.debug('Gemini request: %s', json.dumps(request_log, indent=2, default=str))

    try:
        gen_unique_id = ''.join(random.choices(string.ascii_letters, k=8))
        gen_start = datetime.now(tz=UTC)
        logger.debug('Generating %s at %s', gen_unique_id, gen_start.isoformat())

        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=resolved_model_id,
                contents=prompt_text,
                config=config,
            ),
            timeout=request_timeout,
        )
        usage_data = None
        if response.usage_metadata:
            try:
                usage_data = response.usage_metadata.model_dump()
            except AttributeError:
                usage_data = {
                    'total_token_count': getattr(response.usage_metadata, 'total_token_count', None),
                    'prompt_token_count': getattr(response.usage_metadata, 'prompt_token_count', None),
                    'candidates_token_count': getattr(response.usage_metadata, 'candidates_token_count', None),
                }
        response_log = {
            'text': response.text,
            'usage_metadata': usage_data,
            'has_candidates': bool(getattr(response, 'candidates', None)),
        }
        logger.debug('Gemini response: %s', json.dumps(response_log, indent=2, default=str))

        response_data = None
        if response.text:
            if json_schema:
                try:
                    response_data = json.loads(response.text)
                except json.JSONDecodeError:
                    if return_full_response:
                        return None, None, None
                    return None, None
                try:
                    _validate_response_against_schema(json_schema, response_data)
                except ValueError as validation_error:
                    logger.error('Gemini response failed schema validation: %s', validation_error)
                    if return_full_response:
                        return None, None, response
                    return None, None
            else:
                response_data = {'text': response.text}

        gen_end = datetime.now(tz=UTC)
        ms = (gen_end - gen_start).total_seconds() * 1000
        logger.debug('Content %s received in %.1f ms', gen_unique_id, ms)

        # Track token usage
        usage_metadata = None
        if response.usage_metadata:
            total_tokens = response.usage_metadata.total_token_count or 0
            input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
            output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0
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
                'total_tokens': total_tokens,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'thinking_tokens': thinking_tokens,
            }

        if return_full_response:
            return response_data, usage_metadata, response
        return response_data, usage_metadata

    except TimeoutError:
        logger.error('API request %s timed out after %.0fs', gen_unique_id, request_timeout)
        if return_full_response:
            return None, None, None
        return None, None
    except Exception as e:
        logger.error('API Error: %s', e)
        if return_full_response:
            return None, None, None
        return None, None
    finally:
        if acquired and rate_limiter:
            rate_limiter.release_concurrency()
