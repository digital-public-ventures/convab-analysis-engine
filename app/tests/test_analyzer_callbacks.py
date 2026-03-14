"""Tests for analyzer callback behavior."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pandas as pd
import pytest

from app.analysis import AnalysisConfig, AnalysisRequest, analyze_dataset
from app.analysis import analyzer as analyzer_module
from app.analysis.analyzer import _build_dynamic_batches

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.asyncio  # type: ignore[misc]
@pytest.mark.parametrize(
    ("provider", "api_key_env"),
    [("gemini", "GEMINI_API_KEY"), ("openai", "OPENAI_API_KEY")],
)
async def test_analyze_dataset_invokes_callbacks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    api_key_env: str,
) -> None:
    """Ensure analyze_dataset calls on_row_count and on_batch callbacks."""
    cleaned_csv = tmp_path / "cleaned.csv"
    df = pd.DataFrame({"id": ["1", "2", "3", "4"], "text": ["a", "b", "c", "d"]})
    df.to_csv(cleaned_csv, index=False)

    schema: dict[str, list[object]] = {
        "enum_fields": [],
        "categorical_fields": [],
        "scalar_fields": [],
        "key_quotes_fields": [],
        "text_array_fields": [],
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
        batch_index: int | None = None,
    ) -> list[dict[str, object]]:
        _ = (client, limiter, context, config, batch_index)
        return [
            {
                "record_id": record.get("record_id"),
                "enum_fields": {},
                "categorical_fields": {},
                "scalar_fields": {},
                "key_quotes_fields": {},
                "text_array_fields": {},
            }
            for record in records
        ]

    monkeypatch.setenv("LLM_PROVIDER", provider)
    monkeypatch.setenv(api_key_env, "test")
    monkeypatch.setattr(analyzer_module, "create_llm_client", lambda *args, **kwargs: object())
    monkeypatch.setattr(analyzer_module, "_analyze_batch", fake_analyze_batch)
    model_id = "gemini-3-flash-preview" if provider == "gemini" else "gpt-5-mini"
    thinking_level = "LOW" if provider == "gemini" else "MEDIUM"

    request = AnalysisRequest(
        cleaned_csv=cleaned_csv,
        schema_path=schema_path,
        output_dir=tmp_path / "output",
        use_case="Analyze comments for themes",
        system_prompt="You are a helpful assistant.",
    )

    await analyze_dataset(
        request,
        config=AnalysisConfig(batch_size=2, model_id=model_id, thinking_level=thinking_level),
        on_batch=on_batch,
        on_row_count=on_row_count,
    )

    assert row_counts == [4]
    assert len(batches) == 2
    assert sum(len(batch) for batch in batches) == 4


class TestBuildDynamicBatches:
    """Tests for _build_dynamic_batches."""

    def test_small_records_batch_to_max_size(self) -> None:
        records = [{"id": str(i), "text": "short"} for i in range(10)]
        batches = _build_dynamic_batches(records, max_batch_size=5, char_budget=8000)
        assert len(batches) == 2
        assert all(len(b) == 5 for b in batches)

    def test_large_record_gets_own_batch(self) -> None:
        small = {"id": "1", "text": "short"}
        large = {"id": "2", "text": "x" * 9000}
        records = [small, large, small]
        batches = _build_dynamic_batches(records, max_batch_size=5, char_budget=8000)
        # small fits in first batch, large exceeds budget so gets its own, last small in third
        assert len(batches) == 3
        assert len(batches[0]) == 1
        assert len(batches[1]) == 1
        assert batches[1][0]["id"] == "2"
        assert len(batches[2]) == 1

    def test_char_budget_splits_medium_records(self) -> None:
        records = [{"id": str(i), "text": "a" * 2000} for i in range(6)]
        # Each record ~2030 chars JSON. Budget 5000 → ~2 per batch
        batches = _build_dynamic_batches(records, max_batch_size=5, char_budget=5000)
        assert all(len(b) <= 5 for b in batches)
        assert sum(len(b) for b in batches) == 6
        # With ~2030 chars each, 2 fit in 5000 budget
        assert all(len(b) <= 2 for b in batches)

    def test_empty_records(self) -> None:
        batches = _build_dynamic_batches([], max_batch_size=5, char_budget=8000)
        assert batches == []

    def test_single_record(self) -> None:
        records = [{"id": "1", "text": "hello"}]
        batches = _build_dynamic_batches(records, max_batch_size=5, char_budget=8000)
        assert len(batches) == 1
        assert len(batches[0]) == 1

    def test_all_records_preserved(self) -> None:
        records = [{"id": str(i), "text": "x" * (i * 500)} for i in range(20)]
        batches = _build_dynamic_batches(records, max_batch_size=5, char_budget=8000)
        flat = [r for b in batches for r in b]
        assert len(flat) == 20
        assert [r["id"] for r in flat] == [str(i) for i in range(20)]

    def test_max_batch_size_one(self) -> None:
        records = [{"id": str(i), "text": "short"} for i in range(3)]
        batches = _build_dynamic_batches(records, max_batch_size=1, char_budget=8000)
        assert len(batches) == 3
        assert all(len(b) == 1 for b in batches)
