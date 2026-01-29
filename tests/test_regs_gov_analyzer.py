"""Tests for regs.gov analyzer helpers."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from regs_dot_gov_exploration.complaint_analyzer import (  # noqa: E402
    build_response_schema,
    flatten_analysis_row,
    get_latest_schema_path,
    get_use_head,
)


def test_get_use_head_defaults_true(monkeypatch):
    """USE_HEAD defaults to true when unset."""
    monkeypatch.delenv("USE_HEAD", raising=False)
    assert get_use_head() is True


def test_get_latest_schema_path_from_index(tmp_path):
    """Latest schema path uses the last row in index.csv."""
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    schema_file = schemas_dir / "latest.json"
    schema_file.write_text("{}", encoding="utf-8")

    index_path = schemas_dir / "index.csv"
    index_path.write_text(
        "filename,company\nlatest.json,regs_gov\n",
        encoding="utf-8",
    )

    assert get_latest_schema_path(index_path) == schema_file


def test_build_response_schema_shapes_fields():
    """Response schema reflects categorical/scalar definitions."""
    schema_definition = {
        "categorical_fields": [
            {"field_name": "single", "allow_multiple": False},
            {"field_name": "multi", "allow_multiple": True},
        ],
        "scalar_fields": [{"field_name": "score"}],
    }

    schema = build_response_schema(schema_definition)
    analyzed = schema["properties"]["analyzed_comments"]["items"]["properties"]
    categorical = analyzed["categorical_fields"]["properties"]
    scalar = analyzed["scalar_fields"]["properties"]

    assert categorical["single"]["type"] == "STRING"
    assert categorical["multi"]["type"] == "ARRAY"
    assert scalar["score"]["type"] == "NUMBER"


def test_flatten_analysis_row_handles_lists():
    """Flattened rows join list values with pipes."""
    analysis = {
        "id": "A1",
        "categorical_fields": {"multi": ["a", "b"], "single": "c"},
        "scalar_fields": {"score": 4.2},
    }
    row = flatten_analysis_row(analysis, ["multi", "single"], ["score"])
    assert row["id"] == "A1"
    assert row["multi"] == "a|b"
    assert row["single"] == "c"
    assert row["score"] == 4.2
