"""Pytest configuration and fixtures."""
import pytest


@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return {
        "name": "test",
        "value": 42,
        "items": [1, 2, 3],
    }


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file for testing."""
    file = tmp_path / "test.txt"
    file.write_text("test content")
    return file
