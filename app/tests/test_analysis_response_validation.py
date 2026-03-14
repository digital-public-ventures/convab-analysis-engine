from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

from app.analysis import AnalysisConfig, AnalysisRequest
from app.analysis import analyzer as analyzer_module
from app.prompts.response_schema import build_analysis_response_schema
from app.prompts.response_validation import validate_analysis_payload


def _valid_payload(schema: dict[str, Any], record_id: str = '1') -> dict[str, Any]:
    enum_fields = {
        field['field_name']: field.get('allowed_values', [None])[0] for field in schema.get('enum_fields', [])
    }
    categorical_fields: dict[str, Any] = {}
    for field in schema.get('categorical_fields', []):
        name = field['field_name']
        allowed_values: list[str] = []
        for value in [*field.get('required_values', []), *field.get('suggested_values', [])]:
            text = str(value).strip()
            if text and text not in allowed_values:
                allowed_values.append(text)
        if field.get('allow_multiple'):
            categorical_fields[name] = [allowed_values[0]] if allowed_values else []
        else:
            categorical_fields[name] = allowed_values[0] if allowed_values else ''

    scalar_fields = {field['field_name']: field.get('scale_min', 0) for field in schema.get('scalar_fields', [])}
    key_quotes_fields = {field['field_name']: ['quote'] for field in schema.get('key_quotes_fields', [])}
    text_array_fields = {field['field_name']: [] for field in schema.get('text_array_fields', [])}

    return {
        'records': [
            {
                'record_id': record_id,
                'enum_fields': enum_fields,
                'categorical_fields': categorical_fields,
                'scalar_fields': scalar_fields,
                'key_quotes_fields': key_quotes_fields,
                'text_array_fields': text_array_fields,
            }
        ]
    }


def test_validate_payload_missing_required_field(mock_schema: dict[str, Any]) -> None:
    payload = _valid_payload(mock_schema)
    payload['records'][0]['enum_fields'].pop('category_type')
    failure = validate_analysis_payload(payload, mock_schema)
    assert failure is not None
    assert failure.category == 'missing_required_fields'


def test_validate_payload_wrong_scalar_type_and_range(mock_schema: dict[str, Any]) -> None:
    payload = _valid_payload(mock_schema)
    payload['records'][0]['scalar_fields']['urgency'] = 'high'
    failure = validate_analysis_payload(payload, mock_schema)
    assert failure is not None
    assert failure.category == 'wrong_types'

    payload = _valid_payload(mock_schema)
    payload['records'][0]['scalar_fields']['urgency'] = 999
    failure = validate_analysis_payload(payload, mock_schema)
    assert failure is not None
    assert failure.category == 'wrong_types'


def test_validate_payload_unexpected_keys(mock_schema: dict[str, Any]) -> None:
    payload = _valid_payload(mock_schema)
    payload['records'][0]['unknown'] = 'nope'
    failure = validate_analysis_payload(payload, mock_schema)
    assert failure is not None
    assert failure.category == 'unexpected_keys'


def test_validate_payload_invalid_categorical_arrays() -> None:
    schema = {
        'enum_fields': [],
        'categorical_fields': [
            {
                'field_name': 'topics',
                'required': True,
                'value_mode': 'closed',
                'required_values': [],
                'allow_multiple': True,
                'suggested_values': ['fees', 'fraud'],
                'nullable': False,
            }
        ],
        'scalar_fields': [],
        'key_quotes_fields': [],
        'text_array_fields': [],
    }
    payload = {
        'records': [
            {
                'record_id': '1',
                'enum_fields': {},
                'categorical_fields': {'topics': 'fees'},
                'scalar_fields': {},
                'key_quotes_fields': {},
                'text_array_fields': {},
            }
        ]
    }
    failure = validate_analysis_payload(payload, schema)
    assert failure is not None
    assert failure.category == 'wrong_types'


def test_build_analysis_response_schema_open_categorical_field_has_no_enum() -> None:
    schema = {
        'enum_fields': [],
        'categorical_fields': [
            {
                'field_name': 'product_or_company_mentions',
                'required': True,
                'description': 'Products or companies mentioned in the comment.',
                'value_mode': 'open',
                'required_values': ['None or Not Applicable'],
                'suggested_values': ['CareCredit', 'Affirm'],
                'allow_multiple': True,
                'nullable': False,
                'minItems': 0,
                'maxItems': 15,
                'hint': 'Use examples when relevant but allow new names.',
            }
        ],
        'scalar_fields': [],
        'key_quotes_fields': [],
        'text_array_fields': [],
    }

    response_schema = build_analysis_response_schema(schema)
    field_schema = response_schema['properties']['records']['items']['properties']['categorical_fields']['properties'][
        'product_or_company_mentions'
    ]

    assert field_schema['type'] == 'ARRAY'
    assert field_schema['minItems'] == 0
    assert 'enum' not in field_schema
    assert 'enum' not in field_schema['items']


