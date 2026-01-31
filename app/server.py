"""FastAPI server for CSV cleaning and schema generation."""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, cast

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.analysis import AnalysisRequest, analyze_dataset
from app.config import (
    ANALYSIS_CSV_FILENAME,
    ANALYSIS_JSON_FILENAME,
    DOWNLOADS_DIR,
    LOG_DATE_FORMAT,
    LOG_FORMAT,
    SCHEMA_DEFAULT_HEAD_SIZE,
    SCHEMA_DEFAULT_SAMPLE_SIZE,
)
from app.processing import AttachmentProcessor, DataStore, clean_csv
from app.processing.job_store import JobStatus, JobStore
from app.schema import SchemaGenerator

load_dotenv()

logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)

# Shared processor with pre-warmed OCR
_processor: AttachmentProcessor | None = None
_data_store: DataStore = DataStore()
_job_store: JobStore = JobStore()


def get_processor() -> AttachmentProcessor:
    """Get the shared processor instance."""
    if _processor is None:
        raise RuntimeError("Processor not initialized")
    return _processor


# Pydantic models for request/response
class JobStartResponse(BaseModel):
    """Response model for async job creation."""

    job_id: str
    status: str
    job_type: str
    hash: str | None = None
    cached: bool = False
    poll_url: str
    results_url: str


class SchemaRequest(BaseModel):
    """Request model for /schema endpoint."""

    use_case: str = Field(..., min_length=10, description="Description of intended data analysis")
    sample_size: int = Field(default=SCHEMA_DEFAULT_SAMPLE_SIZE, ge=1, le=100)
    head_size: int = Field(default=SCHEMA_DEFAULT_HEAD_SIZE, ge=1, le=20)


class SchemaResponse(BaseModel):
    """Response model for /schema endpoint."""

    hash: str
    cached: bool = False
    schema_data: dict = Field(..., alias="schema")

    class Config:
        populate_by_name = True


class DataInfoResponse(BaseModel):
    """Response model for /data/{hash} endpoint."""

    hash: str
    has_cleaned_csv: bool
    cleaned_file: str | None = None
    has_schema: bool


class AnalyzeRequest(BaseModel):
    """Request model for /analyze endpoint."""

    hash: str = Field(..., min_length=10, description="Hash of the cleaned dataset")
    use_case: str = Field(..., min_length=10, description="Description of intended analysis")
    system_prompt: str = Field(..., min_length=10, description="System prompt for analysis")


class AnalyzeResponse(BaseModel):
    """Response model for /analyze endpoint."""

    hash: str
    cached: bool = False
    analysis_json: dict
    analysis_csv: str


class JobProgress(BaseModel):
    completed_rows: int
    total_rows: int | None


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    job_type: str
    completed: bool
    error: str | None
    progress: JobProgress
    hash: str | None = None


