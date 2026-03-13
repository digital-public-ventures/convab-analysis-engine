from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

from app.processing.cache import url_to_cache_path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def split_urls(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return url
    return ""


def build_index_rows(input_csv: Path, downloads_dir: Path) -> list[dict[str, str]]:
    extracted_dir = downloads_dir / "extracted_text"
    rows: list[dict[str, str]] = []

    with input_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            comment_id = (row.get("Document ID") or "").strip()
            attachment_field = (row.get("Attachment Files") or "").strip()
            if not comment_id or not attachment_field:
                continue

            urls = [u for u in split_urls(attachment_field) if normalize_url(u)]
            if not urls:
                continue

            pdfs: list[str] = []
            images: list[str] = []
            txt_files: list[str] = []
            attachment_hashes: list[str] = []

            for url in urls:
                local_path = url_to_cache_path(url, downloads_dir)
                if not local_path.exists():
                    continue

                ext = local_path.suffix.lower()
                if ext == ".pdf":
                    pdfs.append(local_path.name)
                elif ext in IMAGE_EXTENSIONS:
                    images.append(local_path.name)

                digest = file_sha256(local_path)
                attachment_hashes.append(digest)

                txt_path = extracted_dir / f"{digest}.txt"
                if txt_path.exists():
                    txt_files.append(txt_path.name)

            if not pdfs and not images and not txt_files:
                continue

            payload = {
                "comment_id": comment_id,
                "attachment_hashes": sorted(set(attachment_hashes)),
                "pdfs": sorted(set(pdfs)),
                "images": sorted(set(images)),
                "txt_files": sorted(set(txt_files)),
            }
            full_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

            rows.append(
                {
                    "comment_id": comment_id,
                    "hash": full_hash,
                    "short_hash": full_hash[:8],
                    "pdfs": json.dumps(payload["pdfs"]),
                    "images": json.dumps(payload["images"]),
                    "txt_files": json.dumps(payload["txt_files"]),
                }
            )

    rows.sort(key=lambda r: r["comment_id"])
    return rows


def main() -> int:
    downloads_dir = Path("app/data/test_image_improvement/downloads")
    input_csv = Path("app/data/test_image_improvement/input.csv")
    output_csv = downloads_dir / "index.csv"

    rows = build_index_rows(input_csv=input_csv, downloads_dir=downloads_dir)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        fieldnames = ["comment_id", "hash", "short_hash", "pdfs", "images", "txt_files"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote={output_csv}")
    print(f"rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
