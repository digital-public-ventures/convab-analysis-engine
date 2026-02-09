"""LLM-powered analysis pipeline for cleaned CSV data."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pandas as pd

from app.config import (
    ANALYSIS_BATCH_SIZE,
    ANALYSIS_CSV_FILENAME,
    ANALYSIS_JSON_FILENAME,
    ANALYSIS_MODEL_ID,
    ANALYSIS_REQUEST_TIMEOUT,
    ANALYSIS_THINKING_LEVEL,
    TOKEN_USAGE_FILE,
)
from app.llm import generate_structured_content, validate_model_config
from app.llm.provider import create_llm_client, resolve_api_key
from app.llm.rate_limiter import AsyncRateLimiter

logger = logging.getLogger(__name__)

MAX_PROMPT_RECORD_CHARS = 500_000
BATCH_CHAR_BUDGET = 100_000
PROMPTS_DIR = Path(__file__).resolve().parent / 'prompts'
ANALYSIS_PROMPT_TEMPLATE = (PROMPTS_DIR / 'analysis_prompt.txt').read_text(encoding='utf-8')
CRITICAL_GUIDELINES = (PROMPTS_DIR / 'critical_guidelines.txt').read_text(encoding='utf-8')

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


@dataclass(frozen=True)
class AnalysisRequest:
    """Inputs required to run an analysis pass."""

    cleaned_csv: Path
    schema_path: Path
    output_dir: Path
    use_case: str
    system_prompt: str


@dataclass(frozen=True)
class AnalysisConfig:
    """Configuration for analysis execution."""

    model_id: str = ANALYSIS_MODEL_ID
    thinking_level: str = ANALYSIS_THINKING_LEVEL
    batch_size: int = ANALYSIS_BATCH_SIZE
    request_timeout: float = ANALYSIS_REQUEST_TIMEOUT


@dataclass(frozen=True)
class AnalysisContext:
    """Shared context for analysis batch calls."""

    system_prompt: str
    schema_summary: str
    use_case: str
    id_column: str
    response_schema: dict[str, Any]
    source_schema_path: str
    source_schema_sha256: str
    response_schema_sha256: str


def _build_analysis_response_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Build a JSON schema for analysis output based on a generated schema.

    Args:
        schema: Generated schema dictionary with enum_fields, categorical_fields,
                scalar_fields, key_quotes_fields, text_array_fields

    Returns:
        JSON schema dictionary for structured LLM output
    """
    enum_fields = schema.get('enum_fields', [])
    categorical_fields = schema.get('categorical_fields', [])
    scalar_fields = schema.get('scalar_fields', [])
    key_quotes_fields = schema.get('key_quotes_fields', [])
    text_array_fields = schema.get('text_array_fields', [])

    enum_props: dict[str, Any] = {}
    for field in enum_fields:
        field_name = field.get('field_name', '').strip()
        if not field_name:
            continue
        enum_props[field_name] = {
            'type': 'STRING',
            'nullable': True,
        }

    categorical_props: dict[str, Any] = {}
    for field in categorical_fields:
        field_name = field.get('field_name', '').strip()
        if not field_name:
            continue
        allow_multiple = bool(field.get('allow_multiple', False))
        if allow_multiple:
            categorical_props[field_name] = {
                'type': 'ARRAY',
                'items': {'type': 'STRING'},
                'nullable': True,
            }
        else:
            categorical_props[field_name] = {
                'type': 'STRING',
                'nullable': True,
            }

    scalar_props: dict[str, Any] = {}
    for field in scalar_fields:
        field_name = field.get('field_name', '').strip()
        if not field_name:
            continue
        scalar_props[field_name] = {
            'type': 'NUMBER',
            'nullable': True,
        }

    key_quotes_props: dict[str, Any] = {}
    for field in key_quotes_fields:
        field_name = field.get('field_name', '').strip()
        if not field_name:
            continue
        key_quotes_props[field_name] = {
            'type': 'ARRAY',
            'items': {'type': 'STRING'},
        }

    text_array_props: dict[str, Any] = {}
    for field in text_array_fields:
        field_name = field.get('field_name', '').strip()
        if not field_name:
            continue
        text_array_props[field_name] = {
            'type': 'ARRAY',
            'items': {'type': 'STRING'},
        }

    return {
        'type': 'OBJECT',
        'properties': {
            'records': {
                'type': 'ARRAY',
                'items': {
                    'type': 'OBJECT',
                    'properties': {
                        'record_id': {'type': 'STRING'},
                        'enum_fields': {
                            'type': 'OBJECT',
                            'properties': enum_props,
                        },
                        'categorical_fields': {
                            'type': 'OBJECT',
                            'properties': categorical_props,
                        },
                        'scalar_fields': {
                            'type': 'OBJECT',
                            'properties': scalar_props,
                        },
                        'key_quotes_fields': {
                            'type': 'OBJECT',
                            'properties': key_quotes_props,
                        },
                        'text_array_fields': {
                            'type': 'OBJECT',
                            'properties': text_array_props,
                        },
                    },
                    'required': ['record_id', 'enum_fields', 'categorical_fields', 'scalar_fields', 'key_quotes_fields', 'text_array_fields'],
                },
            }
        },
        'required': ['records'],
    }


