"""Schema command workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import SCHEMA_DEFAULT_NUM_HEAD_ROWS, SCHEMA_DEFAULT_NUM_SAMPLE_ROWS
from app.processing import DataStore
from app.schema import SchemaGenerator

from .shared import CLIError, load_text, require_dataset, sample_schema_rows


async def run_schema_command(
    *,
    content_hash: str,
    use_case_file: Path,
    sample_size: int = SCHEMA_DEFAULT_NUM_SAMPLE_ROWS,
    head_size: int = SCHEMA_DEFAULT_NUM_HEAD_ROWS,
    data_store: DataStore | None = None,
) -> dict[str, Any]:
    data_store = data_store or DataStore()
    require_dataset(data_store, content_hash)
    use_case = load_text(use_case_file, 'Use-case file')

    existing_schema = data_store.get_schema(content_hash)
    if existing_schema:
        return {
            'command': 'schema',
            'hash': content_hash,
            'cached': True,
            'schema_path': str(existing_schema),
        }

    cleaned_csv = data_store.get_cleaned_csv(content_hash)
    if not cleaned_csv:
        raise CLIError(f"Cleaned CSV not found for hash '{content_hash[:12]}...'. Run clean first.")

    sample_rows = sample_schema_rows(cleaned_csv, sample_size=sample_size, head_size=head_size)
    generator = SchemaGenerator()
    schema = await generator.generate_schema(sample_rows, use_case)
    paths = data_store.ensure_hash_dirs(content_hash)
    schema_path = generator.save_schema(
        schema=schema,
        schema_dir=paths['schema'],
        use_case=use_case,
        rows_sampled=len(sample_rows),
    )

    return {
        'command': 'schema',
        'hash': content_hash,
        'cached': False,
        'schema_path': str(schema_path),
        'rows_sampled': len(sample_rows),
    }
