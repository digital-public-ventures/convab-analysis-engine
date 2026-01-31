"""Tests for the parsed attachments CSV expectations.

This module tests DataProcessor's attachment parsing functionality using
local fixture files. The data is processed once at module scope and all
tests operate on the cached result.
"""

import asyncio
import csv
import json
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse

import pytest
from pytest import TempPathFactory

# Resolve paths relative to this test file
BASE_DIR = Path(__file__).resolve().parents[1]
FIXTURE_DIR = BASE_DIR / "tests/fixtures"
RESPONSES_PATH = FIXTURE_DIR / "regs_gov_comments/responses.csv"
ATTACHMENTS_DIR = FIXTURE_DIR / "regs_gov_attachments"
MANIFEST_PATH = ATTACHMENTS_DIR / "manifest.json"

# Number of rows to process
N_ROWS = 5


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def _read_csv_header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        return next(reader)


def _load_fixture_manifest() -> dict[str, Path]:
    """Load the manifest mapping URLs to local fixture files."""
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Fixture manifest not found: {MANIFEST_PATH}. Run scripts/download_regs_gov_attachments.py"
        )
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {url: ATTACHMENTS_DIR / filename for url, filename in data.items()}


def _create_fake_fetch(mapping: dict[str, Path]) -> Callable[[object, str], bytes]:
    """Create a fake fetch function that returns fixture file content."""

    def fake_fetch(self: object, url: str) -> bytes:
        if url not in mapping:
            raise KeyError(f"No fixture mapping for URL: {url}")
        return mapping[url].read_bytes()

    return fake_fetch


def _parse_attachment_urls(attachment_string: str) -> list[str]:
    """Parse comma-separated attachment URLs."""
    if not attachment_string or not attachment_string.strip():
        return []
    urls = [url.strip() for url in attachment_string.split(",")]
    return [url for url in urls if url]


def _attachment_prefixes(attachment_value: str) -> list[str]:
    """Extract filename prefixes for each attachment URL."""
    prefixes = []
    for url in _parse_attachment_urls(attachment_value):
        filename = Path(urlparse(url).path).name
        prefixes.append(f"{Path(filename).stem}: ")
    return prefixes


def _has_non_empty_prefixed_line(text: str, prefix: str) -> bool:
    """Check if text contains a line starting with prefix followed by content."""
    for line in text.splitlines():
        if line.startswith(prefix) and len(line) > len(prefix):
            return True
    return False


class ProcessedData:
    """Container for processed test data."""

    def __init__(
        self,
        parsed_attachments_path: Path,
        attachments_path: Path,
        responses_with_attachments_path: Path,
        source_rows: list[dict[str, str]],
    ):
        self.parsed_attachments_path = parsed_attachments_path
        self.attachments_path = attachments_path
        self.responses_with_attachments_path = responses_with_attachments_path
        self.source_rows = source_rows


