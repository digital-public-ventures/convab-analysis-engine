"""Data processing utilities for CSV data."""

import csv
import json
from pathlib import Path
from typing import Literal

MAX_ROWS_SAFETY_LIMIT = 10


class DataProcessor:
    """Handles loading and processing of CSV data."""

    def __init__(self, csv_path: str):
        """Initialize the data processor.

        Args:
            csv_path: Path to the CSV file
        """
        self.csv_path = Path(csv_path)
        if not self.csv_path.exists():
            raise FileNotFoundError(f'CSV file not found: {csv_path}')

    def load_sample(self, n_rows: int | Literal['all'] = 5) -> list[dict]:
        """Load a sample of records from CSV.

        Args:
            n_rows: Number of rows to sample, or "all" for all rows
                   (capped at MAX_ROWS_SAFETY_LIMIT for safety)

        Returns:
            List of records as dictionaries
        """
        # Apply safety limit
        if n_rows == 'all' or n_rows > MAX_ROWS_SAFETY_LIMIT:
            n_rows = MAX_ROWS_SAFETY_LIMIT
            print(f'⚠️  Sample size capped at {MAX_ROWS_SAFETY_LIMIT} rows for safety during development')

        records = []

        with open(self.csv_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for i, row in enumerate(reader):
                if i >= n_rows:
                    break

                # Clean up the row - remove empty values
                cleaned_row = {k: v.strip() for k, v in row.items() if v.strip()}
                records.append(cleaned_row)

        print(f'✓ Loaded {len(records)} records from {self.csv_path.name}')
        return records

    def convert_to_json(self, records: list[dict]) -> str:
        """Convert records to formatted JSON string.

        Args:
            records: List of data records

        Returns:
            JSON string representation
        """
        return json.dumps(records, indent=2)

    def save_json(self, records: list[dict], output_path: str) -> None:
        """Save records to a JSON file.

        Args:
            records: List of data records
            output_path: Path to save JSON file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=2)

        print(f'✓ Saved {len(records)} records to {output_path}')