def test_build_analysis_response_schema_closed_categorical_field_uses_required_and_suggested_values() -> None:
    schema = {
        'enum_fields': [],
        'categorical_fields': [
            {
                'field_name': 'reported_harmful_impacts',
                'required': True,
                'description': 'Closed harmful impact taxonomy.',
                'value_mode': 'closed',
                'required_values': ['None or Not Applicable'],
                'suggested_values': ['Debt Burden', 'Credit Damage', 'Debt Burden'],
                'allow_multiple': True,
                'nullable': False,
                'minItems': 0,
                'maxItems': 10,
                'hint': 'Use only the allowed taxonomy values.',
            }
        ],
        'scalar_fields': [],
        'key_quotes_fields': [],
        'text_array_fields': [],
    }

    response_schema = build_analysis_response_schema(schema)
    field_schema = response_schema['properties']['records']['items']['properties']['categorical_fields']['properties'][
        'reported_harmful_impacts'
    ]

    assert field_schema['items']['enum'] == ['None or Not Applicable', 'Debt Burden', 'Credit Damage']


def test_validate_payload_open_categorical_field_accepts_arbitrary_values() -> None:
    schema = {
        'enum_fields': [],
        'categorical_fields': [
            {
                'field_name': 'product_or_company_mentions',
                'required': True,
                'description': 'Products or companies mentioned in the comment.',
                'value_mode': 'open',
                'required_values': ['None or Not Applicable'],
                'suggested_values': ['CareCredit', 'Affirm'],
                'allow_multiple': True,
                'nullable': False,
                'minItems': 0,
                'maxItems': 15,
                'hint': 'Allow new names when the record mentions them.',
            }
        ],
        'scalar_fields': [],
        'key_quotes_fields': [],
        'text_array_fields': [],
    }
    payload = {
        'records': [
            {
                'record_id': '1',
                'enum_fields': {},
                'categorical_fields': {'product_or_company_mentions': ['Unknown', 'PayZen']},
                'scalar_fields': {},
                'key_quotes_fields': {},
                'text_array_fields': {},
            }
        ]
    }

    failure = validate_analysis_payload(payload, schema)

    assert failure is None


def test_validate_payload_closed_categorical_field_rejects_values_outside_allowed_union() -> None:
    schema = {
        'enum_fields': [],
        'categorical_fields': [
            {
                'field_name': 'reported_harmful_impacts',
                'required': True,
                'description': 'Closed harmful impact taxonomy.',
                'value_mode': 'closed',
                'required_values': ['None or Not Applicable'],
                'suggested_values': ['Debt Burden', 'Credit Damage'],
                'allow_multiple': True,
                'nullable': False,
                'minItems': 0,
                'maxItems': 10,
                'hint': 'Use only the allowed taxonomy values.',
            }
        ],
        'scalar_fields': [],
        'key_quotes_fields': [],
        'text_array_fields': [],
    }
    valid_payload = {
        'records': [
            {
                'record_id': '1',
                'enum_fields': {},
                'categorical_fields': {'reported_harmful_impacts': ['None or Not Applicable']},
                'scalar_fields': {},
                'key_quotes_fields': {},
                'text_array_fields': {},
            }
        ]
    }
    invalid_payload = {
        'records': [
            {
                'record_id': '1',
                'enum_fields': {},
                'categorical_fields': {'reported_harmful_impacts': ['Unknown']},
                'scalar_fields': {},
                'key_quotes_fields': {},
                'text_array_fields': {},
            }
        ]
    }

    assert validate_analysis_payload(valid_payload, schema) is None
    failure = validate_analysis_payload(invalid_payload, schema)
    assert failure is not None
    assert failure.category == 'invalid_enum_values'


def test_normalize_categorical_fields_uses_explicit_sentinel_for_empty_multiselect() -> None:
    schema_fields = [
        {
            'field_name': 'product_or_company_mentions',
            'value_mode': 'open',
            'required_values': ['None or Not Applicable'],
            'suggested_values': ['CareCredit', 'Affirm'],
            'allow_multiple': True,
        }
    ]

    normalized = analyzer_module._normalize_categorical_fields(
        {'product_or_company_mentions': []},
        schema_fields,
    )

    assert normalized == {'product_or_company_mentions': ['None or Not Applicable']}