def _summarize_schema(schema: dict[str, Any]) -> str:
    """Create a concise text summary of schema fields for prompting.

    Args:
        schema: Generated schema dictionary

    Returns:
        Human-readable schema summary
    """
    lines: list[str] = []

    enum_fields = schema.get('enum_fields', [])
    if enum_fields:
        lines.append('Enum fields:')
        for field in enum_fields:
            field_name = field.get('field_name', '').strip()
            description = field.get('description', '').strip()
            allowed_values = field.get('allowed_values', [])
            values_text = ', '.join(str(v) for v in allowed_values)
            lines.append(f'- {field_name}: {description} | allowed_values: [{values_text}]')

    categorical_fields = schema.get('categorical_fields', [])
    if categorical_fields:
        lines.append('Categorical fields:')
        for field in categorical_fields:
            field_name = field.get('field_name', '').strip()
            description = field.get('description', '').strip()
            suggested_values = field.get('suggested_values', [])
            allow_multiple = field.get('allow_multiple', False)
            values_text = ', '.join(str(v) for v in suggested_values)
            lines.append(f'- {field_name}: {description} | values: [{values_text}] | allow_multiple={allow_multiple}')

    scalar_fields = schema.get('scalar_fields', [])
    if scalar_fields:
        lines.append('Scalar fields (0-10):')
        for field in scalar_fields:
            field_name = field.get('field_name', '').strip()
            description = field.get('description', '').strip()
            scale_min = field.get('scale_min', 0)
            scale_max = field.get('scale_max', 10)
            lines.append(f'- {field_name}: {description} | scale {scale_min}-{scale_max}')

    key_quotes_fields = schema.get('key_quotes_fields', [])
    if key_quotes_fields:
        lines.append('Key quotes fields:')
        for field in key_quotes_fields:
            field_name = field.get('field_name', '').strip()
            description = field.get('description', '').strip()
            max_quotes = field.get('max_quotes', 1)
            lines.append(f'- {field_name}: {description} | max_quotes={max_quotes}')

    text_array_fields = schema.get('text_array_fields', [])
    if text_array_fields:
        lines.append('Text array fields:')
        for field in text_array_fields:
            field_name = field.get('field_name', '').strip()
            description = field.get('description', '').strip()
            max_items = field.get('max_items')
            max_text = f'max_items={max_items}' if max_items is not None else 'max_items=unlimited'
            lines.append(f'- {field_name}: {description} | {max_text}')

    return '\n'.join(lines)


