"""Unit tests for the in-memory job store."""

from __future__ import annotations

from app.processing.job_store import JobStatus, JobStore


def test_create_job_starts_queued_with_metadata() -> None:
    """New jobs should start queued and preserve metadata."""
    store = JobStore()

    record = store.create_job('clean', metadata={'content_hash': 'abc123'})

    assert record.job_type == 'clean'
    assert record.status == JobStatus.QUEUED
    assert record.metadata == {'content_hash': 'abc123'}
    assert store.get_job(record.job_id) is record


def test_add_results_assigns_sequence_ids_and_updates_completed_rows() -> None:
    """Stored rows should get stable sequence ids for cursor pagination."""
    store = JobStore()
    record = store.create_job('analyze')

    store.add_results(record.job_id, [{'id': 'a'}, {'id': 'b'}])
    store.add_results(record.job_id, [{'id': 'c'}])

    assert [row.sequence_id for row in record.results] == [1, 2, 3]
    assert [row.payload for row in record.results] == [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}]
    assert record.completed_rows == 3


def test_get_results_since_respects_cursor_and_limit() -> None:
    """Cursor reads should page forward without losing remaining rows."""
    store = JobStore()
    record = store.create_job('tag_fix')
    store.add_results(record.job_id, [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}])

    first_page, has_more = store.get_results_since(record.job_id, cursor=0, limit=2)
    second_page, second_has_more = store.get_results_since(record.job_id, cursor=2, limit=2)

    assert [row.payload for row in first_page] == [{'id': 'a'}, {'id': 'b'}]
    assert has_more is True
    assert [row.payload for row in second_page] == [{'id': 'c'}]
    assert second_has_more is False


def test_mark_failed_preserves_partial_results() -> None:
    """Failure should record the error without discarding streamed rows."""
    store = JobStore()
    record = store.create_job('clean')
    store.add_results(record.job_id, [{'id': 'partial'}])

    store.mark_failed(record.job_id, 'boom')

    assert record.status == JobStatus.FAILED
    assert record.error == 'boom'
    assert [row.payload for row in record.results] == [{'id': 'partial'}]
