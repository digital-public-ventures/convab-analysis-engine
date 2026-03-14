"""Run clean -> schema -> analyze -> tag-fix through the CLI and validate outputs."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_ROOT = REPO_ROOT / 'app' / 'tests' / 'fixtures'
EXAMPLE_DATASET_DIR = FIXTURES_ROOT / 'medical_billing_comments'
PROMPTS_DIR = EXAMPLE_DATASET_DIR / 'example_prompts'
RESPONSES_CSV = EXAMPLE_DATASET_DIR / 'responses_100.csv'
DATA_DIR = REPO_ROOT / 'app' / 'data'
CLI_COMMAND = [sys.executable, '-m', 'app.cli']


def _configure_csv_field_limit() -> None:
    max_size = sys.maxsize
    while max_size > 0:
        try:
            csv.field_size_limit(max_size)
        except OverflowError:
            max_size //= 10
        else:
            return


def _run_cli(args: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        [*CLI_COMMAND, *args, '--json'],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"CLI command failed ({' '.join(args)}):\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"CLI command returned non-JSON output ({' '.join(args)}):\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        ) from exc


def _count_rows(csv_path: Path) -> int:
    with csv_path.open(newline='', encoding='utf-8') as handle:
        return sum(1 for _ in csv.DictReader(handle))


def _validate_analysis_csv(csv_path: Path, expected_rows: int) -> None:
    with csv_path.open(newline='', encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle))

    if len(rows) != expected_rows:
        raise AssertionError(f'Expected {expected_rows} analysis rows, got {len(rows)}')

    record_ids = [row.get('record_id') for row in rows]
    if len(record_ids) != len(set(record_ids)):
        raise AssertionError('Duplicate record_id values found in analysis CSV')


def _validate_tag_fix_csv(csv_path: Path, schema_path: Path, expected_rows: int) -> None:
    schema = json.loads(schema_path.read_text(encoding='utf-8'))

    with csv_path.open(newline='', encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle))

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
    parser = argparse.ArgumentParser(description='Run the CLI pipeline against the fixture dataset and validate outputs.')
    parser.add_argument(
        '--input-csv',
        type=Path,
        default=RESPONSES_CSV,
        help='Path to input CSV for the clean stage',
    )
    return parser.parse_args()


def main() -> None:
    _configure_csv_field_limit()
    args = _parse_args()
    input_csv = args.input_csv

    if not input_csv.exists():
        raise FileNotFoundError(f'Input CSV missing: {input_csv}')

    clean_payload = _run_cli(['clean', '--input-csv', str(input_csv)])
    content_hash = str(clean_payload['hash'])
    print(f'clean.hash={content_hash}')

    schema_payload = _run_cli(
        [
            'schema',
            '--hash',
            content_hash,
            '--use-case-file',
            str(PROMPTS_DIR / 'use_case.txt'),
            '--sample-size',
            '10',
            '--head-size',
            '1',
        ]
    )
    if schema_payload.get('hash') != content_hash:
        raise AssertionError(f"Schema hash mismatch: expected {content_hash}, got {schema_payload.get('hash')}")
    print(f'schema.hash={schema_payload["hash"]}')

    analyze_payload = _run_cli(
        [
            'analyze',
            '--hash',
            content_hash,
            '--use-case-file',
            str(PROMPTS_DIR / 'use_case.txt'),
            '--system-prompt-file',
            str(PROMPTS_DIR / 'system_prompt.txt'),
        ]
    )
    if analyze_payload.get('hash') != content_hash:
        raise AssertionError(f"Analyze hash mismatch: expected {content_hash}, got {analyze_payload.get('hash')}")
    print(f'analyze.hash={analyze_payload["hash"]}')

    tag_fix_payload = _run_cli(['tag-fix', '--hash', content_hash])
    if tag_fix_payload.get('hash') != content_hash:
        raise AssertionError(f"Tag-fix hash mismatch: expected {content_hash}, got {tag_fix_payload.get('hash')}")
    print(f'tag_fix.hash={tag_fix_payload["hash"]}')

    cleaned_csv = Path(str(clean_payload['cleaned_csv']))
    expected_rows = _count_rows(cleaned_csv)
    analysis_csv = Path(str(analyze_payload['analysis_csv']))
    schema_path = Path(str(schema_payload['schema_path']))
    tag_fix_csv = Path(str(tag_fix_payload['tag_fix_csv']))

    if not analysis_csv.exists():
        raise FileNotFoundError(f'Analysis CSV not found: {analysis_csv}')
    if not schema_path.exists():
        raise FileNotFoundError(f'Schema JSON not found: {schema_path}')
    if not tag_fix_csv.exists():
        raise FileNotFoundError(f'Tag-fix CSV not found: {tag_fix_csv}')

    _validate_analysis_csv(analysis_csv, expected_rows)
    print('✅ CLI analysis CSV validation passed')
    _validate_tag_fix_csv(tag_fix_csv, schema_path, expected_rows)
    print('✅ CLI tag-fix CSV validation passed')


if __name__ == '__main__':
    main()
