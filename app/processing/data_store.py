"""Hash-based data store for CSV processing artifacts."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, cast

import pandas as pd

from app.config import DATA_DIR


def read_csv_rows(csv_path: Path) -> list[dict[str, Any]]:
    """Read an entire CSV into records."""
    df = pd.read_csv(csv_path)
    return cast("list[dict[str, Any]]", df.to_dict(orient="records"))


class DataStore:
    """Manages hash-based directory structure for CSV data.

    Each uploaded CSV is hashed, and all related artifacts (cleaned data,
    downloaded attachments, generated schemas) are stored in a directory
    named after the hash: app/data/<hash>/
    """

    def __init__(self, data_dir: Path | None = None):
        """Initialize the data store.

        Args:
            data_dir: Base directory for hash folders (default: app/data/)
        """
        self.data_dir = data_dir or DATA_DIR

    @staticmethod
    def hash_content(content: bytes) -> str:
        """Compute SHA256 hash of file content.

        Args:
            content: Raw bytes of the file

        Returns:
            Hex digest of SHA256 hash (64 characters)
        """
        return hashlib.sha256(content).hexdigest()

    def get_hash_dir(self, content_hash: str) -> Path:
        """Get the directory path for a given hash.

        Args:
            content_hash: SHA256 hash of CSV content

        Returns:
            Path to the hash directory
        """
        return self.data_dir / content_hash

    def ensure_hash_dirs(self, content_hash: str) -> dict[str, Path]:
        """Create hash directory and subdirectories if they don't exist.

        Creates the following structure:
        - app/data/<hash>/
        - app/data/<hash>/cleaned_data/
        - app/data/<hash>/downloads/
        - app/data/<hash>/schema/
        - app/data/<hash>/analyzed/

        Args:
            content_hash: SHA256 hash of CSV content

        Returns:
            Dictionary with paths to subdirectories:
            - 'root': app/data/<hash>/
            - 'cleaned_data': app/data/<hash>/cleaned_data/
            - 'downloads': app/data/<hash>/downloads/
            - 'schema': app/data/<hash>/schema/
            - 'analyzed': app/data/<hash>/analyzed/
        """
        hash_dir = self.get_hash_dir(content_hash)
        paths = {
            "root": hash_dir,
            "cleaned_data": hash_dir / "cleaned_data",
            "downloads": hash_dir / "downloads",
            "schema": hash_dir / "schema",
            "analyzed": hash_dir / "analyzed",
        }
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)
        return paths

    def get_analyzed_json(self, content_hash: str, filename: str) -> Path | None:
        """Find analysis JSON output if it exists.

        Args:
            content_hash: SHA256 hash of original CSV content
            filename: Expected JSON filename (e.g., analysis.json)

        Returns:
            Path to analysis JSON file, or None if not found
        """
        analyzed_path = self.get_hash_dir(content_hash) / "analyzed" / filename
        return analyzed_path if analyzed_path.exists() else None

    def get_analyzed_csv(self, content_hash: str, filename: str) -> Path | None:
        """Find analysis CSV output if it exists.

        Args:
            content_hash: SHA256 hash of original CSV content
            filename: Expected CSV filename (e.g., analysis.csv)

        Returns:
            Path to analysis CSV file, or None if not found
        """
        analyzed_path = self.get_hash_dir(content_hash) / "analyzed" / filename
        return analyzed_path if analyzed_path.exists() else None

    def get_cleaned_csv(self, content_hash: str) -> Path | None:
        """Find cleaned CSV if it exists.

        Args:
            content_hash: SHA256 hash of original CSV content

        Returns:
            Path to cleaned CSV file, or None if not found
        """
        cleaned_dir = self.get_hash_dir(content_hash) / "cleaned_data"
        if not cleaned_dir.exists():
            return None

        # Prefer the canonical cleaned artifact produced from the raw input.
        hash_dir = self.get_hash_dir(content_hash)
        raw_input_path = hash_dir / "input.csv"
        preferred_names = []
        if raw_input_path.exists():
            preferred_names.append(f"cleaned_{raw_input_path.name}")
        preferred_names.append("cleaned_input.csv")

        for filename in preferred_names:
            preferred_path = cleaned_dir / filename
            if preferred_path.exists():
                return preferred_path

        cleaned_files = sorted(cleaned_dir.glob("cleaned_*.csv"))
        if not cleaned_files:
            return None

        primary_files = [path for path in cleaned_files if not path.stem.endswith("missing_ids")]
        if len(primary_files) == 1:
            return primary_files[0]

        return cleaned_files[0]

    def get_schema(self, content_hash: str) -> Path | None:
        """Find schema.json if it exists.

        Args:
            content_hash: SHA256 hash of original CSV content

        Returns:
            Path to schema.json file, or None if not found
        """
        schema_path = self.get_hash_dir(content_hash) / "schema" / "schema.json"
        return schema_path if schema_path.exists() else None

    def hash_exists(self, content_hash: str) -> bool:
        """Check if a hash directory exists.

        Args:
            content_hash: SHA256 hash to check

        Returns:
            True if the hash directory exists
        """
        return self.get_hash_dir(content_hash).exists()
