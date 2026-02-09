"""Text normalization helpers for robust LLM requests and cleaned data."""

from __future__ import annotations

import unicodedata


def normalize_text_for_llm(
    value: str,
    *,
    newline_strategy: str = 'space',
    encoding_strategy: str = 'ascii_ignore',
) -> str:
    """Normalize text to reduce model request instability from formatting/encoding.

    Args:
        value: Input text
        newline_strategy: One of:
            - 'space': convert CR/LF variants to single spaces
            - 'normalize': normalize CR/LF variants to '\n'
            - 'keep': preserve existing newlines
        encoding_strategy: One of:
            - 'ascii_ignore': drop non-ascii characters
            - 'ascii_replace': replace non-ascii with '?'
            - 'keep': preserve unicode

    Returns:
        Normalized text
    """
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

    if newline_strategy == 'space':
        text = text.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
    elif newline_strategy == 'normalize':
        text = text.replace('\r\n', '\n').replace('\r', '\n')
    elif newline_strategy == 'keep':
        pass
    else:
        msg = f'Unsupported newline_strategy: {newline_strategy}'
        raise ValueError(msg)

    if encoding_strategy == 'ascii_ignore':
        text = text.encode('ascii', 'ignore').decode('ascii')
    elif encoding_strategy == 'ascii_replace':
        text = text.encode('ascii', 'replace').decode('ascii')
    elif encoding_strategy == 'keep':
        pass
    else:
        msg = f'Unsupported encoding_strategy: {encoding_strategy}'
        raise ValueError(msg)

    return text
