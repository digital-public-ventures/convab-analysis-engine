"""Prompts for Gemini API interactions."""

import json
from pathlib import Path


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


def _load_json_schema(filename: str) -> dict:
    """Load a JSON schema from file.

    Args:
        filename: Name of the JSON file relative to this file's parent directory

    Returns:
        Parsed JSON schema as a dictionary
    """
    schema_path = Path(__file__).parent / filename
    with open(schema_path, encoding='utf-8') as f:
        return json.load(f)


# Load system prompts
SCHEMA_GENERATION_SYSTEM_PROMPT = _load_prompt_file('system_prompt.txt')

# Load JSON response schema
SCHEMA_GENERATION_RESPONSE_SCHEMA = _load_json_schema('response_schema.json')


def _load_use_case() -> str:
    """Load the use case from the cfpb_exploration prompts directory.

    Returns:
        Use case description text
    """
    # Navigate from utilities/prompts/schema_gen/ up to src/, then to cfpb_exploration/prompts/
    use_case_path = Path(__file__).parent.parent.parent.parent / 'cfpb_exploration' / 'prompts' / 'use_case.txt'
    with open(use_case_path, encoding='utf-8') as f:
        return f.read().strip()


def build_schema_generation_prompt(sample_data: list[dict]) -> str:
    """Build the user prompt for schema generation.

    Args:
        sample_data: List of data records in JSON format

    Returns:
        Formatted prompt string
    """
    template = _load_prompt_file('user_prompt_template.txt')
    use_case = _load_use_case()

    return template.format(
        use_case=use_case, num_records=len(sample_data), sample_data=_format_sample_data(sample_data)
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
        # Format each record as readable JSON
        record_json = json.dumps(record, indent=2)

        # Truncate very long records
        if len(record_json) > 1000:
            record_json = record_json[:997] + '...'

        formatted_records.append(f'Record {i}:\n{record_json}\n')

    return '\n'.join(formatted_records)
