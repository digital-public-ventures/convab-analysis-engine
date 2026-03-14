"""Clean command workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import CLEAN_CHUNK_SIZE
from app.processing import AttachmentProcessor, DataStore, clean_csv

from .shared import require_file


async def run_clean_command(
    *,
    input_csv: Path,
    no_cache: bool = False,
    no_cache_ocr: bool = False,
    data_store: DataStore | None = None,
) -> dict[str, Any]:
    input_csv = require_file(input_csv, 'Input CSV')
    data_store = data_store or DataStore()

    content = input_csv.read_bytes()
    content_hash = data_store.hash_content(content)
    paths = data_store.ensure_hash_dirs(content_hash)
    raw_input_path = paths['root'] / 'input.csv'
    raw_input_path.write_bytes(content)

    existing_cleaned = data_store.get_cleaned_csv(content_hash)
    if existing_cleaned and not no_cache:
        return {
            'command': 'clean',
            'hash': content_hash,
            'cached': True,
            'cleaned_csv': str(existing_cleaned),
        }

    processor = AttachmentProcessor(cache_dir=paths['downloads'])
    try:
        cleaned_path = await clean_csv(
            raw_input_path,
            processor=processor,
            output_dir=paths['cleaned_data'],
            downloads_dir=paths['downloads'],
            chunk_size=CLEAN_CHUNK_SIZE,
            incremental_output=True,
            no_cache_ocr=no_cache_ocr,
        )
    finally:
        processor.close()

    return {
        'command': 'clean',
        'hash': content_hash,
        'cached': False,
        'cleaned_csv': str(cleaned_path),
    }
