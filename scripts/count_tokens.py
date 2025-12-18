#!/usr/bin/env python3
"""
Simple token counter for CSV files.
Uses whitespace-delimited word count and applies a heuristic (words / 0.75) to estimate tokens.
"""

import sys
from pathlib import Path


def count_tokens(file_path: str) -> dict:
    """Count words and estimate tokens in a file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Count words (whitespace delimited)
    words = content.split()
    word_count = len(words)

    # Estimate tokens using the heuristic: words / 0.75
    estimated_tokens = int(word_count / 0.75)

    return {
        "word_count": word_count,
        "estimated_tokens": estimated_tokens,
        "file_size_bytes": len(content),
        "file_size_kb": len(content) / 1024,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python count_tokens.py <file_path>")
        print("\nExample: python count_tokens.py ../data/complaints_1.csv")
        sys.exit(1)

    file_path = sys.argv[1]

    if not Path(file_path).exists():
        print(f"Error: File '{file_path}' not found")
        sys.exit(1)

    results = count_tokens(file_path)

    print(f"\n📊 Token Count Results for: {file_path}")
    print("=" * 60)
    print(f"Words (whitespace delimited): {results['word_count']:,}")
    print(f"Estimated tokens (÷ 0.75):   {results['estimated_tokens']:,}")
    print(
        f"File size:                    {results['file_size_kb']:.2f} KB ({results['file_size_bytes']:,} bytes)"
    )
    print("=" * 60)
    print(f"\n💡 Using heuristic: tokens ≈ words / 0.75")
    print()


if __name__ == "__main__":
    main()