@pytest.fixture(scope="module")
def processed_data(tmp_path_factory: TempPathFactory) -> ProcessedData:
    """Process data once and return paths to all generated files.

    This fixture:
    1. Mocks network requests to use local fixture files
    2. Processes N_ROWS from the fixture responses.csv
    3. Generates parsed_attachments.csv, attachments.csv, and responses_with_attachments.csv
    4. Returns paths to all generated files for use by tests
    """
    # Import here to avoid import issues
    import sys

    sys.path.insert(0, str(BASE_DIR))

    from regs_dot_gov_exploration.attachment_processor import AttachmentProcessor
    from regs_dot_gov_exploration.data_processor import DataProcessor

    # Load fixture manifest and validate files exist
    mapping = _load_fixture_manifest()
    missing = [url for url, path in mapping.items() if not path.exists()]
    if missing:
        pytest.fail(
            "Missing fixture files for URLs: " + ", ".join(missing) + ". Run scripts/download_regs_gov_attachments.py"
        )

    # Create output directory
    output_dir = tmp_path_factory.mktemp("parsed_attachments")
    parsed_attachments_path = output_dir / "parsed_attachments.csv"
    attachments_path = output_dir / "attachments.csv"
    responses_with_attachments_path = output_dir / "responses_with_attachments.csv"

    with patch.object(AttachmentProcessor, "_fetch_url", new=_create_fake_fetch(mapping)):
        # Create processor with fixture data
        processor = DataProcessor(csv_path=str(RESPONSES_PATH))

        # Run async export methods synchronously
        loop = asyncio.new_event_loop()
        try:
            # Export parsed attachments
            loop.run_until_complete(
                processor.export_parsed_attachments_csv_async(
                    output_path=str(parsed_attachments_path),
                    n_rows=N_ROWS,
                    download_attachments=True,
                    use_ocr=True,
                )
            )

            # Export attachments
            loop.run_until_complete(
                processor.export_attachments_csv_async(
                    output_path=str(attachments_path),
                    n_rows=N_ROWS,
                    download_attachments=True,
                    use_ocr=True,
                )
            )
        finally:
            loop.close()

        # Export responses with attachments (sync method)
        processor.export_responses_with_attachments_csv(
            output_path=str(responses_with_attachments_path),
            parsed_attachments_path=str(parsed_attachments_path),
            n_rows=N_ROWS,
        )

        # Load source rows for comparison
        source_rows = _read_csv_rows(RESPONSES_PATH)[:N_ROWS]

        return ProcessedData(
            parsed_attachments_path=parsed_attachments_path,
            attachments_path=attachments_path,
            responses_with_attachments_path=responses_with_attachments_path,
            source_rows=source_rows,
        )


@pytest.mark.slow
class TestParsedAttachmentsExpectations:
    """Expectation tests for parsed_attachments.csv."""

    def test_parsed_attachments_file_exists(self, processed_data: ProcessedData) -> None:
        """Parsed attachments CSV should exist at the expected path."""
        assert (
            processed_data.parsed_attachments_path.exists()
        ), f"parsed_attachments.csv is missing. Expected at {processed_data.parsed_attachments_path.as_posix()}"

    def test_parsed_attachments_columns_and_row_count(self, processed_data: ProcessedData) -> None:
        """Parsed attachments CSV should have required columns and row count."""
        header = _read_csv_header(processed_data.parsed_attachments_path)
        assert header[0] == "document_id"
        assert "content_text" in header
        assert "attachment_text" in header

        parsed_rows = _read_csv_rows(processed_data.parsed_attachments_path)
        assert len(parsed_rows) == len(processed_data.source_rows)

    def test_parsed_attachments_document_order(self, processed_data: ProcessedData) -> None:
        """Parsed attachments should preserve document ordering from responses.csv."""
        parsed_rows = _read_csv_rows(processed_data.parsed_attachments_path)

        parsed_doc_ids = [row.get("document_id") for row in parsed_rows]
        response_doc_ids = [row.get("Document ID") for row in processed_data.source_rows]
        assert parsed_doc_ids == response_doc_ids

    @pytest.mark.parametrize(
        "doc_id",
        [
            "CFPB-2023-0038-0002",
            "CFPB-2023-0038-0005",
            "CFPB-2023-0038-0010",
        ],
    )
    def test_attachment_text_prefixes(self, doc_id: str, processed_data: ProcessedData) -> None:
        """Attachment text should include filename prefixes for each attachment URL."""
        parsed_rows = _read_csv_rows(processed_data.parsed_attachments_path)

        parsed_by_id = {row.get("document_id"): row for row in parsed_rows}
        response_by_id = {row.get("Document ID"): row for row in processed_data.source_rows}

        # Skip if doc_id not in processed data
        if doc_id not in parsed_by_id:
            pytest.skip(f"{doc_id} not in processed data")

        parsed_row = parsed_by_id[doc_id]
        response_row = response_by_id[doc_id]
        attachment_text = parsed_row.get("attachment_text") or ""

        prefixes = _attachment_prefixes(response_row.get("Attachment Files", ""))
        assert prefixes, f"Expected attachments for {doc_id}"

        for prefix in prefixes:
            assert prefix in attachment_text, f"Expected attachment text for {doc_id} to include prefix '{prefix}'"
            assert _has_non_empty_prefixed_line(
                attachment_text, prefix
            ), f"Expected attachment text for {doc_id} to include extracted text after '{prefix}'"


