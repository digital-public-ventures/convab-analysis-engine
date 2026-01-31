"""Shared pytest fixtures for app tests."""

from pathlib import Path

import pytest


@pytest.fixture  # type: ignore[misc]
def sample_csv_content() -> bytes:
    """Sample CSV content for testing."""
    return b"""id,text,category
1,Customer complaint about late delivery,complaint
2,Love the product quality,praise
3,How do I return an item?,question
"""


@pytest.fixture  # type: ignore[misc]
def mock_schema() -> dict:
    """Mock schema response for testing."""
    return {
        "schema_name": "Test Schema",
        "version": "1.0",
        "description": "Schema for testing",
        "categorical_fields": [
            {
                "field_name": "sentiment",
                "description": "Overall sentiment",
                "suggested_values": ["positive", "negative", "neutral"],
                "allow_multiple": False,
            }
        ],
        "scalar_fields": [
            {
                "field_name": "urgency",
                "description": "Urgency level",
                "scale_min": 0,
                "scale_max": 10,
                "scale_interpretation": "0=not urgent, 10=extremely urgent",
            }
        ],
        "key_quotes_fields": [
            {
                "field_name": "notable_quotes",
                "description": "Most impactful or emotionally-moving statements",
                "max_quotes": 2,
            }
        ],
    }


@pytest.fixture  # type: ignore[misc]
def sample_data_records() -> list[dict]:
    """Sample data records for schema generation tests."""
    return [
        {"id": 1, "text": "Customer complaint about shipping delay"},
        {"id": 2, "text": "Positive feedback on product quality"},
        {"id": 3, "text": "Question about return policy"},
    ]


@pytest.fixture  # type: ignore[misc]
def test_fixtures_dir() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"
