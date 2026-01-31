"""FastAPI server for data processing and analysis workflows."""

from __future__ import annotations

import asyncio
import csv
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, cast

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google import genai

from regs_dot_gov_exploration.complaint_analyzer import (
    analyze_batch,
    build_response_schema,
    filter_records_with_narratives,
    flatten_analysis_row,
)
from regs_dot_gov_exploration.data_processor import DataProcessor, ResponseRecord
from utilities.llm.gemini_client import validate_model_config
from utilities.llm.rate_limiter import AsyncRateLimiter
from utilities.schema_generator import SchemaGenerator

from .cache_helpers import CACHE_DIR, atomic_copy, best_effort_cache_key, save_upload_to_path

if TYPE_CHECKING:
    from collections.abc import Iterator

app = FastAPI(title="Sensemaking API", version="0.1.0")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sensemaking_api")
logger.propagate = True

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")


@app.get("/")  # type: ignore[misc]
def index() -> FileResponse:
    """Serve the HTML UI."""
    return FileResponse(STATIC_DIR / "index.html")


OUTPUT_ROOT = Path("temp/output/api")


def _timestamp() -> str:
    return datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")


def _ensure_output_dir(prefix: str) -> Path:
    output_dir = OUTPUT_ROOT / f"{prefix}_{_timestamp()}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _extract_field_names(schema_definition: dict, key: str) -> list[str]:
    return [field["field_name"] for field in schema_definition.get(key, []) if field.get("field_name")]


def _write_analysis_csv(
    path: Path,
    analyzed: list[dict[str, object]],
    records: list[ResponseRecord],
    categorical_fields: list[str],
    scalar_fields: list[str],
) -> None:
    comment_by_id = {record.id: record.narrative for record in records}
    csv_fields = ["id", "comment_text", *categorical_fields, *scalar_fields]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for analysis in analyzed:
            row = flatten_analysis_row(analysis, categorical_fields, scalar_fields)
            row["comment_text"] = comment_by_id.get(row["id"], "")
            writer.writerow(row)


def _schema_cache_path(cache_key: str) -> Path:
    return CACHE_DIR / f"{cache_key}.schema.json"


def _get_cached_schema(cache_key: str) -> dict | None:
    path = _schema_cache_path(cache_key)
    if not path.exists():
        return None
    return cast("dict[str, Any]", json.loads(path.read_text(encoding="utf-8")))


def _set_cached_schema(cache_key: str, schema: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _schema_cache_path(cache_key)
    tmp = path.with_suffix(".schema.json.tmp")
    tmp.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _load_and_filter_records(responses_path: Path, rows: int) -> tuple[list[ResponseRecord], list[str]]:
    processor = DataProcessor(csv_path=str(responses_path))
    records = processor.load_records(n_rows="all")
    if not records:
        raise HTTPException(status_code=400, detail="No records loaded from responses.csv")

    narratives = [record.narrative for record in records]
    records, narratives, _ = filter_records_with_narratives(records, narratives)
    if not records:
        raise HTTPException(status_code=400, detail="No usable narrative content in responses.csv")

    return records[:rows], narratives[:rows]


def batched(items: list, size: int) -> Iterator[list]:
    """Yield successive chunks of size n from a list."""
    for i in range(0, len(items), size):
        yield items[i : i + size]


@app.post("/process-data")  # type: ignore[misc]
async def process_data(
    request: Request,
    responses_csv: Annotated[UploadFile, File(...)],
    rows: Annotated[int, Query(ge=1)] = 10,
    use_ocr: Annotated[bool, Query()] = False,  # noqa: FBT002
) -> FileResponse:
    """Process raw responses.csv and return responses_with_attachments.csv."""
    cache_key = best_effort_cache_key(request=request, upload=responses_csv, rows=rows, use_ocr=use_ocr)
    cached_out = CACHE_DIR / f"{cache_key}.responses_with_attachments.csv"
    if cached_out.exists():
        logger.info("process-data cache hit", extra={"cache_key": cache_key, "rows": rows, "use_ocr": use_ocr})
        return FileResponse(
            path=cached_out,
            media_type="text/csv",
            filename="responses_with_attachments.csv",
        )

    logger.info("process-data cache miss", extra={"cache_key": cache_key, "rows": rows, "use_ocr": use_ocr})

    output_dir = _ensure_output_dir("processed")
    responses_path = output_dir / "responses.csv"
    await save_upload_to_path(responses_csv, responses_path)

    processor = DataProcessor(csv_path=str(responses_path))
    parsed_path = output_dir / "parsed_attachments.csv"
    merged_path = output_dir / "responses_with_attachments.csv"

    await processor.export_parsed_attachments_csv_async(
        output_path=str(parsed_path),
        n_rows=rows,
        download_attachments=True,
        use_ocr=use_ocr,
    )
    processor.export_responses_with_attachments_csv(
        output_path=str(merged_path),
        parsed_attachments_path=str(parsed_path),
        n_rows=rows,
    )

    atomic_copy(merged_path, cached_out)
    return FileResponse(
        path=cached_out,
        media_type="text/csv",
        filename="responses_with_attachments.csv",
    )


@app.post("/analyze")  # type: ignore[misc]
async def analyze(
    request: Request,
    use_case: Annotated[str, Form(...)],
    system_prompt: Annotated[str, Form(...)],
    responses_csv: Annotated[UploadFile, File(...)],
    rows: Annotated[int, Query(ge=1)] = 10,
) -> FileResponse:
    """Generate schema + analysis for a responses.csv and return analysis CSV."""
    cache_key = best_effort_cache_key(request=request, upload=responses_csv, rows=rows, use_ocr=False)
    schema_definition = _get_cached_schema(cache_key)
    if schema_definition is None:
        logger.info("analyze schema cache miss", extra={"cache_key": cache_key, "rows": rows})
    else:
        logger.info("analyze schema cache hit", extra={"cache_key": cache_key, "rows": rows})

    output_dir = _ensure_output_dir("analysis")
    responses_path = output_dir / "responses.csv"
    await save_upload_to_path(responses_csv, responses_path)

    records, narratives = _load_and_filter_records(responses_path, rows)
    sample_data = [record.to_dict() for record in records]

    if schema_definition is None:
        generator = SchemaGenerator(
            model_id="gemini-3-flash-preview",
            thinking_level="MINIMAL",
            company="sensemaking",
        )
        schema_definition = await generator.generate_schema(sample_data, use_case)
        _set_cached_schema(cache_key, schema_definition)
    response_schema = build_response_schema(schema_definition)

    categorical_fields = _extract_field_names(schema_definition, "categorical_fields")
    scalar_fields = _extract_field_names(schema_definition, "scalar_fields")

    profile = validate_model_config("flash", "MINIMAL")
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
    limiter = AsyncRateLimiter(profile.rpm, profile.tpm, profile.rpd)

    batch_size = 5
    tasks = [
        analyze_batch(
            client,
            limiter,
            system_prompt,
            response_schema,
            profile.model_id,
            "MINIMAL",
            batch,
            narrative_batch,
        )
        for batch, narrative_batch in zip(
            batched(records, batch_size),
            batched(narratives, batch_size),
            strict=True,
        )
    ]

    results = await asyncio.gather(*tasks)
    analyzed_comments = [item for batch in results for item in batch]

    csv_path = output_dir / "analysis_output.csv"
    _write_analysis_csv(csv_path, analyzed_comments, records, categorical_fields, scalar_fields)

    return FileResponse(
        path=csv_path,
        media_type="text/csv",
        filename="analysis_output.csv",
    )
