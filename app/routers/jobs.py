"""Async job polling routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app import server_runtime
from app.processing.job_store import JobStatus
from app.server_models import JobProgress, JobResultsResponse, JobStatusResponse

router = APIRouter()


@router.get('/jobs/{job_id}', response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Get the current status of a background job."""
    record = server_runtime.job_store.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail='Job not found')

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
        content_hash=record.metadata.get('content_hash'),
    )


@router.get('/jobs/{job_id}/results', response_model=JobResultsResponse)
async def get_job_results(
    job_id: str,
    cursor: str | None = server_runtime.CURSOR_QUERY,
    limit: int = server_runtime.LIMIT_QUERY,
) -> JobResultsResponse:
    """Return completed rows for a job since the provided cursor."""
    record = server_runtime.job_store.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail='Job not found')

    cursor_value = server_runtime.parse_cursor(cursor)
    results, has_more = server_runtime.job_store.get_results_since(job_id, cursor_value, limit)
    rows = [row.payload for row in results]
    next_cursor = str(results[-1].sequence_id) if results else (str(cursor_value) if cursor_value else None)

    return JobResultsResponse(
        job_id=record.job_id,
        rows=rows,
        next_cursor=next_cursor,
        has_more=has_more,
        completed=record.status in (JobStatus.COMPLETED, JobStatus.FAILED),
    )
