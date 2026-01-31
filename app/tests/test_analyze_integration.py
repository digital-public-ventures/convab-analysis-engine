"""Integration test for the analyze pipeline with real LLM calls."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
from dotenv import load_dotenv

from app.analysis import AnalysisRequest, analyze_dataset

HASH_VALUE = "8ca4ff2e602137ec54d559b9b3f4689803e270cfe2f286f51681dd83428dec28"  # pragma: allowlist secret
BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BASE_DIR.parent
FIXTURES_DIR = REPO_ROOT / "app" / "tests" / "fixtures" / HASH_VALUE
PROMPTS_DIR = FIXTURES_DIR / "example_prompts"
OUTPUT_DIR = FIXTURES_DIR / "analyzed" / "integration_test"


def _load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _expected_headers(schema: dict) -> list[str]:
    categorical_fields = schema.get("categorical_fields", [])
    scalar_fields = schema.get("scalar_fields", [])
    key_quotes_fields = schema.get("key_quotes_fields", [])

    headers = ["record_id"]
    headers.extend(field.get("field_name", "").strip() for field in categorical_fields)
    headers.extend(field.get("field_name", "").strip() for field in scalar_fields)
    headers.extend(field.get("field_name", "").strip() for field in key_quotes_fields)

    return [header for header in headers if header]


@pytest.mark.asyncio  # type: ignore[misc]
async def test_analyze_creates_csv_with_expected_headers_and_content() -> None:
    """Analyze data and assert CSV headers and non-null content."""
    load_dotenv()
    if not os.environ.get("GEMINI_API_KEY"):
        pytest.fail("GEMINI_API_KEY environment variable not set")
    cleaned_csv = FIXTURES_DIR / "cleaned_data" / "cleaned_tmp8rgl37tq.csv"
    schema_path = FIXTURES_DIR / "schema" / "schema.json"
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
    output_dir = OUTPUT_DIR / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    use_case = _load_prompt(PROMPTS_DIR / "use_case.txt")
    system_prompt = _load_prompt(PROMPTS_DIR / "system_prompt.txt")

    request = AnalysisRequest(
        cleaned_csv=cleaned_csv,
        schema_path=schema_path,
        output_dir=output_dir,
        use_case=use_case,
        system_prompt=system_prompt,
    )

    analysis_json, analysis_csv = await analyze_dataset(request)

    csv_path = output_dir / "analysis.csv"
    if not csv_path.exists():
        pytest.fail("analysis.csv was not created")
    if analysis_csv.strip() == "":
        pytest.fail("analysis CSV content was empty")

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    expected_headers = _expected_headers(schema)

    csv_df = pd.read_csv(csv_path)
    if list(csv_df.columns) != expected_headers:
        pytest.fail("CSV headers did not match schema fields")

    field_columns = [col for col in csv_df.columns if col != "record_id"]
    if not field_columns:
        pytest.fail("No analysis fields found in CSV header")

    def _is_non_null(value: object) -> bool:
        is_empty_string = isinstance(value, str) and value.strip() == ""
        return value is not None and not (isinstance(value, float) and pd.isna(value)) and not is_empty_string

    threshold = max(1, int(len(field_columns) * 0.6))
    has_populated_row = any(
        sum(_is_non_null(value) for value in row[field_columns]) >= threshold for _, row in csv_df.iterrows()
    )
    if not has_populated_row:
        pytest.fail("No row contained enough non-null analysis fields")

    if not analysis_json.get("records"):
        pytest.fail("analysis JSON records were empty")
