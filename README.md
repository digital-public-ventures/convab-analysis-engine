# Convab

Convab transforms unstructured public comments, complaints, and feedback into structured, analysis-ready datasets. Given a CSV of free-text responses, it cleans the data, generates a tagging schema tailored to the dataset's domain, runs LLM-powered analysis across every record, and deduplicates the resulting tags.

The goal is to make large-scale qualitative feedback — the kind that usually requires weeks or months of manual coding — legible in hours or minutes.

## Background

Effectively understanding large-scale public input is a significant challenge. When a federal agency receives thousands of public comments on a proposed regulation, or a city solicits resident feedback on a long-range plan, the resulting corpus is rich but unwieldy. Traditional manual coding methods are slow and expensive, and simple keyword searches miss the nuance of what people actually said.

Convab uses LLMs to bridge this gap: it reads every comment, tags it against a schema fitted to the dataset, and surfaces structured patterns — while preserving the original voices through extracted quotes.

## Pilot: CFPB Medical Debt RFI

In 2023, the Consumer Financial Protection Bureau asked the public to share their experiences with medical payment products — specialty credit cards and installment loans used to pay uninsured costs of medical, dental, and veterinary care. The Request for Information was part of an effort to understand the effects of medical debt on American consumers.

Almost 5,000 Americans — individuals, advocates, industry groups, and government officials — responded. Reading and analyzing those responses manually took six CFPB staff members three months.

Convab's prototype analyzed a sample of these responses in minutes, producing insights actionable to policymakers:

- **Categorizing common issues and sub-issues** among respondents
- **Isolating different perspectives** from consumers, industry, and consumer advocates
- **Identifying specific products and product models** mentioned repeatedly across comments
- **Distilling policy suggestions** directly from commenter language

Throughout the analysis, Convab pulls exemplar text and quotes to show its work — grounding every category and insight in what people actually wrote.

## How It Works

```text
CSV upload ──▶ Clean ──▶ Generate Schema ──▶ Analyze ──▶ Deduplicate Tags
```

1. **Clean & OCR** — Upload a CSV. Attachments (PDF, DOCX, images) are downloaded and OCR'd. Text is normalized and a cleaned CSV is written to a content-hash-addressed directory.

2. **Generate Schema** — A sample of the cleaned data is sent to an LLM, which produces a JSON tagging schema fitted to the dataset: categorical fields, enums, scalars, quote arrays, and free-text arrays.

3. **Analyze** — Cleaned rows are batched through the LLM. Each record is tagged with structured JSON conforming to the schema. Responses are validated and retried automatically.

4. **Deduplicate Tags** — A final LLM pass merges near-duplicate categorical labels (e.g. "Low Income" / "Low-Income Individuals") and writes a deduplicated CSV.

Convab can be used through its REST API (for integration with other tools) or its CLI (for scripting and local use). Both interfaces expose the same pipeline.

## Quick Start

Requires Python 3.13+ and [uv](https://github.com/astral-sh/uv). A Gemini API key is needed for LLM calls ([Google AI Studio](https://aistudio.google.com/apikey)).

```bash
git clone https://github.com/digital-public-ventures/convab.git
cd convab
uv sync --extra dev

cp .env.example .env
# Edit .env — at minimum set GEMINI_API_KEY

uv run uvicorn app.server:app --reload
```

The server starts at `http://127.0.0.1:8000`. Interactive API docs are available at `/docs`.

See [docs/QUICK_START.md](docs/QUICK_START.md) for a walkthrough of processing your first dataset.

## CLI

The CLI runs the full pipeline without needing the server. Each command corresponds to a pipeline stage and writes results to `app/data/{hash}/`.

```bash
# 1. Clean a CSV
python -m app.cli clean --input-csv responses.csv

# 2. Generate a tagging schema
python -m app.cli schema --hash <hash> --use-case-file use_case.txt

# 3. Analyze every record
python -m app.cli analyze --hash <hash> --use-case-file use_case.txt --system-prompt-file prompt.txt

# 4. Deduplicate tags
python -m app.cli tag-fix --hash <hash>

# Inspect what artifacts exist for a dataset
python -m app.cli data-info --hash <hash>
```

All commands accept `--json` for machine-readable output. `clean`, `analyze`, and `tag-fix` accept `--no-cache` to force reprocessing.

## API

The REST API exposes the same pipeline for integration with other tools. All long-running steps return a job ID immediately — poll `/jobs/{job_id}` for status and retrieve results from `/jobs/{job_id}/results`.

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

## Architecture

```text
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
├── cli/                       # Command-line interface
│   ├── app.py                 #   Entry point and command dispatch
│   ├── parser.py              #   Argument definitions
│   ├── clean.py               #   clean command
│   ├── schema.py              #   schema command
│   ├── analyze.py             #   analyze command
│   ├── tag_fix.py             #   tag-fix command
│   └── data_info.py           #   data-info command
└── tests/
```

Datasets are stored under `app/data/{content_hash}/` with subdirectories for raw input, downloads, cleaned data, schema, analysis output, and post-processing results.

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
