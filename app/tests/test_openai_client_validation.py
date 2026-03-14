"""Tests for OpenAI Responses client schema validation."""

from __future__ import annotations

import pytest

from app.llm.openai_client import (
    _normalize_json_schema_for_openai,
    _validate_response_against_schema,
    generate_structured_content,
    validate_model_config,
)


def test_validate_response_against_schema_accepts_valid_payload() -> None:
    """Validator accepts a minimal valid object payload."""
    schema = {
        'type': 'OBJECT',
        'required': ['records'],
        'properties': {
            'records': {
                'type': 'ARRAY',
                'items': {
                    'type': 'OBJECT',
                    'required': ['record_id'],
                    'properties': {
                        'record_id': {'type': 'STRING'},
                    },
                },
            },
        },
    }
    payload = {'records': [{'record_id': 'abc'}]}

    _validate_response_against_schema(schema, payload)


def test_validate_response_against_schema_rejects_missing_required() -> None:
    """Validator rejects missing required fields."""
    schema = {
        'type': 'OBJECT',
        'required': ['records'],
        'properties': {
            'records': {'type': 'ARRAY'},
        },
    }
    payload = {'not_records': []}

    with pytest.raises(ValueError, match='missing required field'):
        _validate_response_against_schema(schema, payload)


class _FakeResponse:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.usage = None
        self.output = []


class _FakeResponsesAPI:
    async def create(self, **_: object) -> _FakeResponse:
        return _FakeResponse('{"records":"not-an-array"}')


class _FakeClient:
    def __init__(self) -> None:
        self.responses = _FakeResponsesAPI()


@pytest.mark.asyncio
async def test_generate_structured_content_rejects_invalid_schema_payload() -> None:
    """Generator returns no data when JSON parses but fails schema validation."""
    schema = {
        'type': 'OBJECT',
        'required': ['records'],
        'properties': {
            'records': {'type': 'ARRAY'},
        },
    }

    response_data, usage = await generate_structured_content(
        client=_FakeClient(),
        prompt_text='test',
        model_id='gpt-5.2',
        json_schema=schema,
    )

    assert response_data is None
    assert usage is None


def test_validate_model_config_accepts_latest_chat_alias() -> None:
    """Model validation accepts the current chat alias and resolves the base model ID."""
    profile = validate_model_config("gpt-5.2-chat-latest", "HIGH")
    assert profile.model_id == "gpt-5.2"


def test_normalize_json_schema_for_openai_converts_type_and_nullable() -> None:
    """Normalizer converts uppercase types and nullable fields to strict JSON Schema."""
    schema = {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "nullable": True},
            "items": {"type": "ARRAY", "items": {"type": "NUMBER"}},
        },
    }

    normalized = _normalize_json_schema_for_openai(schema)

    assert normalized["type"] == "object"
    assert normalized["additionalProperties"] is False
    assert normalized["required"] == ["name", "items"]
    assert normalized["properties"]["name"]["type"] == ["string", "null"]
    assert normalized["properties"]["items"]["type"] == "array"
