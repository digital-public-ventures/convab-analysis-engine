"""CLI wrapper for data cleaner."""

import asyncio
import sys
from pathlib import Path

from app.processing import clean_csv

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m app.cli <csv_file>")
        sys.exit(1)

    raw_path = Path(sys.argv[1])
    if not raw_path.exists():
        print(f"Error: File not found: {raw_path}")
        sys.exit(1)

    try:
        cleaned_path = asyncio.run(clean_csv(raw_path))
        print(f"Cleaned: {raw_path.name} -> {cleaned_path}")
    except Exception as e:
        print(f"Error cleaning {raw_path.name}: {e}")
        sys.exit(1)
