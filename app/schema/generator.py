"""Schema generation using Gemini API with structured JSON output."""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import SCHEMA_MODEL_ID, SCHEMA_REQUEST_TIMEOUT, SCHEMA_THINKING_LEVEL, TOKEN_USAGE_FILE
from app.llm import generate_structured_content, validate_model_config
from app.llm.provider import create_llm_client, get_llm_provider, resolve_api_key
from app.llm.rate_limiter import AsyncRateLimiter

from .prompts import SCHEMA_GENERATION_RESPONSE_SCHEMA, SCHEMA_GENERATION_SYSTEM_PROMPT, build_schema_generation_prompt

logger = logging.getLogger(__name__)
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
RESPONSE_SCHEMA_EXAMPLE_PATH = PROMPTS_DIR / "response_schema_example.json"


def _load_response_schema_example() -> dict[str, Any]:
    with RESPONSE_SCHEMA_EXAMPLE_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _merge_schema_with_example(schema: dict[str, Any]) -> dict[str, Any]:
    """Merge LLM additional_* schema fields into the canonical example schema."""
    additional_to_canonical = {
        "additional_categorical_fields": "categorical_fields",
        "additional_scalar_fields": "scalar_fields",
        "additional_text_array_fields": "text_array_fields",
    }

    has_additional_fields = any(key in schema for key in additional_to_canonical)
    if not has_additional_fields:
        return schema

    merged_schema = deepcopy(_load_response_schema_example())

    for additional_key, canonical_key in additional_to_canonical.items():
        additional_fields = schema.get(additional_key, [])
        if not isinstance(additional_fields, list):
            continue

        canonical_fields = merged_schema.setdefault(canonical_key, [])
        if not isinstance(canonical_fields, list):
            continue

        existing_field_names = {
            field.get("field_name")
            for field in canonical_fields
            if isinstance(field, dict) and field.get("field_name")
        }
        for field in additional_fields:
            if not isinstance(field, dict):
                continue
            field_name = field.get("field_name")
            if field_name and field_name not in existing_field_names:
                canonical_fields.append(field)
                existing_field_names.add(field_name)

    return merged_schema


