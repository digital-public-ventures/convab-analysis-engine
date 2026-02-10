"""Integration test for running analyze flow on first 5 fixture rows."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import pytest
from dotenv import load_dotenv

from app.analysis.analyzer import AnalysisConfig, AnalysisRequest, analyze_dataset
from app.config import ANALYSIS_CSV_FILENAME, ANALYSIS_JSON_FILENAME

FIXTURES_ROOT = Path(__file__).parent / "fixtures"
CONTENT_HASH = "efa267c019c11e33cf61afe5ffcf9d2b1fa8dbdcd987b83e911eeea795812334"
INPUT_CSV = FIXTURES_ROOT / "raw" / "clean_10.csv"
SCHEMA_PATH = FIXTURES_ROOT / CONTENT_HASH / "schema" / "schema.json"
TEST_USE_CASE = "Extract structured fields for each record."
TEST_SYSTEM_PROMPT = "Return valid JSON matching the schema."
pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_analyze_first_5_rows_from_fixture(tmp_path: Path) -> None:
    """Run analyze flow on first 5 rows from fixture cleaned CSV."""
    load_dotenv()
    if not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY environment variable not set")

    if not INPUT_CSV.exists():
        pytest.fail(f"Missing fixture CSV: {INPUT_CSV}")
    if not SCHEMA_PATH.exists():
        pytest.fail(f"Missing schema fixture: {SCHEMA_PATH}")

    source_df = pd.read_csv(INPUT_CSV)
    subset_df = source_df.head(5).copy()
    if len(subset_df) != 5:
        pytest.fail(f"Fixture CSV had fewer than 5 rows: {len(subset_df)}")

    subset_csv = tmp_path / "cleaned_first_5.csv"
    subset_df.to_csv(subset_csv, index=False)

    output_dir = tmp_path / "analyzed"
    request = AnalysisRequest(
        cleaned_csv=subset_csv,
        schema_path=SCHEMA_PATH,
        output_dir=output_dir,
        use_case=TEST_USE_CASE,
        system_prompt=TEST_SYSTEM_PROMPT,
    )
    payload, csv_text = await analyze_dataset(
        request,
        config=AnalysisConfig(batch_size=1),
    )

    records = payload.get("records", [])
    assert len(records) == 5
    assert payload.get("metadata", {}).get("record_count") == 5

    expected_ids = set(subset_df.iloc[:, 0].astype(str).tolist())
    returned_ids = {str(record.get("record_id", "")) for record in records}
    assert returned_ids == expected_ids

    for record in records:
        assert "enum_fields" in record
        assert "categorical_fields" in record
        assert "scalar_fields" in record
        assert "key_quotes_fields" in record
        assert "text_array_fields" in record

    csv_df = pd.read_csv(pd.io.common.StringIO(csv_text))
    assert len(csv_df) == 5
    assert set(csv_df["record_id"].astype(str)) == expected_ids

    analysis_csv_path = output_dir / ANALYSIS_CSV_FILENAME
    analysis_json_path = output_dir / ANALYSIS_JSON_FILENAME
    assert analysis_csv_path.exists()
    assert analysis_json_path.exists()

    analysis_json = json.loads(analysis_json_path.read_text(encoding="utf-8"))
    assert len(analysis_json.get("records", [])) == 5
