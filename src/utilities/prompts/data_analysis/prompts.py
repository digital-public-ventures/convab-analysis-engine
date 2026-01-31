"""Prompts for data analysis API interactions."""

from pathlib import Path


def _load_prompt_file(filename: str) -> str:
    """Load a prompt template from file.

    Args:
        filename: Name of the prompt file relative to this file's parent directory

    Returns:
        Content of the prompt file
    """
    prompt_path = Path(__file__).parent / filename
    with open(prompt_path, encoding="utf-8") as f:
        return f.read()


# Load raw templates
_SYSTEM_PROMPT_TEMPLATE = _load_prompt_file("system_prompt.txt")
_USER_PROMPT_TEMPLATE = _load_prompt_file("user_prompt_template.txt")


def build_data_analysis_system_prompt(
    comment_basics: str,
    comment_details: str,
) -> str:
    """Build the system prompt for data analysis.

    Args:
        comment_basics: Brief description of the comment type/topic
        comment_details: Detailed context about the comments being analyzed

    Returns:
        Formatted system prompt string
    """
    return _SYSTEM_PROMPT_TEMPLATE.format(
        COMMENT_BASICS=comment_basics,
        COMMENT_DETAILS=comment_details,
    )


def build_data_analysis_user_prompt(data: list[dict]) -> str:
    """Build the user prompt for data analysis.

    Args:
        data: List of data records to analyze

    Returns:
        Formatted user prompt string
    """
    import json

    formatted_data = json.dumps(data, indent=2)
    return _USER_PROMPT_TEMPLATE + formatted_data
