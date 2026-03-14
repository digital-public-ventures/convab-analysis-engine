# Deployment

Deployment automation is not yet productized in this repo. There are no Dockerfiles, CI/CD pipelines, infrastructure-as-code templates, or container images. What follows describes the practical requirements for running the FastAPI server as-is.

## Prerequisites

- **Python 3.13+**, managed with [uv](https://docs.astral.sh/uv/). Install dependencies with `uv sync`.
- **API keys** — at minimum, set `GEMINI_API_KEY` in your environment (or `OPENAI_API_KEY` if using the OpenAI provider). Copy `.env.example` to `.env` for the full list of recognized variables.
- **Writable data directory** — the app writes cleaned CSVs, schemas, analysis output, downloaded attachments, OCR page caches, and logs under `app/data/`. This directory must be persistent and writable by the server process.
- **Network access** — the server downloads attachments from URLs found in uploaded CSVs and makes outbound API calls to the configured LLM provider.
- **OCR models** — PaddleOCR and PaddlePaddle ship as Python dependencies. On first startup the OCR engine downloads model weights automatically. The server pre-warms the engine during its lifespan startup hook.

## Running the server

```bash
uv run uvicorn app.server:app --host 0.0.0.0 --port 8000
```

For anything beyond local use, run uvicorn behind a reverse proxy or process manager (nginx, Caddy, systemd, etc.).

- **Single worker** — background analysis jobs run as `asyncio.Task`s that are not shared across workers. A single-worker deployment is simplest.
- **Upstream timeouts** — LLM calls can take up to 120 seconds per batch. Configure proxy read timeouts accordingly.
- **Disk growth** — processed datasets accumulate under `app/data/`. Plan storage proportional to the number and size of datasets analyzed.

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | Yes (default provider) | Gemini API key |
| `OPENAI_API_KEY` | If using OpenAI | OpenAI API key |
| `LLM_PROVIDER` | No (default: `gemini`) | `gemini` or `openai` |
| `SERVER_CONSOLE_LOG_LEVEL` | No (default: `INFO`) | Console log verbosity |
| `SERVER_FILE_LOG_LEVEL` | No (default: `INFO`) | File log verbosity |
| `SERVER_LOG_FILE` | No | Override log file path |
| `UNSUPPORTED_ATTACHMENT_EXTENSIONS` | No | Comma-separated extensions to skip (e.g. `.htm,.html`) |

## What does not exist

- No container images or orchestration
- No CI/CD or deployment scripts
- No health-check endpoint
- No secrets management beyond `.env`
- No database — job state lives in memory; data lives on the filesystem
