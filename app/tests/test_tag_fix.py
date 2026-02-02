"""Unit tests for tag-fix post-processing."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from app.post_processing.tag_fix import run_tag_fix


@pytest.mark.asyncio
async def test_run_tag_fix_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(
        json.dumps({"categorical_fields": [{"field_name": "issue"}]}),
        encoding="utf-8",
    )

    analysis_csv = tmp_path / "analysis.csv"
    with analysis_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["record_id", "issue"])
        writer.writeheader()
        writer.writerow({"record_id": "1", "issue": "Bankrupcty; Other"})
        writer.writerow({"record_id": "2", "issue": "Other"})

    async def fake_generate_structured_content(**_: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        return (
            {
                "field_name": "issue",
                "canonical_labels": ["Bankruptcy", "Other"],
                "mappings": [
                    {"old_label": "Bankrupcty", "new_label": "Bankruptcy"},
                    {"old_label": "Other", "new_label": "Other"},
                ],
            },
            {"total_tokens": 1},
        )

    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setattr(
        "app.post_processing.tag_fix.generate_structured_content",
        fake_generate_structured_content,
    )

    output_dir = tmp_path / "output"
    result = await run_tag_fix(
        schema_path=schema_path,
        analysis_csv_path=analysis_csv,
        output_dir=output_dir,
    )

    mappings = json.loads(result.mappings_path.read_text(encoding="utf-8"))
    assert mappings["issue"]["Bankrupcty"] == "Bankruptcy"

    with result.deduped_csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert rows[0]["issue"] == "Bankruptcy; Other"
    assert rows[1]["issue"] == "Other"
