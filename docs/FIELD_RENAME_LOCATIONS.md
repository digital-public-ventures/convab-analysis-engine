# Field Rename Locations: Hardcoded References

**Summary**: Field names are NOT hardcoded in active Python source code. References exist only in:
1. Schema files (generated outputs from past experiments)
2. Data files (output CSVs and JSONs from past analysis runs)
3. Documentation files (newly created)

---

## 1. Schema Files (Generated - Not Code)

### Active Schema Files

**File**: `app/schema/prompts/response_schema_old.json`
- **Status**: Old/archived schema reference file
- **Contains**: `"representative_narrative_snippets"` (line 348)
- **Action**: No change needed (historical reference)

---

### Generated Experiment Schema

**File**: `app/tests/fixtures/efa267c019c11e33cf61afe5ffcf9d2b1fa8dbdcd987b83e911eeea795812334/schema/schema.json`
- **Status**: Generated schema from your medical payment products experiment
- **Contains**: `"representative_narrative_snippets"` (line 214)
- **Action**: This will be auto-regenerated on next experiment run using updated base schema

**File**: `app/data/efa267c019c11e33cf61afe5ffcf9d2b1fa8dbdcd987b83e911eeea795812334/schema/schema.json`
- **Status**: Copy of above (same data hash)
- **Contains**: `"representative_narrative_snippets"` (line 214)
- **Action**: Will update when next experiment generates new schema

---

## 2. Data Output Files (From Past Experiments)

### CSV Analysis Output

**Files**:
- `app/data/efa267c019c11e33cf61afe5ffcf9d2b1fa8dbdcd987b83e911eeea795812334/analyzed/analysis.csv`
- `app/data/efa267c019c11e33cf61afe5ffcf9d2b1fa8dbdcd987b83e911eeea795812334/post-processing/analysis_deduped.csv`
- `app/data/archive/efa267c019c11e33cf61afe5ffcf9d2b1fa8dbdcd987b83e911eeea795812334/analyzed/analysis.csv`
- `app/data/archive/efa267c019c11e33cf61afe5ffcf9d2b1fa8dbdcd987b83e911eeea795812334/post_processing/analysis_deduped.csv`

**Status**: Historical data outputs
**Contains**: CSV headers with old field names
**Action**: These are data artifacts. No code changes needed. If you want to migrate old data:
- Create a migration script to rename CSV columns
- Or keep as-is for historical reference (recommended)

### JSON Analysis Output

**Files**:
- `app/data/efa267c019c11e33cf61afe5ffcf9d2b1fa8dbdcd987b83e911eeea795812334/analyzed/analysis.json`
- `app/data/efa267c019c11e33cf61afe5ffcf9d2b1fa8dbdcd987b83e911eeea795812334/post-processing/mappings.json`
- `app/data/archive/...` (same files in archive)

**Status**: Historical data outputs
**Contains**: JSON keys with old field names
**Action**: Same as CSV files - no code changes needed

---

## 3. Documentation Files (Newly Created)

**Files**:
- `docs/SCHEMA_REVIEW.md` - Contains old field names in examples and discussion
- `docs/SCHEMA_UPDATES_SUMMARY.md` - Documents the rename changes
- `docs/FIELD_RENAME_LOCATIONS.md` - This file

**Status**: Documentation/reference
**Action**: No changes needed (they document the changes correctly)

---

## 4. Active Python Source Code

**Result**: ✅ NO hardcoded references found in:
- `app/analysis/*.py`
- `app/llm/*.py`
- `app/schema/*.py`
- `app/processing/*.py`
- `app/server.py`
- `app/tests/*.py`
- `app/config.py`

**Why**: Your codebase dynamically extracts fields from the generated schema JSON at runtime, rather than hardcoding field names. This is excellent architecture!

---

## Code Paths That Handle Schema Dynamically

Here are the key areas that read schemas at runtime (so they'll automatically work with renamed fields):

```
app/schema/generator.py
  └─ Reads base schema (response_schema_example.json)
  └─ Generates merged schema from LLM output
  └─ Field names are dynamic keys, not hardcoded

app/analysis/analyzer.py
  └─ Reads generated schema at runtime
  └─ Iterates over schema fields dynamically
  └─ No hardcoded field references

app/server.py
  └─ Loads schema from file system
  └─ Passes to analysis pipeline
  └─ Field extraction is schema-driven

app/processing/attachment.py
  └─ Processes analysis output
  └─ No hardcoded field dependencies

app/tests/
  └─ E2E tests use fixture schema
  └─ Will use updated schema from fixtures
```

---

## Impact Assessment: Minimal Code Changes Required

| Category | Files | Change Needed | Effort |
|----------|-------|---------------|--------|
| **Python Source** | All `app/` code | ❌ No | 0 hours |
| **Schema Files** | `response_schema_example.json` | ✅ Already done | Complete |
| **Generated Schemas** | Fixture & data schemas | ℹ️ Auto-regenerate | Next experiment |
| **Data Outputs** | Historical CSV/JSON | ❌ No (optional cleanup) | 0-2 hours |
| **Documentation** | Docs/ files | ✅ Already updated | Complete |

---

## What Happens Next

### Next Experiment Run
When you run the schema generation process on a new dataset:

1. ✅ Base schema (updated) will be used as input
2. ✅ LLM will generate merged schema using new field names
3. ✅ Analysis will use new schema
4. ✅ Output will have new field names

### If You Run Analysis with Old Data
If you need to re-analyze using the old medical payment products data:

1. **Option A** (Recommended): Regenerate schema and re-run analysis
   - New outputs will have new field names
   - Old outputs can remain as historical reference

2. **Option B**: Create a field mapping layer
   ```python
   # In analysis pipeline, add mapping if needed:
   OLD_TO_NEW_FIELD_MAPPING = {
       "reported_harms_and_impacts": "reported_harmful_impacts",
       "reported_benefits": "reported_beneficial_impacts",
       "representative_narrative_snippets": "lived_experience_quotes"
   }
   ```

---

## Recommended Actions

### ✅ Complete (No Action Needed)
- [x] Base schema updated (`response_schema_example.json`)
- [x] Field names changed
- [x] Hints updated
- [x] Sentinel values standardized

### ℹ️ Optional (On Next Experiment)
- [ ] Archive old experiment data (historical reference)
- [ ] Regenerate schema and re-run analysis if needed
- [ ] Update any notebooks or reports that reference old field names

### 📋 No Code Changes Required
- Python source code uses dynamic schema loading
- No hardcoded field names to update
- All systems will automatically use new schema

---

## Historical Field References Summary

For reference, here are all the old field names and where they still appear:

| Old Field Name | Appears In | Qty | Notes |
|---|---|---|---|
| `reported_harms_and_impacts` | Data output files | 5 files | Historical data only |
| `reported_benefits` | Data output files | 5 files | Historical data only |
| `representative_narrative_snippets` | Schema files + data | 7 files | Will auto-update on next run |
| | Docs | 2 files | Documentation only |

---

## Conclusion

✅ **No emergency code changes needed**

Your codebase is well-architected to handle schema changes gracefully:
- Fields are dynamically loaded from schema files
- No hardcoded field names in Python
- Next experiment will automatically use new schema
- Historical data can coexist with new data

**Next step**: Run a new experiment with a test dataset to validate that the updated schema produces expected outputs with the new field names.
