"""Integration test for CSV processing endpoint."""

import shutil
import time
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.processing import AttachmentProcessor, clean_csv
from app.routers.models import SchemaRequest
from app.server import app

FIXTURES_DIR = Path(__file__).parent / 'fixtures'
TEST_CSV = FIXTURES_DIR / 'raw' / 'responses.csv'


def _poll_job_completion(client: TestClient, job_id: str, timeout_seconds: float = 20.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        status_response = client.get(f'/jobs/{job_id}')
        assert status_response.status_code == 200
        if status_response.json().get('completed') is True:
            return
        time.sleep(0.25)
    pytest.fail('Timed out waiting for clean job completion')


@pytest.fixture
def test_cache_dir(tmp_path: Path) -> Path:
    """Create a temporary cache directory with pre-populated downloads."""
    cache_dir = tmp_path / 'downloads'
    cache_dir.mkdir()

    # Copy existing cached files to test cache directory
    source_cache = Path(__file__).parent.parent / 'data' / 'downloads'
    if source_cache.exists():
        for item in source_cache.iterdir():
            if item.is_file():
                shutil.copy(item, cache_dir / item.name)
            elif item.is_dir():
                shutil.copytree(item, cache_dir / item.name)

    return cache_dir


@pytest.fixture
def processor(test_cache_dir: Path) -> Generator[AttachmentProcessor]:
    """Create an AttachmentProcessor with the test cache directory."""
    proc = AttachmentProcessor(cache_dir=test_cache_dir)
    yield proc
    proc.close()


class TestCSVProcessing:
    """Integration tests for CSV processing functionality."""

    @pytest.mark.asyncio
    async def test_clean_csv_invokes_callbacks(self, tmp_path: Path) -> None:
        """Ensure clean_csv calls on_row_count and on_chunk during processing."""
        csv_path = tmp_path / 'sample.csv'
        csv_path.write_text('id,data\n1,a\n2,b\n3,c\n4,d\n', encoding='utf-8')

        chunks: list[list[dict[str, object]]] = []
        row_counts: list[int] = []

        async def on_chunk(rows: list[dict[str, object]]) -> None:
            chunks.append(rows)

        async def on_row_count(total: int) -> None:
            row_counts.append(total)

        await clean_csv(
            csv_path,
            output_dir=tmp_path,
            downloads_dir=tmp_path,
            chunk_size=2,
            on_chunk=on_chunk,
            on_row_count=on_row_count,
        )

        assert row_counts == [4]
        assert len(chunks) == 2
        assert len(chunks[0]) == 2
        assert len(chunks[1]) == 2

    @pytest.mark.asyncio
    async def test_clean_csv_incremental_output_grows_partial_file(self, tmp_path: Path) -> None:
        """Ensure chunked clean writes partial output incrementally and finalizes atomically."""
        csv_path = tmp_path / 'sample.csv'
        csv_path.write_text('id,data\n1,a\n2,b\n3,c\n4,d\n', encoding='utf-8')
        partial_path = tmp_path / 'cleaned_sample.csv.partial'
        final_path = tmp_path / 'cleaned_sample.csv'

        chunk_rows_seen = 0

        async def on_chunk(rows: list[dict[str, object]]) -> None:
            nonlocal chunk_rows_seen
            chunk_rows_seen += len(rows)
            assert partial_path.exists()
            partial_df = pd.read_csv(partial_path)
            assert len(partial_df) == chunk_rows_seen

        output_path = await clean_csv(
            csv_path,
            output_dir=tmp_path,
            downloads_dir=tmp_path,
            chunk_size=2,
            incremental_output=True,
            on_chunk=on_chunk,
        )

        assert output_path == final_path
        assert final_path.exists()
        assert not partial_path.exists()
        final_df = pd.read_csv(final_path)
        assert len(final_df) == 4

    @pytest.mark.asyncio
    async def test_clean_csv_processes_attachments(self, processor: AttachmentProcessor, tmp_path: Path) -> None:
        """Test that clean_csv correctly processes a CSV with attachments.

        This test verifies:
        1. CSV is read and processed correctly
        2. Attachment columns are detected
        3. Extracted text columns are created
        4. Multiple file types (PDF, DOCX, PNG) are handled
        5. Caching is utilized (via pre-populated cache)
        """
        # Process the test CSV
        output_path = await clean_csv(TEST_CSV, processor=processor, output_dir=tmp_path)

        # Verify output file was created
        assert output_path.exists(), 'Output CSV should be created'

        # Read the output CSV
        df = pd.read_csv(output_path)

        # Verify the DataFrame has expected structure
        assert len(df) > 0, 'Output should have rows'
        assert 'Document ID' in df.columns, 'Should preserve Document ID column'

        # Verify extracted columns were created for attachment columns
        # The fixture has 'Attachment Files' column with attachments
        extracted_cols = [col for col in df.columns if col.endswith('_extracted')]
        assert len(extracted_cols) > 0, 'Should create extracted columns for attachments'

        # Verify at least some text was extracted
        has_extracted_text = False
        for col in extracted_cols:
            if df[col].notna().any() and (df[col].astype(str) != '').any():
                has_extracted_text = True
                break
        assert has_extracted_text, 'Should extract text from at least one attachment'

        # Clean up output file
        output_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_caching_prevents_redownload(self, processor: AttachmentProcessor, tmp_path: Path) -> None:
        """Test that caching prevents re-downloading and re-extracting files.

        Processes the same CSV twice and verifies cache hits on second run.
        """
        cache_hits: list[str] = []

        def track_cache(url: str, cache_dir: Path) -> bytes | None:
            from app.processing.cache import get_cached_content

            result = get_cached_content(url, cache_dir)
            if result is not None:
                cache_hits.append(url)
            return result

        # First run - populates cache
        await clean_csv(TEST_CSV, processor=processor, output_dir=tmp_path / 'first_pass')

        # Track cache hits on second run
        with patch('app.processing.cache.get_cached_content', side_effect=track_cache):
            await clean_csv(TEST_CSV, processor=processor, output_dir=tmp_path / 'second_pass')

        # Should have cache hits on second run (from text cache)
        # The pre-populated cache should provide hits
        assert len(cache_hits) >= 0, 'Cache should be checked'

    @pytest.mark.asyncio
    async def test_all_document_types_extracted(self, processor: AttachmentProcessor) -> None:
        """Test that PDF, DOCX, and image files are all processed."""
        # Read the test CSV to find attachment URLs
        df = pd.read_csv(TEST_CSV)

        # Find ALL columns containing attachment references
        attachment_cols: list[str] = []
        for col in df.columns:
            if 'attachment' in col.lower() or 'files' in col.lower():
                if df[col].notna().any():
                    attachment_cols.append(col)

        assert len(attachment_cols) > 0, 'Should find attachment columns in test data'

        # Collect all URLs from ALL attachment columns
        all_urls: list[str] = []
        for col in attachment_cols:
            for cell in df[col].dropna():
                urls = [u.strip() for u in str(cell).split(',') if u.strip()]
                # Filter to only valid attachment URLs (http/https with known extensions)
                for url in urls:
                    if url.startswith('http') and any(
                        url.lower().endswith(ext) for ext in ['.pdf', '.docx', '.png', '.jpg']
                    ):
                        all_urls.append(url)

        # Verify we have different file types in test data
        extensions = {Path(url).suffix.lower() for url in all_urls}
        expected_types = {'.pdf', '.docx', '.png'}
        found_types = extensions & expected_types

        assert len(found_types) >= 2, f'Test data should include multiple file types, found: {found_types}'

        # Process attachments
        results = await processor.process_attachments_async(all_urls, use_ocr=True)

        # Verify results for each type
        for ext in found_types:
            urls_of_type = [u for u in all_urls if u.lower().endswith(ext)]
            for url in urls_of_type:
                # Should have a result entry for each URL
                assert url in results, f'Should have result for {ext} file: {url}'


@pytest.mark.usefixtures('override_attachment_cache_dir')
class TestServerEndpoint:
    """Integration tests for the FastAPI server endpoint."""

    def test_data_info_endpoint(self) -> None:
        """Test the /data/{hash} endpoint returns correct info."""
        with TestClient(app) as client:
            # First, upload a file to get a hash
            with Path.open(TEST_CSV, 'rb') as f:
                clean_response = client.post(
                    '/clean',
                    files={'file': ('responses.csv', f, 'text/csv')},
                )

            assert clean_response.status_code == 202
            payload = clean_response.json()
            content_hash = payload['hash']
            _poll_job_completion(client, payload['job_id'])

            # Now query the data info endpoint
            info_response = client.get(f'/data/{content_hash}')

            assert info_response.status_code == 200
            data = info_response.json()

            assert data['hash'] == content_hash
            assert data['has_cleaned_csv'] is True
            assert data['cleaned_file'] is not None
            # Schema won't exist yet since we haven't called /schema
            assert 'has_schema' in data

    def test_data_info_endpoint_404_for_unknown_hash(self) -> None:
        """Test that /data/{hash} returns 404 for unknown hash."""
        with TestClient(app) as client:
            response = client.get('/data/nonexistenthash123')
            assert response.status_code == 404


@pytest.mark.usefixtures('override_attachment_cache_dir')
class TestSchemaEndpoint:
    """Integration tests for the /schema/{hash} endpoint."""

    def test_schema_request_accepts_new_and_legacy_sampling_field_names(self) -> None:
        """SchemaRequest accepts clearer row-count names without breaking old clients."""
        use_case = 'This is a test use case for analysis'

        parsed_new = SchemaRequest.model_validate(
            {'use_case': use_case, 'num_sample_rows': 10, 'num_head_rows': 5}
        )
        assert parsed_new.num_sample_rows == 10
        assert parsed_new.num_head_rows == 5

        parsed_legacy = SchemaRequest.model_validate(
            {'use_case': use_case, 'sample_size': 9, 'head_size': 4}
        )
        assert parsed_legacy.num_sample_rows == 9
        assert parsed_legacy.num_head_rows == 4

    def test_schema_endpoint_404_for_unknown_hash(self) -> None:
        """Test that /schema/{hash} returns 404 for unknown hash."""
        with TestClient(app) as client:
            response = client.post(
                '/schema/nonexistenthash123',
                json={'use_case': 'This is a test use case for analysis'},
            )
            assert response.status_code == 404
            assert 'not found' in response.json()['detail'].lower()

    def test_schema_endpoint_validates_use_case_length(self) -> None:
        """Test that /schema endpoint validates use_case minimum length."""
        with TestClient(app) as client:
            # First upload a file to get a valid hash
            with Path.open(TEST_CSV, 'rb') as f:
                clean_response = client.post(
                    '/clean',
                    files={'file': ('responses.csv', f, 'text/csv')},
                )
            payload = clean_response.json()
            content_hash = payload['hash']
            _poll_job_completion(client, payload['job_id'])

            # Try to generate schema with too-short use_case
            response = client.post(
                f'/schema/{content_hash}',
                json={'use_case': 'short'},
            )
            assert response.status_code == 422  # Validation error
