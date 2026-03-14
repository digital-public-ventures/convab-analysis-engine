"""Run clean -> schema -> analyze -> tag-fix without no_cache and validate outputs."""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_ROOT = REPO_ROOT / 'app' / 'tests' / 'fixtures'
EXAMPLE_DATASET_DIR = FIXTURES_ROOT / 'medical_billing_comments'
PROMPTS_DIR = EXAMPLE_DATASET_DIR / 'example_prompts'
RESPONSES_CSV = EXAMPLE_DATASET_DIR / 'responses_100.csv'
DATA_DIR = REPO_ROOT / 'app' / 'data'
PORT = 8010
DEFAULT_BASE_URL = f'http://127.0.0.1:{PORT}'


def _load_prompt(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def _poll_until_complete(client: httpx.Client, job_id: str, timeout_seconds: float = 600.0) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = client.get(f'/jobs/{job_id}')
            response.raise_for_status()
            payload = response.json()
            if payload.get('completed') is True:
                return payload
        except httpx.RequestError:
            time.sleep(0.5)
            continue
        time.sleep(0.25)
    raise TimeoutError('Timed out waiting for job completion')


def _count_rows(csv_path: Path) -> int:
    with csv_path.open(newline='', encoding='utf-8') as handle:
        return sum(1 for _ in csv.DictReader(handle))


def _resolve_cleaned_csv_path(content_hash: str) -> Path:
    cleaned_dir = DATA_DIR / content_hash / 'cleaned_data'
    cleaned_files = sorted(cleaned_dir.glob('cleaned_*.csv'))
    if not cleaned_files:
        raise FileNotFoundError(f'No cleaned CSV found in {cleaned_dir}')
    return cleaned_files[0]


def _validate_tag_fix_csv(csv_path: Path, schema: dict[str, Any], expected_rows: int) -> None:
    with csv_path.open(newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    if len(rows) != expected_rows:
        raise AssertionError(f'Expected {expected_rows} rows, got {len(rows)}')

    record_ids = [row.get('record_id') for row in rows]
    if len(record_ids) != len(set(record_ids)):
        raise AssertionError('Duplicate record_id values found in tag-fix CSV')

    categorical_fields = [
        field.get('field_name', '').strip() for field in schema.get('categorical_fields', []) if field.get('field_name')
    ]

    for row in rows:
        for field in categorical_fields:
            value = row.get(field, '')
            labels = [token.strip() for token in str(value).split(';') if token.strip()]
            if len(labels) != len(set(labels)):
                raise AssertionError(f'Duplicate labels found for field {field}: {labels}')


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run clean -> schema -> analyze -> tag-fix and validate outputs.')
    parser.add_argument(
        '--input-csv',
        type=Path,
        default=RESPONSES_CSV,
        help='Path to input CSV for /clean (default: app/tests/fixtures/medical_billing_comments/responses_100.csv)',
    )
    parser.add_argument(
        '--base-url',
        default=DEFAULT_BASE_URL,
        help='Base URL for the API server',
    )
    parser.add_argument(
        '--timeout-seconds',
        type=float,
        default=120.0,
        help='HTTP client timeout in seconds',
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    base_url = args.base_url
    input_csv = args.input_csv
    timeout_seconds = args.timeout_seconds
    use_case = _load_prompt(PROMPTS_DIR / 'use_case.txt')
    system_prompt = _load_prompt(PROMPTS_DIR / 'system_prompt.txt')

    if not input_csv.exists():
        raise FileNotFoundError(f'Input CSV missing: {input_csv}')

    with httpx.Client(base_url=base_url, timeout=timeout_seconds) as client:
        with input_csv.open('rb') as handle:
            clean_response = client.post(
                '/clean',
                files={'file': (input_csv.name, handle, 'text/csv')},
            )
        clean_response.raise_for_status()
        clean_payload = clean_response.json()
        job_id = clean_payload.get('job_id')
        if not job_id:
            raise AssertionError('Clean response missing job_id')
        content_hash = clean_payload.get('hash')
        if not content_hash:
            raise AssertionError('Clean response missing hash')
        print(f'clean.hash={content_hash}')

        _poll_until_complete(client, job_id)

        schema_response = client.post(
            f'/schema/{content_hash}',
            json={'use_case': use_case, 'sample_size': 10, 'head_size': 1},
        )
        schema_response.raise_for_status()
        schema_payload = schema_response.json()
        schema = schema_payload.get('schema')
        if not schema:
            raise AssertionError('Schema response missing schema')
        schema_hash = schema_payload.get('hash')
        if schema_hash != content_hash:
            raise AssertionError(f'Schema hash mismatch: expected {content_hash}, got {schema_hash}')
        print(f'schema.hash={schema_hash}')

        analyze_response = client.post(
            '/analyze',
            json={'hash': content_hash, 'use_case': use_case, 'system_prompt': system_prompt},
        )
        analyze_response.raise_for_status()
        analyze_payload = analyze_response.json()
        analyze_job_id = analyze_payload.get('job_id')
        if not analyze_job_id:
            raise AssertionError('Analyze response missing job_id')
        analyze_hash = analyze_payload.get('hash')
        if analyze_hash != content_hash:
            raise AssertionError(f'Analyze hash mismatch: expected {content_hash}, got {analyze_hash}')
        print(f'analyze.hash={analyze_hash}')
        _poll_until_complete(client, analyze_job_id)

        tag_fix_response = client.post(
            '/tag-fix',
            json={'hash': content_hash},
        )
        tag_fix_response.raise_for_status()
        tag_fix_payload = tag_fix_response.json()
        tag_fix_job_id = tag_fix_payload.get('job_id')
        if not tag_fix_job_id:
            raise AssertionError('Tag-fix response missing job_id')
        tag_fix_hash = tag_fix_payload.get('hash')
        if tag_fix_hash != content_hash:
            raise AssertionError(f'Tag-fix hash mismatch: expected {content_hash}, got {tag_fix_hash}')
        print(f'tag_fix.hash={tag_fix_hash}')
        _poll_until_complete(client, tag_fix_job_id)

    cleaned_csv = _resolve_cleaned_csv_path(content_hash)
    expected_rows = _count_rows(cleaned_csv)
    tag_fix_csv = DATA_DIR / content_hash / 'post-processing' / 'analysis_deduped.csv'
    if not tag_fix_csv.exists():
        raise FileNotFoundError(f'Tag-fix CSV not found: {tag_fix_csv}')

    _validate_tag_fix_csv(tag_fix_csv, schema, expected_rows)
    print('✅ Tag-fix CSV validation passed')


if __name__ == '__main__':
    main()
