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

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('provider', 'api_key_env', 'thinking_level'),
    [('gemini', 'GEMINI_API_KEY', 'MINIMAL'), ('openai', 'OPENAI_API_KEY', 'NONE')],
)
async def test_analyze_extracted_15_hits_real_api(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    api_key_env: str,
    thinking_level: str,
) -> None:
    """Run a single-row analysis call against the live provider API."""
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
        'schema_name': 'Integration Minimal Schema',
        'enum_fields': [],
        'categorical_fields': [],
        'scalar_fields': [],
        'key_quotes_fields': [],
        'text_array_fields': [],
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
        config=AnalysisConfig(batch_size=1, thinking_level=thinking_level, request_timeout=20.0),
    )

    records = payload.get('records', [])
    assert len(records) == 1
    assert payload.get('metadata', {}).get('record_count') == 1
    assert str(records[0].get('record_id', '')) == expected_id

    csv_df = pd.read_csv(pd.io.common.StringIO(csv_text))
    assert len(csv_df) == 1
    assert str(csv_df.iloc[0]['record_id']) == expected_id
