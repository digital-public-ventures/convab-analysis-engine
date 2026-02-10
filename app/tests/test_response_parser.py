"""Unit tests for JSON response parsing helpers."""

from __future__ import annotations

import pytest

from app.llm.response_parser import extract_json_from_response


def test_extract_json_from_response_passthrough_dict() -> None:
    payload = {"records": [{"record_id": "1"}]}
    assert extract_json_from_response(payload) == payload


def test_extract_json_from_response_from_markdown_block() -> None:
    wrapped = {"text": '```json\n{"records":[{"record_id":"1"}]}\n```'}
    parsed = extract_json_from_response(wrapped)
    assert parsed["records"][0]["record_id"] == "1"


def test_extract_json_from_response_from_raw_string() -> None:
    raw = '{"records":[{"record_id":"abc"}]}'
    parsed = extract_json_from_response(raw)
    assert parsed["records"][0]["record_id"] == "abc"


def test_extract_json_from_response_rejects_invalid_type() -> None:
    with pytest.raises(ValueError, match="Unsupported response type"):
        extract_json_from_response(123)  # type: ignore[arg-type]


def test_extract_json_from_response_invalid_json_includes_preview() -> None:
    with pytest.raises(ValueError, match="Failed to parse JSON response"):
        extract_json_from_response({"text": "```json\n{not valid json}\n```"})
