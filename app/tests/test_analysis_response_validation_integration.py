"""Integration test that exercises real provider APIs for analysis."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import pytest
from dotenv import load_dotenv

from app.analysis.analyzer import AnalysisConfig, AnalysisRequest, analyze_dataset

REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_CSV = REPO_ROOT / 'app' / 'data' / 'raw' / 'extracted_15.csv'
PROVIDER_TEST_CONFIG = {
    'gemini': {
        'api_key_env': 'GEMINI_API_KEY',
        'model_id': 'gemini-2.5-flash-lite-preview-09-2025',
        'thinking_level': 'NONE',
    },
    'openai': {
        'api_key_env': 'OPENAI_API_KEY',
        'model_id': 'gpt-5-mini',
        'thinking_level': 'LOW',
    },
}

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
@pytest.mark.parametrize('provider', ['gemini', 'openai'])
async def test_analyze_extracted_15_hits_real_api(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
) -> None:
    """Run a single-row analysis call against the live provider API with a small real schema."""
    provider_config = PROVIDER_TEST_CONFIG[provider]
    api_key_env = provider_config['api_key_env']

    load_dotenv()
    if not os.environ.get(api_key_env):
        pytest.skip(f'{api_key_env} environment variable not set')

    if not INPUT_CSV.exists():
        pytest.fail(f'Missing test input CSV: {INPUT_CSV}')
    one_row_csv = tmp_path / 'extracted_1.csv'
    one_row_df = pd.read_csv(INPUT_CSV).head(1).copy()
    if one_row_df.empty:
        pytest.fail(f'Input CSV has no rows: {INPUT_CSV}')
    one_row_df.to_csv(one_row_csv, index=False)

    expected_id = str(one_row_df.iloc[0, 0])
    schema_path = tmp_path / 'schema.json'
    minimal_schema = {
        'schema_name': 'Integration Smoke Schema',
        'enum_fields': [],
        'categorical_fields': [],
        'scalar_fields': [
            {
                'field_name': 'urgency_of_impact',
                'required': True,
                'nullable': False,
                'description': 'How urgent the commenter frames the issue.',
                'scale_min': 0,
                'scale_max': 10,
                'scale_interpretation': '0 = not urgent, 10 = extremely urgent',
            }
        ],
        'key_quotes_fields': [
            {
                'field_name': 'supporting_quotes',
                'required': True,
                'nullable': False,
                'description': 'Direct quotes that support the main concern.',
                'max_quotes': 2,
                'min_items': 0,
            }
        ],
        'text_array_fields': [
            {
                'field_name': 'main_claims',
                'required': True,
                'nullable': False,
                'description': 'Short free-text summaries of the commenter’s main claims.',
                'max_items': 3,
                'min_items': 0,
            }
        ],
    }
    schema_path.write_text(json.dumps(minimal_schema), encoding='utf-8')
    output_dir = tmp_path / f'analyzed_{provider}'
    monkeypatch.setenv('LLM_PROVIDER', provider)

    request = AnalysisRequest(
        cleaned_csv=one_row_csv,
        schema_path=schema_path,
        output_dir=output_dir,
        use_case='Validate strict schema-conformant extraction for public comments.',
        system_prompt='Return valid JSON matching the provided schema exactly.',
    )

    payload, csv_text = await analyze_dataset(
        request,
        config=AnalysisConfig(
            model_id=provider_config['model_id'],
            batch_size=1,
            thinking_level=provider_config['thinking_level'],
            request_timeout=20.0,
        ),
    )

    records = payload.get('records', [])
    assert len(records) == 1
    assert payload.get('metadata', {}).get('record_count') == 1
    assert str(records[0].get('record_id', '')) == expected_id
    assert 'urgency_of_impact' in records[0]['scalar_fields']
    assert 'supporting_quotes' in records[0]['key_quotes_fields']
    assert 'main_claims' in records[0]['text_array_fields']

    csv_df = pd.read_csv(pd.io.common.StringIO(csv_text))
    assert len(csv_df) == 1
    assert str(csv_df.iloc[0]['record_id']) == expected_id
    assert 'urgency_of_impact' in csv_df.columns
    assert 'supporting_quotes' in csv_df.columns
    assert 'main_claims' in csv_df.columns
