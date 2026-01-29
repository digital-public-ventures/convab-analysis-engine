"""Data processing utilities for regulations.gov response data.

This module handles the schema-specific parsing for regulations.gov public comments,
normalizing the data to a common format for analysis.
"""

import csv
import json
import os
import uuid
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

# Safety limit for development
MAX_ROWS_SAFETY_LIMIT = 50


class ResponseRecord:
    """Normalized representation of a regulations.gov public comment."""

    def __init__(
        self,
        id: str,
        narrative: str,
        metadata: dict,
        attachment_urls: list[str],
    ):
        """Initialize a response record.

        Args:
            id: Unique identifier for the record
            narrative: The free-text comment content
            metadata: Additional fields from the source data
            attachment_urls: List of URLs to attached documents
        """
        self.id = id
        self.narrative = narrative
        self.metadata = metadata
        self.attachment_urls = attachment_urls

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "narrative": self.narrative,
            "metadata": self.metadata,
            "attachment_urls": self.attachment_urls,
        }


class DataProcessor:
    """Handles loading and processing of regulations.gov response data.

    This processor is specific to the responses.csv schema from regulations.gov,
    which includes fields like Document ID, Comment, Attachment Files, etc.
    """

    # Column mappings for the responses.csv schema
    ID_COLUMN = "Document ID"
    NARRATIVE_COLUMN = "Comment"
    ATTACHMENT_COLUMN = "Attachment Files"

    # Metadata columns to extract
    METADATA_COLUMNS = [
        "Agency ID",
        "Docket ID",
        "Tracking Number",
        "Document Type",
        "Posted Date",
        "Received Date",
        "Title",
        "First Name",
        "Last Name",
        "City",
        "State/Province",
        "Zip/Postal Code",
        "Country",
        "Organization Name",
        "Category",
    ]

    def __init__(self, csv_path: str | None = None):
        """Initialize the data processor.

        Args:
            csv_path: Path to the CSV file. If None, uses default based on USE_HEAD env var.
        """
        if csv_path is None:
            csv_path = self._get_default_csv_path()

        self.csv_path = Path(csv_path)
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

    def _get_default_csv_path(self) -> str:
        """Get the default CSV path based on USE_HEAD environment variable."""
        use_head = os.getenv("USE_HEAD", "true").lower() in ("true", "1", "yes")
        base_dir = Path(__file__).parent / "data"
        head_path = base_dir / "head" / "responses.csv"
        full_path = base_dir / "responses.csv"

        if use_head:
            if head_path.exists():
                return str(head_path)
            print(
                "Warning: USE_HEAD is true but head sample not found. Falling back to full dataset."
            )

        return str(full_path)

    def _parse_attachment_urls(self, attachment_string: str) -> list[str]:
        """Parse comma-separated attachment URLs.

        Args:
            attachment_string: Comma-separated string of URLs

        Returns:
            List of individual URLs
        """
        if not attachment_string or not attachment_string.strip():
            return []

        # Split by comma and clean up each URL
        urls = [url.strip() for url in attachment_string.split(",")]
        return [url for url in urls if url]

    def _extract_metadata(self, row: dict) -> dict:
        """Extract metadata fields from a row.

        Args:
            row: CSV row as dictionary

        Returns:
            Dictionary of metadata fields (non-empty values only)
        """
        metadata = {}
        for col in self.METADATA_COLUMNS:
            value = row.get(col, "").strip()
            if value:
                metadata[col] = value
        return metadata

    def _generate_id(self) -> str:
        """Generate a unique ID if one is not provided."""
        return f"generated-{uuid.uuid4().hex[:12]}"

    def load_records(self, n_rows: int | Literal["all"] = "all") -> list[ResponseRecord]:
        """Load records from CSV and normalize to ResponseRecord format.

        Args:
            n_rows: Number of rows to load, or "all" for all rows
                   (capped at MAX_ROWS_SAFETY_LIMIT for safety)

        Returns:
            List of normalized ResponseRecord objects
        """
        # Apply safety limit
        if n_rows == "all":
            effective_limit = MAX_ROWS_SAFETY_LIMIT
            print(f"Loading up to {MAX_ROWS_SAFETY_LIMIT} rows (safety limit)")
        elif n_rows > MAX_ROWS_SAFETY_LIMIT:
            effective_limit = MAX_ROWS_SAFETY_LIMIT
            print(f"Row limit capped at {MAX_ROWS_SAFETY_LIMIT} rows for safety")
        else:
            effective_limit = n_rows

        records = []

        with open(self.csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for i, row in enumerate(reader):
                if i >= effective_limit:
                    break

                # Skip non-public submissions (e.g., the original Notice document)
                doc_type = row.get("Document Type", "").strip()
                if doc_type != "Public Submission":
                    continue

                # Extract ID (generate if missing)
                record_id = row.get(self.ID_COLUMN, "").strip()
                if not record_id:
                    record_id = self._generate_id()

                # Extract narrative (comment text)
                narrative = row.get(self.NARRATIVE_COLUMN, "").strip()

                # Extract attachment URLs
                attachment_string = row.get(self.ATTACHMENT_COLUMN, "")
                attachment_urls = self._parse_attachment_urls(attachment_string)

                # Extract metadata
                metadata = self._extract_metadata(row)

                # Create normalized record
                record = ResponseRecord(
                    id=record_id,
                    narrative=narrative,
                    metadata=metadata,
                    attachment_urls=attachment_urls,
                )
                records.append(record)

        print(f"Loaded {len(records)} records from {self.csv_path.name}")
        return records

    def load_sample(self, n_rows: int = 5) -> list[dict]:
        """Load a sample of records as dictionaries (for schema generation).

        Args:
            n_rows: Number of rows to sample

        Returns:
            List of records as dictionaries
        """
        records = self.load_records(n_rows=n_rows)
        return [r.to_dict() for r in records]

    def convert_to_json(self, records: list[ResponseRecord]) -> str:
        """Convert records to formatted JSON string.

        Args:
            records: List of ResponseRecord objects

        Returns:
            JSON string representation
        """
        return json.dumps([r.to_dict() for r in records], indent=2)

    def save_json(self, records: list[ResponseRecord], output_path: str) -> None:
        """Save records to a JSON file.

        Args:
            records: List of ResponseRecord objects
            output_path: Path to save JSON file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in records], f, indent=2)

        print(f"Saved {len(records)} records to {output_path}")

    def get_records_with_attachments(
        self, n_rows: int | Literal["all"] = "all"
    ) -> list[ResponseRecord]:
        """Load only records that have attachments.

        Args:
            n_rows: Maximum number of rows to scan

        Returns:
            List of ResponseRecord objects that have attachment URLs
        """
        all_records = self.load_records(n_rows=n_rows)
        return [r for r in all_records if r.attachment_urls]

    def get_narrative_only_records(
        self, n_rows: int | Literal["all"] = "all"
    ) -> list[ResponseRecord]:
        """Load only records that have inline comments (no attachments).

        Args:
            n_rows: Maximum number of rows to scan

        Returns:
            List of ResponseRecord objects that have narrative text but no attachments
        """
        all_records = self.load_records(n_rows=n_rows)
        return [r for r in all_records if r.narrative and not r.attachment_urls]
