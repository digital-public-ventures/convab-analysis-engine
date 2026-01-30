import asyncio
import csv
import json
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from dotenv import load_dotenv
from google import genai

from ..utilities.llm.gemini_client import generate_structured_content, validate_model_config
from ..utilities.llm.model_config import ModelProfile
from ..utilities.llm.rate_limiter import AsyncRateLimiter

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
BASE_DATA_DIR = Path(__file__).parent / "data"
FULL_INPUT_CSV = BASE_DATA_DIR / "complaints_1.csv"
HEAD_INPUT_CSV = BASE_DATA_DIR / "head" / "complaints_1.csv"
OUTPUT_DIR = "src/cfpb_exploration/output"
TEMP_DIR = "temp/output"
TOKEN_USAGE_FILE = "temp/token_usage.jsonl"  # Shared token usage log  # noqa: S105
SCHEMA_FILE = "src/cfpb_exploration/schemas/google_gemini-3-pro_MEDIUM_2025-12-17T15-28-23.json"

# BATCH SIZE:
# the number of rows per batch, each row is ~500 tokens on average
BATCH_SIZE = 5

# MAX BATCHES:
# Limit the number of batches to process (None = all batches)
# Flash can handle larger number of async batches (1000 TPM), but Pro is limited to 25.
# 1 is a safe number for testing.
MAX_BATCHES = 2

# RESUME FROM BATCH:
# Skip this many batches at the start (useful for resuming failed runs)
# Set to 0 to start from the beginning
RESUME_FROM_BATCH = 0

# --- USER SELECTION ---
# CHANGE THESE VALUES TO SWITCH MODELS
SELECTED_MODEL_KEY = "flash"  # Options: "flash" or "pro"
SELECTED_THINKING_LEVEL = "LOW"  # Options: MINIMAL (flash only), LOW, MEDIUM, HIGH

# --- SCHEMA LOADER ---


def resolve_input_csv() -> Path:
    """Resolve CSV path based on USE_HEAD environment variable."""
    use_head = os.getenv("USE_HEAD", "true").lower() in ("true", "1", "yes")
    if use_head:
        if HEAD_INPUT_CSV.exists():
            return HEAD_INPUT_CSV
        print("Warning: USE_HEAD is true but head sample not found. Falling back to full dataset.")

    return FULL_INPUT_CSV


def load_schema(schema_path: str) -> dict[str, Any]:
    """Load JSON schema from file."""
    with Path(schema_path).open(encoding="utf-8") as f:
        return cast("dict[str, Any]", json.load(f))


# Load schema at module level
JSON_SCHEMA = load_schema(SCHEMA_FILE)

# --- PROMPT LOADERS ---


def load_prompt(filename: str) -> str:
    """Load a prompt from the prompts directory."""
    prompt_path = Path(__file__).parent / "prompts" / filename
    with prompt_path.open(encoding="utf-8") as f:
        return f.read()


SYSTEM_INSTRUCTION = load_prompt("system_prompt.txt")
USER_PROMPT_TEMPLATE = load_prompt("user_prompt_template.txt")


# --- BATCH ANALYSIS WORKER ---


def flatten_complaint_to_csv_row(complaint: dict, original_row: dict | None = None) -> dict:
    """Flatten nested complaint structure to a flat CSV row.

    Args:
        complaint: Analyzed complaint data with nested structure
        original_row: Original CSV row data to preserve

    Returns:
        Merged row with original data and flattened analysis
    """
    # Start with original row data if provided
    row = dict(original_row) if original_row else {}

    # Add id from analysis (should match original)
    row["id"] = complaint.get("id", "")

    # Flatten scalar metrics
    scalar_metrics = complaint.get("scalar_metrics", {})
    for key, value in scalar_metrics.items():
        row[key] = value

    # Flatten categorical dimensions
    categorical_dims = complaint.get("categorical_dimensions", {})
    for key, value in categorical_dims.items():
        # Convert lists to pipe-separated strings
        if isinstance(value, list):
            row[key] = "|".join(str(v) for v in value)
        else:
            row[key] = value

    # Flatten entity relations
    entity_relations = complaint.get("entity_relations", {})
    for key, value in entity_relations.items():
        if isinstance(value, list):
            row[key] = "|".join(str(v) for v in value)
        else:
            row[key] = value

    return row


