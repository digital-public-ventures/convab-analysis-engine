"""Schema generation using Gemini API with structured JSON output."""

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import errors

from .llm.gemini_client import generate_structured_content
from .llm.rate_limiter import AsyncRateLimiter
from .prompts.schema_gen.prompts import (
    SCHEMA_GENERATION_RESPONSE_SCHEMA,
    SCHEMA_GENERATION_SYSTEM_PROMPT,
    build_schema_generation_prompt,
)

load_dotenv()


class SchemaGenerator:
    """Generates tagging schemas for text data using Gemini API."""

    def __init__(
        self,
        model_id: str = 'gemini-3-flash-preview',
        thinking_level: str = 'MINIMAL',
        api_key: str | None = None,
        company: str = 'cfpb',
    ):
        """Initialize the schema generator.

        Args:
            model_id: Gemini model to use (default: gemini-3-flash-preview)
            thinking_level: Thinking level for reasoning (default: MINIMAL)
            api_key: API key for Gemini (defaults to GEMINI_API_KEY env var)
            company: Company/project identifier for filenames (default: cfpb)
        """
        self.model_id = model_id
        self.thinking_level = thinking_level
        self.company = company

        # Initialize Gemini client
        api_key = api_key or os.environ.get('GEMINI_API_KEY')
        if not api_key or api_key == 'YOU_FORGOT_TO_SET_GEMINI_API_KEY':
            raise ValueError('GEMINI_API_KEY environment variable not set')

        self.client = genai.Client(api_key=api_key)

        # Set rate limits based on model
        if 'flash' in model_id:
            self.rate_limiter = AsyncRateLimiter(rpm=1000, tpm=1_000_000, rpd=10_000)
        else:  # pro model
            self.rate_limiter = AsyncRateLimiter(rpm=25, tpm=1_000_000, rpd=250)

    async def generate_schema(self, sample_data: list[dict]) -> dict[str, Any]:
        """Generate a tagging schema based on sample data.

        Args:
            sample_data: List of data records

        Returns:
            Generated schema as a dictionary (schema definition only, not tagged data)

        Raises:
            ValueError: If API returns invalid JSON
            errors.APIError: If API call fails
        """
        print(f'\n🤖 Generating schema using {self.model_id}...')

        # Build the prompt (use_case is now loaded from file)
        user_prompt = build_schema_generation_prompt(sample_data)

        try:
            # Make API call with rate limiting and thinking enabled
            response_data, usage_metadata, full_response = await generate_structured_content(
                client=self.client,
                prompt_text=user_prompt,
                model_id=self.model_id,
                json_schema=SCHEMA_GENERATION_RESPONSE_SCHEMA,
                system_instruction=SCHEMA_GENERATION_SYSTEM_PROMPT,
                thinking_level=self.thinking_level,
                rate_limiter=self.rate_limiter,
                batch_size=len(sample_data),
                include_thoughts=True,
                return_full_response=True,
            )

            if not response_data:
                raise ValueError('No schema generated')

            # Display thinking process if available
            self._display_thinking(full_response)

            # Log token usage
            if usage_metadata:
                total_tokens = usage_metadata['total_tokens']
                print(f'✓ Schema generated ({total_tokens:,} tokens used)')

            return response_data

        except errors.APIError as e:
            print(f'❌ API Error: {e}')
            raise
        except (KeyError, ValueError) as e:
            print(f'❌ Configuration Error: {e}')
            raise

    def _display_thinking(self, response: Any) -> None:
        """Display the model's thinking process if available.

        Args:
            response: Gemini API response object
        """
        if not response.candidates or not response.candidates[0].content:
            return

        parts = response.candidates[0].content.parts
        if not parts:
            return

        for part in parts:
            if part.thought and part.text:
                # Show abbreviated thinking process
                thought_text = part.text
                if len(thought_text) > 300:
                    thought_text = thought_text[:300] + '...'
                print(f'\n💭 [Thinking]: {thought_text}\n')
                break

    def save_schema(
        self,
        schema: dict[str, Any],
        output_dir: str = 'temp/schemas',
        use_case: str = '',
        data_description: str = '',
        rows_sampled: int = 0,
        csv_source: str = '',
    ) -> str:
        """Save the generated schema to a JSON file with metadata tracking.

        Args:
            schema: Schema dictionary to save
            output_dir: Directory to save schemas (default: temp/schemas)
            use_case: User's use case description for metadata
            data_description: Description of the data for metadata
            rows_sampled: Number of rows sampled for metadata
            csv_source: Source CSV file for metadata

        Returns:
            Path to the saved schema file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate filename: {company}_{model}_{thinking}_{timestamp}.json
        timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
        # Sanitize model name for filename
        model_safe = self.model_id.replace('.', '-').replace('/', '-')
        filename = f'{self.company}_{model_safe}_{self.thinking_level}_{timestamp}.json'

        schema_file = output_path / filename

        # Save schema JSON
        with open(schema_file, 'w', encoding='utf-8') as f:
            json.dump(schema, f, indent=2)

        print(f'✓ Schema saved to {schema_file}')

        # Update index.csv
        self._update_schema_index(
            output_dir=output_dir,
            filename=filename,
            timestamp=timestamp,
            use_case=use_case,
            data_description=data_description,
            rows_sampled=rows_sampled,
            csv_source=csv_source,
        )

        return str(schema_file)

    def _update_schema_index(
        self,
        output_dir: str,
        filename: str,
        timestamp: str,
        use_case: str,
        data_description: str,
        rows_sampled: int,
        csv_source: str,
    ) -> None:
        """Update or create the schema index CSV file.

        Args:
            output_dir: Directory containing schemas
            filename: Schema filename
            timestamp: Generation timestamp
            use_case: User's use case description
            data_description: Description of the data
            rows_sampled: Number of rows sampled
            csv_source: Source CSV file
        """
        index_file = Path(output_dir) / 'index.csv'

        # Define CSV headers
        headers = [
            'filename',
            'company',
            'model',
            'thinking_level',
            'timestamp',
            'rows_sampled',
            'csv_source',
            'data_description',
            'use_case',
        ]

        # Check if index exists
        file_exists = index_file.exists()

        # Prepare row data
        row = {
            'filename': filename,
            'company': self.company,
            'model': self.model_id,
            'thinking_level': self.thinking_level,
            'timestamp': timestamp,
            'rows_sampled': rows_sampled,
            'csv_source': csv_source,
            'data_description': data_description,
            'use_case': use_case.replace('\n', ' ').strip()[:500],  # Truncate long use cases
        }

        # Append to index
        with open(index_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)

            # Write header if file is new
            if not file_exists:
                writer.writeheader()

            writer.writerow(row)

        print(f'✓ Updated schema index at {index_file}')
