"""Utilities for file-based caching of downloaded attachments."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def url_to_cache_path(url: str, cache_dir: Path) -> Path:
    """Generate a cache file path for a URL.

    Uses the URL's filename if available, otherwise hashes the URL.
    Prefixes with a short hash to avoid collisions for same-named files.

    Args:
        url: The URL to cache
        cache_dir: Directory to store cached files

    Returns:
        Path where the cached file should be stored
    """
    parsed = urlparse(url)
    filename = Path(parsed.path).name

    if not filename:
        # No filename in URL, use hash of full URL
        url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
        filename = f"download_{url_hash}"
    else:
        # Prefix with short hash to avoid collisions
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        filename = f"{url_hash}_{filename}"

    cache_path = cache_dir / filename
    logger.debug("DOWNLOAD CACHE PATH: %s -> %s", url, cache_path)
    return cache_path


def get_cached_content(url: str, cache_dir: Path) -> bytes | None:
    """Get cached content for a URL if it exists.

    Args:
        url: The URL to look up
        cache_dir: Directory where cached files are stored

    Returns:
        Cached file bytes, or None if not cached
    """
    cache_path = url_to_cache_path(url, cache_dir)
    exists = cache_path.exists()
    logger.debug("DOWNLOAD CACHE LOOKUP: %s exists=%s", cache_path, exists)
    if exists:
        content = cache_path.read_bytes()
        logger.debug("DOWNLOAD CACHE READ: %s (%d bytes)", cache_path, len(content))
        return content
    return None


def save_to_cache(url: str, content: bytes, cache_dir: Path) -> Path:
    """Save content to cache.

    Args:
        url: The URL being cached
        content: The file content to cache
        cache_dir: Directory to store cached files

    Returns:
        Path where the file was saved
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = url_to_cache_path(url, cache_dir)
    cache_path.write_bytes(content)
    logger.debug("DOWNLOAD CACHE WRITE: %s (%d bytes)", cache_path, len(content))
    return cache_path


def _text_cache_path(url_or_path: str, cache_dir: Path) -> Path:
    """Generate a cache file path for extracted text."""
    text_cache_dir = cache_dir / "extracted_text"
    url_hash = hashlib.md5(url_or_path.encode()).hexdigest()
    cache_path = text_cache_dir / f"{url_hash}.txt"
    logger.debug("TEXT CACHE PATH: %s -> %s", url_or_path, cache_path)
    return cache_path


def get_cached_text(url_or_path: str, cache_dir: Path) -> str | None:
    """Get cached extracted text if it exists.

    Args:
        url_or_path: The URL or file path to look up
        cache_dir: Base cache directory

    Returns:
        Cached extracted text, or None if not cached
    """
    cache_path = _text_cache_path(url_or_path, cache_dir)
    exists = cache_path.exists()
    logger.debug("TEXT CACHE LOOKUP: %s exists=%s", cache_path, exists)
    if exists:
        text = cache_path.read_text(encoding="utf-8")
        logger.debug("TEXT CACHE READ: %s (%d chars)", cache_path, len(text))
        return text
    return None


def save_text_to_cache(url_or_path: str, text: str, cache_dir: Path) -> Path:
    """Save extracted text to cache.

    Args:
        url_or_path: The URL or file path being cached
        text: The extracted text to cache
        cache_dir: Base cache directory

    Returns:
        Path where the text file was saved
    """
    cache_path = _text_cache_path(url_or_path, cache_dir)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(text, encoding="utf-8")
    logger.debug("TEXT CACHE WRITE: %s (%d chars)", cache_path, len(text))
    return cache_path
