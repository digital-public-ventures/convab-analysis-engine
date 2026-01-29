"""One-time script to create a sample head file with 7 random rows."""

import csv
import random
from pathlib import Path

INPUT_CSV = Path(__file__).parent / "data" / "responses.csv"
OUTPUT_CSV = Path(__file__).parent / "data" / "head" / "responses.csv"

# Set seed for reproducibility
random.seed(42)

# Read all rows
with open(INPUT_CSV, encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)
    all_rows = list(reader)

print(f"Total rows: {len(all_rows)}")

# Skip the first row (the Notice document) and select 7 random public submissions
# Filter to only Public Submission types (have Comment field content)
public_submissions = [row for row in all_rows if row[4] == "Public Submission"]
print(f"Public submissions: {len(public_submissions)}")

# Select 7 random rows
sample_rows = random.sample(public_submissions, 7)

# Write to output
OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(sample_rows)

print(f"Created {OUTPUT_CSV} with header + 7 rows")

# Print sample document IDs for verification
print("Sample Document IDs:")
for row in sample_rows:
    print(f"  - {row[0]}")
