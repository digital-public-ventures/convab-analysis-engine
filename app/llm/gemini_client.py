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

from .model_config import MODELS, ModelProfile, get_model_profile, resolve_model_id
from .rate_limiter import AsyncRateLimiter
from .token_tracking import record_token_usage

logger = logging.getLogger(__name__)


def _schema_type_name(schema_type: str) -> str:
    """Normalize schema type names across JSON Schema and Gemini style."""
    return schema_type.strip().lower()


def _python_type_name(value: object) -> str:
    """Get a stable type name for validation errors."""
    if value is None:
        return 'null'
    return type(value).__name__


def _matches_schema_type(value: object, schema_type: str) -> bool:
    """Check whether a value matches a JSON-schema-like type."""
    normalized_type = _schema_type_name(schema_type)
    if normalized_type == 'object':
        return isinstance(value, dict)
    if normalized_type == 'array':
        return isinstance(value, list)
    if normalized_type == 'string':
        return isinstance(value, str)
    if normalized_type == 'number':
        return isinstance(value, int | float) and not isinstance(value, bool)
    if normalized_type == 'integer':
        return isinstance(value, int) and not isinstance(value, bool)
    if normalized_type == 'boolean':
        return isinstance(value, bool)
    if normalized_type == 'null':
        return value is None
    return True


def _validate_response_against_schema(schema: dict, value: object, path: str = '$') -> None:
    """Validate response JSON against a response_json_schema.

    Supports the subset used in this project (type, nullable, required, properties,
    items, additionalProperties, enum, min/max constraints).
    """
    if value is None and schema.get('nullable') is True:
        return

    schema_type = schema.get('type')
    if isinstance(schema_type, str):
        if not _matches_schema_type(value, schema_type):
            normalized_type = _schema_type_name(schema_type)
            msg = f'{path}: expected {normalized_type}, got {_python_type_name(value)}'
            raise ValueError(msg)
    elif isinstance(schema_type, list):
        if not any(_matches_schema_type(value, t) for t in schema_type if isinstance(t, str)):
            expected_types = ','.join(sorted(_schema_type_name(t) for t in schema_type if isinstance(t, str)))
            msg = f'{path}: expected one of [{expected_types}], got {_python_type_name(value)}'
            raise ValueError(msg)

    if 'enum' in schema and value not in schema['enum']:
        msg = f'{path}: value not in enum {schema["enum"]}'
        raise ValueError(msg)

    normalized_type = _schema_type_name(schema_type) if isinstance(schema_type, str) else None
    if normalized_type == 'object' and isinstance(value, dict):
        required_fields = schema.get('required', [])
        for field_name in required_fields:
            if field_name not in value:
                msg = f'{path}: missing required field "{field_name}"'
                raise ValueError(msg)

        properties = schema.get('properties', {})
        additional_properties = schema.get('additionalProperties', True)
        if additional_properties is False:
            unexpected = sorted(key for key in value if key not in properties)
            if unexpected:
                msg = f'{path}: unexpected fields {unexpected}'
                raise ValueError(msg)

        for field_name, field_value in value.items():
            field_schema = properties.get(field_name)
            if field_schema is not None:
                _validate_response_against_schema(field_schema, field_value, f'{path}.{field_name}')

    if normalized_type == 'array' and isinstance(value, list):
        min_items = schema.get('minItems')
        max_items = schema.get('maxItems')
        if isinstance(min_items, int) and len(value) < min_items:
            msg = f'{path}: expected at least {min_items} items, got {len(value)}'
            raise ValueError(msg)
        if isinstance(max_items, int) and len(value) > max_items:
            msg = f'{path}: expected at most {max_items} items, got {len(value)}'
            raise ValueError(msg)

        item_schema = schema.get('items')
        if isinstance(item_schema, dict):
            for idx, item in enumerate(value):
                _validate_response_against_schema(item_schema, item, f'{path}[{idx}]')

    if normalized_type == 'string' and isinstance(value, str):
        min_length = schema.get('minLength')
        max_length = schema.get('maxLength')
        if isinstance(min_length, int) and len(value) < min_length:
            msg = f'{path}: expected minLength {min_length}, got {len(value)}'
            raise ValueError(msg)
        if isinstance(max_length, int) and len(value) > max_length:
            msg = f'{path}: expected maxLength {max_length}, got {len(value)}'
            raise ValueError(msg)

    if normalized_type in {'number', 'integer'} and isinstance(value, int | float) and not isinstance(value, bool):
        minimum = schema.get('minimum')
        maximum = schema.get('maximum')
        if isinstance(minimum, int | float) and value < minimum:
            msg = f'{path}: expected minimum {minimum}, got {value}'
            raise ValueError(msg)
        if isinstance(maximum, int | float) and value > maximum:
            msg = f'{path}: expected maximum {maximum}, got {value}'
            raise ValueError(msg)


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
    if models_dict is None:
        models_dict = MODELS

    profile = get_model_profile(model_id_or_key, models_dict=models_dict)
    if not profile:
        available_keys = list(models_dict.keys())
        available_ids = [model.model_id for model in models_dict.values()]
        msg = f'Invalid model. Choose from keys: {available_keys} or model IDs: {available_ids}'
        raise ValueError(msg)

    if thinking_level not in profile.allowed_thinking:
        msg = (
            f"Model {profile.model_id} does not support thinking level '{thinking_level}'. "
            f'Allowed: {profile.allowed_thinking}'
        )
        raise ValueError(msg)

    return profile


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
    prompt_text = normalize_text_for_llm(
        prompt_text,
        newline_strategy='space',
        encoding_strategy='ascii_ignore',
    )
    normalized_prompt_len = len(prompt_text)

    normalized_system_instruction = None
    if system_instruction is not None:
        normalized_system_instruction = normalize_text_for_llm(
            system_instruction,
            newline_strategy='space',
            encoding_strategy='ascii_ignore',
        )

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
    resolved_model_id = resolve_model_id(model_id, models_dict=MODELS)

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
