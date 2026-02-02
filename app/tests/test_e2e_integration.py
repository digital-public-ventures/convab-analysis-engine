"""End-to-end integration test for clean, schema, and analyze pipeline."""

from __future__ import annotations

import json
import logging
import os
import time
from http import HTTPStatus
from pathlib import Path
from typing import Any, cast

import pandas as pd
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from app import server as server_module
from app.config import ANALYSIS_CSV_FILENAME, ANALYSIS_JSON_FILENAME
from app.processing import DataStore
from app.processing.job_store import JobStore
from app.server import app

BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BASE_DIR.parent
FIXTURES_ROOT = REPO_ROOT / 'app' / 'tests' / 'fixtures'
PROMPTS_DIR = FIXTURES_ROOT / 'example_prompts'
RESPONSES_CSV = FIXTURES_ROOT / 'responses_100.csv'
HARDCODED_HASH = 'efa267c019c11e33cf61afe5ffcf9d2b1fa8dbdcd987b83e911eeea795812334'
SCHEMA_FIXTURE = FIXTURES_ROOT / HARDCODED_HASH / 'schema' / 'schema.json'


def _load_prompt(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def _expected_headers(schema: dict) -> list[str]:
    categorical_fields = schema.get('categorical_fields', [])
    scalar_fields = schema.get('scalar_fields', [])
    key_quotes_fields = schema.get('key_quotes_fields', [])

    headers = ['record_id']
    headers.extend(field.get('field_name', '').strip() for field in categorical_fields)
    headers.extend(field.get('field_name', '').strip() for field in scalar_fields)
    headers.extend(field.get('field_name', '').strip() for field in key_quotes_fields)

    return [header for header in headers if header]


def _poll_until_complete(
    client: TestClient,
    job_id: str,
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        status_response = client.get(f'/jobs/{job_id}')
        if status_response.status_code != HTTPStatus.OK:
            pytest.fail(f'Expected 200 status, got {status_response.status_code}')
        status_payload = cast('dict[str, Any]', status_response.json())
        if status_payload.get('completed') is True:
            return status_payload
        time.sleep(0.25)
    pytest.fail('Timed out waiting for job completion')
    raise AssertionError('Timed out waiting for job completion')


def test_clean_and_schema_cache_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run clean and schema endpoints and validate caching behavior."""
    logging.basicConfig(level=logging.DEBUG)
    load_dotenv()
    if not os.environ.get('GEMINI_API_KEY'):
        pytest.fail('GEMINI_API_KEY environment variable not set')

    content = RESPONSES_CSV.read_bytes()
    expected_hash = DataStore.hash_content(content)
    data_store = DataStore(data_dir=FIXTURES_ROOT)
    monkeypatch.setattr(server_module, '_data_store', data_store)
    monkeypatch.setattr(server_module, '_job_store', JobStore())

    use_case = _load_prompt(PROMPTS_DIR / 'use_case.txt')

    cleaned_fixture_dir = FIXTURES_ROOT / HARDCODED_HASH / 'cleaned_data'
    if cleaned_fixture_dir.exists():
        for file_path in cleaned_fixture_dir.glob('*'):
            if file_path.is_file():
                file_path.unlink()

    with TestClient(app) as client:
        clean_response = client.post(
            '/clean?no_cache=true',
            files={'file': ('responses_100.csv', content, 'text/csv')},
        )
        if clean_response.status_code != HTTPStatus.ACCEPTED:
            pytest.fail(f'Expected 202 status, got {clean_response.status_code}')

        clean_payload = clean_response.json()
        content_hash = clean_payload.get('hash')
        if content_hash != expected_hash:
            pytest.fail('Clean response hash did not match computed hash')
        if content_hash != HARDCODED_HASH:
            pytest.fail('Clean response hash did not match the hardcoded test hash')

        job_id = clean_payload.get('job_id')
        if not job_id:
            pytest.fail('Clean response missing job_id')

        _poll_until_complete(client, job_id)

        hash_dir = FIXTURES_ROOT / expected_hash
        if not hash_dir.exists():
            pytest.fail('Hash directory was not created under fixtures')

        cleaned_csv = data_store.get_cleaned_csv(HARDCODED_HASH)
        if not cleaned_csv:
            pytest.fail('Cleaned CSV was not created')

        cleaned_df = pd.read_csv(cleaned_csv)
        responses_df = pd.read_csv(RESPONSES_CSV)
        source_id_column = responses_df.columns[0]
        if source_id_column not in cleaned_df.columns:
            pytest.fail('Cleaned CSV missing source id column')
        if 'Comment' not in cleaned_df.columns:
            pytest.fail('Cleaned CSV missing Comment column')

        if len(cleaned_df) != len(responses_df):
            pytest.fail('Cleaned CSV row count did not match source CSV')

        cleaned_ids = set(cleaned_df[source_id_column].fillna('').astype(str).str.strip())
        source_ids = set(responses_df[source_id_column].fillna('').astype(str).str.strip())
        if cleaned_ids != source_ids:
            pytest.fail('Cleaned CSV ids did not match source IDs')

        cleaned_comments = set(cleaned_df['Comment'].fillna('').astype(str).str.strip())
        source_comments = set(responses_df['Comment'].fillna('').astype(str).str.strip())
        if cleaned_comments != source_comments:
            pytest.fail('Cleaned CSV comments did not match source comments')

        if 'Attachment Files' not in cleaned_df.columns:
            pytest.fail('Cleaned CSV missing Attachment Files column')
        if 'Attachment Files_extracted' not in cleaned_df.columns:
            pytest.fail('Cleaned CSV missing Attachment Files_extracted column')

        attachments_present = cleaned_df['Attachment Files'].fillna('').astype(str).str.strip() != ''
        extracted_present = cleaned_df['Attachment Files_extracted'].fillna('').astype(str).str.strip() != ''
        if not extracted_present[attachments_present].all():
            pytest.fail('Attachment Files_extracted was blank when Attachment Files was present')

        schema_response = client.post(
            f'/schema/{expected_hash}',
            json={'use_case': use_case, 'sample_size': 10, 'head_size': 5},
        )
        if schema_response.status_code != HTTPStatus.OK:
            pytest.fail(f'Expected 200 status, got {schema_response.status_code}')

        schema_payload = schema_response.json()
        if schema_payload.get('cached') is not True:
            pytest.fail('Expected schema cache hit on first request')
        schema = schema_payload.get('schema')
        if not schema:
            pytest.fail('Schema response was empty')


def test_analyze_outputs_with_cached_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run analyze endpoint for a known hash and validate outputs."""
    logging.basicConfig(level=logging.DEBUG)
    load_dotenv()
    if not os.environ.get('GEMINI_API_KEY'):
        pytest.fail('GEMINI_API_KEY environment variable not set')

    data_store = DataStore(data_dir=FIXTURES_ROOT)
    monkeypatch.setattr(server_module, '_data_store', data_store)
    monkeypatch.setattr(server_module, '_job_store', JobStore())

    use_case = _load_prompt(PROMPTS_DIR / 'use_case.txt')
    system_prompt = _load_prompt(PROMPTS_DIR / 'system_prompt.txt')

    if not SCHEMA_FIXTURE.exists():
        pytest.fail('Schema fixture was missing for hardcoded hash')

    schema = json.loads(SCHEMA_FIXTURE.read_text(encoding='utf-8'))

    with TestClient(app) as client:
        analyze_response = client.post(
            '/analyze?no_cache=true',
            json={'hash': HARDCODED_HASH, 'use_case': use_case, 'system_prompt': system_prompt},
        )
        if analyze_response.status_code != HTTPStatus.ACCEPTED:
            pytest.fail(f'Expected 202 status, got {analyze_response.status_code}')

        analyze_payload = analyze_response.json()
        analyze_job_id = analyze_payload.get('job_id')
        if not analyze_job_id:
            pytest.fail('Analyze response missing job_id')

        _poll_until_complete(client, analyze_job_id)

    expected_headers = _expected_headers(cast('dict[str, Any]', schema))

    cleaned_csv = data_store.get_cleaned_csv(HARDCODED_HASH)
    if not cleaned_csv:
        pytest.fail('Cleaned CSV was not created')

    csv_path = data_store.get_analyzed_csv(HARDCODED_HASH, ANALYSIS_CSV_FILENAME)
    if not csv_path or not csv_path.exists():
        pytest.fail('analysis.csv was not created')

    json_path = data_store.get_analyzed_json(HARDCODED_HASH, ANALYSIS_JSON_FILENAME)
    if not json_path or not json_path.exists():
        pytest.fail('analysis.json was not created')

    csv_df = pd.read_csv(csv_path)
    responses_df = pd.read_csv(RESPONSES_CSV)
    source_id_column = responses_df.columns[0]
    if list(csv_df.columns) != expected_headers:
        pytest.fail('CSV headers did not match schema fields')

    if len(csv_df) != len(responses_df):
        pytest.fail('Analysis CSV row count did not match source CSV')

    if csv_df['record_id'].nunique() != len(csv_df):
        pytest.fail('Analysis CSV record_id values were not unique')

    source_ids = set(responses_df[source_id_column].astype(str))
    record_ids = set(csv_df['record_id'].astype(str))
    if record_ids != source_ids:
        pytest.fail('Analysis CSV record_id values did not match source IDs')

    field_columns = [col for col in csv_df.columns if col != 'record_id']
    if not field_columns:
        pytest.fail('No analysis fields found in CSV header')

    scalar_fields = [
        'Product Sentiment Score',
        'Urgency and Distress Level',
        'Seriousness of Life Impact',
    ]
    category_fields = [
        'Stakeholder Type',
        'Vulnerable Population Identifiers',
        'Product and Entity Mentions',
        'Reported Outcomes and Impacts',
        'Policy and Regulatory Recommendations',
    ]
    free_text_fields = [
        'Representative Narrative Snippet',
        'Core Policy Recommendation Quote',
    ]

    for column in scalar_fields + category_fields + free_text_fields:
        if column not in csv_df.columns:
            pytest.fail(f'Missing expected analysis column: {column}')

    def _is_non_null(value: object) -> bool:
        is_empty_string = isinstance(value, str) and value.strip() == ''
        return value is not None and not (isinstance(value, float) and pd.isna(value)) and not is_empty_string

    threshold = max(1, int(len(field_columns) * 0.6))
    has_populated_row = any(
        sum(_is_non_null(value) for value in row[field_columns]) >= threshold for _, row in csv_df.iterrows()
    )
    if not has_populated_row:
        pytest.fail('No row contained enough non-null analysis fields')

    for column in scalar_fields:
        column_series = pd.to_numeric(csv_df[column], errors='coerce')
        if column_series.isna().any():
            pytest.fail(f'Column {column} contained non-numeric values')

    for column in category_fields + free_text_fields:
        if csv_df[column].isna().any():
            pytest.fail(f'Column {column} contained null values')
        if not csv_df[column].map(lambda value: isinstance(value, str) and value.strip() != '').all():
            pytest.fail(f'Column {column} contained blank strings')

    analysis_json = json.loads(json_path.read_text(encoding='utf-8'))
    if not analysis_json.get('records'):
        pytest.fail('analysis JSON records were empty')
