"""Utilities for parsing and cleaning LLM JSON responses."""

import json
import re
from typing import Any, cast


def extract_json_from_response(response: dict | str) -> dict[str, Any]:
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
    if isinstance(response, dict):
        if "text" in response:
            response_text = response["text"]
        else:
            return cast("dict[str, Any]", response)
    elif isinstance(response, str):
        response_text = response
    else:
        raise ValueError(f"Unsupported response type: {type(response)}")

    # Remove markdown code blocks
    response_text = re.sub(r"```json\s*", "", response_text, flags=re.DOTALL)
    response_text = re.sub(r"```\s*", "", response_text, flags=re.DOTALL)

    response_text = response_text.strip()

    try:
        return cast("dict[str, Any]", json.loads(response_text))
    except json.JSONDecodeError as e:
        preview = response_text[:200] + "..." if len(response_text) > 200 else response_text
        raise ValueError(f"Failed to parse JSON response: {e}\nContent preview: {preview}") from e
