"""Tests for regs.gov analyzer helpers."""

from importlib import import_module
from typing import Any, Callable

complaint_analyzer = import_module("src.regs_dot_gov_exploration.complaint_analyzer")
build_response_schema: Callable[[dict[str, Any]], dict[str, Any]] = getattr(
    complaint_analyzer, "build_response_schema"
)
filter_records_with_narratives: Callable[
    [list[Any], list[str]], tuple[list[Any], list[str], int]
] = getattr(complaint_analyzer, "filter_records_with_narratives")
flatten_analysis_row: Callable[[dict[str, Any], list[str], list[str]], dict[str, Any]] = getattr(
    complaint_analyzer, "flatten_analysis_row"
)
get_latest_schema_path: Callable[[Any], Any] = getattr(complaint_analyzer, "get_latest_schema_path")
get_use_head: Callable[[], bool] = getattr(complaint_analyzer, "get_use_head")


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


def test_filter_records_with_narratives():
    """Records without narratives are skipped."""
    records = [
        type("Record", (), {"id": "A"})(),
        type("Record", (), {"id": "B"})(),
    ]
    narratives = ["Valid narrative", ""]

    filtered_records, filtered_narratives, skipped = filter_records_with_narratives(
        records,
        narratives,
    )

    assert skipped == 1
    assert len(filtered_records) == 1
    assert filtered_narratives == ["Valid narrative"]
