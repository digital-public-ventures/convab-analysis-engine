"""FastAPI server for CSV cleaning and schema generation."""

from __future__ import annotations

import json
import logging
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.config import DOWNLOADS_DIR, LOG_DATE_FORMAT, LOG_FORMAT, SCHEMA_DEFAULT_HEAD_SIZE, SCHEMA_DEFAULT_SAMPLE_SIZE
from app.processing import AttachmentProcessor, DataStore, clean_csv
from app.schema import SchemaGenerator

logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)

# Shared processor with pre-warmed OCR
_processor: AttachmentProcessor | None = None
_data_store: DataStore = DataStore()


def get_processor() -> AttachmentProcessor:
    """Get the shared processor instance."""
    if _processor is None:
        raise RuntimeError("Processor not initialized")
    return _processor


# Pydantic models for request/response
class CleanResponse(BaseModel):
    """Response model for /clean endpoint."""

    hash: str
    cleaned_file: str
    cached: bool = False


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


@app.post("/clean", response_model=CleanResponse)  # type: ignore[misc]
async def clean_csv_endpoint(file: UploadFile = File(...)) -> CleanResponse:
    """Clean a CSV file and return info about the cleaned version.

    1. Hash the incoming CSV content
    2. Check if cleaned CSV exists in app/data/<hash>/cleaned_data/
    3. If cached, return immediately; otherwise process and cache
    4. Return JSON with hash and filename
    """
    content = await file.read()
    content_hash = DataStore.hash_content(content)

    logger.debug("Received file: %s (hash: %s...)", file.filename, content_hash[:12])

    # Check cache
    existing = _data_store.get_cleaned_csv(content_hash)
    if existing:
        logger.info("Cache hit for hash: %s...", content_hash[:12])
        return CleanResponse(
            hash=content_hash,
            cleaned_file=existing.name,
            cached=True,
        )

    # Ensure hash directories exist
    paths = _data_store.ensure_hash_dirs(content_hash)

    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        # Create processor with hash-specific downloads directory
        processor = AttachmentProcessor(cache_dir=paths["downloads"])
        # Share the pre-warmed OCR engine
        processor._ocr_engine = get_processor()._ocr_engine

        # Clean the CSV with hash-specific directories
        cleaned_path = await clean_csv(
            tmp_path,
            processor=processor,
            output_dir=paths["cleaned_data"],
            downloads_dir=paths["downloads"],
        )

        logger.info("Cleaned CSV saved: %s", cleaned_path)

        return CleanResponse(
            hash=content_hash,
            cleaned_file=cleaned_path.name,
            cached=False,
        )
    finally:
        # Clean up temp file
        tmp_path.unlink(missing_ok=True)


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
