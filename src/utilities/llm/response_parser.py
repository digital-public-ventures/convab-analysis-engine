"""Utilities for parsing and cleaning LLM JSON responses."""

import json
import re


def extract_json_from_response(response: dict | str) -> dict:
    """Extract and parse JSON from LLM response, handling common wrappers and formatting.

    Handles:
    - {"text": "..."} wrapper objects
    - Markdown code blocks (```json ... ``` or ``` ... ```)
    - Extra whitespace and newlines
    - Direct JSON strings

    Args:
        response: Response from LLM (dict or string)

    Returns:
        Parsed JSON object as a dictionary

    Raises:
        ValueError: If JSON cannot be extracted or parsed
        json.JSONDecodeError: If the extracted content is not valid JSON
    """
    # If response is already a dict, check if it needs unwrapping
    if isinstance(response, dict):
        # If it has a 'text' key, unwrap it
        if 'text' in response:
            response_text = response['text']
        else:
            # Already a clean dict, return as-is
            return response
    elif isinstance(response, str):
        response_text = response
    else:
        raise ValueError(f'Unsupported response type: {type(response)}')

    # Remove markdown code blocks
    # Handle ```json ... ``` and ``` ... ```
    response_text = re.sub(r'```json\s*', '', response_text, flags=re.DOTALL)
    response_text = re.sub(r'```\s*', '', response_text, flags=re.DOTALL)

    # Strip whitespace
    response_text = response_text.strip()

    # Parse JSON
    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        # Provide helpful error message with preview of content
        preview = response_text[:200] + '...' if len(response_text) > 200 else response_text
        raise ValueError(f'Failed to parse JSON response: {e}\nContent preview: {preview}') from e