def _format_records_for_prompt(records: list[dict[str, Any]]) -> str:
    """Format record data for inclusion in the prompt.

    Args:
        records: List of record dictionaries

    Returns:
        Formatted records string
    """
    formatted_records = []
    for i, record in enumerate(records, 1):
        record_json = json.dumps(record, indent=2)
        if len(record_json) > MAX_PROMPT_RECORD_CHARS:
            record_json = record_json[: MAX_PROMPT_RECORD_CHARS - 3] + '...'
        formatted_records.append(f'Record {i}:\n{record_json}\n')
    return '\n'.join(formatted_records)


def _build_analysis_prompt(
    use_case: str,
    schema_summary: str,
    records: list[dict[str, Any]],
    id_column: str,
) -> str:
    """Build the prompt for a batch of records.

    Args:
        use_case: Use case description
        schema_summary: Summary of schema fields
        records: Batch of records to analyze
        id_column: Name of the ID column in the CSV

    Returns:
        Prompt text
    """
    return ANALYSIS_PROMPT_TEMPLATE.format(
        use_case=use_case.strip(),
        schema_summary=schema_summary.strip(),
        id_column=id_column,
        critical_guidelines=CRITICAL_GUIDELINES.strip(),
        records=_format_records_for_prompt(records),
    )


def _build_dynamic_batches(
    records: list[dict[str, Any]],
    max_batch_size: int = ANALYSIS_BATCH_SIZE,
    char_budget: int = BATCH_CHAR_BUDGET,
) -> list[list[dict[str, Any]]]:
    """Group records into batches with dynamic sizing based on character count.

    Larger records result in smaller batches to prevent the LLM from dropping
    responses when the prompt is too complex.

    Args:
        records: All records to batch
        max_batch_size: Maximum records per batch
        char_budget: Maximum total JSON character count per batch

    Returns:
        List of record batches
    """
    batches: list[list[dict[str, Any]]] = []
    current_batch: list[dict[str, Any]] = []
    current_chars = 0

    for record in records:
        record_chars = len(json.dumps(record))

        would_exceed_chars = current_batch and current_chars + record_chars > char_budget
        would_exceed_count = len(current_batch) >= max_batch_size

        if current_batch and (would_exceed_chars or would_exceed_count):
            batches.append(current_batch)
            current_batch = []
            current_chars = 0

        current_batch.append(record)
        current_chars += record_chars

    if current_batch:
        batches.append(current_batch)

    return batches


def _normalize_enum_fields(
    raw_fields: dict[str, Any],
    schema_fields: list[dict[str, Any]],
) -> dict[str, Any]:
    """Normalize enum fields to single string values or None."""
    normalized: dict[str, Any] = {}
    for field in schema_fields:
        field_name = field.get('field_name', '').strip()
        value = raw_fields.get(field_name)
        if value is None:
            normalized[field_name] = None
        elif isinstance(value, list) and value:
            normalized[field_name] = str(value[0])
        else:
            normalized[field_name] = str(value)
    return normalized


def _normalize_categorical_fields(
    raw_fields: dict[str, Any],
    schema_fields: list[dict[str, Any]],
) -> dict[str, Any]:
    """Normalize categorical fields to expected shapes."""
    normalized: dict[str, Any] = {}
    for field in schema_fields:
        field_name = field.get('field_name', '').strip()
        allow_multiple = bool(field.get('allow_multiple', False))
        value = raw_fields.get(field_name)
        if allow_multiple:
            if value is None:
                normalized[field_name] = None
            elif isinstance(value, list):
                normalized[field_name] = [str(v) for v in value]
            else:
                normalized[field_name] = [str(value)]
        elif value is None:
            normalized[field_name] = None
        elif isinstance(value, list) and value:
            normalized[field_name] = str(value[0])
        else:
            normalized[field_name] = str(value)
    return normalized


