"""FastAPI server for CSV cleaning and schema generation."""

from __future__ import annotations

import asyncio
import csv
import json
import logging
import math
import os
import re
import string
import time
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException
from fastapi import Path as PathParam
from fastapi import Query, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from app.analysis import AnalysisRequest, analyze_dataset
from app.config import (
    ANALYSIS_CSV_FILENAME,
    ANALYSIS_JSON_FILENAME,
    CLEAN_CHUNK_SIZE,
    DATA_DIR,
    DOWNLOADS_DIR,
    LOG_DATE_FORMAT,
    LOG_FORMAT,
    POST_PROCESSING_SUBDIR,
    SCHEMA_DEFAULT_HEAD_SIZE,
    SCHEMA_DEFAULT_SAMPLE_SIZE,
    TAG_FIX_DEDUPED_CSV_FILENAME,
    TAG_FIX_MAPPINGS_FILENAME,
    TAG_FIX_STREAM_CHUNK_SIZE,
)
from app.post_processing import TagFixOutput, run_tag_fix
from app.processing import AttachmentProcessor, DataStore, clean_csv
from app.processing.job_store import JobStatus, JobStore
from app.schema import SchemaGenerator

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Coroutine

load_dotenv()

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    console_level_name = os.environ.get("SERVER_CONSOLE_LOG_LEVEL", "INFO").upper()
    file_level_name = os.environ.get("SERVER_FILE_LOG_LEVEL", "DEBUG").upper()
    console_level = getattr(logging, console_level_name, logging.INFO)
    file_level = getattr(logging, file_level_name, logging.DEBUG)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    has_stream_handler = any(
        isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler)
        for handler in root_logger.handlers
    )
    if not has_stream_handler:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(console_level)
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)

    log_dir = DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = Path(os.environ.get("SERVER_LOG_FILE", str(log_dir / "server-analysis-debug.log")))
    log_file.parent.mkdir(parents=True, exist_ok=True)

    existing_file_handler = next(
        (
            handler
            for handler in root_logger.handlers
            if isinstance(handler, RotatingFileHandler) and Path(handler.baseFilename) == log_file
        ),
        None,
    )
    if existing_file_handler is None:
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=10_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        logger.info("File logging enabled at %s", log_file)


_configure_logging()

UPLOAD_FILE = File(...)
NO_CACHE_QUERY = Query(default=False, description="Skip checking for existing cleaned CSV")
NO_CACHE_OCR_QUERY = Query(
    default=False,
    description="Bypass OCR cache reads, re-extract, and overwrite OCR cache entries",
)
CURSOR_QUERY = Query(default=None)
LIMIT_QUERY = Query(default=500, ge=1, le=5000)

_background_tasks: set[asyncio.Task[None]] = set()
_data_store: DataStore = DataStore()
_job_store: JobStore = JobStore()


class ProcessorNotInitializedError(RuntimeError):
    """Raised when the OCR processor is not initialized."""

    def __init__(self) -> None:
        """Initialize the error with a default message."""
        message = "Processor not initialized"
        super().__init__(message)


def get_processor() -> AttachmentProcessor:
    """Get the shared processor instance."""
    processor = getattr(app.state, "processor", None)
    if processor is None:
        raise ProcessorNotInitializedError
    return cast("AttachmentProcessor", processor)


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

    model_config = ConfigDict(populate_by_name=True)

    hash: str
    cached: bool = False
    schema_data: dict = Field(..., alias="schema")


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


class TagFixRequest(BaseModel):
    """Request model for /tag-fix endpoint."""

    hash: str = Field(..., min_length=10, description="Hash of the analyzed dataset")


class JobProgress(BaseModel):
    """Progress details for a background job."""

    completed_rows: int
    total_rows: int | None


class JobStatusResponse(BaseModel):
    """Response model for job status requests."""

    job_id: str
    status: str
    job_type: str
    completed: bool
    error: str | None
    progress: JobProgress
    hash: str | None = None


