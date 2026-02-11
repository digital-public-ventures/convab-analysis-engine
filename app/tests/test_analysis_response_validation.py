from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

from app.analysis import AnalysisConfig, AnalysisRequest
from app.analysis import analyzer as analyzer_module


def _valid_payload(schema: dict[str, Any], record_id: str = "1") -> dict[str, Any]:
    enum_fields = {
        field["field_name"]: field.get("allowed_values", [None])[0]
        for field in schema.get("enum_fields", [])
    }
    categorical_fields: dict[str, Any] = {}
    for field in schema.get("categorical_fields", []):
        name = field["field_name"]
        suggested = field.get("suggested_values", [])
        if field.get("allow_multiple"):
            categorical_fields[name] = [suggested[0]] if suggested else []
        else:
            categorical_fields[name] = suggested[0] if suggested else ""

    scalar_fields = {
        field["field_name"]: field.get("scale_min", 0)
        for field in schema.get("scalar_fields", [])
    }
    key_quotes_fields = {
        field["field_name"]: ["quote"]
        for field in schema.get("key_quotes_fields", [])
    }
    text_array_fields = {
        field["field_name"]: []
        for field in schema.get("text_array_fields", [])
    }

    return {
        "records": [
            {
                "record_id": record_id,
                "enum_fields": enum_fields,
                "categorical_fields": categorical_fields,
                "scalar_fields": scalar_fields,
                "key_quotes_fields": key_quotes_fields,
                "text_array_fields": text_array_fields,
            }
        ]
    }


def test_validate_payload_missing_required_field(mock_schema: dict[str, Any]) -> None:
    payload = _valid_payload(mock_schema)
    payload["records"][0]["enum_fields"].pop("category_type")
    failure = analyzer_module._validate_analysis_payload(payload, mock_schema)
    assert failure is not None
    assert failure.category == "missing_required_fields"


def test_validate_payload_wrong_scalar_type_and_range(mock_schema: dict[str, Any]) -> None:
    payload = _valid_payload(mock_schema)
    payload["records"][0]["scalar_fields"]["urgency"] = "high"
    failure = analyzer_module._validate_analysis_payload(payload, mock_schema)
    assert failure is not None
    assert failure.category == "wrong_types"

    payload = _valid_payload(mock_schema)
    payload["records"][0]["scalar_fields"]["urgency"] = 999
    failure = analyzer_module._validate_analysis_payload(payload, mock_schema)
    assert failure is not None
    assert failure.category == "wrong_types"


def test_validate_payload_unexpected_keys(mock_schema: dict[str, Any]) -> None:
    payload = _valid_payload(mock_schema)
    payload["records"][0]["unknown"] = "nope"
    failure = analyzer_module._validate_analysis_payload(payload, mock_schema)
    assert failure is not None
    assert failure.category == "unexpected_keys"


def test_validate_payload_invalid_categorical_arrays() -> None:
    schema = {
        "enum_fields": [],
        "categorical_fields": [
            {
                "field_name": "topics",
                "required": True,
                "allow_multiple": True,
                "suggested_values": ["fees", "fraud"],
                "nullable": False,
            }
        ],
        "scalar_fields": [],
        "key_quotes_fields": [],
        "text_array_fields": [],
    }
    payload = {
        "records": [
            {
                "record_id": "1",
                "enum_fields": {},
                "categorical_fields": {"topics": "fees"},
                "scalar_fields": {},
                "key_quotes_fields": {},
                "text_array_fields": {},
            }
        ]
    }
    failure = analyzer_module._validate_analysis_payload(payload, schema)
    assert failure is not None
    assert failure.category == "wrong_types"


@pytest.mark.asyncio
async def test_analyze_dataset_rejects_schema_invalid_payloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_schema: dict[str, Any],
) -> None:
    cleaned_csv = tmp_path / "cleaned.csv"
    pd.DataFrame({"id": ["1"], "comment": ["example"]}).to_csv(cleaned_csv, index=False)
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(mock_schema), encoding="utf-8")

    async def fake_generate_structured_content(**kwargs: Any) -> tuple[dict[str, Any], dict[str, int]]:
        _ = kwargs
        payload = _valid_payload(mock_schema, record_id="1")
        payload["records"][0]["enum_fields"]["category_type"] = "not-allowed"
        return payload, {"total_tokens": 1, "input_tokens": 1, "output_tokens": 0, "thinking_tokens": 0}

    monkeypatch.setattr(analyzer_module, "generate_structured_content", fake_generate_structured_content)
    monkeypatch.setattr(analyzer_module, "create_llm_client", lambda api_key=None: object())
    monkeypatch.setattr(analyzer_module, "resolve_api_key", lambda: "test")
    monkeypatch.setattr(
        analyzer_module,
        "validate_model_config",
        lambda model_id, thinking_level: SimpleNamespace(
            model_id=model_id,
            rpm=1000,
            tpm=1_000_000,
            rpd=1_000_000,
            max_concurrency=4,
        ),
    )

    request = AnalysisRequest(
        cleaned_csv=cleaned_csv,
        schema_path=schema_path,
        output_dir=tmp_path / "output",
        use_case="Validate payloads",
        system_prompt="Return valid JSON",
    )
    payload, _csv_text = await analyzer_module.analyze_dataset(
        request,
        config=AnalysisConfig(batch_size=1, thinking_level="NONE"),
    )

    assert payload["records"] == []
    assert payload["metadata"]["record_count"] == 0
