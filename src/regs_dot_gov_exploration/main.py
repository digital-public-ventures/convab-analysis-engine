"""Main analysis orchestrator for regulations.gov public comments.

This module handles loading, processing, and analyzing public comments
submitted to federal regulatory dockets.
"""

import argparse
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from ..utilities.llm.response_parser import extract_json_from_response
from ..utilities.schema_generator import SchemaGenerator
from .attachment_processor import AttachmentProcessor, combine_narratives
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


def load_system_prompt() -> str:
    """Load the system prompt from the prompts directory.

    Returns:
        System prompt text
    """
    system_prompt_path = Path(__file__).parent / "prompts" / "system_prompt.txt"
    with open(system_prompt_path, encoding="utf-8") as f:
        return f.read().strip()


async def generate_schema_command(args: argparse.Namespace) -> None:
    """Handle the generate-schema subcommand.

    Args:
        args: Parsed command line arguments
    """
    try:
        # Load sample data
        processor = DataProcessor(args.csv_path if args.csv_path else None)
        records = processor.load_records(n_rows=args.rows)

        if not records:
            print("No data loaded. Check your CSV file.")
            return

        # Convert to dictionaries for schema generation
        sample_data = [r.to_dict() for r in records]

        # Generate schema
        generator = SchemaGenerator(
            model_id=args.model,
            thinking_level=args.thinking_level,
            company=args.company,
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
        data_desc = f"CSV with {len(sample_data)} sampled records from regulations.gov"

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
            csv_source=str(processor.csv_path),
        )

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error: {e}")
        raise


async def extract_attachments_command(args: argparse.Namespace) -> None:
    """Handle the extract-attachments subcommand.

    Args:
        args: Parsed command line arguments
    """
    try:
        # Load data
        processor = DataProcessor(args.csv_path if args.csv_path else None)
        records = processor.get_records_with_attachments(n_rows=args.rows)

        if not records:
            print("No records with attachments found.")
            return

        print(f"Found {len(records)} records with attachments")

        # Process attachments
        attachment_processor = AttachmentProcessor(timeout=args.timeout)

        for record in records:
            print(f"\nProcessing: {record.id}")
            print(f"  Attachments: {len(record.attachment_urls)}")

            # Extract text from attachments
            attachment_texts = attachment_processor.process_attachments(
                record.attachment_urls,
                skip_errors=True,
            )

            # Combine with inline comment
            combined = combine_narratives(record.narrative, attachment_texts)

            # Display summary
            for url, text in attachment_texts.items():
                status = "extracted" if text else "failed"
                char_count = len(text) if text else 0
                print(f"    - {Path(url).name}: {status} ({char_count} chars)")

            if args.verbose and combined:
                print(f"\n  Combined narrative preview:\n  {combined[:500]}...")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error: {e}")
        raise


async def list_records_command(args: argparse.Namespace) -> None:
    """Handle the list-records subcommand.

    Args:
        args: Parsed command line arguments
    """
    try:
        processor = DataProcessor(args.csv_path if args.csv_path else None)
        records = processor.load_records(n_rows=args.rows)

        print(f"\nLoaded {len(records)} records from {processor.csv_path}")
        print("=" * 80)

        for record in records:
            has_narrative = bool(record.narrative and record.narrative.strip())
            has_attachments = bool(record.attachment_urls)

            narrative_preview = ""
            if has_narrative:
                preview = record.narrative[:100].replace("\n", " ")
                narrative_preview = f'"{preview}..."'
            elif has_attachments:
                narrative_preview = "[See attachments]"
            else:
                narrative_preview = "[No content]"

            print(f"\n{record.id}")
            print(f"  Narrative: {narrative_preview}")
            if has_attachments:
                print(f"  Attachments: {len(record.attachment_urls)}")
                for url in record.attachment_urls:
                    print(f"    - {Path(url).name}")
            if record.metadata.get("Organization Name"):
                print(f'  Organization: {record.metadata["Organization Name"]}')
            if record.metadata.get("State/Province"):
                print(f'  State: {record.metadata["State/Province"]}')

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error: {e}")
        raise


def main() -> None:
    """Main entry point for the regulations.gov exploration CLI."""
    parser = argparse.ArgumentParser(
        description="Regulations.gov Public Comment Analysis Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List records (uses USE_HEAD env var for data source)
  python -m regs_dot_gov_exploration list-records --rows 10

  # Generate analysis schema
  python -m regs_dot_gov_exploration generate-schema --rows 5

  # Extract text from attachments
  python -m regs_dot_gov_exploration extract-attachments --rows 5 --verbose
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Common arguments
    def add_common_args(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument(
            "--csv-path",
            type=str,
            default=None,
            help="Path to CSV file (default: auto-detect based on USE_HEAD env var)",
        )
        subparser.add_argument(
            "--rows",
            type=int,
            default=10,
            help="Number of rows to process (default: 10)",
        )

    # Subcommand: list-records
    list_parser = subparsers.add_parser("list-records", help="List records from the dataset")
    add_common_args(list_parser)

    # Subcommand: generate-schema
    schema_parser = subparsers.add_parser(
        "generate-schema", help="Generate analysis schema from sample data"
    )
    add_common_args(schema_parser)
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
        default="regs_gov",
        help="Company/project identifier for filenames (default: regs_gov)",
    )

    # Subcommand: extract-attachments
    extract_parser = subparsers.add_parser(
        "extract-attachments", help="Extract text from document attachments"
    )
    add_common_args(extract_parser)
    extract_parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds (default: 30.0)",
    )
    extract_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show extracted text previews",
    )

    args = parser.parse_args()

    # Show USE_HEAD status
    use_head = os.getenv("USE_HEAD", "true").lower() in ("true", "1", "yes")
    print(f'USE_HEAD={use_head} (using {"sample" if use_head else "full"} data)')

    # Route to appropriate handler
    if args.command == "list-records":
        asyncio.run(list_records_command(args))
    elif args.command == "generate-schema":
        asyncio.run(generate_schema_command(args))
    elif args.command == "extract-attachments":
        asyncio.run(extract_attachments_command(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
