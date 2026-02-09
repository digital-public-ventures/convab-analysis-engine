"""Find missing record_id values between a full dataset and an analyzed CSV."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Iterable, Set


def _raise_csv_field_limit() -> None:
    max_size = sys.maxsize
    while True:
        try:
            csv.field_size_limit(max_size)
            return
        except OverflowError:
            max_size = max_size // 10


def _load_ids(csv_path: Path, column: str) -> Set[str]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    _raise_csv_field_limit()
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"No header row found in {csv_path}")
        if column not in reader.fieldnames:
            raise ValueError(
                f"Column '{column}' not found in {csv_path}. "
                f"Available columns: {', '.join(reader.fieldnames)}"
            )
        ids = {row[column].strip() for row in reader if row.get(column)}
    return ids


def _sorted_ids(ids: Iterable[str]) -> list[str]:
    return sorted(ids)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare two CSVs and report missing record_id values."
    )
    parser.add_argument(
        "--full",
        required=True,
        type=Path,
        help="Path to the full (pre-analysis) CSV.",
    )
    parser.add_argument(
        "--analysis",
        required=True,
        type=Path,
        help="Path to the analyzed CSV to compare against the full list.",
    )
    parser.add_argument(
        "--column",
        default="record_id",
        help="Column name containing record IDs in both CSVs (default: record_id).",
    )
    parser.add_argument(
        "--full-column",
        default=None,
        help="Column name for IDs in the full CSV (overrides --column).",
    )
    parser.add_argument(
        "--analysis-column",
        default=None,
        help="Column name for IDs in the analysis CSV (overrides --column).",
    )
    args = parser.parse_args()

    full_column = args.full_column or args.column
    analysis_column = args.analysis_column or args.column

    full_ids = _load_ids(args.full, full_column)
    analysis_ids = _load_ids(args.analysis, analysis_column)

    missing = full_ids - analysis_ids
    extra = analysis_ids - full_ids

    print(f"Full CSV IDs: {len(full_ids)}")
    print(f"Analysis CSV IDs: {len(analysis_ids)}")
    print(f"Missing IDs: {len(missing)}")
    if missing:
        for record_id in _sorted_ids(missing):
            print(record_id)

    print(f"Extra IDs (present in analysis, not in full): {len(extra)}")
    if extra:
        for record_id in _sorted_ids(extra):
            print(record_id)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
