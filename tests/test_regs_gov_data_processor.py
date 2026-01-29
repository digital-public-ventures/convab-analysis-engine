"""Tests for the regulations.gov data processor module."""

import csv
import os

import pytest

from src.regs_dot_gov_exploration.data_processor import DataProcessor, ResponseRecord


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
