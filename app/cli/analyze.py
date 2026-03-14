"""Analyze command workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import ANALYSIS_CSV_FILENAME, ANALYSIS_JSON_FILENAME
from app.processing import DataStore

from .shared import CLIError, load_text, require_dataset


async def run_analyze_command(
    *,
    content_hash: str,
    use_case_file: Path,
    system_prompt_file: Path,
    no_cache: bool = False,
    data_store: DataStore | None = None,
) -> dict[str, Any]:
    from app.analysis import AnalysisRequest, analyze_dataset

    data_store = data_store or DataStore()
    require_dataset(data_store, content_hash)
    use_case = load_text(use_case_file, 'Use-case file')
    system_prompt = load_text(system_prompt_file, 'System prompt file')

    existing_json = data_store.get_analyzed_json(content_hash, ANALYSIS_JSON_FILENAME)
    existing_csv = data_store.get_analyzed_csv(content_hash, ANALYSIS_CSV_FILENAME)
    if existing_json and existing_csv and not no_cache:
        return {
            'command': 'analyze',
            'hash': content_hash,
            'cached': True,
            'analysis_json': str(existing_json),
            'analysis_csv': str(existing_csv),
        }

    cleaned_csv = data_store.get_cleaned_csv(content_hash)
    if not cleaned_csv:
        raise CLIError(f"Cleaned CSV not found for hash '{content_hash[:12]}...'. Run clean first.")

    schema_path = data_store.get_schema(content_hash)
    if not schema_path:
        raise CLIError(f"Schema not found for hash '{content_hash[:12]}...'. Run schema first.")

    paths = data_store.ensure_hash_dirs(content_hash)
    await analyze_dataset(
        AnalysisRequest(
            cleaned_csv=cleaned_csv,
            schema_path=schema_path,
            output_dir=paths['analyzed'],
            use_case=use_case,
            system_prompt=system_prompt,
        )
    )

    analysis_json = paths['analyzed'] / ANALYSIS_JSON_FILENAME
    analysis_csv = paths['analyzed'] / ANALYSIS_CSV_FILENAME

    return {
        'command': 'analyze',
        'hash': content_hash,
        'cached': False,
        'analysis_json': str(analysis_json),
        'analysis_csv': str(analysis_csv),
    }
