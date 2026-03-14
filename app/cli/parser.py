"""Argument parser for the dataset CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.config import SCHEMA_DEFAULT_NUM_HEAD_ROWS, SCHEMA_DEFAULT_NUM_SAMPLE_ROWS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='python -m app.cli',
        description='Run dataset pipeline stages without the API server.',
    )
    subparsers = parser.add_subparsers(dest='command')

    clean_parser = subparsers.add_parser('clean', help='Clean a raw CSV and store artifacts under app/data/<hash>/')
    clean_parser.add_argument('--input-csv', type=Path, required=True, help='Path to the raw input CSV')
    clean_parser.add_argument('--no-cache', action='store_true', help='Re-run cleaning even if cleaned output exists')
    clean_parser.add_argument(
        '--no-cache-ocr',
        action='store_true',
        help='Bypass OCR cache reads and force fresh OCR extraction',
    )
    clean_parser.add_argument('--json', action='store_true', help='Emit a single JSON payload to stdout')

    schema_parser = subparsers.add_parser('schema', help='Generate a schema for an existing cleaned dataset hash')
    schema_parser.add_argument('--hash', required=True, dest='content_hash', help='Dataset hash from the clean stage')
    schema_parser.add_argument('--use-case-file', type=Path, required=True, help='Path to the use-case prompt text file')
    schema_parser.add_argument(
        '--sample-size',
        type=int,
        default=SCHEMA_DEFAULT_NUM_SAMPLE_ROWS,
        help='Maximum number of random rows sampled after the head rows',
    )
    schema_parser.add_argument(
        '--head-size',
        type=int,
        default=SCHEMA_DEFAULT_NUM_HEAD_ROWS,
        help='Number of leading rows that must always be included in schema generation',
    )
    schema_parser.add_argument('--json', action='store_true', help='Emit a single JSON payload to stdout')

    analyze_parser = subparsers.add_parser('analyze', help='Analyze a cleaned dataset using an existing schema')
    analyze_parser.add_argument('--hash', required=True, dest='content_hash', help='Dataset hash from the clean stage')
    analyze_parser.add_argument('--use-case-file', type=Path, required=True, help='Path to the use-case prompt text file')
    analyze_parser.add_argument(
        '--system-prompt-file',
        type=Path,
        required=True,
        help='Path to the system prompt text file',
    )
    analyze_parser.add_argument('--no-cache', action='store_true', help='Re-run analysis even if cached output exists')
    analyze_parser.add_argument('--json', action='store_true', help='Emit a single JSON payload to stdout')

    tag_fix_parser = subparsers.add_parser('tag-fix', help='Deduplicate categorical tags for an analyzed dataset')
    tag_fix_parser.add_argument('--hash', required=True, dest='content_hash', help='Dataset hash from the clean stage')
    tag_fix_parser.add_argument('--no-cache', action='store_true', help='Re-run tag fix even if cached output exists')
    tag_fix_parser.add_argument('--json', action='store_true', help='Emit a single JSON payload to stdout')

    data_info_parser = subparsers.add_parser('data-info', help='Inspect which artifacts exist for a dataset hash')
    data_info_parser.add_argument('--hash', required=True, dest='content_hash', help='Dataset hash from the clean stage')
    data_info_parser.add_argument('--json', action='store_true', help='Emit a single JSON payload to stdout')

    return parser