class SchemaGenerator:
    """Generates tagging schemas for text data using Gemini API.

    This generator is agnostic to the incoming CSV structure - it analyzes
    whatever sample data is provided and creates an appropriate schema.
    """

    def __init__(
        self,
        model_id: str | None = None,
        thinking_level: str | None = None,
        api_key: str | None = None,
    ):
        """Initialize the schema generator.

        Args:
            model_id: Gemini model to use (default: from config)
            thinking_level: Thinking level for reasoning (default: from config)
            api_key: API key for active provider (env fallback by provider)
        """
        self.model_id = model_id or SCHEMA_MODEL_ID
        self.thinking_level = thinking_level or SCHEMA_THINKING_LEVEL
        self.provider = get_llm_provider()

        # Initialize provider-specific client
        resolved_api_key = resolve_api_key(api_key=api_key, provider=self.provider)
        self.client = create_llm_client(api_key=resolved_api_key, provider=self.provider)

        profile = validate_model_config(self.model_id, self.thinking_level)
        self.model_id = profile.model_id

        self.rate_limiter = AsyncRateLimiter(
            rpm=profile.rpm,
            tpm=profile.tpm,
            rpd=profile.rpd,
            max_concurrency=profile.max_concurrency,
        )

    async def generate_schema(self, sample_data: list[dict], use_case: str) -> dict[str, Any]:
        """Generate a tagging schema based on sample data.

        The schema generator is fully agnostic to the structure of the incoming
        CSV data - it analyzes whatever fields and values are present in the
        sample data and creates an appropriate schema.

        Args:
            sample_data: List of data records (head + random sample from CSV)
            use_case: Use case description explaining what analysis is needed

        Returns:
            Generated schema as a dictionary with categorical_fields and scalar_fields

        Raises:
            ValueError: If API returns invalid JSON
            errors.APIError: If API call fails
        """
        logger.info('Generating schema using %s with %d samples...', self.model_id, len(sample_data))

        # Build the prompt
        user_prompt = build_schema_generation_prompt(sample_data, use_case)

        try:
            # Make API call with rate limiting and thinking enabled
            response_data, usage_metadata, full_response = await generate_structured_content(
                client=self.client,
                prompt_text=user_prompt,
                model_id=self.model_id,
                json_schema=SCHEMA_GENERATION_RESPONSE_SCHEMA,
                system_instruction=SCHEMA_GENERATION_SYSTEM_PROMPT,
                thinking_level=self.thinking_level,
                token_usage_file=str(TOKEN_USAGE_FILE),
                rate_limiter=self.rate_limiter,
                batch_size=len(sample_data),
                include_thoughts=True,
                return_full_response=True,
                request_timeout=SCHEMA_REQUEST_TIMEOUT,
            )

            if not response_data:
                raise ValueError('No schema generated')

            # Display thinking process if available
            self._display_thinking(full_response)

            # Log token usage
            if usage_metadata:
                total_tokens = usage_metadata['total_tokens']
                logger.info('Schema generated (%d tokens used)', total_tokens)

            return response_data

        except TimeoutError:
            logger.error('API request timed out')
            raise
        except (KeyError, ValueError) as e:
            logger.error('Configuration Error: %s', e)
            raise

    def _display_thinking(self, response: Any) -> None:
        """Display the model's thinking process if available.

        Args:
            response: Gemini API response object
        """
        if not response:
            return

        # Gemini candidate thought parts
        if hasattr(response, 'candidates') and response.candidates and response.candidates[0].content:
            parts = response.candidates[0].content.parts
            if not parts:
                return
            for part in parts:
                if hasattr(part, 'thought') and part.thought and part.text:
                    thought_text = part.text
                    if len(thought_text) > 300:
                        thought_text = thought_text[:300] + '...'
                    logger.debug('Model thinking: %s', thought_text)
                    return

        # OpenAI reasoning summaries
        output = getattr(response, 'output', None)
        if not isinstance(output, list):
            return

        for item in output:
            item_dict: dict[str, Any] | None = None
            if isinstance(item, dict):
                item_dict = item
            elif hasattr(item, 'model_dump'):
                maybe_dict = item.model_dump()
                if isinstance(maybe_dict, dict):
                    item_dict = maybe_dict

            if not item_dict or item_dict.get('type') != 'reasoning':
                continue

            summary = item_dict.get('summary') or []
            if not isinstance(summary, list):
                continue

            for summary_part in summary:
                if isinstance(summary_part, dict):
                    summary_text = summary_part.get('text')
                    if isinstance(summary_text, str) and summary_text:
                        if len(summary_text) > 300:
                            summary_text = summary_text[:300] + '...'
                        logger.debug('Model thinking summary: %s', summary_text)
                        return

    def save_schema(
        self,
        schema: dict[str, Any],
        schema_dir: Path,
        use_case: str = '',
        rows_sampled: int = 0,
    ) -> Path:
        """Save the generated schema to a hash-specific directory.

        Args:
            schema: Schema dictionary to save
            schema_dir: Directory to save schema (e.g., app/data/<hash>/schema/)
            use_case: Use case description for metadata
            rows_sampled: Number of rows sampled for metadata

        Returns:
            Path to the saved schema.json file
        """
        schema_dir.mkdir(parents=True, exist_ok=True)
        merged_schema = _merge_schema_with_example(schema)

        # Add metadata to schema
        schema_with_meta = {
            '_metadata': {
                'generated_at': datetime.now().isoformat(),
                'model_id': self.model_id,
                'thinking_level': self.thinking_level,
                'rows_sampled': rows_sampled,
                'use_case': use_case[:500] if use_case else '',
            },
            **merged_schema,
        }

        schema_file = schema_dir / 'schema.json'

        with open(schema_file, 'w', encoding='utf-8') as f:
            json.dump(schema_with_meta, f, indent=2)

        logger.info('Schema saved to %s', schema_file)

        return schema_file
