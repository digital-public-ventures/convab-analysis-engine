"""Shared helpers for CLI workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.processing import DataStore, estimate_tokens

MAX_SCHEMA_SAMPLE_TOKENS = 50_000


class CLIError(ValueError):
    """User-facing command failure."""


def require_file(path: Path, label: str) -> Path:
    if not path.exists():
        raise CLIError(f'{label} not found: {path}')
    return path


def load_text(path: Path, label: str) -> str:
    return require_file(path, label).read_text(encoding='utf-8')


def require_dataset(data_store: DataStore, content_hash: str) -> None:
    if not data_store.hash_exists(content_hash):
        raise CLIError(f"Dataset with hash '{content_hash[:12]}...' not found. Run clean first.")


def sample_schema_rows(cleaned_csv: Path, sample_size: int, head_size: int) -> list[dict[str, Any]]:
    df = pd.read_csv(cleaned_csv)
    if df.empty:
        raise CLIError(f'Cleaned CSV is empty: {cleaned_csv}')

    head_rows = df.head(head_size).to_dict('records')
    remaining_df = df.iloc[head_size:]
    random_count = min(sample_size, len(remaining_df))
    random_rows = remaining_df.sample(n=random_count).to_dict('records') if random_count > 0 else []

    token_count = estimate_tokens(head_rows + random_rows)
    while token_count > MAX_SCHEMA_SAMPLE_TOKENS and random_rows:
        random_rows.pop()
        token_count = estimate_tokens(head_rows + random_rows)

    return head_rows + random_rows
