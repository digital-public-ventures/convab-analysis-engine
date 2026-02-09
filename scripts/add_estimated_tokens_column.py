"""Append estimated token counts to each row in a CSV file."""

from __future__ import annotations

import argparse
import csv
import math
import re
import string
import sys
from pathlib import Path

DEFAULT_INPUT = Path('app/tests/fixtures/raw/clean_5000.csv')
DEFAULT_TEXT_COLUMN = 'Comment'
DEFAULT_OUTPUT_SUFFIX = '_with_estimated_tokens'
DEFAULT_NEW_COLUMN = 'estimated_tokens'


def _raise_csv_field_limit() -> None:
    max_size = sys.maxsize
    while True:
        try:
            csv.field_size_limit(max_size)
        except OverflowError:
            max_size //= 10
        else:
            return


def _estimate_tokens(text: str) -> int:
    """Estimate tokens with the same heuristic used by the rate limiter."""
    split_pattern = rf'[{re.escape(string.punctuation)}\s]+'
    words = [word for word in re.split(split_pattern, text) if word]
    return max(1, math.ceil(len(words) / 0.75))


def _default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f'{input_path.stem}{DEFAULT_OUTPUT_SUFFIX}{input_path.suffix}')


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Append an estimated_tokens column to a CSV.')
    parser.add_argument(
        '--input',
        type=Path,
        default=DEFAULT_INPUT,
        help='Input CSV path (default: app/tests/fixtures/raw/clean_5000.csv).',
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='Output CSV path (default: <input>_with_estimated_tokens.csv).',
    )
    parser.add_argument(
        '--text-column',
        default=DEFAULT_TEXT_COLUMN,
        help='Column to estimate tokens from (default: Comment).',
    )
    parser.add_argument(
        '--new-column',
        default=DEFAULT_NEW_COLUMN,
        help='Name of appended token column (default: estimated_tokens).',
    )
    parser.add_argument(
        '--max-rows',
        type=int,
        default=None,
        help='Optional maximum rows to process for quick debugging.',
    )
    return parser.parse_args()


def main() -> int:
    """Read CSV rows, append estimated token counts, and write to output."""
    args = _parse_args()
    input_path: Path = args.input
    output_path: Path = args.output or _default_output_path(input_path)
    text_column: str = args.text_column
    new_column: str = args.new_column
    max_rows: int | None = args.max_rows

    if not input_path.exists():
        print(f'Input CSV not found: {input_path}')
        return 1

    _raise_csv_field_limit()

    with input_path.open('r', newline='', encoding='utf-8') as in_handle:
        reader = csv.DictReader(in_handle)
        if not reader.fieldnames:
            print(f'No header row found in {input_path}')
            return 1
        if text_column not in reader.fieldnames:
            print(f"Column '{text_column}' not found in {input_path}")
            return 1

        fieldnames = list(reader.fieldnames)
        if new_column not in fieldnames:
            fieldnames.append(new_column)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('w', newline='', encoding='utf-8') as out_handle:
            writer = csv.DictWriter(out_handle, fieldnames=fieldnames)
            writer.writeheader()

            processed = 0
            for row in reader:
                text = str(row.get(text_column, '') or '')
                row[new_column] = str(_estimate_tokens(text))
                writer.writerow(row)
                processed += 1
                if max_rows is not None and processed >= max_rows:
                    break

    print(f'Wrote {processed} rows to {output_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