class JobResultsResponse(BaseModel):
    job_id: str
    rows: list[dict[str, Any]]
    next_cursor: str | None
    has_more: bool
    completed: bool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Pre-warm OCR engine on startup."""
    global _processor

    logger.info("Starting server, pre-warming OCR engine...")
    _processor = AttachmentProcessor(cache_dir=DOWNLOADS_DIR)
    # Force OCR engine initialization
    _processor._get_ocr_engine()
    logger.info("OCR engine ready")

    yield

    logger.info("Shutting down, closing processor...")
    _processor.close()
    _processor = None


app = FastAPI(title="CSV Cleaner & Schema Generator", lifespan=lifespan)


def _build_job_urls(job_id: str) -> tuple[str, str]:
    return (f"/jobs/{job_id}", f"/jobs/{job_id}/results")


def _parse_cursor(cursor: str | None) -> int:
    if cursor is None or cursor == "":
        return 0
    try:
        value = int(cursor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid cursor") from exc
    if value < 0:
        raise HTTPException(status_code=400, detail="Invalid cursor")
    return value


def _read_csv_rows(csv_path: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(csv_path)
    return cast("list[dict[str, Any]]", df.to_dict(orient="records"))


async def _run_clean_job(job_id: str, content: bytes, content_hash: str) -> None:
    _job_store.mark_running(job_id)
    paths = _data_store.ensure_hash_dirs(content_hash)

    async def _set_total_rows(total_rows: int) -> None:
        _job_store.set_total_rows(job_id, total_rows)

    async def _add_chunk(rows: list[dict[str, Any]]) -> None:
        _job_store.add_results(job_id, rows)

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        processor = AttachmentProcessor(cache_dir=paths["downloads"])
        processor._ocr_engine = get_processor()._ocr_engine

        cleaned_path = await clean_csv(
            tmp_path,
            processor=processor,
            output_dir=paths["cleaned_data"],
            downloads_dir=paths["downloads"],
            chunk_size=200,
            on_chunk=_add_chunk,
            on_row_count=_set_total_rows,
        )

        record = _job_store.get_job(job_id)
        if record and record.completed_rows == 0:
            rows = _read_csv_rows(cleaned_path)
            _job_store.add_results(job_id, rows)
            _job_store.set_total_rows(job_id, len(rows))
        _job_store.mark_completed(job_id)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Clean job failed: %s", exc)
        _job_store.mark_failed(job_id, str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)


async def _run_analyze_job(job_id: str, request: AnalyzeRequest) -> None:
    content_hash = request.hash
    _job_store.mark_running(job_id)

    async def _set_total_rows(total_rows: int) -> None:
        _job_store.set_total_rows(job_id, total_rows)

    async def _add_batch(rows: list[dict[str, Any]]) -> None:
        _job_store.add_results(job_id, rows)

    cleaned_csv = _data_store.get_cleaned_csv(content_hash)
    if not cleaned_csv:
        _job_store.mark_failed(job_id, "Cleaned CSV not found")
        return

    schema_path = _data_store.get_schema(content_hash)
    if not schema_path:
        _job_store.mark_failed(job_id, "Schema not found")
        return

    paths = _data_store.ensure_hash_dirs(content_hash)

    try:
        await analyze_dataset(
            AnalysisRequest(
                cleaned_csv=cleaned_csv,
                schema_path=schema_path,
                output_dir=paths["analyzed"],
                use_case=request.use_case,
                system_prompt=request.system_prompt,
            ),
            on_batch=_add_batch,
            on_row_count=_set_total_rows,
        )
        record = _job_store.get_job(job_id)
        if record and record.completed_rows == 0:
            analysis_csv = _data_store.get_analyzed_csv(content_hash, ANALYSIS_CSV_FILENAME)
            if analysis_csv is None:
                raise FileNotFoundError("analysis.csv not found")
            rows = _read_csv_rows(analysis_csv)
            _job_store.add_results(job_id, rows)
            _job_store.set_total_rows(job_id, len(rows))
        _job_store.mark_completed(job_id)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Analyze job failed: %s", exc)
        _job_store.mark_failed(job_id, str(exc))


@app.post("/clean", response_model=JobStartResponse, status_code=202)  # type: ignore[misc]
async def clean_csv_endpoint(
    file: UploadFile = File(...),
    no_cache: bool = Query(default=False),
) -> JobStartResponse:
    """Start a CSV cleaning job and return the job id immediately."""
    content = await file.read()
    content_hash = DataStore.hash_content(content)

    logger.debug("Received file: %s (hash: %s...)", file.filename, content_hash[:12])

    job = _job_store.create_job("clean", metadata={"hash": content_hash})
    poll_url, results_url = _build_job_urls(job.job_id)

    existing = _data_store.get_cleaned_csv(content_hash)
    if existing and not no_cache:
        logger.info("Cache hit for hash: %s...", content_hash[:12])
        rows = _read_csv_rows(existing)
        _job_store.add_results(job.job_id, rows)
        _job_store.set_total_rows(job.job_id, len(rows))
        _job_store.mark_completed(job.job_id)
        return JobStartResponse(
            job_id=job.job_id,
            status=job.status,
            job_type=job.job_type,
            hash=content_hash,
            cached=True,
            poll_url=poll_url,
            results_url=results_url,
        )

    asyncio.create_task(_run_clean_job(job.job_id, content, content_hash))

    return JobStartResponse(
        job_id=job.job_id,
        status=job.status,
        job_type=job.job_type,
        hash=content_hash,
        cached=False,
        poll_url=poll_url,
        results_url=results_url,
    )


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)  # type: ignore[misc]
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Get the current status of a background job."""
    record = _job_store.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=record.job_id,
        status=record.status,
        job_type=record.job_type,
        completed=record.status in (JobStatus.COMPLETED, JobStatus.FAILED),
        error=record.error,
        progress=JobProgress(
            completed_rows=record.completed_rows,
            total_rows=record.total_rows,
        ),
        hash=record.metadata.get("hash"),
    )


@app.get("/jobs/{job_id}/results", response_model=JobResultsResponse)  # type: ignore[misc]
async def get_job_results(
    job_id: str,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
) -> JobResultsResponse:
    """Return completed rows for a job since the provided cursor."""
    record = _job_store.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")

    cursor_value = _parse_cursor(cursor)
    results, has_more = _job_store.get_results_since(job_id, cursor_value, limit)
    rows = [row.payload for row in results]
    next_cursor = str(results[-1].sequence_id) if results else (str(cursor_value) if cursor_value else None)

    return JobResultsResponse(
        job_id=record.job_id,
        rows=rows,
        next_cursor=next_cursor,
        has_more=has_more,
        completed=record.status in (JobStatus.COMPLETED, JobStatus.FAILED),
    )


