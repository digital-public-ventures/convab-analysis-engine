"""Shared runtime state and helpers for FastAPI routes."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine

from fastapi import File, HTTPException, Query

from app.processing import DataStore
from app.processing.job_store import JobStore

UPLOAD_FILE = File(...)
NO_CACHE_QUERY = Query(default=False, description='Skip checking for existing cleaned CSV')
NO_CACHE_OCR_QUERY = Query(
    default=False,
    description='Bypass OCR cache reads, re-extract, and overwrite OCR cache entries',
)
CURSOR_QUERY = Query(default=None)
LIMIT_QUERY = Query(default=500, ge=1, le=5000)

background_tasks: set[asyncio.Task[None]] = set()
data_store: DataStore = DataStore()
job_store: JobStore = JobStore()


def create_background_task(coro: Coroutine[object, object, None]) -> None:
    """Track a detached task so it is not garbage-collected early."""
    task = asyncio.create_task(coro)
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)


def build_job_urls(job_id: str) -> tuple[str, str]:
    """Build polling URLs for an async job."""
    return (f'/jobs/{job_id}', f'/jobs/{job_id}/results')


def parse_cursor(cursor: str | None) -> int:
    """Parse a results cursor from the API."""
    if cursor is None or cursor == '':
        return 0
    try:
        value = int(cursor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail='Invalid cursor') from exc
    if value < 0:
        raise HTTPException(status_code=400, detail='Invalid cursor')
    return value
