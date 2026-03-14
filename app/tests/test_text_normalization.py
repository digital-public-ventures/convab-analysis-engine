"""Tests for text normalization helpers."""

from app.processing.text_normalization import normalize_text_for_llm


def test_normalize_text_for_llm_uses_single_app_path() -> None:
    """Normalize control chars, newlines, and non-ascii chars the way callers expect."""
    value = "A\r\nB\nC\rD\tE\x00 caf\xe9"

    assert normalize_text_for_llm(value) == "A B C D\tE  caf"
