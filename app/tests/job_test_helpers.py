"""Shared helpers for async job endpoint tests."""

from __future__ import annotations

import json
import shutil
import time
from http import HTTPStatus
from pathlib import Path
from typing import Any, cast

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import config as app_config
from app.config import POST_PROCESSING_SUBDIR, TAG_DEDUP_CSV_FILENAME, TAG_DEDUP_MAPPINGS_FILENAME
from app.processing.job_store import JobStore

HASH_VALUE = '8ca4ff2e602137ec54d559b9b3f4689803e270cfe2f286f51681dd83428dec28'  # pragma: allowlist secret
FIXTURES_DIR = Path(__file__).parent / 'fixtures' / HASH_VALUE
TEST_CSV = FIXTURES_DIR / 'responses.csv'
FIXTURE_SCHEMA = FIXTURES_DIR / 'schema' / 'schema.json'
FIXTURE_ANALYSIS_DIR = FIXTURES_DIR / 'analyzed' / 'integration_test' / '20260131-215335'
STREAMING_BATCH_THRESHOLD = 2


def poll_until_complete(
    client: TestClient,
    job_id: str,
    timeout_seconds: float = 20.0,
) -> dict[str, Any]:
    """Poll job status until completion or timeout."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        status_response = client.get(f'/jobs/{job_id}')
        if status_response.status_code != HTTPStatus.OK:
            pytest.fail(f'Expected 200 status, got {status_response.status_code}')
        status_payload = cast('dict[str, Any]', status_response.json())
        if status_payload.get('completed') is True:
            return status_payload
        time.sleep(0.25)
    message = 'Timed out waiting for job completion'
    pytest.fail(message)
    raise AssertionError(message)


def poll_until_terminal(
    client: TestClient,
    job_id: str,
    timeout_seconds: float = 20.0,
) -> dict[str, Any]:
    """Poll job status until completion or failure."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        status_response = client.get(f'/jobs/{job_id}')
        expect_status(status_response, HTTPStatus.OK)
        status_payload = cast('dict[str, Any]', status_response.json())
        if status_payload.get('completed') is True:
            return status_payload
        time.sleep(0.25)
    message = 'Timed out waiting for job terminal status'
    pytest.fail(message)
    raise AssertionError(message)


def seed_analysis_outputs(content_hash: str) -> None:
    """Seed cached schema + analysis outputs for the requested hash."""
    hash_dir = app_config.DATA_DIR / content_hash
    (hash_dir / 'schema').mkdir(parents=True, exist_ok=True)
    (hash_dir / 'analyzed').mkdir(parents=True, exist_ok=True)

    copy_if_different(FIXTURE_SCHEMA, hash_dir / 'schema' / 'schema.json')
    shutil.copy(FIXTURE_ANALYSIS_DIR / 'analysis.csv', hash_dir / 'analyzed' / 'analysis.csv')
    shutil.copy(FIXTURE_ANALYSIS_DIR / 'analysis.json', hash_dir / 'analyzed' / 'analysis.json')


def seed_tag_fix_outputs(content_hash: str) -> None:
    """Seed cached tag-fix outputs for the requested hash."""
    output_dir = app_config.DATA_DIR / content_hash / POST_PROCESSING_SUBDIR
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(
        FIXTURE_ANALYSIS_DIR / 'analysis.csv',
        output_dir / TAG_DEDUP_CSV_FILENAME,
    )
    (output_dir / TAG_DEDUP_MAPPINGS_FILENAME).write_text(
        json.dumps({'seeded': True}),
        encoding='utf-8',
    )


def copy_if_different(source: Path, destination: Path) -> None:
    """Copy a file unless the source and destination are identical."""
    if source.resolve() == destination.resolve():
        return
    shutil.copy(source, destination)


def expect_status(response: object, expected: HTTPStatus) -> None:
    """Validate HTTP status for a response-like object."""
    status_code = getattr(response, 'status_code', None)
    if status_code != expected:
        pytest.fail(f'Expected {expected} status, got {status_code}')


def expect_truthy(value: object, message: str) -> None:
    """Fail the test if the value is falsy."""
    if not value:
        pytest.fail(message)


def track_results_before_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, bool]:
    """Track whether results are added before completion is marked."""
    state = {'add_called': False, 'marked_after_add': False}
    original_add_results = JobStore.add_results
    original_mark_completed = JobStore.mark_completed

    def add_results(self: JobStore, job_id: str, rows: list[dict[str, object]]) -> None:
        state['add_called'] = True
        original_add_results(self, job_id, rows)

    def mark_completed(self: JobStore, job_id: str) -> None:
        if not state['add_called']:
            pytest.fail('Expected results to be added before completion')
        state['marked_after_add'] = True
        original_mark_completed(self, job_id)

    monkeypatch.setattr(JobStore, 'add_results', add_results)
    monkeypatch.setattr(JobStore, 'mark_completed', mark_completed)
    return state


def write_temp_csv(tmp_path: Path, rows: int) -> Path:
    """Create a temporary CSV with unique IDs."""
    df_source = pd.read_csv(TEST_CSV)
    df_expanded = pd.concat([df_source] * max(1, rows // len(df_source) + 1), ignore_index=True)
    df_expanded = df_expanded.head(rows)
    id_column = df_expanded.columns[0]
    df_expanded[id_column] = [f'{value}-{idx}' for idx, value in enumerate(df_expanded[id_column])]
    temp_csv = tmp_path / 'responses.csv'
    temp_csv.parent.mkdir(parents=True, exist_ok=True)
    df_expanded.to_csv(temp_csv, index=False)
    return temp_csv


def track_add_results_calls(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    """Track how many times add_results is called."""
    state = {'calls': 0}
    original_add_results = JobStore.add_results

    def add_results(self: JobStore, job_id: str, rows: list[dict[str, object]]) -> None:
        state['calls'] += 1
        original_add_results(self, job_id, rows)

    monkeypatch.setattr(JobStore, 'add_results', add_results)
    return state