def test_normalize_categorical_fields_preserves_empty_multiselect_without_sentinel() -> None:
    schema_fields = [
        {
            'field_name': 'vulnerable_population_tags',
            'value_mode': 'closed',
            'required_values': [],
            'suggested_values': ['Low-Income Individuals'],
            'allow_multiple': True,
        }
    ]

    normalized = analyzer_module._normalize_categorical_fields(
        {'vulnerable_population_tags': []},
        schema_fields,
    )

    assert normalized == {'vulnerable_population_tags': []}


@pytest.mark.asyncio
async def test_analyze_dataset_recovers_missing_record_ids_from_partial_batch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_schema: dict[str, Any],
) -> None:
    cleaned_csv = tmp_path / 'cleaned.csv'
    pd.DataFrame({'id': ['1', '2'], 'comment': ['first', 'second']}).to_csv(cleaned_csv, index=False)
    schema_path = tmp_path / 'schema.json'
    schema_path.write_text(json.dumps(mock_schema), encoding='utf-8')

    calls = {'count': 0}

    async def fake_generate_structured_content(**kwargs: Any) -> tuple[dict[str, Any], dict[str, int]]:
        _ = kwargs
        calls['count'] += 1
        if calls['count'] == 1:
            return _valid_payload(mock_schema, record_id='1'), {
                'total_tokens': 1,
                'input_tokens': 1,
                'output_tokens': 0,
                'thinking_tokens': 0,
            }
        return _valid_payload(mock_schema, record_id='2'), {
            'total_tokens': 1,
            'input_tokens': 1,
            'output_tokens': 0,
            'thinking_tokens': 0,
        }

    monkeypatch.setattr(analyzer_module, 'generate_structured_content', fake_generate_structured_content)
    monkeypatch.setattr(analyzer_module, 'create_llm_client', lambda *args, **kwargs: object())
    monkeypatch.setattr(analyzer_module, 'resolve_api_key', lambda *args, **kwargs: 'test')
    monkeypatch.setattr(
        analyzer_module,
        'validate_model_config',
        lambda model_id, thinking_level: SimpleNamespace(
            model_id=model_id,
            provider='gemini',
            rpm=1000,
            tpm=1_000_000,
            rpd=1_000_000,
            max_concurrency=4,
        ),
    )

    request = AnalysisRequest(
        cleaned_csv=cleaned_csv,
        schema_path=schema_path,
        output_dir=tmp_path / 'output',
        use_case='Recover missing IDs',
        system_prompt='Return valid JSON',
    )
    payload, _csv_text = await analyzer_module.analyze_dataset(
        request,
        config=AnalysisConfig(batch_size=2, thinking_level='NONE'),
    )

    assert [record['record_id'] for record in payload['records']] == ['1', '2']
    assert payload['metadata']['record_count'] == 2


@pytest.mark.asyncio
async def test_analyze_dataset_rejects_schema_invalid_payloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_schema: dict[str, Any],
) -> None:
    cleaned_csv = tmp_path / 'cleaned.csv'
    pd.DataFrame({'id': ['1'], 'comment': ['example']}).to_csv(cleaned_csv, index=False)
    schema_path = tmp_path / 'schema.json'
    schema_path.write_text(json.dumps(mock_schema), encoding='utf-8')

    async def fake_generate_structured_content(**kwargs: Any) -> tuple[dict[str, Any], dict[str, int]]:
        _ = kwargs
        payload = _valid_payload(mock_schema, record_id='1')
        payload['records'][0]['enum_fields']['category_type'] = 'not-allowed'
        return payload, {'total_tokens': 1, 'input_tokens': 1, 'output_tokens': 0, 'thinking_tokens': 0}

    monkeypatch.setattr(analyzer_module, 'generate_structured_content', fake_generate_structured_content)
    monkeypatch.setattr(analyzer_module, 'create_llm_client', lambda *args, **kwargs: object())
    monkeypatch.setattr(analyzer_module, 'resolve_api_key', lambda *args, **kwargs: 'test')
    monkeypatch.setattr(
        analyzer_module,
        'validate_model_config',
        lambda model_id, thinking_level: SimpleNamespace(
            model_id=model_id,
            provider='gemini',
            rpm=1000,
            tpm=1_000_000,
            rpd=1_000_000,
            max_concurrency=4,
        ),
    )

    request = AnalysisRequest(
        cleaned_csv=cleaned_csv,
        schema_path=schema_path,
        output_dir=tmp_path / 'output',
        use_case='Validate payloads',
        system_prompt='Return valid JSON',
    )
    with pytest.raises(ValueError, match='failed after'):
        await analyzer_module.analyze_dataset(
            request,
            config=AnalysisConfig(batch_size=1, thinking_level='NONE'),
        )
