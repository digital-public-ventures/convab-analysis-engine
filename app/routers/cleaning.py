"""Cleaning and dataset-info routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi import Path as PathParam

from app import server_runtime
from app.processing import DataStore
from app.server_jobs import read_csv_rows, run_clean_job
from app.server_models import DataInfoResponse, JobStartResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post('/clean', response_model=JobStartResponse, status_code=202)
async def clean_csv_endpoint(
    request: Request,
    file: UploadFile = server_runtime.UPLOAD_FILE,
    *,
    no_cache: bool = server_runtime.NO_CACHE_QUERY,
    no_cache_ocr: bool = server_runtime.NO_CACHE_OCR_QUERY,
) -> JobStartResponse:
    """Start a CSV cleaning job and return the job id immediately."""
    content = await file.read()
    content_hash = DataStore.hash_content(content)

    logger.debug('Received file: %s (hash: %s...)', file.filename, content_hash[:12])

    job = server_runtime.job_store.create_job('clean', metadata={'content_hash': content_hash})
    poll_url, results_url = server_runtime.build_job_urls(job.job_id)

    existing = server_runtime.data_store.get_cleaned_csv(content_hash)
    if existing and not no_cache:
        logger.info('Cache hit for hash: %s...', content_hash[:12])
        rows = read_csv_rows(existing)
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

    processor = getattr(request.app.state, 'processor', None)
    if processor is None:
        raise HTTPException(status_code=500, detail='Processor not initialized')

    server_runtime.create_background_task(
        run_clean_job(
            job.job_id,
            content,
            content_hash,
            shared_ocr_engine=processor.get_ocr_engine(),
            no_cache_ocr=no_cache_ocr,
        )
    )

    return JobStartResponse(
        job_id=job.job_id,
        status=job.status,
        job_type=job.job_type,
        content_hash=content_hash,
        cached=False,
        poll_url=poll_url,
        results_url=results_url,
    )


@router.get('/data/{hash}', response_model=DataInfoResponse)
async def get_data_info(content_hash: str = PathParam(..., alias='hash')) -> DataInfoResponse:
    """Get information about a processed dataset."""
    if not server_runtime.data_store.hash_exists(content_hash):
        raise HTTPException(status_code=404, detail='Dataset not found')

    cleaned = server_runtime.data_store.get_cleaned_csv(content_hash)
    schema = server_runtime.data_store.get_schema(content_hash)

    return DataInfoResponse(
        content_hash=content_hash,
        has_cleaned_csv=cleaned is not None,
        cleaned_file=cleaned.name if cleaned else None,
        has_schema=schema is not None,
    )
