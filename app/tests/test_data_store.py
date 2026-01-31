"""Unit tests for DataStore class."""

import hashlib
from pathlib import Path

from app.processing.data_store import DataStore


class TestDataStore:
    """Tests for hash-based data storage."""

    def test_hash_content_returns_sha256(self) -> None:
        """Test that hash_content returns 64-char hex string."""
        content = b"test content"
        hash_result = DataStore.hash_content(content)

        assert len(hash_result) == 64
        assert all(c in "0123456789abcdef" for c in hash_result)

    def test_hash_content_is_deterministic(self) -> None:
        """Test same content produces same hash."""
        content = b"reproducible content"
        hash1 = DataStore.hash_content(content)
        hash2 = DataStore.hash_content(content)

        assert hash1 == hash2

    def test_different_content_different_hash(self) -> None:
        """Test different content produces different hash."""
        hash1 = DataStore.hash_content(b"content A")
        hash2 = DataStore.hash_content(b"content B")

        assert hash1 != hash2

    def test_hash_content_matches_known_value(self) -> None:
        """Test hash matches known SHA256 value."""
        # SHA256 of 'hello' is known
        content = b"hello"
        hash_result = DataStore.hash_content(content)
        expected = hashlib.sha256(content).hexdigest()

        assert hash_result == expected

    def test_ensure_hash_dirs_creates_structure(self, tmp_path: Path) -> None:
        """Test that ensure_hash_dirs creates all subdirectories."""
        store = DataStore(data_dir=tmp_path)
        test_hash = "a" * 64  # Valid 64-char hash

        paths = store.ensure_hash_dirs(test_hash)

        assert paths["root"].exists()
        assert paths["cleaned_data"].exists()
        assert paths["downloads"].exists()
        assert paths["schema"].exists()

        assert paths["root"] == tmp_path / test_hash
        assert paths["cleaned_data"] == tmp_path / test_hash / "cleaned_data"
        assert paths["downloads"] == tmp_path / test_hash / "downloads"
        assert paths["schema"] == tmp_path / test_hash / "schema"

    def test_ensure_hash_dirs_idempotent(self, tmp_path: Path) -> None:
        """Test that calling ensure_hash_dirs twice doesn't fail."""
        store = DataStore(data_dir=tmp_path)
        test_hash = "b" * 64

        paths1 = store.ensure_hash_dirs(test_hash)
        paths2 = store.ensure_hash_dirs(test_hash)

        assert paths1 == paths2
        assert all(p.exists() for p in paths1.values())

    def test_get_hash_dir(self, tmp_path: Path) -> None:
        """Test get_hash_dir returns correct path."""
        store = DataStore(data_dir=tmp_path)
        test_hash = "c" * 64

        result = store.get_hash_dir(test_hash)

        assert result == tmp_path / test_hash

    def test_get_cleaned_csv_returns_none_if_missing(self, tmp_path: Path) -> None:
        """Test get_cleaned_csv returns None for non-existent hash."""
        store = DataStore(data_dir=tmp_path)

        result = store.get_cleaned_csv("nonexistent_hash")

        assert result is None

    def test_get_cleaned_csv_returns_none_if_dir_empty(self, tmp_path: Path) -> None:
        """Test get_cleaned_csv returns None for empty cleaned_data dir."""
        store = DataStore(data_dir=tmp_path)
        test_hash = "d" * 64

        store.ensure_hash_dirs(test_hash)
        result = store.get_cleaned_csv(test_hash)

        assert result is None

    def test_get_cleaned_csv_finds_file(self, tmp_path: Path) -> None:
        """Test get_cleaned_csv finds existing cleaned CSV."""
        store = DataStore(data_dir=tmp_path)
        test_hash = "e" * 64

        # Create structure with CSV
        paths = store.ensure_hash_dirs(test_hash)
        csv_file = paths["cleaned_data"] / "cleaned_test.csv"
        csv_file.write_text("col1,col2\na,b")

        result = store.get_cleaned_csv(test_hash)

        assert result == csv_file

    def test_get_schema_returns_none_if_missing(self, tmp_path: Path) -> None:
        """Test get_schema returns None for non-existent hash."""
        store = DataStore(data_dir=tmp_path)

        result = store.get_schema("nonexistent_hash")

        assert result is None

    def test_get_schema_finds_file(self, tmp_path: Path) -> None:
        """Test get_schema finds existing schema.json."""
        store = DataStore(data_dir=tmp_path)
        test_hash = "f" * 64

        # Create structure with schema
        paths = store.ensure_hash_dirs(test_hash)
        schema_file = paths["schema"] / "schema.json"
        schema_file.write_text('{"schema_name": "test"}')

        result = store.get_schema(test_hash)

        assert result == schema_file

    def test_hash_exists_false_for_missing(self, tmp_path: Path) -> None:
        """Test hash_exists returns False for non-existent hash."""
        store = DataStore(data_dir=tmp_path)

        assert store.hash_exists("nonexistent") is False

    def test_hash_exists_true_for_existing(self, tmp_path: Path) -> None:
        """Test hash_exists returns True for existing hash dir."""
        store = DataStore(data_dir=tmp_path)
        test_hash = "g" * 64

        store.ensure_hash_dirs(test_hash)

        assert store.hash_exists(test_hash) is True
