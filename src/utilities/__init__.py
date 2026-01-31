"""Shared utilities for the project.

This package provides:
- LLM integration utilities (see utilities.llm)
- Schema generation (SchemaGenerator)
- Attachment parsing utilities
"""

from .attachment_parser import parse_attachment_urls
from .schema_generator import SchemaGenerator

__all__ = [
    "SchemaGenerator",
    "parse_attachment_urls",
]
