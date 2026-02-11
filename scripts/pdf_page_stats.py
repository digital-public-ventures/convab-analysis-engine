from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import fitz

from app.config import PDF_OCR_MIN_TEXT_CHARS, PDF_OCR_RENDER_DPI
from app.processing.cache import content_hash, pdf_page_image_cache_path, url_to_cache_path


def _split_urls(cell_value: str) -> list[str]:
    return [part.strip() for part in cell_value.split(",") if part.strip()]


def _build_pdf_row_lookup(raw_csv_path: Path, downloads_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Map downloaded PDF filenames back to row metadata from the Attachment Files column."""
    lookup: dict[str, list[dict[str, Any]]] = {}
    with raw_csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=2):
            attachment_files = (row.get("Attachment Files") or "").strip()
            if not attachment_files:
                continue

            for url in _split_urls(attachment_files):
                if not url.lower().startswith("http"):
                    continue
                if not url.lower().endswith(".pdf"):
                    continue

                local_name = url_to_cache_path(url, downloads_dir).name
                lookup.setdefault(local_name, []).append(
                    {
                        "csv_row_number": row_number,
                        "document_id": row.get("Document ID", ""),
                        "attachment_url": url,
                    }
                )
    return lookup


def generate_stats(
    raw_csv_path: Path,
    downloads_dir: Path,
    output_csv_path: Path,
    min_text_chars: int = PDF_OCR_MIN_TEXT_CHARS,
    render_dpi: int = PDF_OCR_RENDER_DPI,
) -> None:
    pdf_pages_dir = downloads_dir / "pdf_pages"
    row_lookup = _build_pdf_row_lookup(raw_csv_path, downloads_dir)
    pdf_paths = sorted(downloads_dir.glob("*.pdf"))
    unmapped_pdf_count = sum(1 for path in pdf_paths if path.name not in row_lookup)

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with output_csv_path.open("w", newline="", encoding="utf-8") as out_handle:
        writer = csv.DictWriter(
            out_handle,
            fieldnames=[
                "pdf_filename",
                "document_sha256",
                "csv_row_number",
                "document_id",
                "attachment_url",
                "mapped_from_attachment_files",
                "page_index",
                "page_number",
                "native_text_chars",
                "min_text_chars_threshold",
                "meets_native_threshold",
                "below_native_threshold",
                "render_image_exists",
                "render_image_filename",
            ],
        )
        writer.writeheader()

        for pdf_path in pdf_paths:
            pdf_bytes = pdf_path.read_bytes()
            document_sha256 = content_hash(pdf_bytes)
            mapping_entries = row_lookup.get(pdf_path.name, [])
            if not mapping_entries:
                mapping_entries = [
                    {
                        "csv_row_number": "",
                        "document_id": "",
                        "attachment_url": "",
                    }
                ]

            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                for page_index, page in enumerate(doc):
                    native_text_chars = len(page.get_text().strip())
                    meets_threshold = native_text_chars >= min_text_chars
                    render_path = pdf_page_image_cache_path(
                        document_sha256=document_sha256,
                        page_index=page_index,
                        dpi=render_dpi,
                        cache_dir=downloads_dir,
                    )
                    has_render_image = render_path.exists()

                    for entry in mapping_entries:
                        writer.writerow(
                            {
                                "pdf_filename": pdf_path.name,
                                "document_sha256": document_sha256,
                                "csv_row_number": entry["csv_row_number"],
                                "document_id": entry["document_id"],
                                "attachment_url": entry["attachment_url"],
                                "mapped_from_attachment_files": bool(entry["attachment_url"]),
                                "page_index": page_index,
                                "page_number": page_index + 1,
                                "native_text_chars": native_text_chars,
                                "min_text_chars_threshold": min_text_chars,
                                "meets_native_threshold": meets_threshold,
                                "below_native_threshold": not meets_threshold,
                                "render_image_exists": has_render_image,
                                "render_image_filename": render_path.name if has_render_image else "",
                            }
                        )

    print(f"wrote_stats_csv={output_csv_path}")
    print(f"pdf_count={len(pdf_paths)}")
    print(f"mapped_pdf_filenames={len(row_lookup)}")
    print(f"unmapped_pdf_filenames={unmapped_pdf_count}")
    print(f"pdf_pages_dir_exists={pdf_pages_dir.exists()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate per-page native text/OCR-cache stats for downloaded PDFs.")
    parser.add_argument("--raw-csv", type=Path, required=True, help="Path to input raw CSV (must include Attachment Files).")
    parser.add_argument("--downloads-dir", type=Path, required=True, help="Path to hash downloads directory.")
    parser.add_argument("--output-csv", type=Path, required=True, help="Path to output stats CSV.")
    parser.add_argument(
        "--min-text-chars",
        type=int,
        default=PDF_OCR_MIN_TEXT_CHARS,
        help=f"Native text chars threshold (default: {PDF_OCR_MIN_TEXT_CHARS}).",
    )
    parser.add_argument(
        "--render-dpi",
        type=int,
        default=PDF_OCR_RENDER_DPI,
        help=f"Render DPI used for cached PDF pages (default: {PDF_OCR_RENDER_DPI}).",
    )
    args = parser.parse_args()

    generate_stats(
        raw_csv_path=args.raw_csv,
        downloads_dir=args.downloads_dir,
        output_csv_path=args.output_csv,
        min_text_chars=args.min_text_chars,
        render_dpi=args.render_dpi,
    )


if __name__ == "__main__":
    main()