@pytest.mark.slow
class TestAttachmentsCsv:
    """Expectation tests for attachments.csv."""

    def test_attachments_csv_exists(self, processed_data: ProcessedData) -> None:
        """Attachments CSV should exist at the expected path."""
        assert (
            processed_data.attachments_path.exists()
        ), f"attachments.csv is missing. Expected at {processed_data.attachments_path.as_posix()}"

    def test_attachments_csv_columns(self, processed_data: ProcessedData) -> None:
        """Attachments CSV should have url and extracted_text columns."""
        header = _read_csv_header(processed_data.attachments_path)
        assert header == ["url", "extracted_text"]

    def test_attachments_csv_rows_match_attachment_urls(self, processed_data: ProcessedData) -> None:
        """Attachments CSV should have one row per attachment URL."""
        attachment_rows = _read_csv_rows(processed_data.attachments_path)

        expected_urls = []
        for row in processed_data.source_rows:
            expected_urls.extend(_parse_attachment_urls(row.get("Attachment Files", "")))

        attachment_urls = [row.get("url") for row in attachment_rows]
        assert attachment_urls == expected_urls
        assert all((row.get("extracted_text") or "").strip() for row in attachment_rows)

    def test_fixture_manifest_covers_all_attachment_urls(self) -> None:
        """Fixture manifest should cover every Attachment Files URL in first N_ROWS."""
        source_rows = _read_csv_rows(RESPONSES_PATH)[:N_ROWS]
        expected_urls = []
        for row in source_rows:
            expected_urls.extend(_parse_attachment_urls(row.get("Attachment Files", "")))

        mapping = _load_fixture_manifest()
        missing = [url for url in expected_urls if url not in mapping]
        assert not missing, f"Fixture manifest missing URLs: {missing}. Run scripts/download_regs_gov_attachments.py"


@pytest.mark.slow
class TestResponsesWithAttachmentsCsv:
    """Expectation tests for responses_with_attachments.csv."""

    def test_responses_with_attachments_file_exists(self, processed_data: ProcessedData) -> None:
        """Responses with attachments CSV should exist at the expected path."""
        assert processed_data.responses_with_attachments_path.exists(), (
            f"responses_with_attachments.csv is missing. "
            f"Expected at {processed_data.responses_with_attachments_path.as_posix()}"
        )

    def test_responses_with_attachments_header_matches_source(
        self,
        processed_data: ProcessedData,
    ) -> None:
        """Responses with attachments CSV should preserve source headers."""
        source_header = _read_csv_header(RESPONSES_PATH)
        merged_header = _read_csv_header(processed_data.responses_with_attachments_path)
        assert merged_header == source_header

    @pytest.mark.parametrize(
        "doc_id",
        [
            "CFPB-2023-0038-0002",
            "CFPB-2023-0038-0005",
            "CFPB-2023-0038-0010",
        ],
    )
    def test_responses_with_attachments_includes_attachment_text(
        self,
        doc_id: str,
        processed_data: ProcessedData,
    ) -> None:
        """Merged responses should include parsed attachment text in Comment."""
        merged_rows = _read_csv_rows(processed_data.responses_with_attachments_path)
        parsed_rows = _read_csv_rows(processed_data.parsed_attachments_path)

        merged_by_id = {row.get("Document ID"): row for row in merged_rows}
        parsed_by_id = {row.get("document_id"): row for row in parsed_rows}

        # Skip if doc_id not in processed data
        if doc_id not in merged_by_id:
            pytest.skip(f"{doc_id} not in processed data")

        source_by_id = {row.get("Document ID"): row for row in processed_data.source_rows}

        attachment_text = (parsed_by_id[doc_id].get("attachment_text") or "").strip()
        assert attachment_text, f"Expected attachment text for {doc_id}"

        merged_comment = (merged_by_id[doc_id].get("Comment") or "").strip()
        source_comment = (source_by_id[doc_id].get("Comment") or "").strip()

        if source_comment:
            assert source_comment in merged_comment
        assert attachment_text in merged_comment
