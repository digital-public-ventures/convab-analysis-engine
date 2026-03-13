# Testing

All tests live under `app/tests/`. Pytest is configured in `pyproject.toml` with `testpaths = ["app/tests"]`.

## Running Tests

```bash
# All tests (includes coverage report)
pytest

# Unit tests only (skip integration tests that call live APIs)
pytest -k "not integration"

# Specific file
pytest app/tests/test_csv_processing.py

# Verbose with full tracebacks
pytest -vv --tb=long
```

Coverage reports are generated automatically (`--cov=app`) in terminal, HTML (`htmlcov/`), and XML formats.

## Test Layout

### Unit Tests (no API key required)

| File | What it tests |
|------|---------------|
| `test_csv_processing.py` | CSV cleaning logic and text normalization |
| `test_data_store.py` | Content-hash directory management |
| `test_costs.py` | Token cost tracking |
| `test_response_parser.py` | LLM response JSON parsing |
| `test_analysis_response_validation.py` | Schema validation of analysis output |
| `test_model_provider_resolution.py` | LLM provider selection logic |
| `test_rate_limiter_concurrency.py` | Async rate limiter correctness |
| `test_cli.py` | CLI module |
| `test_analyzer_callbacks.py` | Analysis callback hooks |

### Integration Tests (require API keys or live model access)

| File | What it tests |
|------|---------------|
| `test_e2e_integration.py` | Full pipeline: clean → schema → analyze |
| `test_job_handling_integration.py` | Async job creation, polling, and results |
| `test_schema_generation.py` | Schema generation via live LLM call |
| `test_analyze_first5_integration.py` | Analysis of a 5-row sample |
| `test_gemini_client_validation.py` | Gemini API client against live API |
| `test_openai_client_validation.py` | OpenAI API client against live API |
| `test_analysis_response_validation_integration.py` | End-to-end response validation |
| `test_rate_limiter_throughput_integration.py` | Rate limiter under real timing |
| `test_attachment_ocr.py` | Attachment download and OCR extraction |
| `test_pdf_mixed_ocr.py` | PDF pages with mixed text/image content |
| `test_tag_fix.py` | Tag deduplication via live LLM call |

Integration tests are marked with `@pytest.mark.integration`. To run only integration tests:

```bash
pytest -m integration
```

## Test Fixtures

Test data lives in `app/tests/fixtures/`:

- `responses_100.csv` — 100-row sample dataset used by E2E tests and `scripts/run_e2e.py`
- `example_prompts/` — system and user prompts for integration tests
- `e2e_analyze.log` — debug log from the last E2E run (inspect this before re-running E2E tests to diagnose failures)

Shared fixtures are defined in `app/tests/conftest.py`, including sample CSV content, mock schemas, and a flash-model monkeypatch for E2E tests that overrides the default model to avoid RPM limits.

## E2E Script

For a quick end-to-end validation outside of pytest:

```bash
uv run python scripts/run_e2e.py
```

This processes `app/tests/fixtures/responses_100.csv` through the full pipeline and validates all outputs.