@app.post("/schema/{hash}", response_model=SchemaResponse)  # type: ignore[misc]
async def generate_schema_endpoint(
    hash: str,
    request: SchemaRequest,
) -> SchemaResponse:
    """Generate a tagging schema for a previously cleaned CSV.

    1. Verify hash directory and cleaned CSV exist
    2. Check if schema already exists
    3. If cached, return it; otherwise generate and cache
    4. Sample head + N random rows from cleaned CSV
    5. Call SchemaGenerator with sample data
    """
    # Validate hash exists
    if not _data_store.hash_exists(hash):
        raise HTTPException(
            status_code=404,
            detail=f"Dataset with hash '{hash[:12]}...' not found. Run /clean first.",
        )

    # Check for existing schema
    existing_schema = _data_store.get_schema(hash)
    if existing_schema:
        logger.info("Schema cache hit for hash: %s...", hash[:12])
        with open(existing_schema, encoding="utf-8") as f:
            schema_data = json.load(f)
        return SchemaResponse(
            hash=hash,
            cached=True,
            schema=schema_data,
        )

    # Get cleaned CSV
    cleaned_csv = _data_store.get_cleaned_csv(hash)
    if not cleaned_csv:
        raise HTTPException(
            status_code=404,
            detail=f"Cleaned CSV not found for hash '{hash[:12]}...'. Run /clean first.",
        )

    # Read and sample data
    logger.debug("Reading cleaned CSV: %s", cleaned_csv)
    df = pd.read_csv(cleaned_csv)

    # Get head rows
    head_rows = df.head(request.head_size).to_dict("records")

    # Get random sample (excluding head rows)
    remaining_df = df.iloc[request.head_size :]
    sample_count = min(request.sample_size, len(remaining_df))
    if sample_count > 0:
        random_rows = remaining_df.sample(n=sample_count).to_dict("records")
    else:
        random_rows = []

    sample_data = head_rows + random_rows
    logger.info(
        "Sampled %d rows for schema generation (head=%d, random=%d)",
        len(sample_data),
        len(head_rows),
        len(random_rows),
    )

    # Generate schema
    try:
        generator = SchemaGenerator()
        schema = await generator.generate_schema(sample_data, request.use_case)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Schema generation failed: {e}") from e
    except Exception as e:
        logger.error("Schema generation error: %s", e)
        raise HTTPException(status_code=500, detail=f"Schema generation failed: {e}") from e

    # Save schema
    paths = _data_store.ensure_hash_dirs(hash)
    generator.save_schema(
        schema=schema,
        schema_dir=paths["schema"],
        use_case=request.use_case,
        rows_sampled=len(sample_data),
    )

    return SchemaResponse(
        hash=hash,
        cached=False,
        schema=schema,
    )


@app.get("/data/{hash}", response_model=DataInfoResponse)  # type: ignore[misc]
async def get_data_info(hash: str) -> DataInfoResponse:
    """Get information about a processed dataset."""
    if not _data_store.hash_exists(hash):
        raise HTTPException(status_code=404, detail="Dataset not found")

    cleaned = _data_store.get_cleaned_csv(hash)
    schema = _data_store.get_schema(hash)

    return DataInfoResponse(
        hash=hash,
        has_cleaned_csv=cleaned is not None,
        cleaned_file=cleaned.name if cleaned else None,
        has_schema=schema is not None,
    )


@app.post("/analyze", response_model=JobStartResponse, status_code=202)  # type: ignore[misc]
async def analyze_dataset_endpoint(
    request: AnalyzeRequest,
    no_cache: bool = Query(default=False),
) -> JobStartResponse:
    """Start an analysis job and return the job id immediately."""
    content_hash = request.hash

    if not _data_store.hash_exists(content_hash):
        raise HTTPException(
            status_code=404,
            detail=f"Dataset with hash '{content_hash[:12]}...' not found. Run /clean first.",
        )

    job = _job_store.create_job("analyze", metadata={"hash": content_hash})
    poll_url, results_url = _build_job_urls(job.job_id)

    existing_json = _data_store.get_analyzed_json(content_hash, ANALYSIS_JSON_FILENAME)
    existing_csv = _data_store.get_analyzed_csv(content_hash, ANALYSIS_CSV_FILENAME)
    if existing_json and existing_csv and not no_cache:
        logger.info("Analysis cache hit for hash: %s...", content_hash[:12])
        rows = _read_csv_rows(existing_csv)
        _job_store.add_results(job.job_id, rows)
        _job_store.set_total_rows(job.job_id, len(rows))
        _job_store.mark_completed(job.job_id)
        return JobStartResponse(
            job_id=job.job_id,
            status=job.status,
            job_type=job.job_type,
            hash=content_hash,
            cached=True,
            poll_url=poll_url,
            results_url=results_url,
        )

    asyncio.create_task(
        _run_analyze_job(
            job_id=job.job_id,
            request=request,
        )
    )

    return JobStartResponse(
        job_id=job.job_id,
        status=job.status,
        job_type=job.job_type,
        hash=content_hash,
        cached=False,
        poll_url=poll_url,
        results_url=results_url,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