def _normalize_scalar_fields(
    raw_fields: dict[str, Any],
    schema_fields: list[dict[str, Any]],
) -> dict[str, Any]:
    """Normalize scalar fields to floats or nulls."""
    normalized: dict[str, Any] = {}
    for field in schema_fields:
        field_name = field.get('field_name', '').strip()
        value = raw_fields.get(field_name)
        if value is None or value == '':
            normalized[field_name] = None
        elif isinstance(value, (int, float)):
            normalized[field_name] = float(value)
        else:
            try:
                normalized[field_name] = float(value)
            except (TypeError, ValueError):
                normalized[field_name] = None
    return normalized


def _normalize_key_quotes_fields(
    raw_fields: dict[str, Any],
    schema_fields: list[dict[str, Any]],
) -> dict[str, Any]:
    """Normalize key quote fields to list-of-string arrays."""
    normalized: dict[str, Any] = {}
    for field in schema_fields:
        field_name = field.get('field_name', '').strip()
        value = raw_fields.get(field_name)
        if value is None:
            normalized[field_name] = []
        elif isinstance(value, list):
            normalized[field_name] = [str(v) for v in value]
        else:
            normalized[field_name] = [str(value)]
    return normalized


def _normalize_text_array_fields(
    raw_fields: dict[str, Any],
    schema_fields: list[dict[str, Any]],
) -> dict[str, Any]:
    """Normalize text array fields to list-of-string arrays."""
    normalized: dict[str, Any] = {}
    for field in schema_fields:
        field_name = field.get('field_name', '').strip()
        value = raw_fields.get(field_name)
        if value is None:
            normalized[field_name] = []
        elif isinstance(value, list):
            normalized[field_name] = [str(v) for v in value]
        else:
            normalized[field_name] = [str(value)]
    return normalized


def _normalize_records(
    records: list[dict[str, Any]],
    schema: dict[str, Any],
) -> list[dict[str, Any]]:
    """Normalize LLM outputs to match expected schema."""
    enum_fields = schema.get('enum_fields', [])
    categorical_fields = schema.get('categorical_fields', [])
    scalar_fields = schema.get('scalar_fields', [])
    key_quotes_fields = schema.get('key_quotes_fields', [])
    text_array_fields = schema.get('text_array_fields', [])

    normalized: list[dict[str, Any]] = []
    for record in records:
        record_id = str(record.get('record_id', ''))
        enum_out = _normalize_enum_fields(
            record.get('enum_fields', {}) or {},
            enum_fields,
        )
        categorical_out = _normalize_categorical_fields(
            record.get('categorical_fields', {}) or {},
            categorical_fields,
        )
        scalar_out = _normalize_scalar_fields(
            record.get('scalar_fields', {}) or {},
            scalar_fields,
        )
        quotes_out = _normalize_key_quotes_fields(
            record.get('key_quotes_fields', {}) or {},
            key_quotes_fields,
        )
        text_array_out = _normalize_text_array_fields(
            record.get('text_array_fields', {}) or {},
            text_array_fields,
        )

        normalized.append(
            {
                'record_id': record_id,
                'enum_fields': enum_out,
                'categorical_fields': categorical_out,
                'scalar_fields': scalar_out,
                'key_quotes_fields': quotes_out,
                'text_array_fields': text_array_out,
            }
        )

    return normalized


