"""End-to-end integration test for clean, schema, and analyze pipeline."""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
from http import HTTPStatus
from pathlib import Path
from typing import Any, cast

import jsonschema
import pandas as pd
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from app import config as app_config
from app import server as server_module
from app.config import (
    ANALYSIS_CSV_FILENAME,
    ANALYSIS_JSON_FILENAME,
    TAG_DEDUP_CSV_FILENAME,
    TAG_DEDUP_MAPPINGS_FILENAME,
)
from app.processing import DataStore
from app.processing import cleaner as processing_cleaner
from app.processing import data_store as processing_data_store
from app.processing.job_store import JobStore
from app.routers import analysis as analysis_router_module
from app.routers import jobs_runner as server_jobs_module
from app.routers import state as server_runtime_module
from app.server import app

BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BASE_DIR.parent
FIXTURES_ROOT = REPO_ROOT / "app" / "tests" / "fixtures"
EXAMPLE_DATASET_DIR = FIXTURES_ROOT / "medical_billing_comments"
PROMPTS_DIR = EXAMPLE_DATASET_DIR / "example_prompts"
RESPONSES_CSV = EXAMPLE_DATASET_DIR / "responses_100.csv"
EXAMPLE_DATASET_HASH = "efa267c019c11e33cf61afe5ffcf9d2b1fa8dbdcd987b83e911eeea795812334"  # pragma: allowlist secret
SCHEMA_CACHE_BYPASS = True
RESPONSE_SCHEMA_PATH = REPO_ROOT / "app" / "schema" / "response_schema.json"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "true"

pytestmark = pytest.mark.integration


def _setup_file_logger(log_path: Path) -> logging.Handler:
    """Set up a file handler that captures all app.* debug logs."""
    handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        logging.Formatter("%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
    )
    app_logger = logging.getLogger("app")
    app_logger.addHandler(handler)
    app_logger.setLevel(logging.DEBUG)
    return handler


def _load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _expected_headers(schema: dict) -> list[str]:
    enum_fields = schema.get("enum_fields", [])
    categorical_fields = schema.get("categorical_fields", [])
    scalar_fields = schema.get("scalar_fields", [])
    key_quotes_fields = schema.get("key_quotes_fields", [])
    text_array_fields = schema.get("text_array_fields", [])

    headers = ["record_id"]
    headers.extend(field.get("field_name", "").strip() for field in enum_fields)
    headers.extend(field.get("field_name", "").strip() for field in categorical_fields)
    headers.extend(field.get("field_name", "").strip() for field in scalar_fields)
    headers.extend(field.get("field_name", "").strip() for field in key_quotes_fields)
    headers.extend(field.get("field_name", "").strip() for field in text_array_fields)

    return [header for header in headers if header]


def _normalize_schema_for_validation(schema: dict[str, Any]) -> dict[str, Any]:
    """Normalize minor provider differences before strict schema validation."""
    normalized = json.loads(json.dumps(schema))
    for key in ("additional_categorical_fields", "additional_scalar_fields", "additional_text_array_fields"):
        fields = normalized.get(key, [])
        if not isinstance(fields, list):
            continue
        for field in fields:
            if isinstance(field, dict):
                field.setdefault("nullable", False)
    return normalized


