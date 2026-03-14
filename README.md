# Convab

Convab transforms unstructured public comments, complaints, and feedback into structured, analysis-ready datasets. Given a CSV of free-text responses, it cleans the data, generates a tagging schema tailored to the dataset's domain, runs LLM-powered analysis across every record, and deduplicates the resulting tags.

The goal is to make large-scale qualitative feedback — the kind that usually requires weeks or months of manual coding — legible in hours or minutes.

## How It Works

```text
CSV upload ──▶ Clean ──▶ Generate Schema ──▶ Analyze ──▶ Deduplicate Tags
```

1. **Clean & OCR** — Upload a CSV. Attachments (PDF, DOCX, images) are downloaded and OCR'd. Text is normalized and a cleaned CSV is written to a content-hash-addressed directory.

2. **Generate Schema** — A sample of the cleaned data is sent to an LLM, which produces a JSON tagging schema fitted to the dataset: categorical fields, enums, scalars, quote arrays, and free-text arrays.

3. **Analyze** — Cleaned rows are batched through the LLM. Each record is tagged with structured JSON conforming to the schema. Responses are validated and retried automatically.

4. **Deduplicate Tags** — A final LLM pass merges near-duplicate categorical labels (e.g. "Low Income" / "Low-Income Individuals") and writes a deduplicated CSV.

All long-running steps return a job ID immediately. Poll `/jobs/{job_id}` for status and retrieve results from `/jobs/{job_id}/results`.

## Quick Start

Requires Python 3.13+ and [uv](https://github.com/astral-sh/uv). A Gemini API key is needed for LLM calls ([Google AI Studio](https://aistudio.google.com/apikey)).

```bash
git clone https://github.com/jimmoffet/sensemaking.git
cd sensemaking
uv sync --extra dev

cp .env.example .env
# Edit .env — at minimum set GEMINI_API_KEY

uv run uvicorn app.server:app --reload
```

The server starts at `http://127.0.0.1:8000`. Interactive API docs are available at `/docs`.

See [docs/QUICK_START.md](docs/QUICK_START.md) for a walkthrough of processing your first dataset.

## Architecture

```
app/
├── server.py                  # FastAPI app, lifespan wiring
├── config.py                  # Paths, model IDs, processing constants
├── routers/                   # HTTP layer
│   ├── cleaning.py            #   /clean and /data
│   ├── schema.py              #   /schema
│   ├── analysis.py            #   /analyze and /tag-fix
│   └── jobs.py                #   /jobs polling and cursor results
├── prompts/                   # LLM interaction contracts
│   ├── schema_generation/     #   Schema generation prompts and response schema
│   ├── analysis/              #   Analysis prompts and templates
│   ├── response_schema.py     #   Builds structured output schema for analysis
│   └── response_validation.py #   Validates LLM output against schema
├── schema/
│   └── generator.py           # Schema generation orchestration
├── analysis/
│   └── analyzer.py            # Batch analysis pipeline
├── processing/                # Data ingestion
│   ├── cleaner.py             #   CSV cleaning, attachment detection
│   ├── attachment.py          #   PDF/DOCX/image download + OCR
│   ├── cache.py               #   OCR result caching
│   ├── data_store.py          #   Content-hash directory management
│   └── job_store.py           #   Async job tracking
├── llm/                       # LLM provider abstraction
│   ├── gemini_client.py       #   Gemini API wrapper
│   ├── openai_client.py       #   OpenAI API wrapper
│   ├── model_config.py        #   Provider-aware model configuration
│   ├── rate_limiter.py        #   Async rate limiter
│   └── costs.py               #   Token/cost tracking
├── dedup/
│   └── tag_dedup.py           # LLM-driven tag deduplication
└── tests/
```

Datasets are stored under `app/data/{content_hash}/` with subdirectories for raw input, downloads, cleaned data, schema, analysis output, and post-processing results.

## API

All endpoints accept and return JSON unless noted.

| Method | Path                     | Description                                                                                    |
| ------ | ------------------------ | ---------------------------------------------------------------------------------------------- |
| `POST` | `/clean`                 | Upload a CSV file (multipart). Cleans text, downloads and OCR's attachments. Returns a job ID. |
| `POST` | `/schema/{hash}`         | Generate a tagging schema for the cleaned dataset. Body: `{ use_case }`.                       |
| `POST` | `/analyze`               | Start analysis. Body: `{ hash, use_case, system_prompt }`. Returns a job ID.                   |
| `POST` | `/tag-fix`               | Start tag deduplication. Body: `{ hash }`. Returns a job ID.                                   |
| `GET`  | `/jobs/{job_id}`         | Poll job status. `completed` is true when the job finishes (check `error` for failures).       |
| `GET`  | `/jobs/{job_id}/results` | Cursor-paginated results. Pass `cursor` and `limit` query params.                              |
| `GET`  | `/data/{hash}`           | Check whether cleaned data and schema exist for a given hash.                                  |

All `POST` endpoints that create jobs accept `?no_cache=true` to force reprocessing. `/clean` also accepts `?no_cache_ocr=true` to re-extract OCR.

## Development

```bash
ruff check .                 # Lint
ruff format .                # Format
mypy .                       # Type check

pytest                       # All tests (some require API keys)
pytest -k "not integration"  # Unit tests only
```

See [docs/TESTING.md](docs/TESTING.md) for test layout, fixtures, and API key requirements.

## License

MIT