def _records_to_csv_rows(
    records: list[dict[str, Any]],
    schema: dict[str, Any],
) -> list[dict[str, Any]]:
    """Flatten normalized records into CSV rows.

    Args:
        records: Normalized records
        schema: Generated schema dictionary

    Returns:
        List of flat dictionaries for CSV output
    """
    enum_fields = schema.get('enum_fields', [])
    categorical_fields = schema.get('categorical_fields', [])
    scalar_fields = schema.get('scalar_fields', [])
    key_quotes_fields = schema.get('key_quotes_fields', [])
    text_array_fields = schema.get('text_array_fields', [])

    rows: list[dict[str, Any]] = []
    for record in records:
        row: dict[str, Any] = {'record_id': record.get('record_id', '')}

        enum_out = record.get('enum_fields', {})
        for field in enum_fields:
            field_name = field.get('field_name', '').strip()
            row[field_name] = enum_out.get(field_name)

        categorical_out = record.get('categorical_fields', {})
        for field in categorical_fields:
            field_name = field.get('field_name', '').strip()
            allow_multiple = bool(field.get('allow_multiple', False))
            value = categorical_out.get(field_name)
            if allow_multiple and isinstance(value, list):
                row[field_name] = '; '.join(str(v) for v in value)
            else:
                row[field_name] = value

        scalar_out = record.get('scalar_fields', {})
        for field in scalar_fields:
            field_name = field.get('field_name', '').strip()
            row[field_name] = scalar_out.get(field_name)

        quotes_out = record.get('key_quotes_fields', {})
        for field in key_quotes_fields:
            field_name = field.get('field_name', '').strip()
            quotes = quotes_out.get(field_name)
            if isinstance(quotes, list):
                row[field_name] = ' | '.join(str(v) for v in quotes)
            else:
                row[field_name] = quotes

        text_array_out = record.get('text_array_fields', {})
        for field in text_array_fields:
            field_name = field.get('field_name', '').strip()
            values = text_array_out.get(field_name)
            if isinstance(values, list):
                row[field_name] = ' | '.join(str(v) for v in values)
            else:
                row[field_name] = values

        rows.append(row)

    return rows


async def _analyze_batch(
    client: object,
    limiter: AsyncRateLimiter,
    context: AnalysisContext,
    config: AnalysisConfig,
    records: list[dict[str, Any]],
    batch_index: int | None = None,
) -> list[dict[str, Any]]:
    """Analyze a batch of records using the LLM.

    Args:
        client: API client
        limiter: Async rate limiter
        context: Analysis context for prompt and schema
        config: Analysis configuration
        records: Batch of records

    Returns:
        List of analyzed record dictionaries
    """
    batch_label = f'batch={batch_index}' if batch_index is not None else 'batch=?'
    record_char_sizes = [len(json.dumps(record)) for record in records]
    input_ids = [str(record.get('record_id', '')) for record in records]
    batch_char_size = sum(record_char_sizes)
    logger.debug(
        (
            'Starting analyze %s with %d records, total_record_chars=%d, '
            'record_ids=%s, per_record_chars=%s, schema_path=%s, source_schema_sha256=%s, response_schema_sha256=%s'
        ),
        batch_label,
        len(records),
        batch_char_size,
        input_ids,
        record_char_sizes,
        context.source_schema_path,
        context.source_schema_sha256,
        context.response_schema_sha256,
    )

    started_at = time.monotonic()
    max_retries = 5

    prompt_text = _build_analysis_prompt(
        context.use_case,
        context.schema_summary,
        records,
        context.id_column,
    )

    response_data = None
    for attempt in range(1 + max_retries):
        response_data, _ = await generate_structured_content(
            client=client,
            prompt_text=prompt_text,
            model_id=config.model_id,
            json_schema=context.response_schema,
            system_instruction=context.system_prompt,
            thinking_level=config.thinking_level,
            token_usage_file=str(TOKEN_USAGE_FILE),
            rate_limiter=limiter,
            batch_size=len(records),
            request_timeout=config.request_timeout,
        )

        if response_data and isinstance(response_data.get('records'), list):
            break

        if attempt < max_retries:
            logger.warning(
                'Analyze %s attempt %d failed (empty/invalid response), retrying...',
                batch_label,
                attempt + 1,
            )
        else:
            duration = time.monotonic() - started_at
            if not response_data:
                logger.warning('Analyze %s returned empty response data after %d attempts (%.2fs)', batch_label, attempt + 1, duration)
            else:
                logger.warning('Analyze %s returned non-list records payload after %d attempts (%.2fs)', batch_label, attempt + 1, duration)
            return []

    records_data = response_data.get('records', [])

    output_ids = [str(record.get('record_id', '')) for record in records_data]
    if len(output_ids) != len(input_ids):
        missing_ids = sorted(set(input_ids) - set(output_ids))
        extra_ids = sorted(set(output_ids) - set(input_ids))
        logger.warning(
            'Analyze %s returned %d/%d records (missing=%d, extra=%d)',
            batch_label,
            len(output_ids),
            len(input_ids),
            len(missing_ids),
            len(extra_ids),
        )
        if missing_ids:
            logger.warning(
                'Analyze %s missing record_ids sample: %s',
                batch_label,
                missing_ids[:10],
            )
            logger.debug('Analyze %s missing record_ids: %s', batch_label, missing_ids)
        if extra_ids:
            logger.warning(
                'Analyze %s extra record_ids sample: %s',
                batch_label,
                extra_ids[:10],
            )
            logger.debug('Analyze %s extra record_ids: %s', batch_label, extra_ids)

    duration = time.monotonic() - started_at
    logger.debug('Completed analyze %s with %d records (%.2fs)', batch_label, len(output_ids), duration)

    return cast('list[dict[str, Any]]', records_data)