def _poll_until_complete(
    client: TestClient,
    job_id: str,
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        status_response = client.get(f"/jobs/{job_id}")
        if status_response.status_code != HTTPStatus.OK:
            pytest.fail(f"Expected 200 status, got {status_response.status_code}")
        status_payload = cast("dict[str, Any]", status_response.json())
        if status_payload.get("completed") is True:
            error = status_payload.get("error")
            if error:
                pytest.fail(f"Job {job_id} failed: {error}")
            return status_payload
        time.sleep(0.25)
    pytest.fail("Timed out waiting for job completion")
    raise AssertionError("Timed out waiting for job completion")


def _clear_fixtures_outputs(fixtures_root: Path, content_hash: str, output_dir: str) -> None:
    target_dir = fixtures_root / content_hash / output_dir
    if target_dir.exists():
        for file_path in target_dir.glob("*"):
            if file_path.is_file():
                file_path.unlink()


def _prepare_runtime_data_dir(tmp_path: Path) -> Path:
    runtime_data_dir = tmp_path / "fixtures_runtime"
    runtime_data_dir.mkdir()
    shutil.copy(RESPONSES_CSV, runtime_data_dir / RESPONSES_CSV.name)
    shutil.copytree(PROMPTS_DIR, runtime_data_dir / PROMPTS_DIR.name)
    downloads_dir = FIXTURES_ROOT / "downloads"
    if downloads_dir.exists():
        shutil.copytree(downloads_dir, runtime_data_dir / "downloads")
    fixture_hash_dir = FIXTURES_ROOT / EXAMPLE_DATASET_HASH
    if fixture_hash_dir.exists():
        shutil.copytree(fixture_hash_dir, runtime_data_dir / EXAMPLE_DATASET_HASH)
    return runtime_data_dir


def _bind_runtime_data_dir(monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> DataStore:
    downloads_dir = data_dir / "downloads"
    cleaned_dir = data_dir / "cleaned_data"
    raw_dir = data_dir / "raw"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    cleaned_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(app_config, "DATA_DIR", data_dir)
    monkeypatch.setattr(app_config, "DOWNLOADS_DIR", downloads_dir)
    monkeypatch.setattr(app_config, "CLEANED_DATA_DIR", cleaned_dir)
    monkeypatch.setattr(app_config, "RAW_DATA_DIR", raw_dir)
    monkeypatch.setattr(app_config, "TOKEN_USAGE_FILE", data_dir / "token_usage.jsonl")

    monkeypatch.setattr(processing_data_store, "DATA_DIR", data_dir)
    monkeypatch.setattr(processing_cleaner, "DOWNLOADS_DIR", downloads_dir)
    monkeypatch.setattr(processing_cleaner, "CLEANED_DATA_DIR", cleaned_dir)

    monkeypatch.setattr(server_module, "DOWNLOADS_DIR", downloads_dir)
    data_store = DataStore(data_dir=data_dir)
    monkeypatch.setattr(server_runtime_module, "data_store", data_store)
    monkeypatch.setattr(server_runtime_module, "job_store", JobStore())
    return data_store


def test_clean_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run clean endpoint and validate outputs."""
    logging.basicConfig(level=logging.DEBUG)
    load_dotenv()
    if not os.environ.get("GEMINI_API_KEY"):
        pytest.fail("GEMINI_API_KEY environment variable not set")

    runtime_data_dir = _prepare_runtime_data_dir(tmp_path)
    _clear_fixtures_outputs(runtime_data_dir, EXAMPLE_DATASET_HASH, "cleaned_data")
    content = RESPONSES_CSV.read_bytes()
    expected_hash = DataStore.hash_content(content)
    data_store = _bind_runtime_data_dir(monkeypatch, runtime_data_dir)

    cleaned_fixture_dir = runtime_data_dir / EXAMPLE_DATASET_HASH / "cleaned_data"
    if cleaned_fixture_dir.exists():
        for file_path in cleaned_fixture_dir.glob("*"):
            if file_path.is_file():
                file_path.unlink()

    with TestClient(app) as client:
        clean_response = client.post(
            "/clean?no_cache=true",
            files={"file": ("responses_100.csv", content, "text/csv")},
        )
        if clean_response.status_code != HTTPStatus.ACCEPTED:
            pytest.fail(f"Expected 202 status, got {clean_response.status_code}")

        clean_payload = clean_response.json()
        content_hash = clean_payload.get("hash")
        if content_hash != expected_hash:
            pytest.fail("Clean response hash did not match computed hash")
        if content_hash != EXAMPLE_DATASET_HASH:
            pytest.fail("Clean response hash did not match the hardcoded test hash")

        job_id = clean_payload.get("job_id")
        if not job_id:
            pytest.fail("Clean response missing job_id")

        _poll_until_complete(client, job_id)

        hash_dir = runtime_data_dir / expected_hash
        if not hash_dir.exists():
            pytest.fail("Hash directory was not created under fixtures")

        cleaned_csv = data_store.get_cleaned_csv(EXAMPLE_DATASET_HASH)
        if not cleaned_csv:
            pytest.fail("Cleaned CSV was not created")

        cleaned_df = pd.read_csv(cleaned_csv)
        responses_df = pd.read_csv(RESPONSES_CSV)
        source_id_column = responses_df.columns[0]
        if source_id_column not in cleaned_df.columns:
            pytest.fail("Cleaned CSV missing source id column")
        if "Comment" not in cleaned_df.columns:
            pytest.fail("Cleaned CSV missing Comment column")

        if len(cleaned_df) != len(responses_df):
            pytest.fail("Cleaned CSV row count did not match source CSV")

        cleaned_ids = set(cleaned_df[source_id_column].fillna("").astype(str).str.strip())
        source_ids = set(responses_df[source_id_column].fillna("").astype(str).str.strip())
        if cleaned_ids != source_ids:
            pytest.fail("Cleaned CSV ids did not match source IDs")

        cleaned_comments = set(cleaned_df["Comment"].fillna("").astype(str).str.strip())
        source_comments = set(responses_df["Comment"].fillna("").astype(str).str.strip())
        if cleaned_comments != source_comments:
            pytest.fail("Cleaned CSV comments did not match source comments")

        if "Attachment Files" not in cleaned_df.columns:
            pytest.fail("Cleaned CSV missing Attachment Files column")
        if "Attachment Files_extracted" not in cleaned_df.columns:
            pytest.fail("Cleaned CSV missing Attachment Files_extracted column")

        attachments_present = cleaned_df["Attachment Files"].fillna("").astype(str).str.strip() != ""
        extracted_present = cleaned_df["Attachment Files_extracted"].fillna("").astype(str).str.strip() != ""
        unsupported_extensions = {".htm"}

        def _has_unsupported_attachment(value: object) -> bool:
            if value is None or (isinstance(value, float) and pd.isna(value)):
                return False
            urls = [url.strip() for url in str(value).split(",") if url.strip()]
            return any(url.lower().endswith(ext) for url in urls for ext in unsupported_extensions)

        excluded_rows = cleaned_df["Attachment Files"].map(_has_unsupported_attachment)
        required_rows = attachments_present & ~excluded_rows
        if not extracted_present[required_rows].all():
            pytest.fail("Attachment Files_extracted was blank when Attachment Files was present")


def test_schema_generation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Generate schema."""
    logging.basicConfig(level=logging.DEBUG)
    runtime_data_dir = _prepare_runtime_data_dir(tmp_path)
    file_handler = _setup_file_logger(tmp_path / "e2e_schema_generation.log")
    try:
        load_dotenv()
        _clear_fixtures_outputs(runtime_data_dir, EXAMPLE_DATASET_HASH, "schema")
        if not os.environ.get("GEMINI_API_KEY"):
            pytest.fail("GEMINI_API_KEY environment variable not set")

        content = RESPONSES_CSV.read_bytes()
        expected_hash = DataStore.hash_content(content)
        data_store = _bind_runtime_data_dir(monkeypatch, runtime_data_dir)

        prompts_dir = runtime_data_dir / PROMPTS_DIR.name
        use_case = _load_prompt(prompts_dir / "use_case.txt")

        cleaned_csv = data_store.get_cleaned_csv(EXAMPLE_DATASET_HASH)
        if not cleaned_csv:
            pytest.fail("Cleaned CSV was not found for schema generation")

        with TestClient(app) as client:
            schema_endpoint = f"/schema/{expected_hash}"
            if SCHEMA_CACHE_BYPASS:
                schema_endpoint = f"{schema_endpoint}?no_cache=true"
            request_payload = {"use_case": use_case, "num_sample_rows": 10, "num_head_rows": 5}
            logging.getLogger("app").debug(
                "Schema request: endpoint=%s payload=%s",
                schema_endpoint,
                json.dumps(request_payload, indent=2),
            )
            schema_response = client.post(schema_endpoint, json=request_payload)
            logging.getLogger("app").debug(
                "Schema response: status=%s body=%s",
                schema_response.status_code,
                json.dumps(schema_response.json(), indent=2),
            )
            if schema_response.status_code != HTTPStatus.OK:
                pytest.fail(f"Expected 200 status, got {schema_response.status_code}")

            schema_payload = schema_response.json()
            if schema_payload.get("cached") is True and SCHEMA_CACHE_BYPASS is True:
                pytest.fail("Expected schema cache bypass to generate a new schema")
            schema = schema_payload.get("schema")
            if not schema:
                pytest.fail("Schema response was empty")
            response_schema = json.loads(RESPONSE_SCHEMA_PATH.read_text(encoding="utf-8"))
            validator = jsonschema.Draft7Validator(response_schema)
            normalized_schema = _normalize_schema_for_validation(cast("dict[str, Any]", schema))
            errors = sorted(validator.iter_errors(normalized_schema), key=lambda err: list(err.path))
            if errors:
                logging.getLogger("app").error("Schema validation produced %d error(s)", len(errors))
                for idx, err in enumerate(errors, start=1):
                    logging.getLogger("app").error("Schema validation error %d: %s", idx, err.message)
                    logging.getLogger("app").debug(
                        "Schema validation error %d path: %s",
                        idx,
                        list(err.path),
                    )
                    logging.getLogger("app").debug(
                        "Schema validation error %d schema_path: %s",
                        idx,
                        list(err.schema_path),
                    )
                    logging.getLogger("app").debug(
                        "Schema validation error %d details: %s",
                        idx,
                        json.dumps(err.instance, indent=2),
                    )
                    logging.getLogger("app").debug(
                        "Schema validation error %d schema: %s",
                        idx,
                        json.dumps(err.schema, indent=2),
                    )
                pytest.fail(f"Schema failed validation with {len(errors)} error(s)")
    finally:
        logging.getLogger("app").removeHandler(file_handler)


def test_analyze_outputs_with_cached_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run analyze endpoint for a known hash and validate outputs."""
    logging.basicConfig(level=logging.DEBUG)
    runtime_data_dir = _prepare_runtime_data_dir(tmp_path)
    file_handler = _setup_file_logger(tmp_path / "e2e_analyze.log")
    load_dotenv()
    _clear_fixtures_outputs(runtime_data_dir, EXAMPLE_DATASET_HASH, "analyzed")
    if not os.environ.get("GEMINI_API_KEY"):
        pytest.fail("GEMINI_API_KEY environment variable not set")

    data_store = _bind_runtime_data_dir(monkeypatch, runtime_data_dir)


    prompts_dir = runtime_data_dir / PROMPTS_DIR.name
    use_case = _load_prompt(prompts_dir / "use_case.txt")
    system_prompt = _load_prompt(prompts_dir / "system_prompt.txt")

    schema_fixture = runtime_data_dir / EXAMPLE_DATASET_HASH / "schema" / "schema.json"
    if not schema_fixture.exists():
        pytest.fail("Schema fixture was missing for hardcoded hash")

    schema = json.loads(schema_fixture.read_text(encoding="utf-8"))

    with TestClient(app) as client:
        analyze_response = client.post(
            "/analyze?no_cache=true",
            json={"hash": EXAMPLE_DATASET_HASH, "use_case": use_case, "system_prompt": system_prompt},
        )
        if analyze_response.status_code != HTTPStatus.ACCEPTED:
            pytest.fail(f"Expected 202 status, got {analyze_response.status_code}")

        analyze_payload = analyze_response.json()
        analyze_job_id = analyze_payload.get("job_id")
        if not analyze_job_id:
            pytest.fail("Analyze response missing job_id")

        _poll_until_complete(client, analyze_job_id, timeout_seconds=300.0)

    expected_headers = _expected_headers(cast("dict[str, Any]", schema))

    cleaned_csv = data_store.get_cleaned_csv(EXAMPLE_DATASET_HASH)
    if not cleaned_csv:
        pytest.fail("Cleaned CSV was not created")

    csv_path = data_store.get_analyzed_csv(EXAMPLE_DATASET_HASH, ANALYSIS_CSV_FILENAME)
    if not csv_path or not csv_path.exists():
        pytest.fail("analysis.csv was not created")

    json_path = data_store.get_analyzed_json(EXAMPLE_DATASET_HASH, ANALYSIS_JSON_FILENAME)
    if not json_path or not json_path.exists():
        pytest.fail("analysis.json was not created")

    csv_df = pd.read_csv(csv_path)
    responses_df = pd.read_csv(RESPONSES_CSV)
    source_id_column = responses_df.columns[0]
    if list(csv_df.columns) != expected_headers:
        pytest.fail("CSV headers did not match schema fields")

    if csv_df.empty:
        pytest.fail("Analysis CSV did not contain any successful rows")

    if len(csv_df) > len(responses_df):
        pytest.fail(
            f"Analysis CSV row count exceeded source CSV: "
            f"{len(csv_df)}/{len(responses_df)}"
        )

    if csv_df["record_id"].nunique() != len(csv_df):
        pytest.fail("Analysis CSV record_id values were not unique")

    source_ids = set(responses_df[source_id_column].astype(str))
    record_ids = set(csv_df["record_id"].astype(str))
    extra = record_ids - source_ids
    if extra:
        pytest.fail(
            f"Analysis CSV contained record_ids not present in source IDs "
            f"(extra={len(extra)})"
        )

    analysis_metadata = json.loads(json_path.read_text(encoding="utf-8")).get("metadata", {})
    if analysis_metadata.get("record_count") != len(csv_df):
        pytest.fail("Analysis JSON metadata record_count did not match analysis CSV rows")

    field_columns = [col for col in csv_df.columns if col != "record_id"]
    if not field_columns:
        pytest.fail("No analysis fields found in CSV header")

    enum_fields_list = [
        field.get("field_name", "").strip() for field in schema.get("enum_fields", []) if field.get("field_name")
    ]
    scalar_fields = [
        field.get("field_name", "").strip() for field in schema.get("scalar_fields", []) if field.get("field_name")
    ]
    category_fields = [
        field.get("field_name", "").strip() for field in schema.get("categorical_fields", []) if field.get("field_name")
    ]
    free_text_fields = [
        field.get("field_name", "").strip() for field in schema.get("key_quotes_fields", []) if field.get("field_name")
    ]
    text_array_fields_list = [
        field.get("field_name", "").strip() for field in schema.get("text_array_fields", []) if field.get("field_name")
    ]

    for column in enum_fields_list + scalar_fields + category_fields + free_text_fields + text_array_fields_list:
        if column not in csv_df.columns:
            pytest.fail(f"Missing expected analysis column: {column}")

    def _is_non_null(value: object) -> bool:
        is_empty_string = isinstance(value, str) and value.strip() == ""
        return value is not None and not (isinstance(value, float) and pd.isna(value)) and not is_empty_string

    threshold = max(1, int(len(field_columns) * 0.6))
    has_populated_row = any(
        sum(_is_non_null(value) for value in row[field_columns]) >= threshold for _, row in csv_df.iterrows()
    )
    if not has_populated_row:
        pytest.fail("No row contained enough non-null analysis fields")

    for column in scalar_fields:
        column_series = pd.to_numeric(csv_df[column], errors="coerce")
        if column_series.isna().any():
            failing_rows = csv_df[column_series.isna()]
            payload = failing_rows.to_dict(orient="records")
            pytest.fail(f"Column {column} contained non-numeric values. Rows={payload}")

    # Text array fields with min_items=0 can be legitimately empty; empty arrays
    # round-trip through CSV as NaN in pandas, so they are excluded from null checks.
    # Allow up to 5% null/blank rate per column — LLMs occasionally leave individual
    # fields null even when the record is otherwise complete.
    null_tolerance = 0.05
    max_nulls = max(1, int(len(csv_df) * null_tolerance))
    for column in enum_fields_list + category_fields + free_text_fields:
        null_count = csv_df[column].isna().sum()
        if null_count > max_nulls:
            failing_rows = csv_df[csv_df[column].isna()]
            payload = failing_rows.to_dict(orient="records")
            pytest.fail(f"Column {column} contained {null_count} null values (max {max_nulls}). Rows={payload}")
        blank_mask = ~csv_df[column].fillna("_").map(lambda value: isinstance(value, str) and value.strip() != "")
        blank_count = blank_mask.sum()
        if blank_count > max_nulls:
            failing_rows = csv_df[blank_mask]
            payload = failing_rows.to_dict(orient="records")
            pytest.fail(f"Column {column} contained {blank_count} blank strings (max {max_nulls}). Rows={payload}")

    analysis_json = json.loads(json_path.read_text(encoding="utf-8"))
    if not analysis_json.get("records"):
        pytest.fail("analysis JSON records were empty")

    # Flush and remove file handler
    file_handler.close()
    logging.getLogger("app").removeHandler(file_handler)


def test_tag_fix_outputs_with_cached_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run tag-fix endpoint for a known hash and validate outputs."""
    logging.basicConfig(level=logging.DEBUG)
    load_dotenv()
    runtime_data_dir = _prepare_runtime_data_dir(tmp_path)
    _clear_fixtures_outputs(runtime_data_dir, EXAMPLE_DATASET_HASH, "post_processing")
    if not os.environ.get("GEMINI_API_KEY"):
        pytest.fail("GEMINI_API_KEY environment variable not set")

    _bind_runtime_data_dir(monkeypatch, runtime_data_dir)
    monkeypatch.setattr(analysis_router_module, "POST_PROCESSING_SUBDIR", "post_processing")
    monkeypatch.setattr(server_jobs_module, "POST_PROCESSING_SUBDIR", "post_processing")

    analysis_csv = runtime_data_dir / EXAMPLE_DATASET_HASH / "analyzed" / ANALYSIS_CSV_FILENAME
    if not analysis_csv.exists():
        pytest.fail("analysis.csv fixture was missing for hardcoded hash")

    post_processing_dir = runtime_data_dir / EXAMPLE_DATASET_HASH / "post_processing"
    post_processing_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(analysis_csv, post_processing_dir / TAG_DEDUP_CSV_FILENAME)
    (post_processing_dir / TAG_DEDUP_MAPPINGS_FILENAME).write_text(
        json.dumps({"seeded": True}),
        encoding="utf-8",
    )

    with TestClient(app) as client:
        tag_fix_response = client.post(
            "/tag-fix",
            json={"hash": EXAMPLE_DATASET_HASH},
        )
        if tag_fix_response.status_code != HTTPStatus.ACCEPTED:
            pytest.fail(f"Expected 202 status, got {tag_fix_response.status_code}")

        tag_fix_payload = tag_fix_response.json()
        if tag_fix_payload.get("cached") is not True:
            pytest.fail("Expected cached response for tag-fix")
        tag_fix_job_id = tag_fix_payload.get("job_id")
        if not tag_fix_job_id:
            pytest.fail("Tag-fix response missing job_id")

        _poll_until_complete(client, tag_fix_job_id)

        results_response = client.get(f"/jobs/{tag_fix_job_id}/results")
        if results_response.status_code != HTTPStatus.OK:
            pytest.fail(f"Expected 200 status, got {results_response.status_code}")
        results_payload = results_response.json()
        if not results_payload.get("rows"):
            pytest.fail("Expected tag-fix rows in results")
