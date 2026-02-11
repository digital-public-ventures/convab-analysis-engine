"""LLM-driven tag deduplication for categorical analysis fields."""

from __future__ import annotations

import asyncio
import csv
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from app.config import ANALYSIS_MODEL_ID, ANALYSIS_THINKING_LEVEL, TOKEN_USAGE_FILE
from app.llm import generate_structured_content, validate_model_config
from app.llm.provider import create_llm_client, resolve_api_key
from app.llm.rate_limiter import AsyncRateLimiter

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a data normalization assistant. Deduplicate categorical labels by fixing typos and minor variations.
Return mappings that are conservative: only merge labels that are clearly the same concept.
"""  # noqa: E501

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "field_name": {"type": "STRING"},
        "canonical_labels": {"type": "ARRAY", "items": {"type": "STRING"}},
        "mappings": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "old_label": {"type": "STRING"},
                    "new_label": {"type": "STRING"},
                },
                "required": ["old_label", "new_label"],
            },
        },
    },
    "required": ["field_name", "canonical_labels", "mappings"],
}


@dataclass(frozen=True)
class FieldMapping:
    field_name: str
    canonical_labels: list[str]
    mapping: dict[str, str]


@dataclass(frozen=True)
class TagFixOutput:
    mappings_path: Path
    deduped_csv_path: Path


def _load_schema_fields(schema_path: Path) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    categorical_fields = schema.get("categorical_fields", [])
    field_names: list[str] = []
    for field in categorical_fields:
        name = str(field.get("field_name", "")).strip()
        if name:
            field_names.append(name)
    return field_names


def _collect_labels(csv_path: Path, categorical_fields: list[str]) -> dict[str, list[str]]:
    labels_by_field: dict[str, set[str]] = {field: set() for field in categorical_fields}
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            for field in categorical_fields:
                value = row.get(field, "")
                if value is None:
                    continue
                for token in str(value).split(";"):
                    label = token.strip()
                    if label:
                        labels_by_field[field].add(label)
    return {field: sorted(labels) for field, labels in labels_by_field.items()}


def _build_prompt(field_name: str, labels: list[str]) -> str:
    label_block = "\n".join(f"- {label}" for label in labels)
    return "\n".join(
        [
            f"Field: {field_name}",
            "Labels:",
            label_block,
            "",
            "Return JSON with canonical_labels and mappings.",
            "- canonical_labels should be the deduped list.",
            "- mappings must include every old_label in the input, mapped to a canonical new_label.",
            "- If no change is needed, map the label to itself.",
        ]
    )


async def _dedupe_field(
    client: object,
    limiter: AsyncRateLimiter,
    field_name: str,
    labels: list[str],
    model_id: str,
    thinking_level: str,
    token_usage_file: Path,
) -> FieldMapping:
    prompt_text = _build_prompt(field_name, labels)
    response_data, _ = await generate_structured_content(
        client=client,
        prompt_text=prompt_text,
        model_id=model_id,
        json_schema=RESPONSE_SCHEMA,
        system_instruction=SYSTEM_PROMPT,
        thinking_level=thinking_level,
        token_usage_file=str(token_usage_file),
        rate_limiter=limiter,
        batch_size=1,
    )
    if not response_data:
        raise ValueError(f"No response for field {field_name}")

    canonical = [str(label).strip() for label in response_data.get("canonical_labels", []) if str(label).strip()]
    mapping: dict[str, str] = {}
    for item in response_data.get("mappings", []) or []:
        old_label = str(item.get("old_label", "")).strip()
        new_label = str(item.get("new_label", "")).strip()
        if old_label and new_label:
            mapping[old_label] = new_label

    missing = [label for label in labels if label not in mapping]
    if missing:
        logger.warning("Missing mappings for %s: %s", field_name, missing)
        for label in missing:
            mapping[label] = label

    if not canonical:
        canonical = sorted({mapping[label] for label in labels})

    return FieldMapping(field_name=field_name, canonical_labels=canonical, mapping=mapping)


def _apply_mapping(
    csv_path: Path,
    output_path: Path,
    mappings: dict[str, dict[str, str]],
    categorical_fields: list[str],
) -> None:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    for row in rows:
        for field in categorical_fields:
            value = row.get(field)
            if value is None:
                continue
            labels = [token.strip() for token in str(value).split(";") if token.strip()]
            mapped = [mappings[field].get(label, label) for label in labels]
            deduped: list[str] = []
            seen: set[str] = set()
            for label in mapped:
                if label not in seen:
                    deduped.append(label)
                    seen.add(label)
            row[field] = "; ".join(deduped)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_mappings(mappings_path: Path, mappings: dict[str, dict[str, str]]) -> None:
    mappings_path.parent.mkdir(parents=True, exist_ok=True)
    mappings_path.write_text(json.dumps(mappings, indent=2), encoding="utf-8")

async def run_tag_fix(
    *,
    schema_path: Path,
    analysis_csv_path: Path,
    output_dir: Path,
    model_id: str = ANALYSIS_MODEL_ID,
    thinking_level: str = ANALYSIS_THINKING_LEVEL,
    token_usage_file: Path = TOKEN_USAGE_FILE,
    api_key: str | None = None,
) -> TagFixOutput:
    categorical_fields = _load_schema_fields(schema_path)
    if not categorical_fields:
        raise ValueError("No categorical fields found in schema.")

    labels_by_field = _collect_labels(analysis_csv_path, categorical_fields)

    profile = validate_model_config(model_id, thinking_level)
    client = create_llm_client(
        api_key=resolve_api_key(
            api_key=api_key,
            provider=profile.provider,
            model_id_or_key=profile.model_id,
        ),
        provider=profile.provider,
        model_id_or_key=profile.model_id,
    )
    limiter = AsyncRateLimiter(profile.rpm, profile.tpm, profile.rpd, max_concurrency=profile.max_concurrency)

    tasks = [
        _dedupe_field(
            client=client,
            limiter=limiter,
            field_name=field_name,
            labels=labels_by_field[field_name],
            model_id=profile.model_id,
            thinking_level=thinking_level,
            token_usage_file=token_usage_file,
        )
        for field_name in categorical_fields
    ]

    results = await asyncio.gather(*tasks)
    mappings = {result.field_name: result.mapping for result in results}

    output_dir.mkdir(parents=True, exist_ok=True)
    mappings_path = output_dir / "mappings.json"
    deduped_csv_path = output_dir / "analysis_deduped.csv"

    _write_mappings(mappings_path, mappings)
    _apply_mapping(analysis_csv_path, deduped_csv_path, mappings, categorical_fields)

    return TagFixOutput(mappings_path=mappings_path, deduped_csv_path=deduped_csv_path)
