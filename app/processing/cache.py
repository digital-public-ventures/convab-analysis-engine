"""Utilities for file-based caching of downloaded attachments."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from urllib.parse import urlparse

from app.config import PDF_PAGE_CACHE_SUBDIR

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


def content_hash(content: bytes) -> str:
    """Return SHA256 hash for binary content."""
    return hashlib.sha256(content).hexdigest()


def _legacy_text_cache_path(url_or_path: str, cache_dir: Path) -> Path:
    """Generate a cache file path for extracted text."""
    text_cache_dir = cache_dir / "extracted_text"
    url_hash = hashlib.md5(url_or_path.encode()).hexdigest()
    cache_path = text_cache_dir / f"{url_hash}.txt"
    logger.debug("TEXT CACHE PATH: %s -> %s", url_or_path, cache_path)
    return cache_path


def text_cache_path_from_content_hash(content_sha256: str, cache_dir: Path) -> Path:
    """Generate text cache path from content hash."""
    text_cache_dir = cache_dir / "extracted_text"
    return text_cache_dir / f"{content_sha256}.txt"


def get_cached_text(
    url_or_path: str,
    cache_dir: Path,
    *,
    content_sha256: str | None = None,
) -> str | None:
    """Get cached extracted text if it exists.

    Args:
        url_or_path: The URL or file path to look up
        cache_dir: Base cache directory

    Returns:
        Cached extracted text, or None if not cached
    """
    if content_sha256:
        content_cache_path = text_cache_path_from_content_hash(content_sha256, cache_dir)
        content_exists = content_cache_path.exists()
        logger.debug("TEXT CACHE LOOKUP (content hash): %s exists=%s", content_cache_path, content_exists)
        if content_exists:
            text = content_cache_path.read_text(encoding="utf-8")
            logger.debug("TEXT CACHE READ (content hash): %s (%d chars)", content_cache_path, len(text))
            return text

    legacy_cache_path = _legacy_text_cache_path(url_or_path, cache_dir)
    exists = legacy_cache_path.exists()
    logger.debug("TEXT CACHE LOOKUP (legacy): %s exists=%s", legacy_cache_path, exists)
    if exists:
        text = legacy_cache_path.read_text(encoding="utf-8")
        logger.debug("TEXT CACHE READ (legacy): %s (%d chars)", legacy_cache_path, len(text))
        return text
    return None


def save_text_to_cache(
    url_or_path: str,
    text: str,
    cache_dir: Path,
    *,
    content_sha256: str | None = None,
) -> Path:
    """Save extracted text to cache.

    Args:
        url_or_path: The URL or file path being cached
        text: The extracted text to cache
        cache_dir: Base cache directory

    Returns:
        Path where the text file was saved
    """
    if content_sha256:
        cache_path = text_cache_path_from_content_hash(content_sha256, cache_dir)
    else:
        cache_path = _legacy_text_cache_path(url_or_path, cache_dir)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(text, encoding="utf-8")
    logger.debug("TEXT CACHE WRITE: %s (%d chars)", cache_path, len(text))
    return cache_path


def pdf_page_image_cache_path(
    document_sha256: str,
    page_index: int,
    dpi: int,
    cache_dir: Path,
) -> Path:
    """Generate cache path for a rendered PDF page image."""
    page_cache_dir = cache_dir / PDF_PAGE_CACHE_SUBDIR
    return page_cache_dir / f"{document_sha256}_p{page_index}_dpi{dpi}.png"


def get_cached_pdf_page_image(
    document_sha256: str,
    page_index: int,
    dpi: int,
    cache_dir: Path,
) -> bytes | None:
    """Get cached PDF page image bytes if present."""
    cache_path = pdf_page_image_cache_path(document_sha256, page_index, dpi, cache_dir)
    exists = cache_path.exists()
    logger.debug("PDF PAGE CACHE LOOKUP: %s exists=%s", cache_path, exists)
    if not exists:
        return None
    content = cache_path.read_bytes()
    logger.debug("PDF PAGE CACHE READ: %s (%d bytes)", cache_path, len(content))
    return content


def save_pdf_page_image_to_cache(
    document_sha256: str,
    page_index: int,
    dpi: int,
    image_bytes: bytes,
    cache_dir: Path,
) -> Path:
    """Save rendered PDF page image bytes to cache."""
    cache_path = pdf_page_image_cache_path(document_sha256, page_index, dpi, cache_dir)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(image_bytes)
    logger.debug("PDF PAGE CACHE WRITE: %s (%d bytes)", cache_path, len(image_bytes))
    return cache_path
