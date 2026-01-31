"""Download regulations.gov attachment fixtures based on a manifest file."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "tests/fixtures/regs_gov_attachments"
MANIFEST_PATH = FIXTURES_DIR / "manifest.json"


def main() -> None:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}")

    with MANIFEST_PATH.open(encoding="utf-8") as handle:
        manifest = json.load(handle)

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": (
            "application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/png,*/*"
        ),
    }

    with httpx.Client(follow_redirects=True, timeout=60.0, headers=headers) as client:
        for url, filename in manifest.items():
            target = FIXTURES_DIR / filename
            if target.exists():
                print(f"Skipping existing: {target.name}")
                continue

            print(f"Downloading: {url}")
            response = client.get(url)
            response.raise_for_status()
            target.write_bytes(response.content)
            print(f"Saved: {target.name} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
