"""Tests for analyzer callback behavior."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pandas as pd
import pytest

from app.analysis import AnalysisConfig, AnalysisRequest, analyze_dataset
from app.analysis import analyzer as analyzer_module

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.asyncio  # type: ignore[misc]
async def test_analyze_dataset_invokes_callbacks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure analyze_dataset calls on_row_count and on_batch callbacks."""
    cleaned_csv = tmp_path / "cleaned.csv"
    df = pd.DataFrame({"id": ["1", "2", "3", "4"], "text": ["a", "b", "c", "d"]})
    df.to_csv(cleaned_csv, index=False)

    schema: dict[str, list[object]] = {
        "categorical_fields": [],
        "scalar_fields": [],
        "key_quotes_fields": [],
    }
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")

    batches: list[list[dict[str, object]]] = []
    row_counts: list[int] = []

    async def on_batch(rows: list[dict[str, object]]) -> None:
        batches.append(rows)

    async def on_row_count(total: int) -> None:
        row_counts.append(total)

    async def fake_analyze_batch(
        *,
        client: object,
        limiter: object,
        context: object,
        config: AnalysisConfig,
        records: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        _ = (client, limiter, context, config)
        return [
            {
                "record_id": record.get("record_id"),
                "categorical_fields": {},
                "scalar_fields": {},
                "key_quotes_fields": {},
            }
            for record in records
        ]

    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setattr(analyzer_module, "_analyze_batch", fake_analyze_batch)

    request = AnalysisRequest(
        cleaned_csv=cleaned_csv,
        schema_path=schema_path,
        output_dir=tmp_path / "output",
        use_case="Analyze comments for themes",
        system_prompt="You are a helpful assistant.",
    )

    await analyze_dataset(
        request,
        config=AnalysisConfig(batch_size=2),
        on_batch=on_batch,
        on_row_count=on_row_count,
    )

    assert row_counts == [4]
    assert len(batches) == 2
    assert sum(len(batch) for batch in batches) == 4
