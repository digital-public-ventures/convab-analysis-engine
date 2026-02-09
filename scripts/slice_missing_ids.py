"""Create a slice of the cleaned CSV containing only missing record IDs."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


MISSING_IDS = {
    "CFPB-2023-0038-0006",
    "CFPB-2023-0038-0007",
    "CFPB-2023-0038-0008",
    "CFPB-2023-0038-0009",
    "CFPB-2023-0038-0010",
    "CFPB-2023-0038-0021",
    "CFPB-2023-0038-0022",
    "CFPB-2023-0038-0023",
    "CFPB-2023-0038-0024",
    "CFPB-2023-0038-0025",
}


def _raise_csv_field_limit() -> None:
    max_size = sys.maxsize
    while True:
        try:
            csv.field_size_limit(max_size)
            return
        except OverflowError:
            max_size = max_size // 10


def main() -> int:
    input_path = Path(
        "app/data/efa267c019c11e33cf61afe5ffcf9d2b1fa8dbdcd987b83e911eeea795812334/"
        "cleaned_data/cleaned_tmpfr95eanq_comment_attachment_concat.csv"
    )
    output_path = Path(
        "app/data/efa267c019c11e33cf61afe5ffcf9d2b1fa8dbdcd987b83e911eeea795812334/"
        "cleaned_data/cleaned_missing_ids.csv"
    )
    id_column = "Document ID"

    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    _raise_csv_field_limit()

    with input_path.open("r", newline="", encoding="utf-8") as read_handle:
        reader = csv.DictReader(read_handle)
        if reader.fieldnames is None:
            raise ValueError(f"No header row found in {input_path}")
        if id_column not in reader.fieldnames:
            raise ValueError(
                f"Column '{id_column}' not found in {input_path}. "
                f"Available columns: {', '.join(reader.fieldnames)}"
            )

        with output_path.open("w", newline="", encoding="utf-8") as write_handle:
            writer = csv.DictWriter(write_handle, fieldnames=reader.fieldnames)
            writer.writeheader()
            count = 0
            for row in reader:
                record_id = row.get(id_column, "").strip()
                if record_id in MISSING_IDS:
                    writer.writerow(row)
                    count += 1

    print(f"Wrote {count} rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
