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
from app.prompts.analysis import build_analysis_prompt, summarize_schema
from app.prompts.response_schema import build_analysis_response_schema
from app.prompts.response_validation import validate_analysis_payload

logger = logging.getLogger(__name__)

BATCH_CHAR_BUDGET = 100_000

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
    source_schema: dict[str, Any]


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

    def _categorical_sentinel(field: dict[str, Any]) -> str | None:
        for value in [*field.get('required_values', []), *field.get('suggested_values', [])]:
            text = str(value).strip()
            if text == 'None or Not Applicable':
                return text
        return None

    normalized: dict[str, Any] = {}
    for field in schema_fields:
        field_name = field.get('field_name', '').strip()
        allow_multiple = bool(field.get('allow_multiple', False))
        sentinel = _categorical_sentinel(field)
        value = raw_fields.get(field_name)
        if allow_multiple:
            if value is None:
                normalized[field_name] = [sentinel] if sentinel else None
            elif isinstance(value, list):
                normalized_values = [str(v) for v in value]
                normalized[field_name] = normalized_values or ([sentinel] if sentinel else [])
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


def _format_batch_label(batch_index: int | str | None) -> str:
    return f'batch={batch_index}' if batch_index is not None else 'batch=?'


def _child_batch_index(batch_index: int | str | None, suffix: str) -> str:
    if batch_index is None:
        return suffix
    return f'{batch_index}.{suffix}'


async def _request_validated_batch_response(
    client: object,
    limiter: AsyncRateLimiter,
    context: AnalysisContext,
    config: AnalysisConfig,
    records: list[dict[str, Any]],
    prompt_text: str,
    batch_label: str,
    max_retries: int,
) -> tuple[dict[str, Any] | None, bool, int]:
    response_data: dict[str, Any] | None = None
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

        if response_data:
            failure = validate_analysis_payload(response_data, context.source_schema)
            if failure is None:
                return response_data, False, attempt + 1
            logger.warning(
                'Analyze %s attempt %d failed schema validation category=%s: %s',
                batch_label,
                attempt + 1,
                failure.category,
                failure.message,
            )

        if attempt < max_retries:
            logger.warning(
                'Analyze %s attempt %d failed (empty/invalid response), retrying...',
                batch_label,
                attempt + 1,
            )

    return response_data, True, max_retries + 1


