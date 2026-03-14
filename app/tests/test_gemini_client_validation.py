"""Tests for Gemini response schema validation."""

from __future__ import annotations

import pytest

from app.llm.gemini_client import _validate_response_against_schema, generate_structured_content


def test_validate_response_against_schema_accepts_valid_payload() -> None:
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
    def __init__(self, text: str) -> None:
        self.text = text
        self.usage_metadata = None
        self.candidates = None


class _FakeModels:
    async def generate_content(self, **_: object) -> _FakeResponse:
        return _FakeResponse('{"records":"not-an-array"}')


class _FakeAio:
    def __init__(self) -> None:
        self.models = _FakeModels()


class _FakeClient:
    def __init__(self) -> None:
        self.aio = _FakeAio()


@pytest.mark.asyncio
async def test_generate_structured_content_rejects_invalid_schema_payload() -> None:
    schema = {
        'type': 'OBJECT',
        'required': ['records'],
        'properties': {
            'records': {'type': 'ARRAY'},
        },
    }

    response_data, usage = await generate_structured_content(
        client=_FakeClient(),  # type: ignore[arg-type]
        prompt_text='test',
        model_id='flash',
        json_schema=schema,
    )

    assert response_data is None
    assert usage is None
