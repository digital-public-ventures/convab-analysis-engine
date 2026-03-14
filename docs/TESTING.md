# Testing

All tests live under `app/tests/`. Pytest is configured in `pyproject.toml` with `testpaths = ["app/tests"]`.

## Running Tests

```bash
# All tests (includes coverage report)
pytest

# Fast tests only — no API keys needed
pytest -m "not integration"

# Integration tests only
pytest -m integration

# Specific file
pytest app/tests/test_csv_processing.py

# Verbose with full tracebacks
pytest -vv --tb=long
```

Coverage reports are generated automatically (`--cov=app`) in terminal, HTML (`htmlcov/`), and XML formats.

## Test Layout

### Unit Tests (no API key required)

These run in seconds with no network access. LLM calls are mocked or use fake responses.

| File | What it tests |
|------|---------------|
| `test_csv_processing.py` | CSV cleaning, text normalization, attachment handling |
| `test_data_store.py` | Content-hash directory management |
| `test_job_store.py` | In-memory async job state and cursor pagination |
| `test_llm_utils.py` | Token cost calculation, provider resolution, and response parsing helpers |
| `test_cli.py` | CLI argument validation and output |
| `test_analysis_response_validation.py` | Schema validation of analysis output (mocked LLM) |
| `test_analyzer_callbacks.py` | Batch callbacks, dynamic batching, character budgets |
| `test_schema_generation.py` | Schema generation prompt construction (mocked LLM) |
| `test_gemini_client_validation.py` | Gemini response schema validation (fake payloads) |
| `test_openai_client_validation.py` | OpenAI response schema validation (fake payloads) |
| `test_pdf_mixed_ocr.py` | PDF mixed text/image page handling (mocked structures) |

### Integration Tests (require API keys)

These call live LLM APIs and are marked `@pytest.mark.integration` (except `test_tag_fix.py` and `test_attachment_ocr.py`, which lack the marker but still need network access).

| File | API key(s) | What it tests |
|------|-----------|---------------|
| `test_e2e_integration.py` | `GEMINI_API_KEY` | Full pipeline: clean → schema → analyze → post-process |
| `test_server_lifecycle.py` | `GEMINI_API_KEY` | Async job creation, polling, caching, and results retrieval |
| `test_analyze_first5_integration.py` | `GEMINI_API_KEY` | Analysis of a 5-row sample against live model |
| `test_analysis_response_validation_integration.py` | `GEMINI_API_KEY`, `OPENAI_API_KEY` | Response validation against both providers (parametrized) |
| `test_rate_limiter_throughput_integration.py` | — | Rate limiter under real timing with 5000-row fixture |
| `test_tag_fix.py` | `GEMINI_API_KEY`, `OPENAI_API_KEY` | Tag deduplication via live LLM (parametrized by provider) |
| `test_attachment_ocr.py` | — | Attachment download, OCR text extraction, PDF regression |

Tests that need a missing API key will `pytest.skip()` or `pytest.fail()` with a clear message.

## API Keys

| Variable | Where to get it | Used by |
|----------|----------------|---------|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) | Most integration tests |
| `OPENAI_API_KEY` | [OpenAI Platform](https://platform.openai.com/api-keys) | `test_tag_fix.py`, `test_analysis_response_validation_integration.py` |

Set them in your shell before running integration tests:

```bash
export GEMINI_API_KEY=your-key
export OPENAI_API_KEY=your-key
```

## Test Fixtures

Test data lives in `app/tests/fixtures/`:

| Path | Purpose |
|------|---------|
| `medical_billing_comments/responses_100.csv` | 100-row sample dataset — primary E2E fixture |
| `medical_billing_comments/example_prompts/` | Example schema/analyze prompts used by the E2E flow |
| `raw/clean_10.csv` | 10-row pre-cleaned CSV for `test_analyze_first5_integration` |
| `raw/clean_5000.csv` | 5000-row CSV for rate limiter throughput tests |
| `e2e_analyze.log` | Debug log from last E2E run — **inspect before re-running E2E tests** |
| `<content-hash>/` | Auto-generated directories with cleaned data, schemas, and analysis results |

Shared fixtures are defined in `app/tests/conftest.py`:
- `override_data_dir` (autouse) — forces data directories into test fixtures
- `override_llm_model_ids` (autouse) — swaps in `gemini-2.5-flash-lite-preview-09-2025` with thinking disabled, avoiding RPM limits on expensive models
- `sample_csv_content`, `mock_schema`, `sample_data_records` — test data builders

## E2E Script

For a quick end-to-end validation outside of pytest:

```bash
uv run python scripts/run_e2e.py
```

Processes `app/tests/fixtures/medical_billing_comments/responses_100.csv` through the full pipeline (clean → schema → analyze → tag-fix) and validates all outputs.