async def analyze_batch(
    client: genai.Client,
    model_profile: ModelProfile,
    limiter: AsyncRateLimiter,
    batch: list[dict],
    batch_idx: int,
    run_temp_dir: Path,
    csv_fieldnames: list[str],
) -> list[dict]:
    """Process a single batch of complaints with rate limiting."""
    # 1. Build Prompt
    prompt_text = USER_PROMPT_TEMPLATE
    for item in batch:
        prompt_text += f'--- Object ID: {item.get("id", "Unknown")} ---\n'
        prompt_text += f'Product: {item.get("Product", "")}\n'
        prompt_text += f'Narrative: {item.get("Consumer complaint narrative", "")}\n\n'

    try:
        # 2. Execute Request with Automatic Rate Limiting
        print(f"⏳ Batch {batch_idx}: Preparing request...")

        response_data, _ = await generate_structured_content(
            client=client,
            prompt_text=prompt_text,
            model_id=model_profile.model_id,
            json_schema=JSON_SCHEMA,
            system_instruction=SYSTEM_INSTRUCTION,
            thinking_level=SELECTED_THINKING_LEVEL,
            token_usage_file=TOKEN_USAGE_FILE,
            rate_limiter=limiter,
            batch_size=len(batch),
        )
    except (ValueError, ConnectionError, TimeoutError) as e:
        print(f"🔥 Batch {batch_idx} Failed: {e!s}")
        return []

    # 3. Process & Write Temp Files (JSON and CSV)
    if response_data:
        analyzed_data = cast(
            "list[dict[str, Any]]",
            response_data.get("analyzed_complaints", []),
        )

        # Write JSON file
        temp_json_filename = Path(run_temp_dir) / f"batch_{batch_idx}_size{len(batch)}_{int(time.time())}.json"
        with temp_json_filename.open("w", encoding="utf-8") as f:
            json.dump(analyzed_data, f, indent=2)

        # Write CSV file with merged original + analyzed data
        temp_csv_filename = Path(run_temp_dir) / f"batch_{batch_idx}_size{len(batch)}_{int(time.time())}.csv"
        with temp_csv_filename.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
            writer.writeheader()

            # Create a mapping of id to original batch item
            batch_map = {item.get("id", ""): item for item in batch}

            for complaint in analyzed_data:
                complaint_id = complaint.get("id", "")
                original_row = batch_map.get(complaint_id, {})
                flattened = flatten_complaint_to_csv_row(complaint, original_row)
                writer.writerow(flattened)

        print(f"✅ Batch {batch_idx}: Success. Saved {len(analyzed_data)} items to {temp_json_filename}")
        return analyzed_data

    print(f"❌ Batch {batch_idx}: Failed to generate valid response.")
    return []


# --- MAIN ORCHESTRATOR ---


