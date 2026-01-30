"""Analyzer flow for regulations.gov public comments."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from dotenv import load_dotenv
from google import genai

from ..utilities.llm.gemini_client import generate_structured_content, validate_model_config
from ..utilities.llm.rate_limiter import AsyncRateLimiter
from .attachment_processor import AttachmentProcessor, combine_narratives
from .data_processor import DataProcessor, ResponseRecord

load_dotenv()

OUTPUT_DIR = "src/regs_dot_gov_exploration/output"
TEMP_DIR = "temp/output"
TOKEN_USAGE_FILE = "temp/token_usage.jsonl"  # noqa: S105
SCHEMA_INDEX = "src/regs_dot_gov_exploration/schemas/index.csv"


def get_use_head() -> bool:
    """Return USE_HEAD value, defaulting to true when unset."""
    return os.getenv("USE_HEAD", "true").lower() in ("true", "1", "yes")


def get_latest_schema_path(index_path: Path) -> Path:
    """Return the latest schema path from the schema index."""
    if not index_path.exists():
        raise FileNotFoundError(f"Schema index not found: {index_path}")

    with index_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise FileNotFoundError("Schema index is empty; generate a schema first.")

    latest = rows[-1]["filename"]
    return index_path.parent / latest


def load_schema(schema_path: Path) -> dict[str, Any]:
    """Load schema JSON from disk."""
    with schema_path.open(encoding="utf-8") as f:
        return cast("dict[str, Any]", json.load(f))


def build_response_schema(schema_definition: dict[str, Any]) -> dict[str, Any]:
    """Build a response schema for analysis from the schema definition."""
    categorical_fields = schema_definition.get("categorical_fields", [])
    scalar_fields = schema_definition.get("scalar_fields", [])

    categorical_props: dict[str, Any] = {}
    for field in categorical_fields:
        field_name = field.get("field_name")
        if not field_name:
            continue
        if field.get("allow_multiple", False):
            categorical_props[field_name] = {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            }
        else:
            categorical_props[field_name] = {"type": "STRING"}

    scalar_props: dict[str, Any] = {}
    for field in scalar_fields:
        field_name = field.get("field_name")
        if not field_name:
            continue
        scalar_props[field_name] = {"type": "NUMBER"}

    return {
        "type": "OBJECT",
        "properties": {
            "analyzed_comments": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "id": {"type": "STRING"},
                        "categorical_fields": {
                            "type": "OBJECT",
                            "properties": categorical_props,
                        },
                        "scalar_fields": {
                            "type": "OBJECT",
                            "properties": scalar_props,
                        },
                    },
                    "required": ["id", "categorical_fields", "scalar_fields"],
                },
            }
        },
    }


def load_system_prompt() -> str:
    """Load the system prompt from the prompts directory."""
    system_prompt_path = Path(__file__).parent / "prompts" / "system_prompt.txt"
    with system_prompt_path.open(encoding="utf-8") as f:
        return f.read().strip()


def load_user_prompt_template() -> str:
    """Load the user prompt template from the prompts directory."""
    user_prompt_path = Path(__file__).parent / "prompts" / "user_prompt_template.txt"
    with user_prompt_path.open(encoding="utf-8") as f:
        return f.read().strip()


def format_record_text(record: ResponseRecord, narrative: str) -> str:
    """Format a single record for prompt inclusion."""
    metadata_json = json.dumps(record.metadata, ensure_ascii=False)
    return f"Record ID: {record.id}\nNarrative: {narrative}\nMetadata: {metadata_json}\n"


def build_prompt(records: list[ResponseRecord], narratives: list[str]) -> str:
    """Build the full prompt text for a batch of records."""
    template = load_user_prompt_template()
    record_blocks = [format_record_text(record, narrative) for record, narrative in zip(records, narratives)]
    data_block = "\n---\n".join(record_blocks)
    return f"{template}\n{data_block}\n```"


def filter_records_with_narratives(
    records: list[ResponseRecord],
    narratives: list[str],
) -> tuple[list[ResponseRecord], list[str], int]:
    """Filter out records with empty narratives.

    Returns filtered records, filtered narratives, and count skipped.
    """
    filtered_records: list[ResponseRecord] = []
    filtered_narratives: list[str] = []
    skipped = 0

    for record, narrative in zip(records, narratives):
        if narrative and narrative.strip():
            filtered_records.append(record)
            filtered_narratives.append(narrative)
        else:
            skipped += 1

    return filtered_records, filtered_narratives, skipped


def flatten_analysis_row(
    analysis: dict[str, Any],
    categorical_fields: list[str],
    scalar_fields: list[str],
) -> dict[str, Any]:
    """Flatten analysis output for CSV export."""
    row: dict[str, Any] = {"id": analysis.get("id", "")}
    categorical_values = analysis.get("categorical_fields", {}) or {}
    scalar_values = analysis.get("scalar_fields", {}) or {}

    for field in categorical_fields:
        value = categorical_values.get(field)
        if isinstance(value, list):
            row[field] = "|".join(str(item) for item in value)
        else:
            row[field] = value

    for field in scalar_fields:
        row[field] = scalar_values.get(field)

    return row


async def analyze_batch(
    client: genai.Client,
    limiter: AsyncRateLimiter,
    system_prompt: str,
    response_schema: dict[str, Any],
    model_id: str,
    thinking_level: str,
    records: list[ResponseRecord],
    narratives: list[str],
) -> list[dict[str, Any]]:
    """Analyze a batch of records."""
    prompt_text = build_prompt(records, narratives)
    response_data, _ = await generate_structured_content(
        client=client,
        prompt_text=prompt_text,
        model_id=model_id,
        json_schema=response_schema,
        system_instruction=system_prompt,
        thinking_level=thinking_level,
        token_usage_file=TOKEN_USAGE_FILE,
        rate_limiter=limiter,
        batch_size=len(records),
    )

    if not response_data:
        return []

    analyzed = response_data.get("analyzed_comments", [])
    return cast(list[dict[str, Any]], analyzed)


async def run_analysis(args: argparse.Namespace) -> None:
    """Run the regs.gov analysis flow."""
    use_head = get_use_head()
    print(f'USE_HEAD={use_head} (using {"sample" if use_head else "full"} data)')

    processor = DataProcessor(args.csv_path if args.csv_path else None)
    if args.csv_path and use_head:
        print("Warning: USE_HEAD is true but --csv-path was provided.")

    if args.include_attachments:
        records = processor.get_records_with_attachments(n_rows=args.rows)
        if not records:
            print("No records with attachments found; falling back to narrative-only records.")
            records = processor.get_narrative_only_records(n_rows=args.rows)
    else:
        records = processor.get_narrative_only_records(n_rows=args.rows)

    if not records:
        print("No records loaded. Check your CSV file.")
        return

    schema_path = Path(args.schema_path) if args.schema_path else get_latest_schema_path(Path(SCHEMA_INDEX))
    schema_definition = load_schema(schema_path)
    response_schema = build_response_schema(schema_definition)

    categorical_fields = [
        field.get("field_name") for field in schema_definition.get("categorical_fields", []) if field.get("field_name")
    ]
    scalar_fields = [
        field.get("field_name") for field in schema_definition.get("scalar_fields", []) if field.get("field_name")
    ]

    profile = validate_model_config(args.model_key, args.thinking_level)
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
    limiter = AsyncRateLimiter(profile.rpm, profile.tpm, profile.rpd)

    system_prompt = load_system_prompt()

    narratives: list[str] = []
    if args.include_attachments:
        attachment_processor = AttachmentProcessor(timeout=args.attachment_timeout)
        for record in records:
            attachment_texts = attachment_processor.process_attachments(
                record.attachment_urls,
                skip_errors=True,
                use_ocr=args.use_ocr,
            )
            combined = combine_narratives(record.narrative, attachment_texts)
            narratives.append(combined if combined else record.narrative)
    else:
        narratives = [record.narrative for record in records]

    records, narratives, skipped = filter_records_with_narratives(records, narratives)
    if skipped:
        print(
            "Warning: Skipped records with empty narratives. " "Use --include-attachments to include attachment text."
        )
    if not records:
        print("No records with usable narrative content. Try --include-attachments.")
        return

    batch_size = args.batch_size
    batches = [records[i : i + batch_size] for i in range(0, len(records), batch_size)]
    narrative_batches = [narratives[i : i + batch_size] for i in range(0, len(narratives), batch_size)]

    if args.max_batches is not None:
        batches = batches[: args.max_batches]
        narrative_batches = narrative_batches[: args.max_batches]

    tasks = [
        analyze_batch(
            client,
            limiter,
            system_prompt,
            response_schema,
            profile.model_id,
            args.thinking_level,
            batch,
            narrative_batch,
        )
        for batch, narrative_batch in zip(batches, narrative_batches)
    ]

    start_time = time.time()
    results = await asyncio.gather(*tasks)
    analyzed_comments = [item for batch in results for item in batch]

    output_dir = Path(args.output_dir) if args.output_dir else Path(OUTPUT_DIR)
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    output_run_dir = output_dir / timestamp
    output_run_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_run_dir / f"{args.model_key}_{args.thinking_level}_{timestamp}.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(analyzed_comments, f, indent=2)

    csv_path = output_run_dir / f"{args.model_key}_{args.thinking_level}_{timestamp}.csv"
    csv_fields = ["id", *categorical_fields, *scalar_fields]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for analysis in analyzed_comments:
            writer.writerow(flatten_analysis_row(analysis, categorical_fields, scalar_fields))

    elapsed = time.time() - start_time
    print(f"Saved {len(analyzed_comments)} analyses in {elapsed:.2f}s to {output_run_dir}")


async def analyze_command(args: argparse.Namespace) -> None:
    """CLI entry point for analyze subcommand."""
    try:
        await run_analysis(args)
    except FileNotFoundError as err:
        print(f"Error: {err}")
    except Exception as err:  # pragma: no cover - surfaced in CLI
        print(f"Error: {err}")
        raise
