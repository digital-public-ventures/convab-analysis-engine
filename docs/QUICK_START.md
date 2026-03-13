# Quick Start

Get the server running locally and process your first dataset.

## Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv)
- A Gemini API key ([Google AI Studio](https://aistudio.google.com/apikey))

## Setup

```bash
git clone https://github.com/jimmoffet/sensemaking.git
cd sensemaking
uv sync --extra dev

cp .env.example .env
# Edit .env and set GEMINI_API_KEY
```

## Start the Server

```bash
uv run uvicorn app.server:app --reload
```

The server starts at `http://127.0.0.1:8000`. Interactive API docs are available at `/docs`. On first startup the OCR engine is pre-warmed (a few seconds).

## First Run

Upload the bundled 100-row fixture through the full pipeline using curl:

**1. Clean**

```bash
curl -X POST http://127.0.0.1:8000/clean \
  -F "file=@app/tests/fixtures/responses_100.csv"
```

Note the `job_id` and `hash` from the response.

**2. Poll until cleaning finishes**

```bash
curl http://127.0.0.1:8000/jobs/{job_id}
```

Wait for `"completed": true`. Always check that `"error"` is `null` — the server returns `completed: true` for both successful and failed jobs.

**3. Generate a schema**

```bash
curl -X POST http://127.0.0.1:8000/schema/{hash} \
  -H "Content-Type: application/json" \
  -d '{"use_case": "Analyze public comments on a proposed federal regulation"}'
```

**4. Run analysis**

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"hash": "{hash}", "use_case": "Analyze public comments on a proposed federal regulation", "system_prompt": "You are an expert policy analyst."}'
```

Poll the returned `job_id` the same way.

**5. Deduplicate tags**

```bash
curl -X POST http://127.0.0.1:8000/tag-fix \
  -H "Content-Type: application/json" \
  -d '{"hash": "{hash}"}'
```

Results are written to `app/data/{hash}/post-processing/analysis_deduped.csv`.

## End-to-End Check (Optional)

`scripts/run_e2e.py` automates the full pipeline (clean, schema, analyze, tag-fix) and validates outputs. With the server running:

```bash
uv run python scripts/run_e2e.py
```

It runs against `app/tests/fixtures/responses_100.csv` by default. Pass `--input-csv` to use a different file. The script takes several minutes depending on Gemini API rate limits.
