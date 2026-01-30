"""Attachment parsing utilities."""

from __future__ import annotations


def parse_attachment_urls(attachment_string: str) -> list[str]:
    """Parse comma-separated attachment URLs.

    Args:
        attachment_string: Comma-separated string of URLs

    Returns:
        List of individual URLs
    """
    if not attachment_string or not attachment_string.strip():
        return []

    urls = [url.strip() for url in attachment_string.split(",")]
    return [url for url in urls if url]
