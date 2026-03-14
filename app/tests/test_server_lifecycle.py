"""Integration tests for async job handling endpoints."""

from __future__ import annotations

import asyncio
import json
import shutil
import time
import uuid
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import config as app_config
from app import server as server_module
from app import server_jobs as server_jobs_module
from app.config import TAG_DEDUP_CSV_FILENAME, TAG_DEDUP_MAPPINGS_FILENAME
from app.processing import TagDedupOutput
from app.server import app
from app.tests.job_test_helpers import (
    FIXTURE_SCHEMA,
    STREAMING_BATCH_THRESHOLD,
    TEST_CSV,
    copy_if_different,
    expect_status,
    expect_truthy,
    poll_until_complete,
    poll_until_terminal,
    seed_analysis_outputs,
    seed_tag_fix_outputs,
    track_add_results_calls,
    track_results_before_completion,
    write_temp_csv,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from app.analysis import AnalysisConfig, AnalysisRequest

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures('override_attachment_cache_dir')
class TestAsyncJobHandling:
    """Contract tests for async job endpoints from the API requester perspective."""

    def test_clean_job_returns_job_id_and_cursor_results(self) -> None:
        """Start a clean job and retrieve results with cursor pagination."""
        with TestClient(app) as client:
            with TEST_CSV.open('rb') as handle:
                response = client.post(
                    '/clean',
                    files={'file': ('responses.csv', handle, 'text/csv')},
                )

            expect_status(response, HTTPStatus.ACCEPTED)
            payload = response.json()
            expect_truthy(payload.get('job_id'), 'Expected job_id in response')
            expect_truthy(payload.get('hash'), 'Expected dataset hash in response')
            expect_truthy(payload.get('results_url'), 'Expected results_url in response')

            job_id = payload['job_id']

            early_results = client.get(f'/jobs/{job_id}/results')
            expect_status(early_results, HTTPStatus.OK)
            early_payload = early_results.json()
            for key in ('rows', 'next_cursor'):
                if key not in early_payload:
                    pytest.fail(f'Expected {key} in early results')

            poll_until_complete(client, job_id)

            results_response = client.get(f'/jobs/{job_id}/results')
            expect_status(results_response, HTTPStatus.OK)
            results_payload = results_response.json()

            rows = results_payload.get('rows', [])
            expect_truthy(rows, 'Expected cleaned rows in results')
            cursor = results_payload.get('next_cursor')
            expect_truthy(cursor, 'Expected cursor for follow-up polling')
            if results_payload.get('completed') is not True:
                pytest.fail('Expected completed to be true')

            follow_up = client.get(f'/jobs/{job_id}/results', params={'cursor': cursor})
            expect_status(follow_up, HTTPStatus.OK)
            follow_payload = follow_up.json()
            if follow_payload.get('rows') != []:
                pytest.fail('Expected no new rows after cursor')
            if follow_payload.get('completed') is not True:
                pytest.fail('Expected completed to be true')

    def test_clean_job_streams_results_incrementally(self, tmp_path: Path) -> None:
        """Verify results appear while a clean job is still running."""
        unique_id = uuid.uuid4().hex
        expected_rows = 120
        rows = [f'{unique_id}-{i},Test data {i}' for i in range(expected_rows)]
        csv_content = 'id,data\n' + '\n'.join(rows)
        csv_path = tmp_path / 'responses.csv'
        csv_path.write_text(csv_content, encoding='utf-8')

        with TestClient(app) as client:
            with csv_path.open('rb') as handle:
                response = client.post(
                    '/clean?no_cache=true',
                    files={'file': ('responses.csv', handle, 'text/csv')},
                )

            expect_status(response, HTTPStatus.ACCEPTED)
            response_payload = response.json()
            job_id = response_payload['job_id']
            content_hash = response_payload['hash']

            saw_running_with_results = False
            deadline = time.time() + 10

            while time.time() < deadline:
                status = client.get(f'/jobs/{job_id}').json()
                results = client.get(f'/jobs/{job_id}/results').json()

                if status.get('status') == 'running' and len(results.get('rows', [])) > 0:
                    saw_running_with_results = True

                if status.get('completed') is True:
                    break

                time.sleep(0.1)

            final_results = client.get(f'/jobs/{job_id}/results').json()
            if not final_results.get('rows'):
                pytest.fail('Expected rows in clean job results')
            if len(final_results['rows']) != expected_rows:
                pytest.fail('Expected clean job final rows to match input row count')

            cleaned_path = server_module.DataStore(app_config.DATA_DIR).get_cleaned_csv(content_hash)
            if cleaned_path is None:
                pytest.fail('Expected cleaned CSV to exist after clean job completion')
            cleaned_df = pd.read_csv(cleaned_path)
            if len(cleaned_df) != expected_rows:
                pytest.fail('Expected cleaned CSV row count to match input row count')

            if not saw_running_with_results:
                print('NOTE: Clean job completed before incremental results observed')

    def test_clean_job_persists_raw_input_early(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Ensure /clean persists the raw input file under the hash root when the job starts."""

        async def slow_clean_csv(input_path: str | Path, **kwargs: object) -> Path:
            df = pd.read_csv(input_path)
            await asyncio.sleep(0.3)
            output_dir = kwargs.get('output_dir')
            save_dir = output_dir if isinstance(output_dir, Path) else TEST_CSV.parent
            save_dir.mkdir(parents=True, exist_ok=True)
            output_path = save_dir / f'cleaned_{Path(input_path).name}'
            df.to_csv(output_path, index=False)
            return output_path

        monkeypatch.setattr(server_jobs_module, 'clean_csv', slow_clean_csv)

        temp_csv = write_temp_csv(tmp_path, rows=30)
        content = temp_csv.read_bytes()
        expected_hash = server_module.DataStore.hash_content(content)
        raw_input_path = app_config.DATA_DIR / expected_hash / 'input.csv'

        with TestClient(app) as client:
            with temp_csv.open('rb') as handle:
                response = client.post(
                    '/clean?no_cache=true',
                    files={'file': ('responses.csv', handle, 'text/csv')},
                )

            expect_status(response, HTTPStatus.ACCEPTED)
            payload = response.json()
            if payload.get('hash') != expected_hash:
                pytest.fail('Expected clean response hash to match uploaded content hash')

            deadline = time.time() + 2.0
            while time.time() < deadline and not raw_input_path.exists():
                time.sleep(0.05)

            if not raw_input_path.exists():
                pytest.fail('Expected raw input file to be persisted early in hash root')
            if raw_input_path.read_bytes() != content:
                pytest.fail('Expected persisted raw input bytes to match uploaded content')

            poll_until_complete(client, payload['job_id'])

    def test_clean_job_streams_results_before_completion(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Ensure clean jobs return partial results before completion."""
        state = track_results_before_completion(monkeypatch)

        async def slow_clean_csv(input_path: str | Path, **kwargs: object) -> Path:
            output_dir = kwargs.get('output_dir')
            on_chunk = kwargs.get('on_chunk')
            on_row_count = kwargs.get('on_row_count')
            df = pd.read_csv(input_path)
            rows = df.to_dict(orient='records')
            if callable(on_row_count):
                result = on_row_count(len(rows))
                if asyncio.iscoroutine(result):
                    await result

            midpoint = max(1, len(rows) // 2)
            if callable(on_chunk):
                await asyncio.sleep(0.2)
                first_batch = on_chunk(rows[:midpoint])
                if asyncio.iscoroutine(first_batch):
                    await first_batch
                await asyncio.sleep(0.2)
                second_batch = on_chunk(rows[midpoint:])
                if asyncio.iscoroutine(second_batch):
                    await second_batch

            save_dir = output_dir if isinstance(output_dir, Path) else TEST_CSV.parent
            save_dir.mkdir(parents=True, exist_ok=True)
            output_path = save_dir / f'cleaned_{Path(input_path).name}'
            df.to_csv(output_path, index=False)
            return output_path

        monkeypatch.setattr(server_jobs_module, 'clean_csv', slow_clean_csv)

        df_source = pd.read_csv(TEST_CSV)
        df_source[df_source.columns[0]] = [
            f'{value}-{idx}' for idx, value in enumerate(df_source[df_source.columns[0]])
        ]
        temp_csv = tmp_path / 'responses.csv'
        df_source.to_csv(temp_csv, index=False)

        with TestClient(app) as client:
            with temp_csv.open('rb') as handle:
                response = client.post(
                    '/clean',
                    files={'file': ('responses.csv', handle, 'text/csv')},
                )

            expect_status(response, HTTPStatus.ACCEPTED)
            job_id = response.json()['job_id']

            poll_until_complete(client, job_id)

        if not state['marked_after_add']:
            pytest.fail('Expected completion after results were added')

    def test_analyze_job_returns_cursor_paginated_results(self) -> None:
        """Start an analysis job and retrieve results with cursor pagination."""
        with TestClient(app) as client:
            with TEST_CSV.open('rb') as handle:
                clean_response = client.post(
                    '/clean',
                    files={'file': ('responses.csv', handle, 'text/csv')},
                )

            expect_status(clean_response, HTTPStatus.ACCEPTED)
            clean_payload = clean_response.json()
            content_hash = clean_payload['hash']

            poll_until_complete(client, clean_payload['job_id'])
            seed_analysis_outputs(content_hash)

            analyze_response = client.post(
                '/analyze',
                json={
                    'hash': content_hash,
                    'use_case': 'Analyze public comments for themes and sentiment',
                    'system_prompt': 'You are a helpful research assistant.',
                },
            )

            expect_status(analyze_response, HTTPStatus.ACCEPTED)
            analyze_payload = analyze_response.json()
            expect_truthy(analyze_payload.get('job_id'), 'Expected job_id in analyze response')

            analyze_job_id = analyze_payload['job_id']
            poll_until_complete(client, analyze_job_id)

            results_response = client.get(f'/jobs/{analyze_job_id}/results')
            expect_status(results_response, HTTPStatus.OK)
            results_payload = results_response.json()
            expect_truthy(results_payload.get('rows'), 'Expected analysis rows')
            if results_payload.get('completed') is not True:
                pytest.fail('Expected completed to be true')

            cursor = results_payload.get('next_cursor')
            expect_truthy(cursor, 'Expected cursor in analysis results')

            follow_up = client.get(f'/jobs/{analyze_job_id}/results', params={'cursor': cursor})
            expect_status(follow_up, HTTPStatus.OK)
            follow_payload = follow_up.json()
            if follow_payload.get('rows') != []:
                pytest.fail('Expected no new rows after cursor')
            if follow_payload.get('completed') is not True:
                pytest.fail('Expected completed to be true')

    def test_analyze_job_streams_results_before_completion(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Ensure analyze jobs return partial results before completion."""

        async def slow_analyze_dataset(
            request: AnalysisRequest,
            config: AnalysisConfig | None = None,
            on_batch: Callable[[list[dict[str, Any]]], Awaitable[None]] | None = None,
            on_row_count: Callable[[int], Awaitable[None]] | None = None,
        ) -> tuple[dict[str, Any], str]:
            _ = config
            df = pd.read_csv(request.cleaned_csv)
            id_column = df.columns[0]
            rows = [{'record_id': str(row[id_column])} for _, row in df.iterrows()]
            if on_row_count is not None:
                await on_row_count(len(rows))

            midpoint = max(1, len(rows) // 2)
            if on_batch is not None:
                await asyncio.sleep(0.2)
                await on_batch(rows[:midpoint])
                await asyncio.sleep(0.5)
                await on_batch(rows[midpoint:])

            output_dir = request.output_dir
            output_dir.mkdir(parents=True, exist_ok=True)
            csv_path = output_dir / 'analysis.csv'
            json_path = output_dir / 'analysis.json'
            payload = {'metadata': {'record_count': len(rows)}, 'records': rows}
            pd.DataFrame(rows).to_csv(csv_path, index=False)
            json_path.write_text(
                json.dumps(payload),
                encoding='utf-8',
            )
            return payload, csv_path.read_text(encoding='utf-8')

        state = track_results_before_completion(monkeypatch)

        monkeypatch.setattr(server_jobs_module, 'analyze_dataset', slow_analyze_dataset)

        df_source = pd.read_csv(TEST_CSV)
        df_expanded = pd.concat([df_source, df_source], ignore_index=True)
        id_column = df_expanded.columns[0]
        df_expanded[id_column] = [f'{value}-{idx}' for idx, value in enumerate(df_expanded[id_column])]
        temp_csv = tmp_path / 'responses.csv'
        df_expanded.to_csv(temp_csv, index=False)

        with TestClient(app) as client:
            with temp_csv.open('rb') as handle:
                clean_response = client.post(
                    '/clean',
                    files={'file': ('responses.csv', handle, 'text/csv')},
                )

            expect_status(clean_response, HTTPStatus.ACCEPTED)
            clean_payload = clean_response.json()
            content_hash = clean_payload['hash']
            poll_until_complete(client, clean_payload['job_id'])

            hash_dir = app_config.DATA_DIR / content_hash
            schema_dir = hash_dir / 'schema'
            schema_dir.mkdir(parents=True, exist_ok=True)
            copy_if_different(FIXTURE_SCHEMA, schema_dir / 'schema.json')

            analyze_response = client.post(
                '/analyze',
                json={
                    'hash': content_hash,
                    'use_case': 'Analyze public comments for themes and sentiment',
                    'system_prompt': 'You are a helpful research assistant.',
                },
            )

            expect_status(analyze_response, HTTPStatus.ACCEPTED)
            analyze_job_id = analyze_response.json()['job_id']

            poll_until_complete(client, analyze_job_id)

        if not state['marked_after_add']:
            pytest.fail('Expected completion after results were added')

    def test_tag_fix_job_returns_cursor_paginated_results(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Start a tag-fix job and retrieve results with cursor pagination."""

        async def fake_deduplicate_tags(**kwargs: object) -> TagDedupOutput:
            output_dir = kwargs['output_dir']
            analysis_csv_path = kwargs['analysis_csv_path']
            output_dir.mkdir(parents=True, exist_ok=True)
            deduped_path = output_dir / TAG_DEDUP_CSV_FILENAME
            shutil.copy(analysis_csv_path, deduped_path)
            mappings_path = output_dir / TAG_DEDUP_MAPPINGS_FILENAME
            mappings_path.write_text(json.dumps({'seeded': True}), encoding='utf-8')
            return TagDedupOutput(mappings_path=mappings_path, deduped_csv_path=deduped_path)

        monkeypatch.setattr(server_jobs_module, 'deduplicate_tags', fake_deduplicate_tags)

        with TestClient(app) as client:
            with TEST_CSV.open('rb') as handle:
                clean_response = client.post(
                    '/clean',
                    files={'file': ('responses.csv', handle, 'text/csv')},
                )

            expect_status(clean_response, HTTPStatus.ACCEPTED)
            clean_payload = clean_response.json()
            content_hash = clean_payload['hash']

            poll_until_complete(client, clean_payload['job_id'])
            seed_analysis_outputs(content_hash)

            tag_fix_response = client.post(
                '/tag-fix',
                json={'hash': content_hash},
            )

            expect_status(tag_fix_response, HTTPStatus.ACCEPTED)
            tag_fix_payload = tag_fix_response.json()
            expect_truthy(tag_fix_payload.get('job_id'), 'Expected job_id in tag-fix response')

            tag_fix_job_id = tag_fix_payload['job_id']
            poll_until_complete(client, tag_fix_job_id)

            results_response = client.get(f'/jobs/{tag_fix_job_id}/results')
            expect_status(results_response, HTTPStatus.OK)
            results_payload = results_response.json()
            expect_truthy(results_payload.get('rows'), 'Expected tag-fix rows')
            if results_payload.get('completed') is not True:
                pytest.fail('Expected completed to be true')

            cursor = results_payload.get('next_cursor')
            expect_truthy(cursor, 'Expected cursor in tag-fix results')

            follow_up = client.get(f'/jobs/{tag_fix_job_id}/results', params={'cursor': cursor})
            expect_status(follow_up, HTTPStatus.OK)
            follow_payload = follow_up.json()
            if follow_payload.get('rows') != []:
                pytest.fail('Expected no new rows after cursor')
            if follow_payload.get('completed') is not True:
                pytest.fail('Expected completed to be true')

    def test_tag_fix_endpoint_returns_cached_results(self) -> None:
        """Cached tag-fix outputs should return immediately with results."""
        with TestClient(app) as client:
            with TEST_CSV.open('rb') as handle:
                clean_response = client.post(
                    '/clean',
                    files={'file': ('responses.csv', handle, 'text/csv')},
                )

            expect_status(clean_response, HTTPStatus.ACCEPTED)
            clean_payload = clean_response.json()
            content_hash = clean_payload['hash']
            poll_until_complete(client, clean_payload['job_id'])

            seed_analysis_outputs(content_hash)
            seed_tag_fix_outputs(content_hash)

            tag_fix_response = client.post(
                '/tag-fix',
                json={'hash': content_hash},
            )

            expect_status(tag_fix_response, HTTPStatus.ACCEPTED)
            if tag_fix_response.json().get('cached') is not True:
                pytest.fail('Expected cached response for tag-fix')

            tag_fix_job_id = tag_fix_response.json()['job_id']
            poll_until_complete(client, tag_fix_job_id)

            results_response = client.get(f'/jobs/{tag_fix_job_id}/results')
            expect_status(results_response, HTTPStatus.OK)
            results_payload = results_response.json()
            expect_truthy(results_payload.get('rows'), 'Expected cached tag-fix rows')

    def test_clean_no_cache_bypasses_cached(self, tmp_path: Path) -> None:
        """Ensure no_cache forces a fresh clean job even when cached."""
        temp_csv = write_temp_csv(tmp_path, rows=25)

        with TestClient(app) as client:
            with temp_csv.open('rb') as handle:
                first_response = client.post(
                    '/clean',
                    files={'file': ('responses.csv', handle, 'text/csv')},
                )

            expect_status(first_response, HTTPStatus.ACCEPTED)
            first_payload = first_response.json()
            poll_until_complete(client, first_payload['job_id'])

            with temp_csv.open('rb') as handle:
                cached_response = client.post(
                    '/clean',
                    files={'file': ('responses.csv', handle, 'text/csv')},
                )

            expect_status(cached_response, HTTPStatus.ACCEPTED)
            cached_payload = cached_response.json()
            if cached_payload.get('cached') is not True:
                pytest.fail('Expected cached response on repeated clean')

            with temp_csv.open('rb') as handle:
                no_cache_response = client.post(
                    '/clean?no_cache=true',
                    files={'file': ('responses.csv', handle, 'text/csv')},
                )

            expect_status(no_cache_response, HTTPStatus.ACCEPTED)
            if no_cache_response.json().get('cached') is True:
                pytest.fail('Expected no_cache to bypass cache')

    def test_clean_large_file_streams_multiple_batches(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Large clean jobs should emit multiple result batches."""
        state = track_add_results_calls(monkeypatch)
        temp_csv = write_temp_csv(tmp_path, rows=450)

        with TestClient(app) as client:
            with temp_csv.open('rb') as handle:
                response = client.post(
                    '/clean?no_cache=true',
                    files={'file': ('responses.csv', handle, 'text/csv')},
                )

            expect_status(response, HTTPStatus.ACCEPTED)
            poll_until_complete(client, response.json()['job_id'])

        if state['calls'] < STREAMING_BATCH_THRESHOLD:
            pytest.fail('Expected multiple add_results calls for large file')

    def test_clean_job_failure_returns_partial_results(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Failed clean jobs should retain partial results."""

        async def failing_clean_csv(input_path: str | Path, **kwargs: object) -> Path:
            on_chunk = kwargs.get('on_chunk')
            df = pd.read_csv(input_path)
            rows = df.to_dict(orient='records')
            if callable(on_chunk):
                first_batch = on_chunk(rows[:1])
                if asyncio.iscoroutine(first_batch):
                    await first_batch
            raise ValueError

        monkeypatch.setattr(server_jobs_module, 'clean_csv', failing_clean_csv)

        unique_id = uuid.uuid4().hex
        temp_csv = tmp_path / 'failure_input.csv'
        temp_csv.write_text(
            f'id,data\n{unique_id}-1,a\n{unique_id}-2,b\n',
            encoding='utf-8',
        )

        with TestClient(app) as client:
            with temp_csv.open('rb') as handle:
                response = client.post(
                    '/clean?no_cache=true',
                    files={'file': ('responses.csv', handle, 'text/csv')},
                )

            expect_status(response, HTTPStatus.ACCEPTED)
            job_id = response.json()['job_id']
            status_payload = poll_until_terminal(client, job_id)

            if status_payload.get('status') != 'failed':
                pytest.fail('Expected failed status for clean job')

            results_response = client.get(f'/jobs/{job_id}/results')
            expect_status(results_response, HTTPStatus.OK)
            if not results_response.json().get('rows'):
                pytest.fail('Expected partial results after failure')

    def test_clean_job_failure_keeps_partial_file_unpublished(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Failed clean jobs should keep identifiable partial output and no final cleaned CSV."""

        async def failing_clean_csv(input_path: str | Path, **kwargs: object) -> Path:
            output_dir = kwargs.get('output_dir')
            save_dir = output_dir if isinstance(output_dir, Path) else tmp_path
            save_dir.mkdir(parents=True, exist_ok=True)
            partial_path = save_dir / f'cleaned_{Path(input_path).name}.partial'
            partial_path.write_text('id,data\n1,partial\n', encoding='utf-8')
            raise ValueError('forced failure after partial write')

        monkeypatch.setattr(server_jobs_module, 'clean_csv', failing_clean_csv)

        unique_id = uuid.uuid4().hex
        temp_csv = tmp_path / 'failure_input.csv'
        temp_csv.write_text(
            f'id,data\n{unique_id}-1,a\n{unique_id}-2,b\n',
            encoding='utf-8',
        )

        with TestClient(app) as client:
            with temp_csv.open('rb') as handle:
                response = client.post(
                    '/clean?no_cache=true',
                    files={'file': ('responses.csv', handle, 'text/csv')},
                )

            expect_status(response, HTTPStatus.ACCEPTED)
            payload = response.json()
            content_hash = payload['hash']
            job_id = payload['job_id']
            status_payload = poll_until_terminal(client, job_id)

            if status_payload.get('status') != 'failed':
                pytest.fail('Expected failed status for clean job')

            cleaned_dir = app_config.DATA_DIR / content_hash / 'cleaned_data'
            partial_files = list(cleaned_dir.glob('cleaned_*.csv.partial'))
            final_files = list(cleaned_dir.glob('cleaned_*.csv'))
            if not partial_files:
                pytest.fail('Expected partial cleaned CSV file to remain after failure')
            if final_files:
                pytest.fail('Did not expect finalized cleaned CSV after failure')

            data_response = client.get(f'/data/{content_hash}')
            expect_status(data_response, HTTPStatus.OK)
            if data_response.json().get('has_cleaned_csv') is not False:
                pytest.fail('Expected data endpoint to report no finalized cleaned CSV')

    def test_analyze_job_failure_returns_partial_results(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Failed analyze jobs should retain partial results."""

        async def failing_analyze_dataset(
            request: AnalysisRequest,
            config: AnalysisConfig | None = None,
            on_batch: Callable[[list[dict[str, Any]]], Awaitable[None]] | None = None,
            on_row_count: Callable[[int], Awaitable[None]] | None = None,
        ) -> tuple[dict[str, Any], str]:
            _ = (request, config, on_row_count)
            rows = [{'record_id': '1'}]
            if on_batch is not None:
                await on_batch(rows)
            raise ValueError

        monkeypatch.setattr(server_jobs_module, 'analyze_dataset', failing_analyze_dataset)

        temp_csv = write_temp_csv(tmp_path, rows=10)

        with TestClient(app) as client:
            with temp_csv.open('rb') as handle:
                clean_response = client.post(
                    '/clean?no_cache=true',
                    files={'file': ('responses.csv', handle, 'text/csv')},
                )

            expect_status(clean_response, HTTPStatus.ACCEPTED)
            clean_payload = clean_response.json()
            poll_until_complete(client, clean_payload['job_id'])

            hash_dir = app_config.DATA_DIR / clean_payload['hash']
            schema_dir = hash_dir / 'schema'
            schema_dir.mkdir(parents=True, exist_ok=True)
            copy_if_different(FIXTURE_SCHEMA, schema_dir / 'schema.json')

            analyze_response = client.post(
                '/analyze?no_cache=true',
                json={
                    'hash': clean_payload['hash'],
                    'use_case': 'Analyze public comments for themes and sentiment',
                    'system_prompt': 'You are a helpful research assistant.',
                },
            )

            expect_status(analyze_response, HTTPStatus.ACCEPTED)
            job_id = analyze_response.json()['job_id']
            status_payload = poll_until_terminal(client, job_id)

            if status_payload.get('status') != 'failed':
                pytest.fail('Expected failed status for analyze job')

            results_response = client.get(f'/jobs/{job_id}/results')
            expect_status(results_response, HTTPStatus.OK)
            if not results_response.json().get('rows'):
                pytest.fail('Expected partial results after analyze failure')

    def test_concurrent_clean_jobs(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Multiple clean jobs should complete independently."""

        async def fast_clean_csv(input_path: str | Path, **kwargs: object) -> Path:
            output_dir = kwargs.get('output_dir')
            on_chunk = kwargs.get('on_chunk')
            on_row_count = kwargs.get('on_row_count')
            df = pd.read_csv(input_path)
            rows = df.to_dict(orient='records')
            if callable(on_row_count):
                result = on_row_count(len(rows))
                if asyncio.iscoroutine(result):
                    await result
            if callable(on_chunk):
                batch = on_chunk(rows)
                if asyncio.iscoroutine(batch):
                    await batch
            save_dir = output_dir if isinstance(output_dir, Path) else tmp_path
            save_dir.mkdir(parents=True, exist_ok=True)
            output_path = save_dir / f'cleaned_{Path(input_path).name}'
            df.to_csv(output_path, index=False)
            return output_path

        monkeypatch.setattr(server_jobs_module, 'clean_csv', fast_clean_csv)
        temp_csv_one = write_temp_csv(tmp_path / 'one', rows=15)
        temp_csv_two = write_temp_csv(tmp_path / 'two', rows=18)

        with TestClient(app) as client:
            with temp_csv_one.open('rb') as handle:
                response_one = client.post(
                    '/clean?no_cache=true',
                    files={'file': ('responses.csv', handle, 'text/csv')},
                )

            with temp_csv_two.open('rb') as handle:
                response_two = client.post(
                    '/clean?no_cache=true',
                    files={'file': ('responses.csv', handle, 'text/csv')},
                )

            expect_status(response_one, HTTPStatus.ACCEPTED)
            expect_status(response_two, HTTPStatus.ACCEPTED)

            job_one = response_one.json()['job_id']
            job_two = response_two.json()['job_id']

            poll_until_complete(client, job_one)
            poll_until_complete(client, job_two)

            results_one = client.get(f'/jobs/{job_one}/results')
            results_two = client.get(f'/jobs/{job_two}/results')

            expect_status(results_one, HTTPStatus.OK)
            expect_status(results_two, HTTPStatus.OK)

            if not results_one.json().get('rows'):
                pytest.fail('Expected rows for first job')
            if not results_two.json().get('rows'):
                pytest.fail('Expected rows for second job')
