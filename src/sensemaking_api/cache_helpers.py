"""Utilities for best-effort file-based caching in the API."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, cast

import xxhash

if TYPE_CHECKING:
    from fastapi import Request, UploadFile

CACHE_DIR = Path("temp/cache/processed")


def best_effort_cache_key(*, request: Request, upload: UploadFile, rows: int, use_ocr: bool) -> str:
    """Build a cache key without reading upload bytes.

    Priority:
      1) X-Cache-Key header (recommended)
      2) filename + request content-length + params
    """
    client_key = request.headers.get("x-cache-key")
    if client_key:
        material = f"v1|client|{client_key}|rows={rows}|ocr={int(use_ocr)}"
        return cast("str", xxhash.xxh3_128_hexdigest(material.encode("utf-8")))

    content_length = request.headers.get("content-length", "unknown")
    filename = upload.filename or "unknown"
    material = f"v1|meta|filename={filename}|req_len={content_length}|rows={rows}|ocr={int(use_ocr)}"
    return cast("str", xxhash.xxh3_128_hexdigest(material.encode("utf-8")))


async def save_upload_to_path(upload: UploadFile, dst: Path, *, chunk_size: int = 8 * 1024 * 1024) -> None:
    """Stream upload to disk, reading bytes only on cache miss."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("wb") as handle:
        while True:
            chunk = await upload.read(chunk_size)
            if not chunk:
                break
            handle.write(chunk)

    await upload.seek(0)


def atomic_copy(src: Path, dst: Path) -> None:
    """Copy file atomically to avoid partially-written cache files."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    shutil.copyfile(src, tmp)
    tmp.replace(dst)
