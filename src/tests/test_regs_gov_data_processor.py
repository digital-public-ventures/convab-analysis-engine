"""Tests for the regulations.gov data processor module."""

import csv
import os
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from regs_dot_gov_exploration.data_processor import DataProcessor, ResponseRecord  # noqa: E402
from utilities.attachment_parser import parse_attachment_urls  # noqa: E402


@pytest.fixture
def sample_csv(tmp_path):
    """Create a sample CSV file for testing."""
    csv_path = tmp_path / "test_responses.csv"
    rows = [
        {
            "Document ID": "TEST-001",
            "Agency ID": "CFPB",
            "Docket ID": "CFPB-2023-0038",
            "Document Type": "Public Submission",
            "Comment": "This is a test comment.",
            "Attachment Files": "https://example.com/doc1.pdf,https://example.com/doc2.pdf",
            "First Name": "John",
            "Last Name": "Doe",
            "Posted Date": "2023-09-19T04:00Z",
        },
        {
            "Document ID": "TEST-002",
            "Agency ID": "CFPB",
            "Docket ID": "CFPB-2023-0038",
            "Document Type": "Public Submission",
            "Comment": "Another test comment with no attachments.",
            "Attachment Files": "",
            "First Name": "Jane",
            "Last Name": "Smith",
            "Posted Date": "2023-09-20T04:00Z",
        },
        {
            "Document ID": "TEST-003",
            "Agency ID": "CFPB",
            "Docket ID": "CFPB-2023-0038",
            "Document Type": "Notice",  # Should be filtered out
            "Comment": "This is a notice, not a public submission.",
            "Attachment Files": "",
            "First Name": "",
            "Last Name": "",
            "Posted Date": "2023-09-18T04:00Z",
        },
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "Document ID",
            "Agency ID",
            "Docket ID",
            "Document Type",
            "Comment",
            "Attachment Files",
            "First Name",
            "Last Name",
            "Posted Date",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return csv_path


class TestResponseRecord:
    """Tests for the ResponseRecord class."""

    def test_initialization(self):
        """Test basic ResponseRecord creation."""
        record = ResponseRecord(
            id="test-123",
            narrative="Test narrative",
            metadata={"key": "value"},
            attachment_urls=["https://example.com/doc.pdf"],
        )
        assert record.id == "test-123"
        assert record.narrative == "Test narrative"
        assert record.metadata == {"key": "value"}
        assert record.attachment_urls == ["https://example.com/doc.pdf"]

    def test_to_dict(self):
        """Test converting ResponseRecord to dictionary."""
        record = ResponseRecord(
            id="test-456",
            narrative="Another narrative",
            metadata={"field": "data"},
            attachment_urls=[],
        )
        result = record.to_dict()
        assert result["id"] == "test-456"
        assert result["narrative"] == "Another narrative"
        assert result["metadata"] == {"field": "data"}
        assert result["attachment_urls"] == []


class TestDataProcessor:
    """Tests for the DataProcessor class."""

    def test_load_records_basic(self, sample_csv):
        """Test loading records from CSV."""
        processor = DataProcessor(csv_path=str(sample_csv))
        records = processor.load_records(n_rows=10)

        # Should only get 2 records (the Notice type is filtered out)
        assert len(records) == 2

    def test_load_records_filters_non_public_submissions(self, sample_csv):
        """Test that non-public submissions are filtered out."""
        processor = DataProcessor(csv_path=str(sample_csv))
        records = processor.load_records(n_rows=10)

        for record in records:
            # None should have 'Notice' document type
            assert "Notice" not in record.metadata.get("Document Type", "")

    def test_parse_attachment_urls(self, sample_csv):
        """Test attachment URL parsing."""
        processor = DataProcessor(csv_path=str(sample_csv))
        records = processor.load_records(n_rows=10)

        # First record should have 2 attachments
        record_with_attachments = next(r for r in records if r.id == "TEST-001")
        assert len(record_with_attachments.attachment_urls) == 2
        assert "https://example.com/doc1.pdf" in record_with_attachments.attachment_urls

        # Second record should have no attachments
        record_without = next(r for r in records if r.id == "TEST-002")
        assert len(record_without.attachment_urls) == 0

    def test_parse_attachment_urls_utility(self):
        """Test attachment URL parsing utility."""
        result = parse_attachment_urls("a.pdf, b.pdf,  ,c.pdf")
        assert result == ["a.pdf", "b.pdf", "c.pdf"]

    def test_metadata_extraction(self, sample_csv):
        """Test metadata field extraction."""
        processor = DataProcessor(csv_path=str(sample_csv))
        records = processor.load_records(n_rows=10)

        record = next(r for r in records if r.id == "TEST-001")
        assert record.metadata["First Name"] == "John"
        assert record.metadata["Last Name"] == "Doe"
        assert record.metadata["Agency ID"] == "CFPB"

    def test_narrative_extraction(self, sample_csv):
        """Test narrative (comment) extraction."""
        processor = DataProcessor(csv_path=str(sample_csv))
        records = processor.load_records(n_rows=10)

        record = next(r for r in records if r.id == "TEST-001")
        assert record.narrative == "This is a test comment."

    def test_row_limit(self, sample_csv):
        """Test that row limit is respected."""
        processor = DataProcessor(csv_path=str(sample_csv))
        records = processor.load_records(n_rows=1)

        assert len(records) == 1

    def test_convert_to_json(self, sample_csv):
        """Test JSON conversion."""
        processor = DataProcessor(csv_path=str(sample_csv))
        records = processor.load_records(n_rows=10)

        json_str = processor.convert_to_json(records)
        assert '"id":' in json_str
        assert '"narrative":' in json_str

    def test_export_parsed_csv(self, sample_csv, tmp_path):
        """Test exporting parsed CSV output."""
        output_path = tmp_path / "parsed.csv"
        processor = DataProcessor(csv_path=str(sample_csv))
        processor.export_parsed_csv(output_path=str(output_path), n_rows=10)

        content = output_path.read_text(encoding="utf-8")
        assert "id" in content
        assert "metadata_json" in content

    def test_save_json(self, sample_csv, tmp_path):
        """Test saving records to JSON file."""
        output_path = tmp_path / "output.json"
        processor = DataProcessor(csv_path=str(sample_csv))
        records = processor.load_records(n_rows=10)
        processor.save_json(records, str(output_path))

        assert output_path.exists()
        import json

        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 2
        assert data[0]["id"] == "TEST-001"

    def test_get_records_with_attachments(self, sample_csv):
        """Test filtering records that have attachments."""
        processor = DataProcessor(csv_path=str(sample_csv))
        records = processor.get_records_with_attachments(n_rows=10)

        assert len(records) == 1
        assert records[0].id == "TEST-001"
        assert len(records[0].attachment_urls) == 2

    def test_get_narrative_only_records(self, sample_csv):
        """Test filtering records with narrative but no attachments."""
        processor = DataProcessor(csv_path=str(sample_csv))
        records = processor.get_narrative_only_records(n_rows=10)

        assert len(records) == 1
        assert records[0].id == "TEST-002"
        assert records[0].narrative == "Another test comment with no attachments."
        assert len(records[0].attachment_urls) == 0

    def test_generate_id_format(self, sample_csv):
        """Test that generated IDs have expected format."""
        processor = DataProcessor(csv_path=str(sample_csv))
        generated_id = processor._generate_id()

        assert generated_id.startswith("generated-")
        assert len(generated_id) == len("generated-") + 12

    def test_file_not_found_raises_error(self, tmp_path):
        """Test that missing CSV file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            DataProcessor(csv_path=str(tmp_path / "nonexistent.csv"))


class TestDataProcessorWithSampleData:
    """Tests using the actual sample data from the module."""

    @pytest.fixture
    def head_processor(self):
        """Create a processor using the head sample data."""
        # Set USE_HEAD to use sample data
        old_env = os.environ.get("USE_HEAD")
        os.environ["USE_HEAD"] = "true"
        processor = DataProcessor()
        if old_env is None:
            del os.environ["USE_HEAD"]
        else:
            os.environ["USE_HEAD"] = old_env
        return processor

    def test_sample_data_loads(self, head_processor):
        """Test that the sample data file loads correctly."""
        records = head_processor.load_records(n_rows=3)
        assert len(records) > 0

    def test_sample_data_has_attachments(self, head_processor):
        """Test that sample data records have attachment URLs."""
        records = head_processor.load_records(n_rows=3)
        # At least some records should have attachments
        records_with_attachments = [r for r in records if r.attachment_urls]
        assert len(records_with_attachments) > 0

    def test_attachment_urls_are_valid_format(self, head_processor):
        """Test that attachment URLs have expected format."""
        records = head_processor.load_records(n_rows=5)
        for record in records:
            for url in record.attachment_urls:
                assert url.startswith("https://downloads.regulations.gov/")


@pytest.mark.unit
class TestParseAttachmentUrlsEdgeCases:
    """Edge case tests for the parse_attachment_urls utility."""

    def test_single_url(self):
        """Test parsing a single URL."""
        result = parse_attachment_urls("https://example.com/doc.pdf")
        assert result == ["https://example.com/doc.pdf"]

    def test_empty_string(self):
        """Test parsing an empty string."""
        result = parse_attachment_urls("")
        assert result == []

    def test_whitespace_only(self):
        """Test parsing whitespace-only string."""
        result = parse_attachment_urls("   ")
        assert result == []

    def test_multiple_commas_no_content(self):
        """Test parsing string with only commas."""
        result = parse_attachment_urls(",,,")
        assert result == []

    def test_urls_with_leading_trailing_whitespace(self):
        """Test that whitespace is trimmed from URLs."""
        result = parse_attachment_urls("  a.pdf  ,  b.pdf  ")
        assert result == ["a.pdf", "b.pdf"]

    def test_preserves_url_order(self):
        """Test that URL order is preserved."""
        result = parse_attachment_urls("c.pdf,a.pdf,b.pdf")
        assert result == ["c.pdf", "a.pdf", "b.pdf"]

    def test_handles_tabs_and_newlines(self):
        """Test handling of various whitespace characters."""
        result = parse_attachment_urls("a.pdf,\tb.pdf,\nc.pdf")
        assert result == ["a.pdf", "b.pdf", "c.pdf"]


@pytest.mark.unit
class TestAsyncExportMethodsMocked:
    """Mock-based tests for async export methods (fast, no real I/O)."""

    @pytest.fixture
    def sample_csv_with_attachments(self, tmp_path):
        """Create a minimal CSV with attachment URLs for testing."""
        csv_path = tmp_path / "test.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["Document ID", "Document Type", "Comment", "Attachment Files"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Document ID": "TEST-001",
                    "Document Type": "Public Submission",
                    "Comment": "Test comment",
                    "Attachment Files": "https://example.com/doc.pdf",
                }
            )
        return csv_path

    @pytest.mark.asyncio
    async def test_export_parsed_attachments_csv_async_without_download(
        self,
        sample_csv_with_attachments,
        tmp_path,
    ):
        """Test async export with download_attachments=False (no network calls)."""
        output_path = tmp_path / "output.csv"
        processor = DataProcessor(csv_path=str(sample_csv_with_attachments))

        await processor.export_parsed_attachments_csv_async(
            output_path=str(output_path),
            n_rows=1,
            download_attachments=False,
        )

        assert output_path.exists()
        with open(output_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["document_id"] == "TEST-001"

    @pytest.mark.asyncio
    async def test_export_attachments_csv_async_without_download(
        self,
        sample_csv_with_attachments,
        tmp_path,
    ):
        """Test per-attachment export with download_attachments=False."""
        output_path = tmp_path / "attachments.csv"
        processor = DataProcessor(csv_path=str(sample_csv_with_attachments))

        await processor.export_attachments_csv_async(
            output_path=str(output_path),
            n_rows=1,
            download_attachments=False,
        )

        assert output_path.exists()
        with open(output_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["url"] == "https://example.com/doc.pdf"
        assert rows[0]["extracted_text"] == ""

    def test_export_responses_with_attachments_csv(self, sample_csv_with_attachments, tmp_path):
        """Test merging attachment text into responses."""
        # First create a parsed attachments file
        parsed_path = tmp_path / "parsed.csv"
        with open(parsed_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["document_id", "content_text", "attachment_text"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "document_id": "TEST-001",
                    "content_text": "Test comment",
                    "attachment_text": "doc: Extracted PDF content",
                }
            )

        output_path = tmp_path / "merged.csv"
        processor = DataProcessor(csv_path=str(sample_csv_with_attachments))
        processor.export_responses_with_attachments_csv(
            output_path=str(output_path),
            parsed_attachments_path=str(parsed_path),
            n_rows=1,
        )

        assert output_path.exists()
        with open(output_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert "Test comment" in rows[0]["Comment"]
        assert "Extracted PDF content" in rows[0]["Comment"]
