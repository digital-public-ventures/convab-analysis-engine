"""Unit tests for schema generation with mocked Gemini calls."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestSchemaGenerator:
    """Unit tests for SchemaGenerator class."""

    @pytest.mark.asyncio
    async def test_generate_schema_constructs_correct_prompt(
        self, sample_data_records: list[dict], mock_schema: dict
    ) -> None:
        """Test that generate_schema builds correct Gemini request."""
        with patch("app.schema.generator.generate_structured_content") as mock_gen:
            mock_gen.return_value = (mock_schema, {"total_tokens": 100}, MagicMock())

            # Mock the genai.Client
            with patch("app.schema.generator.genai.Client"):
                from app.schema import SchemaGenerator

                generator = SchemaGenerator(api_key="test-key")
                await generator.generate_schema(
                    sample_data=sample_data_records,
                    use_case="Analyze customer feedback",
                )

                # Verify generate_structured_content was called
                mock_gen.assert_called_once()
                call_kwargs = mock_gen.call_args.kwargs

                # Verify prompt contains sample data
                assert "customer feedback" in call_kwargs["prompt_text"].lower()
                assert "shipping delay" in call_kwargs["prompt_text"]

                # Verify JSON schema is passed
                assert call_kwargs["json_schema"] is not None
                assert "categorical_fields" in str(call_kwargs["json_schema"])

    @pytest.mark.asyncio
    async def test_generate_schema_returns_valid_structure(
        self, sample_data_records: list[dict], mock_schema: dict
    ) -> None:
        """Test that returned schema has expected structure."""
        with patch("app.schema.generator.generate_structured_content") as mock_gen:
            mock_gen.return_value = (mock_schema, {"total_tokens": 100}, MagicMock())

            with patch("app.schema.generator.genai.Client"):
                from app.schema import SchemaGenerator

                generator = SchemaGenerator(api_key="test-key")
                schema = await generator.generate_schema(
                    sample_data=sample_data_records,
                    use_case="Test use case for analysis",
                )

                assert "schema_name" in schema
                assert "categorical_fields" in schema
                assert "scalar_fields" in schema
                assert "key_quotes_fields" in schema
                assert isinstance(schema["categorical_fields"], list)
                assert isinstance(schema["scalar_fields"], list)
                assert isinstance(schema["key_quotes_fields"], list)
                for field in schema["categorical_fields"]:
                    assert field.get("required") is True
                for field in schema["scalar_fields"]:
                    assert field.get("required") is True
                for field in schema["key_quotes_fields"]:
                    assert field.get("required") is True

    @pytest.mark.asyncio
    async def test_generate_schema_raises_on_empty_response(self, sample_data_records: list[dict]) -> None:
        """Test that ValueError is raised when API returns empty response."""
        with patch("app.schema.generator.generate_structured_content") as mock_gen:
            mock_gen.return_value = (None, None, None)

            with patch("app.schema.generator.genai.Client"):
                from app.schema import SchemaGenerator

                generator = SchemaGenerator(api_key="test-key")

                with pytest.raises(ValueError, match="No schema generated"):
                    await generator.generate_schema(
                        sample_data=sample_data_records,
                        use_case="Test use case",
                    )

    def test_save_schema_creates_file(self, tmp_path: Path, mock_schema: dict) -> None:
        """Test that save_schema creates schema.json file."""
        with patch("app.schema.generator.genai.Client"):
            from app.schema import SchemaGenerator

            generator = SchemaGenerator(api_key="test-key")
            schema_dir = tmp_path / "schema"
            schema_dir.mkdir()

            result = generator.save_schema(
                schema=mock_schema,
                schema_dir=schema_dir,
                use_case="Test use case",
                rows_sampled=10,
            )

            assert result.exists()
            assert result.name == "schema.json"

            with result.open() as f:
                saved = json.load(f)

            assert saved["schema_name"] == "Test Schema"
            assert "_metadata" in saved
            assert saved["_metadata"]["rows_sampled"] == 10

    def test_save_schema_includes_metadata(self, tmp_path: Path, mock_schema: dict) -> None:
        """Test that saved schema includes metadata."""
        with patch("app.schema.generator.genai.Client"):
            from app.schema import SchemaGenerator

            generator = SchemaGenerator(api_key="test-key")
            schema_dir = tmp_path / "schema"
            schema_dir.mkdir()

            result = generator.save_schema(
                schema=mock_schema,
                schema_dir=schema_dir,
                use_case="Analyze sentiment patterns in reviews",
                rows_sampled=15,
            )

            with result.open() as f:
                saved = json.load(f)

            metadata = saved["_metadata"]
            assert "generated_at" in metadata
            assert metadata["model_id"] == "gemini-3-flash-preview"
            assert metadata["thinking_level"] == "MINIMAL"
            assert metadata["rows_sampled"] == 15
            assert "sentiment" in metadata["use_case"].lower()

    @pytest.mark.asyncio
    async def test_generate_schema_propagates_exception(self, sample_data_records: list[dict]) -> None:
        """Test that exceptions from API calls are properly propagated."""
        with patch("app.schema.generator.generate_structured_content") as mock_gen:
            mock_gen.side_effect = RuntimeError("API rate limit exceeded")

            with patch("app.schema.generator.genai.Client"):
                from app.schema import SchemaGenerator

                generator = SchemaGenerator(api_key="test-key")

                with pytest.raises(RuntimeError, match="rate limit"):
                    await generator.generate_schema(
                        sample_data=sample_data_records,
                        use_case="Test use case",
                    )

    def test_missing_api_key_raises_error(self) -> None:
        """Test that ValueError is raised when API key is missing."""
        with patch("app.schema.generator.genai.Client"), patch.dict("os.environ", {}, clear=True):
            from app.schema import SchemaGenerator

            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                SchemaGenerator()

    def test_flash_model_uses_higher_rate_limits(self) -> None:
        """Test that flash models get higher rate limits."""
        with patch("app.schema.generator.genai.Client"):
            from app.schema import SchemaGenerator

            generator = SchemaGenerator(api_key="test-key", model_id="gemini-3-flash-preview")
            assert generator.rate_limiter.rpm_limit == 1000

    def test_pro_model_uses_lower_rate_limits(self) -> None:
        """Test that pro models get lower rate limits."""
        with patch("app.schema.generator.genai.Client"):
            from app.schema import SchemaGenerator

            generator = SchemaGenerator(api_key="test-key", model_id="gemini-pro")
            assert generator.rate_limiter.rpm_limit == 25

    def test_save_schema_truncates_long_use_case(self, tmp_path: Path, mock_schema: dict) -> None:
        """Test that very long use cases are truncated in metadata."""
        with patch("app.schema.generator.genai.Client"):
            from app.schema import SchemaGenerator

            generator = SchemaGenerator(api_key="test-key")
            schema_dir = tmp_path / "schema"
            schema_dir.mkdir()

            long_use_case = "x" * 1000
            result = generator.save_schema(
                schema=mock_schema,
                schema_dir=schema_dir,
                use_case=long_use_case,
                rows_sampled=5,
            )

            with result.open() as f:
                saved = json.load(f)

            # Use case should be truncated to 500 chars
            assert len(saved["_metadata"]["use_case"]) == 500


class TestPromptConstruction:
    """Tests for prompt building functions."""

    def test_build_schema_generation_prompt_includes_use_case(self) -> None:
        """Test that use_case is included in prompt."""
        from app.schema.prompts import build_schema_generation_prompt

        prompt = build_schema_generation_prompt(
            sample_data=[{"text": "sample"}],
            use_case="Identify themes in customer reviews",
        )

        assert "Identify themes in customer reviews" in prompt
        assert "sample" in prompt

    def test_build_schema_generation_prompt_includes_record_count(self) -> None:
        """Test that record count is included in prompt."""
        from app.schema.prompts import build_schema_generation_prompt

        sample_data = [{"id": i, "text": f"record {i}"} for i in range(5)]
        prompt = build_schema_generation_prompt(
            sample_data=sample_data,
            use_case="Test",
        )

        assert "5 records" in prompt

    def test_build_schema_generation_prompt_formats_records(self) -> None:
        """Test that records are formatted in prompt."""
        from app.schema.prompts import build_schema_generation_prompt

        sample_data = [
            {"id": 1, "text": "First record"},
            {"id": 2, "text": "Second record"},
        ]
        prompt = build_schema_generation_prompt(
            sample_data=sample_data,
            use_case="Test",
        )

        assert "Record 1:" in prompt
        assert "Record 2:" in prompt
        assert "First record" in prompt
        assert "Second record" in prompt

    def test_build_schema_generation_prompt_truncates_large_records(self) -> None:
        """Test that large records are truncated."""
        from app.schema.prompts import build_schema_generation_prompt

        large_text = "x" * 2000
        prompt = build_schema_generation_prompt(
            sample_data=[{"text": large_text}],
            use_case="Test",
        )

        # Should be truncated to ~1000 chars + overhead
        assert len(prompt) < 2000 + 500
        assert "..." in prompt

    def test_response_schema_has_required_fields(self) -> None:
        """Test that response schema defines required fields."""
        from app.schema.prompts import SCHEMA_GENERATION_RESPONSE_SCHEMA

        assert "properties" in SCHEMA_GENERATION_RESPONSE_SCHEMA
        assert "required" in SCHEMA_GENERATION_RESPONSE_SCHEMA

        required = SCHEMA_GENERATION_RESPONSE_SCHEMA["required"]
        assert "schema_name" in required
        assert "categorical_fields" in required
        assert "scalar_fields" in required
        assert "key_quotes_fields" in required

    def test_system_prompt_loaded(self) -> None:
        """Test that system prompt is loaded."""
        from app.schema.prompts import SCHEMA_GENERATION_SYSTEM_PROMPT

        assert len(SCHEMA_GENERATION_SYSTEM_PROMPT) > 100
        assert "expert data analyst" in SCHEMA_GENERATION_SYSTEM_PROMPT.lower()

    def test_system_prompt_mentions_key_quotes(self) -> None:
        """Test that system prompt includes guidance on key quotes."""
        from app.schema.prompts import SCHEMA_GENERATION_SYSTEM_PROMPT

        assert "key quotes" in SCHEMA_GENERATION_SYSTEM_PROMPT.lower()

    def test_response_schema_categorical_field_structure(self) -> None:
        """Test that categorical_fields schema has correct properties."""
        from app.schema.prompts import SCHEMA_GENERATION_RESPONSE_SCHEMA

        cat_schema = SCHEMA_GENERATION_RESPONSE_SCHEMA["properties"]["categorical_fields"]
        cat_item = cat_schema["items"]["properties"]

        assert "field_name" in cat_item
        assert "description" in cat_item
        assert "suggested_values" in cat_item
        assert "allow_multiple" in cat_item

    def test_response_schema_scalar_field_structure(self) -> None:
        """Test that scalar_fields schema has correct properties."""
        from app.schema.prompts import SCHEMA_GENERATION_RESPONSE_SCHEMA

        scalar_schema = SCHEMA_GENERATION_RESPONSE_SCHEMA["properties"]["scalar_fields"]
        scalar_item = scalar_schema["items"]["properties"]

        assert "field_name" in scalar_item
        assert "description" in scalar_item
        assert "scale_min" in scalar_item
        assert "scale_max" in scalar_item
        assert "scale_interpretation" in scalar_item

    def test_response_schema_key_quotes_field_structure(self) -> None:
        """Test that key_quotes_fields schema has correct properties."""
        from app.schema.prompts import SCHEMA_GENERATION_RESPONSE_SCHEMA

        quotes_schema = SCHEMA_GENERATION_RESPONSE_SCHEMA["properties"]["key_quotes_fields"]
        quotes_item = quotes_schema["items"]["properties"]

        assert "field_name" in quotes_item
        assert "description" in quotes_item
        assert "max_quotes" in quotes_item
