"""Prompt construction helpers for record analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MAX_PROMPT_RECORD_CHARS = 500_000
PROMPTS_DIR = Path(__file__).resolve().parent
ANALYSIS_PROMPT_TEMPLATE = (PROMPTS_DIR / 'analysis_prompt.txt').read_text(encoding='utf-8')
CRITICAL_GUIDELINES = (PROMPTS_DIR / 'critical_guidelines.txt').read_text(encoding='utf-8')


def summarize_schema(schema: dict[str, Any]) -> str:
    """Create a concise text summary of schema fields for prompting."""
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


def format_records_for_prompt(records: list[dict[str, Any]]) -> str:
    """Format record data for inclusion in the prompt."""
    formatted_records = []
    for i, record in enumerate(records, 1):
        record_json = json.dumps(record, indent=2)
        if len(record_json) > MAX_PROMPT_RECORD_CHARS:
            record_json = record_json[: MAX_PROMPT_RECORD_CHARS - 3] + '...'
        formatted_records.append(f'Record {i}:\n{record_json}\n')
    return '\n'.join(formatted_records)


def build_analysis_prompt(
    use_case: str,
    schema_summary: str,
    records: list[dict[str, Any]],
    id_column: str,
) -> str:
    """Build the prompt for a batch of records."""
    return ANALYSIS_PROMPT_TEMPLATE.format(
        use_case=use_case.strip(),
        schema_summary=schema_summary.strip(),
        id_column=id_column,
        critical_guidelines=CRITICAL_GUIDELINES.strip(),
        records=format_records_for_prompt(records),
    )
