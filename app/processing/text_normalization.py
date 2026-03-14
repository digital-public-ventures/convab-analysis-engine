"""Text normalization helpers for robust LLM requests and cleaned data."""

from __future__ import annotations

import unicodedata


def normalize_text_for_llm(
    value: str,
) -> str:
    """Normalize text to the single LLM-safe format used across the app."""
    text = unicodedata.normalize('NFKC', value)

    # Replace non-printable control chars (except tab/newline) with spaces.
    chars: list[str] = []
    for ch in text:
        if ch in ('\n', '\t', '\r'):
            chars.append(ch)
            continue
        if unicodedata.category(ch).startswith('C'):
            chars.append(' ')
            continue
        chars.append(ch)
    text = ''.join(chars)

    text = text.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
    text = text.encode('ascii', 'ignore').decode('ascii')
    return text