class JobResultsResponse(BaseModel):
    """Response model for job result pagination."""

    job_id: str
    rows: list[dict[str, Any]]
    next_cursor: str | None
    has_more: bool
    completed: bool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Pre-warm OCR engine on startup."""
    logger.info("Starting server, pre-warming OCR engine...")
    processor = AttachmentProcessor(cache_dir=DOWNLOADS_DIR)
    # Force OCR engine initialization
    processor.get_ocr_engine()
    app.state.processor = processor
    logger.info("OCR engine ready")

    yield

    logger.info("Shutting down, closing processor...")
    processor = getattr(app.state, "processor", None)
    if processor is not None:
        processor.close()
    app.state.processor = None


app = FastAPI(title="CSV Cleaner & Schema Generator", lifespan=lifespan)


def _create_background_task(coro: Coroutine[object, object, None]) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


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


def _estimate_tokens(value: Any) -> int:
    """Estimate tokens using the same heuristic as AsyncRateLimiter."""
    content = json.dumps(value, default=str)
    split_pattern = rf"[{re.escape(string.punctuation)}\s]+"
    words = [word for word in re.split(split_pattern, content) if word]
    return max(1, math.ceil(len(words) / 0.75))


def _read_csv_rows(csv_path: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(csv_path)
    return cast("list[dict[str, Any]]", df.to_dict(orient="records"))


def _read_cached_analysis_rows(csv_path: Path) -> list[dict[str, Any]] | None:
    try:
        return _read_csv_rows(csv_path)
    except Exception:
        logger.exception("Failed reading cached analysis CSV: %s", csv_path)
        return None


def _add_csv_results(job_id: str, csv_path: Path, chunk_size: int) -> int:
    total_rows = 0
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        batch: list[dict[str, Any]] = []
        for row in reader:
            batch.append(cast("dict[str, Any]", row))
            total_rows += 1
            if len(batch) >= chunk_size:
                _job_store.add_results(job_id, batch)
                batch = []
        if batch:
            _job_store.add_results(job_id, batch)
    return total_rows


async def _run_clean_job(job_id: str, content: bytes, content_hash: str, *, no_cache_ocr: bool = False) -> None:
    _job_store.mark_running(job_id)
    paths = _data_store.ensure_hash_dirs(content_hash)
    raw_input_path = paths["root"] / "input.csv"
    raw_input_path.write_bytes(content)
    logger.debug(
        "Clean job cache dirs: root=%s downloads=%s cleaned=%s no_cache_ocr=%s",
        paths["root"],
        paths["downloads"],
        paths["cleaned_data"],
        no_cache_ocr,
    )
    logger.debug("Clean job raw input persisted: %s (%d bytes)", raw_input_path, len(content))

    async def _set_total_rows(total_rows: int) -> None:
        _job_store.set_total_rows(job_id, total_rows)

    async def _add_chunk(rows: list[dict[str, Any]]) -> None:
        _job_store.add_results(job_id, rows)

    try:
        processor = AttachmentProcessor(cache_dir=paths["downloads"])
        processor.set_shared_ocr_engine(get_processor().get_ocr_engine())

        cleaned_path = await clean_csv(
            raw_input_path,
            processor=processor,
            output_dir=paths["cleaned_data"],
            downloads_dir=paths["downloads"],
            chunk_size=CLEAN_CHUNK_SIZE,
            incremental_output=True,
            on_chunk=_add_chunk,
            on_row_count=_set_total_rows,
            no_cache_ocr=no_cache_ocr,
        )
        logger.info("Cleaned CSV saved to: %s", cleaned_path)
        _job_store.mark_completed(job_id)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Clean job failed")
        _job_store.mark_failed(job_id, str(exc))


async def _run_analyze_job(job_id: str, request: AnalyzeRequest) -> None:
    content_hash = request.hash
    _job_store.mark_running(job_id)
    job_started_at = time.monotonic()
    logger.debug(
        "Analyze job %s started for hash %s...",
        job_id,
        content_hash[:12],
    )

    async def _set_total_rows(total_rows: int) -> None:
        _job_store.set_total_rows(job_id, total_rows)

    async def _add_batch(rows: list[dict[str, Any]]) -> None:
        _job_store.add_results(job_id, rows)

    cleaned_csv = _data_store.get_cleaned_csv(content_hash)
    if not cleaned_csv:
        logger.error("Analyze job %s failed: cleaned CSV not found for hash %s", job_id, content_hash)
        _job_store.mark_failed(job_id, "Cleaned CSV not found")
        return

    schema_path = _data_store.get_schema(content_hash)
    if not schema_path:
        logger.error("Analyze job %s failed: schema not found for hash %s", job_id, content_hash)
        _job_store.mark_failed(job_id, "Schema not found")
        return

    paths = _data_store.ensure_hash_dirs(content_hash)
    analysis_json_path = paths["analyzed"] / ANALYSIS_JSON_FILENAME
    analysis_csv_path = paths["analyzed"] / ANALYSIS_CSV_FILENAME

    logger.debug(
        "Analyze job %s using cleaned_csv=%s schema=%s output_dir=%s",
        job_id,
        cleaned_csv,
        schema_path,
        paths["analyzed"],
    )
    try:
        with cleaned_csv.open(newline="", encoding="utf-8") as handle:
            cleaned_rows = sum(1 for _ in csv.DictReader(handle))
        logger.debug("Analyze job %s cleaned CSV row count=%d", job_id, cleaned_rows)
    except Exception:
        logger.exception("Analyze job %s failed while counting cleaned CSV rows", job_id)

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
        output_rows = 0
        if analysis_csv_path.exists():
            with analysis_csv_path.open(newline="", encoding="utf-8") as handle:
                output_rows = sum(1 for _ in csv.DictReader(handle))
        json_size = analysis_json_path.stat().st_size if analysis_json_path.exists() else 0
        csv_size = analysis_csv_path.stat().st_size if analysis_csv_path.exists() else 0
        logger.info(
            "Analyze job %s output summary: json_exists=%s csv_exists=%s json_size=%d csv_size=%d csv_rows=%d",
            job_id,
            analysis_json_path.exists(),
            analysis_csv_path.exists(),
            json_size,
            csv_size,
            output_rows,
        )
        _job_store.mark_completed(job_id)
        logger.debug(
            "Analyze job %s completed in %.2fs",
            job_id,
            time.monotonic() - job_started_at,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Analyze job failed")
        _job_store.mark_failed(job_id, str(exc))


async def _run_tag_fix_job(job_id: str, request: TagFixRequest) -> None:
    content_hash = request.hash
    _job_store.mark_running(job_id)
    job_started_at = time.monotonic()
    logger.debug("Tag-fix job %s started for hash %s...", job_id, content_hash[:12])

    analysis_csv = _data_store.get_analyzed_csv(content_hash, ANALYSIS_CSV_FILENAME)
    if not analysis_csv:
        _job_store.mark_failed(job_id, "Analysis CSV not found")
        return

    schema_path = _data_store.get_schema(content_hash)
    if not schema_path:
        _job_store.mark_failed(job_id, "Schema not found")
        return

    output_dir = _data_store.get_hash_dir(content_hash) / POST_PROCESSING_SUBDIR

    try:
        result: TagFixOutput = await run_tag_fix(
            schema_path=schema_path,
            analysis_csv_path=analysis_csv,
            output_dir=output_dir,
        )
        total_rows = _add_csv_results(job_id, result.deduped_csv_path, TAG_FIX_STREAM_CHUNK_SIZE)
        _job_store.set_total_rows(job_id, total_rows)
        _job_store.mark_completed(job_id)
        logger.debug(
            "Tag-fix job %s completed in %.2fs",
            job_id,
            time.monotonic() - job_started_at,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Tag-fix job failed")
        _job_store.mark_failed(job_id, str(exc))


@app.post("/clean", response_model=JobStartResponse, status_code=202)
async def clean_csv_endpoint(
    file: UploadFile = UPLOAD_FILE,
    *,
    no_cache: bool = NO_CACHE_QUERY,
    no_cache_ocr: bool = NO_CACHE_OCR_QUERY,
) -> JobStartResponse:
    """Start a CSV cleaning job and return the job id immediately.

    Args:
        file: CSV file to clean
        no_cache: If True, skip checking for existing cleaned CSV and re-process
                  (but still use cached OCR results for attachments)
        no_cache_ocr: If True, bypass OCR cache reads (extracted text and rendered PDF page images),
                      force fresh OCR extraction, and overwrite OCR cache entries while still
                      reusing downloaded attachment files
    """
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

    _create_background_task(_run_clean_job(job.job_id, content, content_hash, no_cache_ocr=no_cache_ocr))

    return JobStartResponse(
        job_id=job.job_id,
        status=job.status,
        job_type=job.job_type,
        hash=content_hash,
        cached=False,
        poll_url=poll_url,
        results_url=results_url,
    )


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
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


@app.get("/jobs/{job_id}/results", response_model=JobResultsResponse)
async def get_job_results(
    job_id: str,
    cursor: str | None = CURSOR_QUERY,
    limit: int = LIMIT_QUERY,
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


@app.post("/schema/{hash}", response_model=SchemaResponse)
async def generate_schema_endpoint(
    request: SchemaRequest,
    content_hash: str = PathParam(..., alias="hash"),
) -> SchemaResponse:
    """Generate a tagging schema for a previously cleaned CSV.

    1. Verify hash directory and cleaned CSV exist
    2. Check if schema already exists
    3. If cached, return it; otherwise generate and cache
    4. Sample head + N random rows from cleaned CSV
    5. Call SchemaGenerator with sample data
    """
    # Validate hash exists
    if not _data_store.hash_exists(content_hash):
        raise HTTPException(
            status_code=404,
            detail=f"Dataset with hash '{content_hash[:12]}...' not found. Run /clean first.",
        )

    # Check for existing schema
    existing_schema = _data_store.get_schema(content_hash)
    if existing_schema:
        logger.info("Schema cache hit for hash: %s...", content_hash[:12])
        with existing_schema.open(encoding="utf-8") as f:
            schema_data = json.load(f)
        return SchemaResponse(
            hash=content_hash,
            cached=True,
            schema=schema_data,
        )

    # Get cleaned CSV
    cleaned_csv = _data_store.get_cleaned_csv(content_hash)
    if not cleaned_csv:
        raise HTTPException(
            status_code=404,
            detail=f"Cleaned CSV not found for hash '{content_hash[:12]}...'. Run /clean first.",
        )

    # Read and sample data
    logger.debug("Reading cleaned CSV: %s", cleaned_csv)
    df = pd.read_csv(cleaned_csv)

    # Get head rows
    head_rows = df.head(request.head_size).to_dict("records")

    # Get random sample (excluding head rows)
    remaining_df = df.iloc[request.head_size :]
    sample_count = min(request.sample_size, len(remaining_df))
    random_rows = remaining_df.sample(n=sample_count).to_dict("records") if sample_count > 0 else []

    max_sample_tokens = 50_000
    token_count = _estimate_tokens(head_rows + random_rows)
    while token_count > max_sample_tokens and random_rows:
        random_rows.pop()
        token_count = _estimate_tokens(head_rows + random_rows)

    sample_data = head_rows + random_rows
    logger.info(
        "Sampled %d rows for schema generation (head=%d, random=%d, estimated_tokens=%d)",
        len(sample_data),
        len(head_rows),
        len(random_rows),
        token_count,
    )

    # Generate schema
    try:
        generator = SchemaGenerator()
        schema = await generator.generate_schema(sample_data, request.use_case)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Schema generation failed: {e}") from e
    except Exception as exc:
        logger.exception("Schema generation error")
        raise HTTPException(status_code=500, detail=f"Schema generation failed: {exc}") from exc

    # Save schema
    paths = _data_store.ensure_hash_dirs(content_hash)
    generator.save_schema(
        schema=schema,
        schema_dir=paths["schema"],
        use_case=request.use_case,
        rows_sampled=len(sample_data),
    )

    return SchemaResponse(
        hash=content_hash,
        cached=False,
        schema=schema,
    )


@app.get("/data/{hash}", response_model=DataInfoResponse)
async def get_data_info(content_hash: str = PathParam(..., alias="hash")) -> DataInfoResponse:
    """Get information about a processed dataset."""
    if not _data_store.hash_exists(content_hash):
        raise HTTPException(status_code=404, detail="Dataset not found")

    cleaned = _data_store.get_cleaned_csv(content_hash)
    schema = _data_store.get_schema(content_hash)

    return DataInfoResponse(
        hash=content_hash,
        has_cleaned_csv=cleaned is not None,
        cleaned_file=cleaned.name if cleaned else None,
        has_schema=schema is not None,
    )


@app.post("/analyze", response_model=JobStartResponse, status_code=202)
async def analyze_dataset_endpoint(
    request: AnalyzeRequest,
    *,
    no_cache: bool = NO_CACHE_QUERY,
) -> JobStartResponse:
    """Start an analysis job and return the job id immediately."""
    content_hash = request.hash
    logger.debug(
        "/analyze request received hash=%s no_cache=%s use_case_len=%d system_prompt_len=%d",
        content_hash,
        no_cache,
        len(request.use_case),
        len(request.system_prompt),
    )

    if not _data_store.hash_exists(content_hash):
        logger.error("/analyze hash not found: %s", content_hash)
        raise HTTPException(
            status_code=404,
            detail=f"Dataset with hash '{content_hash[:12]}...' not found. Run /clean first.",
        )

    job = _job_store.create_job("analyze", metadata={"hash": content_hash})
    poll_url, results_url = _build_job_urls(job.job_id)

    existing_json = _data_store.get_analyzed_json(content_hash, ANALYSIS_JSON_FILENAME)
    existing_csv = _data_store.get_analyzed_csv(content_hash, ANALYSIS_CSV_FILENAME)
    if existing_json and existing_csv and not no_cache:
        cached_rows = 0
        try:
            with existing_csv.open(newline="", encoding="utf-8") as handle:
                cached_rows = sum(1 for _ in csv.DictReader(handle))
        except Exception:
            logger.exception("Failed counting cached analysis CSV rows: %s", existing_csv)

        rows = _read_cached_analysis_rows(existing_csv)
        if rows is not None:
            logger.info(
                "Analysis cache hit for hash=%s json=%s csv=%s cached_rows=%d json_size=%d csv_size=%d",
                content_hash,
                existing_json,
                existing_csv,
                cached_rows,
                existing_json.stat().st_size,
                existing_csv.stat().st_size,
            )
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

        logger.warning(
            "Ignoring invalid analysis cache for hash=%s (json=%s csv=%s); regenerating",
            content_hash,
            existing_json,
            existing_csv,
        )

    logger.debug(
        "Scheduling analyze background job job_id=%s hash=%s no_cache=%s",
        job.job_id,
        content_hash,
        no_cache,
    )
    _create_background_task(
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


@app.post("/tag-fix", response_model=JobStartResponse, status_code=202)
async def tag_fix_endpoint(
    request: TagFixRequest,
    *,
    no_cache: bool = NO_CACHE_QUERY,
) -> JobStartResponse:
    """Start a tag-fix job and return the job id immediately."""
    content_hash = request.hash

    if not _data_store.hash_exists(content_hash):
        raise HTTPException(
            status_code=404,
            detail=f"Dataset with hash '{content_hash[:12]}...' not found. Run /clean first.",
        )

    job = _job_store.create_job("tag-fix", metadata={"hash": content_hash})
    poll_url, results_url = _build_job_urls(job.job_id)

    output_dir = _data_store.get_hash_dir(content_hash) / POST_PROCESSING_SUBDIR
    deduped_csv = output_dir / TAG_FIX_DEDUPED_CSV_FILENAME
    mappings_path = output_dir / TAG_FIX_MAPPINGS_FILENAME
    if deduped_csv.exists() and mappings_path.exists() and not no_cache:
        total_rows = _add_csv_results(job.job_id, deduped_csv, TAG_FIX_STREAM_CHUNK_SIZE)
        _job_store.set_total_rows(job.job_id, total_rows)
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

    _create_background_task(
        _run_tag_fix_job(
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

    uvicorn.run(app, host="127.0.0.1", port=8000)
