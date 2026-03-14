# Sensemaking

A platform for extracting structured insights from free-text public comments, complaints, and feedback at scale. Upload a CSV of responses, and Sensemaking cleans the data, generates a tagging schema tailored to the dataset, runs LLM-powered analysis across every record, and deduplicates the resulting tags -- producing a structured, analysis-ready dataset.

## How It Works

```
CSV upload ──▶ /clean ──▶ /schema/{hash} ──▶ /analyze ──▶ /tag-fix
```

1. **Clean & OCR** -- Upload a CSV via `/clean`. Attachments (PDF, DOCX, images) are downloaded and OCR'd. Text is normalized and a cleaned CSV is written to a content-hash-addressed directory.
2. **Generate schema** -- `/schema/{hash}` samples the cleaned data and asks an LLM to produce a JSON tagging schema (categorical fields, scalars, quote arrays) fitted to the dataset's domain.
3. **Analyze** -- `/analyze` batches cleaned rows through the LLM, producing per-record structured JSON conforming to the schema.
4. **Deduplicate tags** -- `/tag-fix` uses an LLM pass to merge near-duplicate categorical labels (e.g. "Low Income" / "Low-Income Individuals") and writes a final deduplicated CSV.

All long-running steps return a job ID immediately. Poll `/jobs/{job_id}` for status and stream results from `/jobs/{job_id}/results`.

## Quick Start

Requires Python 3.13+ and [uv](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/jimmoffet/sensemaking.git
cd sensemaking
uv sync --extra dev

cp .env.example .env
# Edit .env -- at minimum set GEMINI_API_KEY

uv run uvicorn app.server:app --reload
```

The server starts at `http://127.0.0.1:8000`. Interactive docs at `/docs`.

## Architecture

```
app/
├── server.py                  # FastAPI app setup and lifespan wiring
├── config.py                  # Paths, model IDs, processing constants
├── routers/
│   ├── cleaning.py            # /clean and /data routes
│   ├── schema.py              # /schema route
│   ├── analysis.py            # /analyze and /tag-fix routes
│   └── jobs.py                # /jobs polling and cursor results
├── server_models.py           # Shared request/response models
├── server_runtime.py          # Shared in-memory stores and route helpers
├── server_jobs.py             # Background job execution helpers
├── processing/
│   ├── cleaner.py             # CSV cleaning, attachment detection
│   ├── attachment.py          # PDF/DOCX/image download + OCR extraction
│   ├── cache.py               # OCR result caching
│   ├── data_store.py          # Content-hash directory management
│   └── job_store.py           # Async job tracking with cursor-based results
├── schema/
│   ├── generator.py           # LLM-driven JSON schema creation
│   └── prompts/               # System/user prompt templates, base schema example
├── analysis/
│   ├── analyzer.py            # Batch LLM analysis pipeline
│   └── response_validation.py # Validate LLM output against schema
├── llm/
│   ├── gemini_client.py       # Gemini API wrapper
│   ├── openai_client.py       # OpenAI API wrapper
│   ├── model_config.py        # Provider-aware model configuration
│   ├── rate_limiter.py        # Async rate limiter
│   └── costs.py               # Token/cost tracking
├── dedup/
│   └── tag_dedup.py           # LLM-driven tag deduplication
└── tests/                     # Unit and integration tests
```

Datasets are stored under `app/data/{content_hash}/` with subdirectories for raw input, downloads, cleaned data, schema, analysis output, and post-processing results.

## API

All endpoints accept and return JSON unless noted.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/clean` | Upload a CSV file (multipart). Returns a job ID. Cleans text, downloads and OCR's attachments. |
| `GET` | `/jobs/{job_id}` | Poll job status. `completed` is true when the job finishes (check `error` for failures). |
| `GET` | `/jobs/{job_id}/results` | Cursor-paginated results. Pass `cursor` and `limit` query params. |
| `POST` | `/schema/{hash}` | Generate a tagging schema for the cleaned dataset. Body: `{ use_case }`. |
| `GET` | `/data/{hash}` | Check whether cleaned CSV and schema exist for a given hash. |
| `POST` | `/analyze` | Start analysis. Body: `{ hash, use_case, system_prompt }`. Returns a job ID. |
| `POST` | `/tag-fix` | Start tag deduplication. Body: `{ hash }`. Returns a job ID. |

All `POST` endpoints that create jobs accept a `?no_cache=true` query param to force reprocessing. `/clean` also accepts `?no_cache_ocr=true` to re-extract OCR.

## Development

```bash
# Code quality
ruff check .                 # Lint
ruff format .                # Format
mypy .                       # Type check

# Tests
pytest                       # Run all tests (some require API keys)
pytest -k "not integration"  # Unit tests only
```

## License

MIT
