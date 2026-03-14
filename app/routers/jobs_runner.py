"""Background job helpers for router endpoints."""

from __future__ import annotations

import csv
import json
import logging
import time
from pathlib import Path
from typing import Any, cast

from app.analysis import AnalysisRequest as DatasetAnalysisRequest
from app.analysis import analyze_dataset
from app.config import (
    ANALYSIS_CSV_FILENAME,
    ANALYSIS_JSON_FILENAME,
    CLEAN_CHUNK_SIZE,
    POST_PROCESSING_SUBDIR,
    TAG_DEDUP_STREAM_CHUNK_SIZE,
)
from app.processing import AttachmentProcessor, TagDedupOutput, clean_csv, deduplicate_tags, read_csv_rows
from app.routers import state
from app.routers.models import AnalyzeRequest, TagDedupRequest

logger = logging.getLogger(__name__)


def read_cached_analysis_rows(csv_path: Path) -> list[dict[str, Any]] | None:
    """Read cached analysis rows defensively."""
    try:
        return read_csv_rows(csv_path)
    except Exception:
        logger.exception('Failed reading cached analysis CSV: %s', csv_path)
        return None


def add_csv_results(job_id: str, csv_path: Path, chunk_size: int) -> int:
    """Stream CSV rows into the job store in batches."""
    total_rows = 0
    with csv_path.open(newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        batch: list[dict[str, Any]] = []
        for row in reader:
            batch.append(cast('dict[str, Any]', row))
            total_rows += 1
            if len(batch) >= chunk_size:
                state.job_store.add_results(job_id, batch)
                batch = []
        if batch:
            state.job_store.add_results(job_id, batch)
    return total_rows


async def run_clean_job(
    job_id: str,
    content: bytes,
    content_hash: str,
    *,
    shared_ocr_engine: Any,
    no_cache_ocr: bool = False,
) -> None:
    """Run the clean job in the background."""
    state.job_store.mark_running(job_id)
    paths = state.data_store.ensure_hash_dirs(content_hash)
    raw_input_path = paths['root'] / 'input.csv'
    raw_input_path.write_bytes(content)
    logger.debug(
        'Clean job cache dirs: root=%s downloads=%s cleaned=%s no_cache_ocr=%s',
        paths['root'],
        paths['downloads'],
        paths['cleaned_data'],
        no_cache_ocr,
    )
    logger.debug('Clean job raw input persisted: %s (%d bytes)', raw_input_path, len(content))

    async def set_total_rows(total_rows: int) -> None:
        state.job_store.set_total_rows(job_id, total_rows)

    async def add_chunk(rows: list[dict[str, Any]]) -> None:
        state.job_store.add_results(job_id, rows)

    try:
        processor = AttachmentProcessor(cache_dir=paths['downloads'])
        processor.set_shared_ocr_engine(shared_ocr_engine)

        cleaned_path = await clean_csv(
            raw_input_path,
            processor=processor,
            output_dir=paths['cleaned_data'],
            downloads_dir=paths['downloads'],
            chunk_size=CLEAN_CHUNK_SIZE,
            incremental_output=True,
            on_chunk=add_chunk,
            on_row_count=set_total_rows,
            no_cache_ocr=no_cache_ocr,
        )
        logger.info('Cleaned CSV saved to: %s', cleaned_path)
        state.job_store.mark_completed(job_id)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception('Clean job failed')
        state.job_store.mark_failed(job_id, str(exc))


async def run_analyze_job(job_id: str, request: AnalyzeRequest) -> None:
    """Run the analyze job in the background."""
    content_hash = request.content_hash
    state.job_store.mark_running(job_id)
    job_started_at = time.monotonic()
    logger.debug('Analyze job %s started for hash %s...', job_id, content_hash[:12])

    async def set_total_rows(total_rows: int) -> None:
        state.job_store.set_total_rows(job_id, total_rows)

    async def add_batch(rows: list[dict[str, Any]]) -> None:
        state.job_store.add_results(job_id, rows)

    cleaned_csv = state.data_store.get_cleaned_csv(content_hash)
    if not cleaned_csv:
        logger.error('Analyze job %s failed: cleaned CSV not found for hash %s', job_id, content_hash)
        state.job_store.mark_failed(job_id, 'Cleaned CSV not found')
        return

    schema_path = state.data_store.get_schema(content_hash)
    if not schema_path:
        logger.error('Analyze job %s failed: schema not found for hash %s', job_id, content_hash)
        state.job_store.mark_failed(job_id, 'Schema not found')
        return

    paths = state.data_store.ensure_hash_dirs(content_hash)
    analysis_json_path = paths['analyzed'] / ANALYSIS_JSON_FILENAME
    analysis_csv_path = paths['analyzed'] / ANALYSIS_CSV_FILENAME

    logger.debug(
        'Analyze job %s using cleaned_csv=%s schema=%s output_dir=%s',
        job_id,
        cleaned_csv,
        schema_path,
        paths['analyzed'],
    )
    try:
        with cleaned_csv.open(newline='', encoding='utf-8') as handle:
            cleaned_rows = sum(1 for _ in csv.DictReader(handle))
        logger.debug('Analyze job %s cleaned CSV row count=%d', job_id, cleaned_rows)
    except Exception:
        logger.exception('Analyze job %s failed while counting cleaned CSV rows', job_id)

    try:
        await analyze_dataset(
            DatasetAnalysisRequest(
                cleaned_csv=cleaned_csv,
                schema_path=schema_path,
                output_dir=paths['analyzed'],
                use_case=request.use_case,
                system_prompt=request.system_prompt,
            ),
            on_batch=add_batch,
            on_row_count=set_total_rows,
        )
        output_rows = 0
        if analysis_csv_path.exists():
            with analysis_csv_path.open(newline='', encoding='utf-8') as handle:
                output_rows = sum(1 for _ in csv.DictReader(handle))
        json_size = analysis_json_path.stat().st_size if analysis_json_path.exists() else 0
        csv_size = analysis_csv_path.stat().st_size if analysis_csv_path.exists() else 0
        logger.info(
            'Analyze job %s output summary: json_exists=%s csv_exists=%s json_size=%d csv_size=%d csv_rows=%d',
            job_id,
            analysis_json_path.exists(),
            analysis_csv_path.exists(),
            json_size,
            csv_size,
            output_rows,
        )
        state.job_store.mark_completed(job_id)
        logger.debug('Analyze job %s completed in %.2fs', job_id, time.monotonic() - job_started_at)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception('Analyze job failed')
        state.job_store.mark_failed(job_id, str(exc))


async def run_tag_dedup_job(job_id: str, request: TagDedupRequest) -> None:
    """Run the tag-dedup job in the background."""
    content_hash = request.content_hash
    state.job_store.mark_running(job_id)
    job_started_at = time.monotonic()
    logger.debug('Tag dedup job %s started for hash %s...', job_id, content_hash[:12])

    analysis_csv = state.data_store.get_analyzed_csv(content_hash, ANALYSIS_CSV_FILENAME)
    if not analysis_csv:
        state.job_store.mark_failed(job_id, 'Analysis CSV not found')
        return

    schema_path = state.data_store.get_schema(content_hash)
    if not schema_path:
        state.job_store.mark_failed(job_id, 'Schema not found')
        return

    output_dir = state.data_store.get_hash_dir(content_hash) / POST_PROCESSING_SUBDIR

    try:
        result: TagDedupOutput = await deduplicate_tags(
            schema_path=schema_path,
            analysis_csv_path=analysis_csv,
            output_dir=output_dir,
        )
        total_rows = add_csv_results(job_id, result.deduped_csv_path, TAG_DEDUP_STREAM_CHUNK_SIZE)
        state.job_store.set_total_rows(job_id, total_rows)
        state.job_store.mark_completed(job_id)
        logger.debug('Tag dedup job %s completed in %.2fs', job_id, time.monotonic() - job_started_at)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception('Tag dedup job failed')
        state.job_store.mark_failed(job_id, str(exc))
