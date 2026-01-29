import argparse
import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

from ..utilities.llm.response_parser import extract_json_from_response
from ..utilities.schema_generator import SchemaGenerator
from .data_processor import DataProcessor

load_dotenv()


def load_use_case() -> str:
    """Load the use case from the prompts directory.

    Returns:
        Use case description text
    """
    use_case_path = Path(__file__).parent / "prompts" / "use_case.txt"
    with open(use_case_path, encoding="utf-8") as f:
        return f.read().strip()


async def generate_schema_command(args: argparse.Namespace) -> None:
    """Handle the generate-schema subcommand.

    Args:
        args: Parsed command line arguments
    """
    try:
        # Load sample data
        processor = DataProcessor(args.csv_path if args.csv_path else None)
        sample_data = processor.load_sample(n_rows=args.rows)

        if not sample_data:
            print("❌ No data loaded. Check your CSV file.")
            return

        # Generate schema
        generator = SchemaGenerator(
            model_id=args.model, thinking_level=args.thinking_level, company=args.company
        )

        schema = await generator.generate_schema(sample_data)

        # Extract clean JSON from response (handles wrappers and markdown)
        schema = extract_json_from_response(schema)

        # Display schema
        print("\n" + "=" * 80)
        print("GENERATED SCHEMA")
        print("=" * 80)
        print(json.dumps(schema, indent=2))
        print("=" * 80)

        # Prepare data description
        data_desc = f"CSV with {len(sample_data)} sampled records"

        # Load use case from file
        use_case = load_use_case()

        # Save schema with metadata
        output_dir = args.output_dir if args.output_dir else "temp/schemas"
        generator.save_schema(
            schema=schema,
            output_dir=output_dir,
            use_case=use_case,
            data_description=data_desc,
            rows_sampled=len(sample_data),
            csv_source=args.csv_path,
        )

    except FileNotFoundError as e:
        print(f"❌ {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CFPB Exploration Tools")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Subcommand: generate-schema
    schema_parser = subparsers.add_parser(
        "generate-schema", help="Generate a tagging schema from sample data"
    )
    schema_parser.add_argument(
        "--csv-path",
        type=str,
        default=None,
        help="Path to CSV file (default: auto-detect based on USE_HEAD env var)",
    )
    schema_parser.add_argument(
        "--rows", type=int, default=5, help="Number of rows to sample (default: 5, max: 10)"
    )
    schema_parser.add_argument(
        "--model",
        type=str,
        default="gemini-3-flash-preview",
        help="Model ID (default: gemini-3-flash-preview)",
    )
    schema_parser.add_argument(
        "--thinking-level",
        type=str,
        default="MINIMAL",
        choices=["MINIMAL", "LOW", "MEDIUM", "HIGH"],
        help="Thinking level (default: MINIMAL)",
    )
    schema_parser.add_argument(
        "--output-dir",
        type=str,
        default="temp/schemas",
        help="Directory to save schemas (default: temp/schemas)",
    )
    schema_parser.add_argument(
        "--company",
        type=str,
        default="cfpb",
        help="Company/project identifier for filenames (default: cfpb)",
    )

    # Subcommand: prompt (original functionality)
    prompt_parser = subparsers.add_parser("prompt", help="Send a direct prompt to Gemini")
    prompt_parser.add_argument("prompt", type=str, help="User prompt (required)")
    prompt_parser.add_argument(
        "--model",
        type=str,
        default="gemini-3-flash-preview",
        help="Model ID (default: gemini-3-flash-preview)",
    )
    prompt_parser.add_argument(
        "--thinking-level",
        type=str,
        default="HIGH",
        choices=["MINIMAL", "LOW", "MEDIUM", "HIGH"],
        help="Thinking level (default: HIGH)",
    )
    prompt_parser.add_argument(
        "--system-prompt",
        type=str,
        default=None,
        help="Optional system instruction to guide model behavior",
    )

    args = parser.parse_args()

    # Route to appropriate handler
    if args.command == "generate-schema":
        asyncio.run(generate_schema_command(args))
    else:
        parser.print_help()