async def _recover_exhausted_batch(
    client: object,
    limiter: AsyncRateLimiter,
    context: AnalysisContext,
    config: AnalysisConfig,
    records: list[dict[str, Any]],
    batch_index: int | str | None,
    batch_label: str,
    attempts_used: int,
    response_data: dict[str, Any] | None,
    started_at: float,
    input_ids: list[str],
) -> list[dict[str, Any]]:
    duration = time.monotonic() - started_at
    if not response_data:
        logger.warning(
            'Analyze %s returned empty response data after %d attempts (%.2fs)', batch_label, attempts_used, duration
        )
    else:
        logger.warning(
            'Analyze %s returned schema-invalid payload after %d attempts (%.2fs)', batch_label, attempts_used, duration
        )

    if len(records) > 1:
        midpoint = max(1, len(records) // 2)
        logger.warning(
            'Analyze %s splitting failed batch into %d and %d records for narrower retries',
            batch_label,
            midpoint,
            len(records) - midpoint,
        )
        first_half = await _analyze_batch(
            client=client,
            limiter=limiter,
            context=context,
            config=config,
            records=records[:midpoint],
            batch_index=_child_batch_index(batch_index, '1'),
        )
        second_half = await _analyze_batch(
            client=client,
            limiter=limiter,
            context=context,
            config=config,
            records=records[midpoint:],
            batch_index=_child_batch_index(batch_index, '2'),
        )
        return first_half + second_half

    record_id = input_ids[0] if input_ids else 'unknown'
    msg = f'Analyze {batch_label} failed after {attempts_used} attempts for record_id={record_id}'
    raise ValueError(msg)


def _reconcile_batch_records(
    input_ids: list[str],
    records_data: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[str], list[str], list[str]]:
    records_by_id: dict[str, dict[str, Any]] = {}
    duplicate_ids: list[str] = []
    extra_ids: list[str] = []
    for record in records_data:
        record_id = str(record.get('record_id', ''))
        if record_id not in input_ids:
            extra_ids.append(record_id)
            continue
        if record_id in records_by_id:
            duplicate_ids.append(record_id)
            continue
        records_by_id[record_id] = record

    missing_ids = [record_id for record_id in input_ids if record_id not in records_by_id]
    return records_by_id, missing_ids, extra_ids, duplicate_ids


def _log_reconciliation_issues(
    batch_label: str,
    input_ids: list[str],
    records_by_id: dict[str, dict[str, Any]],
    missing_ids: list[str],
    extra_ids: list[str],
    duplicate_ids: list[str],
) -> None:
    if not missing_ids and not extra_ids and not duplicate_ids:
        return

    logger.warning(
        'Analyze %s returned %d/%d records (missing=%d, extra=%d, duplicate=%d)',
        batch_label,
        len(records_by_id),
        len(input_ids),
        len(missing_ids),
        len(extra_ids),
        len(duplicate_ids),
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
    if duplicate_ids:
        logger.warning(
            'Analyze %s duplicate record_ids sample: %s',
            batch_label,
            duplicate_ids[:10],
        )
        logger.debug('Analyze %s duplicate record_ids: %s', batch_label, duplicate_ids)


async def _recover_missing_records(
    client: object,
    limiter: AsyncRateLimiter,
    context: AnalysisContext,
    config: AnalysisConfig,
    records: list[dict[str, Any]],
    batch_index: int | str | None,
    batch_label: str,
    input_ids: list[str],
    records_by_id: dict[str, dict[str, Any]],
    missing_ids: list[str],
) -> dict[str, dict[str, Any]]:
    missing_id_set = set(missing_ids)
    missing_records = [record for record in records if str(record.get('record_id', '')) in missing_id_set]
    logger.warning(
        'Analyze %s retrying %d missing record_ids as a follow-up batch',
        batch_label,
        len(missing_records),
    )
    recovered_records = await _analyze_batch(
        client=client,
        limiter=limiter,
        context=context,
        config=config,
        records=missing_records,
        batch_index=_child_batch_index(batch_index, 'missing'),
    )
    for record in recovered_records:
        record_id = str(record.get('record_id', ''))
        if record_id in input_ids and record_id not in records_by_id:
            records_by_id[record_id] = record

    remaining_missing_ids = [record_id for record_id in input_ids if record_id not in records_by_id]
    if remaining_missing_ids:
        msg = f'Analyze {batch_label} missing record_ids after recovery: {remaining_missing_ids[:10]}'
        raise ValueError(msg)
    return records_by_id


async def _analyze_batch(
    client: object,
    limiter: AsyncRateLimiter,
    context: AnalysisContext,
    config: AnalysisConfig,
    records: list[dict[str, Any]],
    batch_index: int | str | None = None,
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
    batch_label = _format_batch_label(batch_index)
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
    prompt_text = build_analysis_prompt(
        context.use_case,
        context.schema_summary,
        records,
        context.id_column,
    )

    response_data, exhausted, attempts_used = await _request_validated_batch_response(
        client=client,
        limiter=limiter,
        context=context,
        config=config,
        records=records,
        prompt_text=prompt_text,
        batch_label=batch_label,
        max_retries=max_retries,
    )
    if exhausted:
        return await _recover_exhausted_batch(
            client=client,
            limiter=limiter,
            context=context,
            config=config,
            records=records,
            batch_index=batch_index,
            batch_label=batch_label,
            attempts_used=attempts_used,
            response_data=response_data,
            started_at=started_at,
            input_ids=input_ids,
        )

    records_data = response_data.get('records', [])
    records_by_id, missing_ids, extra_ids, duplicate_ids = _reconcile_batch_records(input_ids, records_data)
    _log_reconciliation_issues(
        batch_label=batch_label,
        input_ids=input_ids,
        records_by_id=records_by_id,
        missing_ids=missing_ids,
        extra_ids=extra_ids,
        duplicate_ids=duplicate_ids,
    )
    if missing_ids:
        records_by_id = await _recover_missing_records(
            client=client,
            limiter=limiter,
            context=context,
            config=config,
            records=records,
            batch_index=batch_index,
            batch_label=batch_label,
            input_ids=input_ids,
            records_by_id=records_by_id,
            missing_ids=missing_ids,
        )

    ordered_records = [records_by_id[record_id] for record_id in input_ids if record_id in records_by_id]
    output_ids = [str(record.get('record_id', '')) for record in ordered_records]

    duration = time.monotonic() - started_at
    logger.debug('Completed analyze %s with %d records (%.2fs)', batch_label, len(output_ids), duration)

    return cast('list[dict[str, Any]]', ordered_records)


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
    api_key = resolve_api_key(provider=profile.provider, model_id_or_key=profile.model_id)
    client = create_llm_client(api_key=api_key, provider=profile.provider, model_id_or_key=profile.model_id)
    limiter = AsyncRateLimiter(profile.rpm, profile.tpm, profile.rpd, max_concurrency=profile.max_concurrency)

    prompt_prep_started_at = time.monotonic()
    response_schema = build_analysis_response_schema(schema)
    response_schema_sha256 = hashlib.sha256(
        json.dumps(response_schema, sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
    schema_summary = summarize_schema(schema)
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
        source_schema=schema,
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
        logger.error(
            'Normalized %d records from %d input rows',
            len(normalized),
            len(records),
        )
        msg = f'Analysis output row count mismatch: normalized={len(normalized)} input={len(records)}'
        raise ValueError(msg)
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
