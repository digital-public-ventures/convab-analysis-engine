"""Data-info command workflow."""

from __future__ import annotations

from typing import Any

from app.processing import DataStore

from .shared import require_dataset


def build_data_info_payload(*, content_hash: str, data_store: DataStore | None = None) -> dict[str, Any]:
    data_store = data_store or DataStore()
    require_dataset(data_store, content_hash)
    cleaned_csv = data_store.get_cleaned_csv(content_hash)
    schema_path = data_store.get_schema(content_hash)

    return {
        'command': 'data-info',
        'hash': content_hash,
        'has_cleaned_csv': cleaned_csv is not None,
        'cleaned_file': cleaned_csv.name if cleaned_csv else None,
        'has_schema': schema_path is not None,
    }
