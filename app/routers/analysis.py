"""Analysis and tag-dedup routes."""

from __future__ import annotations

import csv
import logging

from fastapi import APIRouter, HTTPException
from fastapi import Query

from app import server_runtime
from app.config import (
    ANALYSIS_CSV_FILENAME,
    ANALYSIS_JSON_FILENAME,
    POST_PROCESSING_SUBDIR,
    TAG_DEDUP_CSV_FILENAME,
    TAG_DEDUP_MAPPINGS_FILENAME,
    TAG_DEDUP_STREAM_CHUNK_SIZE,
)
from app.server_jobs import add_csv_results, read_cached_analysis_rows, run_analyze_job, run_tag_dedup_job
from app.server_models import AnalyzeRequest, JobStartResponse, TagDedupRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post('/analyze', response_model=JobStartResponse, status_code=202)
async def analyze_dataset_endpoint(
    request: AnalyzeRequest,
    *,
    no_cache: bool = Query(default=False, description='Skip checking for existing cleaned CSV'),
) -> JobStartResponse:
    """Start an analysis job and return the job id immediately."""
    content_hash = request.content_hash
    logger.debug(
        '/analyze request received hash=%s no_cache=%s use_case_len=%d system_prompt_len=%d',
        content_hash,
        no_cache,
        len(request.use_case),
        len(request.system_prompt),
    )

    if not server_runtime.data_store.hash_exists(content_hash):
        logger.error('/analyze hash not found: %s', content_hash)
        raise HTTPException(
            status_code=404,
            detail=f"Dataset with hash '{content_hash[:12]}...' not found. Run /clean first.",
        )

    job = server_runtime.job_store.create_job('analyze', metadata={'content_hash': content_hash})
    poll_url, results_url = server_runtime.build_job_urls(job.job_id)

    existing_json = server_runtime.data_store.get_analyzed_json(content_hash, ANALYSIS_JSON_FILENAME)
    existing_csv = server_runtime.data_store.get_analyzed_csv(content_hash, ANALYSIS_CSV_FILENAME)
    if existing_json and existing_csv and not no_cache:
        cached_rows = 0
        try:
            with existing_csv.open(newline='', encoding='utf-8') as handle:
                cached_rows = sum(1 for _ in csv.DictReader(handle))
        except Exception:
            logger.exception('Failed counting cached analysis CSV rows: %s', existing_csv)

        rows = read_cached_analysis_rows(existing_csv)
        if rows is not None:
            logger.info(
                'Analysis cache hit for hash=%s json=%s csv=%s cached_rows=%d json_size=%d csv_size=%d',
                content_hash,
                existing_json,
                existing_csv,
                cached_rows,
                existing_json.stat().st_size,
                existing_csv.stat().st_size,
            )
            server_runtime.job_store.add_results(job.job_id, rows)
            server_runtime.job_store.set_total_rows(job.job_id, len(rows))
            server_runtime.job_store.mark_completed(job.job_id)
            return JobStartResponse(
                job_id=job.job_id,
                status=job.status,
                job_type=job.job_type,
                content_hash=content_hash,
                cached=True,
                poll_url=poll_url,
                results_url=results_url,
            )

        logger.warning(
            'Ignoring invalid analysis cache for hash=%s (json=%s csv=%s); regenerating',
            content_hash,
            existing_json,
            existing_csv,
        )

    logger.debug(
        'Scheduling analyze background job job_id=%s hash=%s no_cache=%s',
        job.job_id,
        content_hash,
        no_cache,
    )
    server_runtime.create_background_task(run_analyze_job(job_id=job.job_id, request=request))

    return JobStartResponse(
        job_id=job.job_id,
        status=job.status,
        job_type=job.job_type,
        content_hash=content_hash,
        cached=False,
        poll_url=poll_url,
        results_url=results_url,
    )


@router.post('/tag-fix', response_model=JobStartResponse, status_code=202)
async def tag_fix_endpoint(
    request: TagDedupRequest,
    *,
    no_cache: bool = Query(default=False, description='Skip checking for existing cleaned CSV'),
) -> JobStartResponse:
    """Start a tag-fix job and return the job id immediately."""
    content_hash = request.content_hash

    if not server_runtime.data_store.hash_exists(content_hash):
        raise HTTPException(
            status_code=404,
            detail=f"Dataset with hash '{content_hash[:12]}...' not found. Run /clean first.",
        )

    job = server_runtime.job_store.create_job('tag_fix', metadata={'content_hash': content_hash})
    poll_url, results_url = server_runtime.build_job_urls(job.job_id)

    output_dir = server_runtime.data_store.get_hash_dir(content_hash) / POST_PROCESSING_SUBDIR
    deduped_csv = output_dir / TAG_DEDUP_CSV_FILENAME
    mappings_path = output_dir / TAG_DEDUP_MAPPINGS_FILENAME
    if deduped_csv.exists() and mappings_path.exists() and not no_cache:
        total_rows = add_csv_results(job.job_id, deduped_csv, TAG_DEDUP_STREAM_CHUNK_SIZE)
        server_runtime.job_store.set_total_rows(job.job_id, total_rows)
        server_runtime.job_store.mark_completed(job.job_id)
        return JobStartResponse(
            job_id=job.job_id,
            status=job.status,
            job_type=job.job_type,
            content_hash=content_hash,
            cached=True,
            poll_url=poll_url,
            results_url=results_url,
        )

    server_runtime.create_background_task(run_tag_dedup_job(job_id=job.job_id, request=request))

    return JobStartResponse(
        job_id=job.job_id,
        status=job.status,
        job_type=job.job_type,
        content_hash=content_hash,
        cached=False,
        poll_url=poll_url,
        results_url=results_url,
    )