async def main() -> None:
    """Main orchestrator for complaint analysis.

    Processes consumer complaints in batches using LLM analysis,
    generates structured JSON and CSV outputs, and validates results.
    """
    # 0. Setup & Validation
    profile = validate_model_config(SELECTED_MODEL_KEY, SELECTED_THINKING_LEVEL)

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)

    print("--- STARTING ANALYSIS ---")
    print(f"Model: {profile.model_id}")
    print(f"Limits: {profile.rpm} RPM | {profile.tpm:,} TPM | {profile.rpd} RPD")
    print(f"Thinking Level: {SELECTED_THINKING_LEVEL}")

    client = genai.Client(api_key=API_KEY)
    limiter = AsyncRateLimiter(profile.rpm, profile.tpm, profile.rpd)

    # 1. Load Data
    rows = []
    input_csv = resolve_input_csv()
    try:
        with input_csv.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except FileNotFoundError:
        print("Input file not found.")
        return

    # Check if first column is 'id', if not add it with UUIDs
    if rows and list(rows[0].keys())[0] != "id":
        print('⚠️  First column is not "id" - adding unique ID column')
        for row in rows:
            # Create ordered dict with id first
            row_with_id = {"id": str(uuid.uuid4())}
            row_with_id.update(row)
            # Replace the row contents
            row.clear()
            row.update(row_with_id)

    print(f"Loaded {len(rows)} rows from {input_csv}. Batch size: {BATCH_SIZE}")

    # 2. Determine CSV fieldnames: original columns + analyzed columns
    # Get original CSV column names
    original_fieldnames = list(rows[0].keys()) if rows else []

    # Determine analyzed field names from schema structure
    analyzed_fieldnames = ["id"]
    sample_schema = (
        JSON_SCHEMA.get("properties", {}).get("analyzed_complaints", {}).get("items", {}).get("properties", {})
    )
    scalar_props = sample_schema.get("scalar_metrics", {}).get("properties", {})
    analyzed_fieldnames.extend(scalar_props.keys())
    categorical_props = sample_schema.get("categorical_dimensions", {}).get("properties", {})
    analyzed_fieldnames.extend(categorical_props.keys())
    entity_props = sample_schema.get("entity_relations", {}).get("properties", {})
    analyzed_fieldnames.extend(entity_props.keys())

    # Combine: original columns first, then new analyzed columns (avoiding duplicates)
    csv_fieldnames = original_fieldnames.copy()
    for field in analyzed_fieldnames:
        if field not in csv_fieldnames:
            csv_fieldnames.append(field)

    # 3. Create Tasks
    batches = [rows[i : i + BATCH_SIZE] for i in range(0, len(rows), BATCH_SIZE)]

    # Create a unique temp directory for THIS run to avoid pollution
    run_id = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    current_run_dir = Path(TEMP_DIR) / run_id
    current_run_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created temp directory: {current_run_dir}")

    # Apply resume logic (skip batches if resuming)
    if RESUME_FROM_BATCH > 0:
        print(f"⏭️  Resuming: Skipping first {RESUME_FROM_BATCH} batch(es)")
        batches = batches[RESUME_FROM_BATCH:]

    if MAX_BATCHES is not None:
        batches = batches[:MAX_BATCHES]
        max_rows = len(batches) * BATCH_SIZE
        print(f"Limiting to {MAX_BATCHES} batch(es) ({max_rows} rows max)")

    # Pass current_run_dir and csv_fieldnames to the worker
    # Adjust batch index to account for resume offset
    tasks = [
        analyze_batch(client, profile, limiter, b, i + 1 + RESUME_FROM_BATCH, current_run_dir, csv_fieldnames)
        for i, b in enumerate(batches)
    ]

    # 3. Run Async
    start_time = time.time()
    await asyncio.gather(*tasks)

    # 4. Consolidate Results
    all_complaints = []
    # Consolidate files ONLY from the current run directory
    temp_files = list(current_run_dir.glob("*.json"))
    print(f"\nConsolidating {len(temp_files)} batch files from {current_run_dir}...")

    for tf in temp_files:
        with tf.open(encoding="utf-8") as f:
            try:
                batch_data = json.load(f)
                all_complaints.extend(batch_data)
            except json.JSONDecodeError:
                print(f"Skipping corrupt file: {tf}")

    # 5. Consolidate CSV files
    temp_csv_files = sorted(current_run_dir.glob("*.csv"))
    print(f"Consolidating {len(temp_csv_files)} CSV batch files from {current_run_dir}...")

    # Read all CSV files and consolidate (skip headers after first file)
    all_csv_rows = []
    for csv_file in temp_csv_files:
        with csv_file.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            all_csv_rows.extend(list(reader))

    # 6. Write Final Output (JSON and CSV)
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")

    # Create timestamped subfolder for this run's output
    output_run_dir = Path(OUTPUT_DIR) / timestamp
    output_run_dir.mkdir(parents=True, exist_ok=True)

    final_json_filename = f"{SELECTED_MODEL_KEY}_{SELECTED_THINKING_LEVEL}_{timestamp}.json"
    final_json_path = output_run_dir / final_json_filename

    with final_json_path.open("w", encoding="utf-8") as f:
        json.dump(all_complaints, f, indent=2)

    # Write final CSV
    final_csv_filename = f"{SELECTED_MODEL_KEY}_{SELECTED_THINKING_LEVEL}_{timestamp}.csv"
    final_csv_path = output_run_dir / final_csv_filename

    with final_csv_path.open("w", encoding="utf-8", newline="") as f:
        if all_csv_rows:
            writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
            writer.writeheader()
            writer.writerows(all_csv_rows)

    # 7. Validation & Success Reporting
    elapsed_time = time.time() - start_time
    expected_rows = len(batches) * BATCH_SIZE if MAX_BATCHES else len(rows)

    print("\n" + "=" * 60)

    # Check for failures
    failures = []

    if not all_complaints:
        failures.append("❌ No data in final output (empty array)")

    if len(all_complaints) < expected_rows:
        failures.append(f"❌ Expected {expected_rows} items, got {len(all_complaints)}")

    # Check for non-empty values in at least one complaint
    if all_complaints:
        has_content = False
        for complaint in all_complaints:
            if any(str(v).strip() for v in complaint.values() if v):
                has_content = True
                break
        if not has_content:
            failures.append("❌ All complaint objects appear empty")

    # Validate CSV row count matches expected
    csv_row_count = len(all_csv_rows)
    if csv_row_count != expected_rows:
        failures.append(f"❌ CSV row count mismatch: expected {expected_rows}, got {csv_row_count}")

    if failures:
        print("❌ JOB FAILED")
        print("\nFailure Summary:")
        for failure in failures:
            print(f"  {failure}")
        print("\nRoot Cause: Check logs above for API errors, authentication issues, or rate limit problems")
    else:
        print("✅ JOB COMPLETE")

    print(f"\nProcessed: {len(rows)} total rows available")
    print(f'Attempted: {expected_rows} rows ({len(batches)} batch{"es" if len(batches) != 1 else ""})')
    print(f"Successful Analysis: {len(all_complaints)} JSON items, {csv_row_count} CSV rows")
    print(f"Time Elapsed: {elapsed_time:.2f}s")
    print(f"Final JSON Output: {final_json_path}")
    print(f"Final CSV Output: {final_csv_path}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
