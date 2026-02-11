"""Send a POST request to the /analyze endpoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib import error, request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hit /analyze for a cleaned dataset hash.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base server URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--hash",
        default="b44a0e56cd1eb8d91fd506c78cde9af2e684a763e271a2bcd60eaaff6b5ab7b9",
        dest="content_hash",
        help="Cleaned dataset hash",
    )
    parser.add_argument(
        "--use-case-file",
        default="app/data/raw/schedule-f-use-case.txt",
        help="Path to use-case text file",
    )
    parser.add_argument(
        "--system-prompt-file",
        default="app/schema/prompts/system_prompt.txt",
        help="Path to system prompt text file",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Set no_cache=true query param",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    use_case = Path(args.use_case_file).read_text(encoding="utf-8")
    system_prompt = Path(args.system_prompt_file).read_text(encoding="utf-8")

    payload = {
        "hash": args.content_hash,
        "use_case": use_case,
        "system_prompt": system_prompt,
    }
    query = "?no_cache=true" if args.no_cache else ""
    url = f"{args.base_url.rstrip('/')}/analyze{query}"

    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=120) as resp:
            print(f"HTTP {resp.status}")
            print(resp.read().decode("utf-8"))
            return 0
    except error.HTTPError as exc:
        print(f"HTTP {exc.code}")
        print(exc.read().decode("utf-8", errors="replace"))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
