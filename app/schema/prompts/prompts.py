"""Prompts for schema generation."""

import json
from pathlib import Path
from typing import Any, cast


def _load_prompt_file(filename: str) -> str:
    """Load a prompt template from file.

    Args:
        filename: Name of the prompt file relative to this file's parent directory

    Returns:
        Content of the prompt file
    """
    prompt_path = Path(__file__).parent / filename
    with open(prompt_path, encoding='utf-8') as f:
        return f.read()


def _load_json_schema(filename: str) -> dict[str, Any]:
    """Load a JSON schema from file.

    Args:
        filename: Name of the JSON file relative to this file's parent directory

    Returns:
        Parsed JSON schema as a dictionary
    """
    schema_path = Path(__file__).parent / filename
    with open(schema_path, encoding='utf-8') as f:
        return cast('dict[str, Any]', json.load(f))


def _validate_supported_schema_keywords(schema: dict[str, Any], path: tuple[str | int, ...] = ()) -> dict[str, Any]:
    """Validate that schema has no keywords unsupported by Gemini's structured output API.

    Raises:
        ValueError: If unsupported keywords are found at any location in the schema.
    """
    unsupported_keywords = {'allOf', 'contains', 'const'}
    for key, value in schema.items():
        if key in unsupported_keywords:
            dotted_path = '.'.join(str(part) for part in (*path, key))
            raise ValueError(
                f"Unsupported JSON Schema keyword '{key}' found at '{dotted_path}'. "
                'Remove unsupported keywords before calling Gemini structured output.'
            )
        if isinstance(value, dict):
            _validate_supported_schema_keywords(value, (*path, key))
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                if isinstance(item, dict):
                    _validate_supported_schema_keywords(item, (*path, key, idx))
    return schema


# Load system prompt base text and append canonical example schema guidance.
_SCHEMA_GENERATION_SYSTEM_PROMPT_BASE = _load_prompt_file('system_prompt.txt').rstrip()
_SCHEMA_GENERATION_EXAMPLE = _load_json_schema('response_schema_example.json')
_SCHEMA_GENERATION_EXAMPLE_JSON = json.dumps(_SCHEMA_GENERATION_EXAMPLE, indent=2)

SCHEMA_GENERATION_SYSTEM_PROMPT = (
    f'{_SCHEMA_GENERATION_SYSTEM_PROMPT_BASE}\n\n'
    'IMPORTANT: The following example schema is canonical for fixed fields. '
    'Do not duplicate any `field_name` from this example anywhere in your output, '
    'including across different field arrays.\n\n'
    'Canonical example schema:\n'
    f'{_SCHEMA_GENERATION_EXAMPLE_JSON}'
)

# Load JSON response schema, validating unsupported keywords are absent
SCHEMA_GENERATION_RESPONSE_SCHEMA = _validate_supported_schema_keywords(_load_json_schema('response_schema.json'))


def build_schema_generation_prompt(sample_data: list[dict], use_case: str) -> str:
    """Build the user prompt for schema generation.

    Args:
        sample_data: List of data records in JSON format
        use_case: Use case description text

    Returns:
        Formatted prompt string
    """
    template = _load_prompt_file('user_prompt_template.txt')

    return template.format(
        use_case=use_case,
        num_records=len(sample_data),
        sample_data=_format_sample_data(sample_data),
    )


def _format_sample_data(sample_data: list[dict]) -> str:
    """Format sample data for inclusion in prompt.

    Args:
        sample_data: List of data records

    Returns:
        Formatted string representation
    """
    formatted_records = []
    for i, record in enumerate(sample_data, 1):
        record_json = json.dumps(record, indent=2)

        # Truncate very long records
        if len(record_json) > 15000:
            record_json = record_json[:14997] + '...'

        formatted_records.append(f'Record {i}:\n{record_json}\n')

    return '\n'.join(formatted_records)
