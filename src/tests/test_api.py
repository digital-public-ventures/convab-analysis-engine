"""API-only tests for the FastAPI app."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Protocol, cast

import xxhash
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

import sensemaking_api.app as api_app
from utilities.schema_generator import SchemaGenerator


class _HasId(Protocol):
    id: str


def _build_csv(rows: list[list[str]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def _responses_csv_bytes() -> bytes:
    header = [
        "Document ID",
        "Comment",
        "Attachment Files",
        "Document Type",
        "Agency ID",
    ]
    row = [
        "CFPB-2023-0001-0001",
        "Sample comment text.",
        "",
        "Public Submission",
        "CFPB",
    ]
    return _build_csv([header, row])


def test_process_data_returns_csv(tmp_path: Path) -> None:
    client = TestClient(api_app.app)
    csv_bytes = _responses_csv_bytes()

    cache_key = "test-process-data"
    digest = xxhash.xxh3_128_hexdigest(f"v1|client|{cache_key}|rows=1|ocr=0".encode())
    expected_cache_path = api_app.CACHE_DIR / f"{digest}.responses_with_attachments.csv"
    if expected_cache_path.exists():
        expected_cache_path.unlink()

    response = client.post(
        "/process-data?rows=1",
        files={"responses_csv": ("responses.csv", csv_bytes, "text/csv")},
        headers={"X-Cache-Key": cache_key},
    )

    assert response.status_code == 200
    body = response.text
    assert "Document ID" in body
    assert "Sample comment text." in body
    assert expected_cache_path.exists()


def test_analyze_returns_csv(monkeypatch: MonkeyPatch) -> None:
    async def fake_generate_schema(self: SchemaGenerator, sample_data: list[dict], use_case: str) -> dict:
        return {
            "categorical_fields": [
                {"field_name": "category", "allow_multiple": False},
            ],
            "scalar_fields": [
                {"field_name": "score"},
            ],
        }

    async def fake_analyze_batch(*args: object, **kwargs: object) -> list[dict[str, object]]:
        records_obj = kwargs.get("records") or args[6]
        records = cast(list[_HasId], records_obj)
        return [
            {
                "id": record.id,
                "categorical_fields": {"category": "A"},
                "scalar_fields": {"score": 1},
            }
            for record in records
        ]

    monkeypatch.setattr(SchemaGenerator, "generate_schema", fake_generate_schema, raising=True)
    monkeypatch.setattr(api_app, "analyze_batch", fake_analyze_batch, raising=True)

    client = TestClient(api_app.app)
    csv_bytes = _responses_csv_bytes()

    response = client.post(
        "/analyze?rows=1",
        data={"use_case": "Test use case", "system_prompt": "Test prompt"},
        files={"responses_csv": ("responses.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 200
    body = response.text
    assert "comment_text" in body
    assert "category" in body
    assert "score" in body
    assert "Sample comment text." in body
