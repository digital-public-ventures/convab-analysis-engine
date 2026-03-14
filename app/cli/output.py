"""Output helpers for the dataset CLI."""

from __future__ import annotations

import json
from typing import Any


def print_human_output(payload: dict[str, Any]) -> None:
    command = str(payload.get('command', '')).replace('-', '_')
    content_hash = payload.get('hash')
    if content_hash:
        print(f'{command}.hash={content_hash}')
    for key, value in payload.items():
        if key in {'command', 'hash'}:
            continue
        print(f'{command}.{key}={value}')


def print_json_output(payload: dict[str, Any]) -> None:
    print(json.dumps(payload))
