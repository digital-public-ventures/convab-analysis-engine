"""OpenAI Responses API client utilities for structured generation."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import random
import string
from datetime import UTC, datetime
from typing import Any, Literal, overload

from app.config import TOKEN_USAGE_FILE
from app.text_normalization import normalize_text_for_llm

from .model_config import ModelProfile, resolve_model_id
from .model_config import validate_model_config as validate_model_profile
from .rate_limiter import AsyncRateLimiter
from .schema_validation import (
    schema_type_name as _schema_type_name,
)
from .schema_validation import (
    validate_response_against_schema as _validate_response_against_schema,
)
from .token_tracking import record_token_usage

logger = logging.getLogger(__name__)


def _to_dict(value: object) -> dict[str, Any] | None:
    """Convert SDK models to dictionaries when possible."""
    if isinstance(value, dict):
        return value
    if hasattr(value, 'model_dump'):
        try:
            dumped = value.model_dump()
            if isinstance(dumped, dict):
                return dumped
        except (AttributeError, TypeError, ValueError):  # pragma: no cover - defensive
            return None
    return None


def _extract_response_text(response: object) -> str | None:
    """Extract assistant text from a Responses API object."""
    output_text = getattr(response, 'output_text', None)
    if isinstance(output_text, str):
        return output_text

    output = getattr(response, 'output', None)
    if not isinstance(output, list):
        return None

    chunks: list[str] = []
    for item in output:
        item_dict = _to_dict(item)
        if not item_dict:
            continue
        content = item_dict.get('content', [])
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get('type') == 'output_text':
                text = part.get('text')
                if isinstance(text, str):
                    chunks.append(text)

    if chunks:
        return ''.join(chunks)
    return None


def _extract_usage_fields(response: object) -> tuple[int, int, int, int] | None:
    """Extract usage fields as (total, input, output, thinking)."""
    usage = getattr(response, 'usage', None)
    if usage is None:
        return None

    usage_dict = _to_dict(usage)
    if usage_dict is None:
        usage_dict = {
            'total_tokens': getattr(usage, 'total_tokens', 0),
            'input_tokens': getattr(usage, 'input_tokens', 0),
            'output_tokens': getattr(usage, 'output_tokens', 0),
            'output_tokens_details': getattr(usage, 'output_tokens_details', None),
        }

    total_tokens = int(usage_dict.get('total_tokens') or 0)
    input_tokens = int(usage_dict.get('input_tokens') or 0)
    output_tokens = int(usage_dict.get('output_tokens') or 0)

    output_details = usage_dict.get('output_tokens_details')
    if not isinstance(output_details, dict):
        output_details = _to_dict(output_details) or {}

    thinking_tokens = int(output_details.get('reasoning_tokens') or 0)
    if thinking_tokens == 0:
        thinking_tokens = max(0, total_tokens - input_tokens - output_tokens)

    return total_tokens, input_tokens, output_tokens, thinking_tokens


def _normalize_reasoning_effort(thinking_level: str) -> str:
    """Map existing thinking-level input to Responses API reasoning effort."""
    normalized = thinking_level.strip().upper()
    effort_map = {
        'NONE': 'none',
        'MINIMAL': 'minimal',
        'LOW': 'low',
        'MEDIUM': 'medium',
        'HIGH': 'high',
        'XHIGH': 'xhigh',
    }
    return effort_map.get(normalized, normalized.lower())


def _build_schema_name(model_id: str) -> str:
    """Build a valid Responses API schema name."""
    safe_chars = [ch if ch.isalnum() else '_' for ch in model_id]
    name = ''.join(safe_chars).strip('_')
    if not name:
        name = 'structured_output'
    return name[:64]


def _normalize_json_schema_for_openai(schema: object) -> object:
    """Normalize app/Gemini-style schema fields to strict JSON Schema for OpenAI."""
    if isinstance(schema, dict):
        normalized: dict[str, object] = {}
        nullable_flag = bool(schema.get('nullable') is True)

        for key, value in schema.items():
            if key == 'nullable':
                continue
            if key == 'type':
                if isinstance(value, str):
                    normalized[key] = _schema_type_name(value)
                elif isinstance(value, list):
                    normalized[key] = [
                        _schema_type_name(item) if isinstance(item, str) else _normalize_json_schema_for_openai(item)
                        for item in value
                    ]
                else:
                    normalized[key] = _normalize_json_schema_for_openai(value)
                continue
            normalized[key] = _normalize_json_schema_for_openai(value)

        if nullable_flag:
            current_type = normalized.get('type')
            if isinstance(current_type, str):
                normalized['type'] = [current_type, 'null']
            elif isinstance(current_type, list):
                if 'null' not in current_type:
                    normalized['type'] = [*current_type, 'null']
            else:
                normalized['type'] = ['null']

        current_type = normalized.get('type')
        is_object_type = (
            current_type == 'object'
            or (isinstance(current_type, list) and 'object' in current_type)
        )
        if is_object_type and 'additionalProperties' not in normalized:
            normalized['additionalProperties'] = False
        if is_object_type and isinstance(normalized.get('properties'), dict):
            normalized['required'] = list(normalized['properties'].keys())
        return normalized

    if isinstance(schema, list):
        return [_normalize_json_schema_for_openai(item) for item in schema]

    return schema


async def _create_response(client: object, request_params: dict[str, object], request_timeout: float) -> object:
    """Call responses.create for either sync or async OpenAI SDK clients."""
    responses_api = getattr(client, 'responses', None)
    create_method = getattr(responses_api, 'create', None)
    if create_method is None:
        msg = 'Client must provide responses.create(...)'
        raise AttributeError(msg)

    if inspect.iscoroutinefunction(create_method):
        return await asyncio.wait_for(create_method(**request_params), timeout=request_timeout)

    response = await asyncio.wait_for(asyncio.to_thread(create_method, **request_params), timeout=request_timeout)
    if inspect.isawaitable(response):
        return await asyncio.wait_for(response, timeout=request_timeout)
    return response


def validate_model_config(model_id_or_key: str, thinking_level: str, models_dict: dict | None = None) -> ModelProfile:
    """Validate model key and thinking level configuration.

    Args:
        model_id_or_key: Model key or full model ID to validate
        thinking_level: Thinking level to validate (NONE, MINIMAL, LOW, MEDIUM, HIGH, XHIGH)
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
        provider='openai',
    )


