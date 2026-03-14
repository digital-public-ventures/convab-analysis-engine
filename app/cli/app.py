"""Top-level CLI app orchestration."""

from __future__ import annotations

import asyncio
import sys
from argparse import Namespace
from typing import Any

from dotenv import load_dotenv

from .analyze import run_analyze_command
from .clean import run_clean_command
from .data_info import build_data_info_payload
from .output import print_human_output, print_json_output
from .parser import build_parser
from .schema import run_schema_command
from .tag_fix import run_tag_fix_command


async def dispatch_command(args: Namespace) -> dict[str, Any]:
    if args.command == 'clean':
        return await run_clean_command(
            input_csv=args.input_csv,
            no_cache=args.no_cache,
            no_cache_ocr=args.no_cache_ocr,
        )
    if args.command == 'schema':
        return await run_schema_command(
            content_hash=args.content_hash,
            use_case_file=args.use_case_file,
            sample_size=args.sample_size,
            head_size=args.head_size,
        )
    if args.command == 'analyze':
        return await run_analyze_command(
            content_hash=args.content_hash,
            use_case_file=args.use_case_file,
            system_prompt_file=args.system_prompt_file,
            no_cache=args.no_cache,
        )
    if args.command == 'tag-fix':
        return await run_tag_fix_command(
            content_hash=args.content_hash,
            no_cache=args.no_cache,
        )
    if args.command == 'data-info':
        return build_data_info_payload(content_hash=args.content_hash)
    raise ValueError(f'Unknown command: {args.command}')


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help(sys.stderr)
        return 1

    try:
        payload = asyncio.run(dispatch_command(args))
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1

    if getattr(args, 'json', False):
        print_json_output(payload)
    else:
        print_human_output(payload)
    return 0
