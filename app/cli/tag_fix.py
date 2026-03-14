"""Tag-fix command workflow."""

from __future__ import annotations

from typing import Any

from app.config import (
    ANALYSIS_CSV_FILENAME,
    POST_PROCESSING_SUBDIR,
    TAG_DEDUP_CSV_FILENAME,
    TAG_DEDUP_MAPPINGS_FILENAME,
)
from app.processing import DataStore, deduplicate_tags

from .shared import CLIError, require_dataset


async def run_tag_fix_command(
    *,
    content_hash: str,
    no_cache: bool = False,
    data_store: DataStore | None = None,
) -> dict[str, Any]:
    data_store = data_store or DataStore()
    require_dataset(data_store, content_hash)

    output_dir = data_store.get_hash_dir(content_hash) / POST_PROCESSING_SUBDIR
    deduped_csv = output_dir / TAG_DEDUP_CSV_FILENAME
    mappings_path = output_dir / TAG_DEDUP_MAPPINGS_FILENAME
    if deduped_csv.exists() and mappings_path.exists() and not no_cache:
        return {
            'command': 'tag-fix',
            'hash': content_hash,
            'cached': True,
            'tag_fix_csv': str(deduped_csv),
            'mappings_path': str(mappings_path),
        }

    analysis_csv = data_store.get_analyzed_csv(content_hash, ANALYSIS_CSV_FILENAME)
    if not analysis_csv:
        raise CLIError(f"Analysis CSV not found for hash '{content_hash[:12]}...'. Run analyze first.")

    schema_path = data_store.get_schema(content_hash)
    if not schema_path:
        raise CLIError(f"Schema not found for hash '{content_hash[:12]}...'. Run schema first.")

    result = await deduplicate_tags(
        schema_path=schema_path,
        analysis_csv_path=analysis_csv,
        output_dir=output_dir,
    )

    return {
        'command': 'tag-fix',
        'hash': content_hash,
        'cached': False,
        'tag_fix_csv': str(result.deduped_csv_path),
        'mappings_path': str(result.mappings_path),
    }