async def analyze_dataset(
    request: AnalysisRequest,
    config: AnalysisConfig | None = None,
    on_batch: Callable[[list[dict[str, Any]]], Awaitable[None]] | None = None,
    on_row_count: Callable[[int], Awaitable[None]] | None = None,
) -> tuple[dict[str, Any], str]:
    """Analyze a cleaned CSV using a generated schema and return outputs.

    Args:
        request: AnalysisRequest containing paths and prompts
        config: Optional AnalysisConfig override
        on_batch: Optional callback invoked with each normalized batch
        on_row_count: Optional callback invoked with total record count

    Returns:
        Tuple of (analysis_json_dict, analysis_csv_text)
    """
    config = config or AnalysisConfig()
    analysis_started_at = time.monotonic()
    logger.debug(
        'Starting analysis (batch_size=%d, model_id=%s, thinking=%s, timeout=%.1fs)',
        config.batch_size,
        config.model_id,
        config.thinking_level,
        config.request_timeout,
    )
    request.output_dir.mkdir(parents=True, exist_ok=True)

    if not request.schema_path.exists():
        msg = f'Schema path does not exist: {request.schema_path}'
        raise ValueError(msg)

    load_schema_started_at = time.monotonic()
    schema_path_resolved = request.schema_path.resolve()
    schema_bytes = request.schema_path.read_bytes()
    source_schema_sha256 = hashlib.sha256(schema_bytes).hexdigest()
    with request.schema_path.open(encoding='utf-8') as f:
        schema = json.load(f)
    logger.debug(
        'Loaded schema in %.2fs from path=%s sha256=%s',
        time.monotonic() - load_schema_started_at,
        schema_path_resolved,
        source_schema_sha256,
    )

    load_csv_started_at = time.monotonic()
    df = pd.read_csv(request.cleaned_csv)
    if df.empty:
        msg = 'Cleaned CSV is empty'
        raise ValueError(msg)

    logger.debug('Loaded cleaned CSV in %.2fs', time.monotonic() - load_csv_started_at)

    logger.debug('Loaded cleaned CSV with %d rows and %d columns', len(df), len(df.columns))

    record_build_started_at = time.monotonic()
    id_column = df.columns[0]
    records: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        record = row.to_dict()
        record['record_id'] = str(row[id_column])
        records.append(record)
    if on_row_count is not None:
        await on_row_count(len(records))
    logger.debug('Prepared %d records in %.2fs', len(records), time.monotonic() - record_build_started_at)

    profile = validate_model_config(config.model_id, config.thinking_level)
    api_key = resolve_api_key()
    client = create_llm_client(api_key=api_key)
    limiter = AsyncRateLimiter(profile.rpm, profile.tpm, profile.rpd, max_concurrency=profile.max_concurrency)

    prompt_prep_started_at = time.monotonic()
    response_schema = _build_analysis_response_schema(schema)
    response_schema_sha256 = hashlib.sha256(
        json.dumps(response_schema, sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
    schema_summary = _summarize_schema(schema)
    logger.debug(
        'Prepared prompt inputs in %.2fs (source_schema_sha256=%s response_schema_sha256=%s)',
        time.monotonic() - prompt_prep_started_at,
        source_schema_sha256,
        response_schema_sha256,
    )

    batch_prep_started_at = time.monotonic()
    batches = _build_dynamic_batches(records, max_batch_size=config.batch_size)
    batch_sizes = [len(b) for b in batches]
    batch_char_sizes = [sum(len(json.dumps(record)) for record in batch) for batch in batches]
    logger.debug(
        'Prepared %d dynamic batches (max_size=%d, sizes=%s, batch_chars=%s)',
        len(batches),
        config.batch_size,
        batch_sizes,
        batch_char_sizes,
    )
    logger.debug('Batch preparation took %.2fs', time.monotonic() - batch_prep_started_at)

    context = AnalysisContext(
        system_prompt=request.system_prompt,
        schema_summary=schema_summary,
        use_case=request.use_case,
        id_column=id_column,
        response_schema=response_schema,
        source_schema_path=str(schema_path_resolved),
        source_schema_sha256=source_schema_sha256,
        response_schema_sha256=response_schema_sha256,
    )

    analysis_config = AnalysisConfig(
        model_id=profile.model_id,
        thinking_level=config.thinking_level,
        batch_size=config.batch_size,
    )

    task_prep_started_at = time.monotonic()
    tasks = [
        _analyze_batch(
            client=client,
            limiter=limiter,
            context=context,
            config=analysis_config,
            records=batch,
            batch_index=index,
        )
        for index, batch in enumerate(batches, start=1)
    ]
    logger.debug('Spawned %d batch tasks in %.2fs', len(tasks), time.monotonic() - task_prep_started_at)

    normalized: list[dict[str, Any]] = []
    batch_completion_started_at = time.monotonic()
    first_batch_at: float | None = None
    for task in asyncio.as_completed(tasks):
        batch_result = await task
        if first_batch_at is None:
            first_batch_at = time.monotonic()
            logger.debug('First batch completed in %.2fs', first_batch_at - batch_completion_started_at)
        normalized_batch = _normalize_records(batch_result, schema)
        normalized.extend(normalized_batch)
        if on_batch is not None:
            await on_batch(normalized_batch)
    logger.debug('All batches completed in %.2fs', time.monotonic() - batch_completion_started_at)

    if len(normalized) != len(records):
        logger.warning(
            'Normalized %d records from %d input rows',
            len(normalized),
            len(records),
        )
    else:
        logger.debug(
            'Normalized %d records from %d input rows',
            len(normalized),
            len(records),
        )

    total_duration = time.monotonic() - analysis_started_at
    logger.debug('Analysis completed in %.2fs', total_duration)

    analysis_payload = {
        'metadata': {
            'generated_at': datetime.now(tz=UTC).isoformat(),
            'model_id': profile.model_id,
            'thinking_level': config.thinking_level,
            'batch_size': config.batch_size,
            'record_count': len(normalized),
            'use_case': request.use_case if request.use_case else '',
        },
        'records': normalized,
    }

    json_path = request.output_dir / ANALYSIS_JSON_FILENAME
    with json_path.open('w', encoding='utf-8') as f:
        json.dump(analysis_payload, f, indent=2)

    csv_rows = _records_to_csv_rows(normalized, schema)
    csv_df = pd.DataFrame(csv_rows)
    csv_path = request.output_dir / ANALYSIS_CSV_FILENAME
    csv_df.to_csv(csv_path, index=False)

    return analysis_payload, csv_path.read_text(encoding='utf-8')