@overload
async def generate_structured_content(
    client: object,
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
    client: object,
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
    client: object,
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
    """Generate structured content via OpenAI Responses API."""
    original_prompt_len = len(prompt_text)
    prompt_text = normalize_text_for_llm(prompt_text)
    normalized_prompt_len = len(prompt_text)

    normalized_system_instruction = None
    if system_instruction is not None:
        normalized_system_instruction = normalize_text_for_llm(system_instruction)

    if normalized_prompt_len != original_prompt_len:
        logger.debug(
            'Normalized prompt text before OpenAI request: chars %d -> %d',
            original_prompt_len,
            normalized_prompt_len,
        )
    if system_instruction is not None and normalized_system_instruction != system_instruction:
        logger.debug(
            'Normalized system instruction before OpenAI request: chars %d -> %d',
            len(system_instruction),
            len(normalized_system_instruction or ''),
        )

    resolved_model_id = resolve_model_id(model_id, provider='openai')

    acquired = False
    if isinstance(rate_limiter, AsyncRateLimiter):
        await rate_limiter.acquire_concurrency()
        acquired = True
        estimated_input_tokens = await rate_limiter.count_tokens_and_acquire(
            client=client,  # type: ignore[arg-type]
            model_id=resolved_model_id,
            prompt_text=prompt_text,
            system_instruction=normalized_system_instruction,
            batch_size=batch_size,
        )
        logger.debug('Sending OpenAI request (%d input tokens estimated)...', estimated_input_tokens)

    request_params: dict[str, object] = {
        'model': resolved_model_id,
        'input': prompt_text,
    }

    if normalized_system_instruction:
        request_params['instructions'] = normalized_system_instruction

    if thinking_level:
        normalized_thinking = thinking_level.upper()
        if normalized_thinking != 'NONE':
            reasoning: dict[str, object] = {
                'effort': _normalize_reasoning_effort(normalized_thinking),
            }
            if include_thoughts:
                reasoning['summary'] = 'detailed'
            request_params['reasoning'] = reasoning

    if json_schema:
        normalized_schema = _normalize_json_schema_for_openai(json_schema)
        request_params['text'] = {
            'format': {
                'type': 'json_schema',
                'name': _build_schema_name(resolved_model_id),
                'schema': normalized_schema,
                'strict': True,
            }
        }
        request_params.pop('reasoning', None)

    request_log = {
        'model': resolved_model_id,
        'prompt_text': prompt_text,
        'system_instruction': system_instruction,
        'json_schema': normalized_schema if json_schema else None,
        'thinking_level': thinking_level,
        'include_thoughts': include_thoughts,
        'request_params': request_params,
    }
    logger.debug('OpenAI request: %s', json.dumps(request_log, indent=2, default=str))

    gen_unique_id = ''.join(random.choices(string.ascii_letters, k=8))

    try:
        gen_start = datetime.now(tz=UTC)
        logger.debug('Generating %s at %s', gen_unique_id, gen_start.isoformat())

        response = await _create_response(client, request_params=request_params, request_timeout=request_timeout)

        response_text = _extract_response_text(response)
        usage_fields = _extract_usage_fields(response)

        response_log = {
            'output_text': response_text,
            'usage': usage_fields,
        }
        logger.debug('OpenAI response: %s', json.dumps(response_log, indent=2, default=str))

        response_data = None
        if response_text:
            if json_schema:
                try:
                    response_data = json.loads(response_text)
                except json.JSONDecodeError:
                    if return_full_response:
                        return None, None, response
                    return None, None
                try:
                    _validate_response_against_schema(json_schema, response_data)
                except ValueError as validation_error:
                    logger.error('OpenAI response failed schema validation: %s', validation_error)
                    if return_full_response:
                        return None, None, response
                    return None, None
            else:
                response_data = {'text': response_text}

        gen_end = datetime.now(tz=UTC)
        ms = (gen_end - gen_start).total_seconds() * 1000
        logger.debug('Content %s received in %.1f ms', gen_unique_id, ms)

        usage_metadata = None
        if usage_fields is not None:
            total_tokens, input_tokens, output_tokens, thinking_tokens = usage_fields
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
        if acquired and isinstance(rate_limiter, AsyncRateLimiter):
            rate_limiter.release_concurrency()
