"""In-memory job store for async processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from threading import Lock
from typing import Any
from uuid import uuid4


class JobStatus(StrEnum):
    """Lifecycle states for background jobs."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class JobResultRow:
    """Represent a single result row with a sequence id."""

    sequence_id: int
    payload: dict[str, Any]


@dataclass
class JobRecord:
    """In-memory record for tracking job status and results."""

    job_id: str
    job_type: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    total_rows: int | None = None
    completed_rows: int = 0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    results: list[JobResultRow] = field(default_factory=list)


class JobStore:
    """Thread-safe in-memory job store."""

    def __init__(self) -> None:
        """Initialize an empty job store."""
        self._jobs: dict[str, JobRecord] = {}
        self._lock = Lock()

    def create_job(self, job_type: str, metadata: dict[str, Any] | None = None) -> JobRecord:
        """Create and register a new job record."""
        job_id = uuid4().hex
        now = datetime.now(tz=UTC)
        record = JobRecord(
            job_id=job_id,
            job_type=job_type,
            status=JobStatus.QUEUED,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )
        with self._lock:
            self._jobs[job_id] = record
        return record

    def get_job(self, job_id: str) -> JobRecord | None:
        """Return the job record for the given id, if any."""
        with self._lock:
            return self._jobs.get(job_id)

    def mark_running(self, job_id: str) -> None:
        """Mark a job as running."""
        self._update_status(job_id, JobStatus.RUNNING)

    def mark_failed(self, job_id: str, error: str) -> None:
        """Mark a job as failed with an error message."""
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return
            record.status = JobStatus.FAILED
            record.error = error
            record.updated_at = datetime.now(tz=UTC)

    def mark_completed(self, job_id: str) -> None:
        """Mark a job as completed."""
        self._update_status(job_id, JobStatus.COMPLETED)

    def add_results(self, job_id: str, rows: list[dict[str, Any]]) -> None:
        """Append result rows for a job and update completion counts."""
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return
            start_sequence = len(record.results) + 1
            for offset, row in enumerate(rows):
                record.results.append(JobResultRow(sequence_id=start_sequence + offset, payload=row))
            record.completed_rows = len(record.results)
            record.updated_at = datetime.now(tz=UTC)

    def set_total_rows(self, job_id: str, total_rows: int) -> None:
        """Set the total row count for a job."""
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return
            record.total_rows = total_rows
            record.updated_at = datetime.now(tz=UTC)

    def get_results_since(self, job_id: str, cursor: int, limit: int) -> tuple[list[JobResultRow], bool]:
        """Return results since the cursor and whether more results are available."""
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return [], False
            start_index = max(cursor, 0)
            available = [row for row in record.results if row.sequence_id > start_index]
            sliced = available[:limit]
            has_more = len(available) > len(sliced)
            return sliced, has_more

    def _update_status(self, job_id: str, status: JobStatus) -> None:
        """Internal helper to update job status."""
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return
            record.status = status
            record.updated_at = datetime.now(tz=UTC)
