# Smart Dogfood Documentation

**Purpose**: Document the intelligent template update system that preserves user work while applying template improvements.

---

## Overview

`smart-dogfood.sh` is an intelligent template update system that safely applies template improvements to your workspace without destroying custom work. It implements **ADR 002: Smart Template Update System**.

### Key Features

✅ **Safe Updates**: Never loses user work
✅ **Automatic Backup**: Creates git stash before each update
✅ **Dry-Run Mode**: Preview changes before applying
✅ **Three-Tier Classification**: Template-only, user-content, hybrid files
✅ **Smart Merging**: Intelligently merges hybrid files like `.gitignore`

---

## Quick Start

### Basic Usage

```bash
# Apply template updates (safe - creates backup first)
./smart-dogfood.sh

# Preview what would change (recommended first time)
./smart-dogfood.sh --dry-run

# Show detailed progress
./smart-dogfood.sh --verbose
```

### First-Time Workflow

```bash
# 1. Preview changes
./smart-dogfood.sh --dry-run

# 2. Apply updates
./smart-dogfood.sh

# 3. Review what changed
git diff

# 4. If happy, commit
git add -A
git commit -m "Apply template updates"

# 5. If unhappy, rollback
git stash pop  # Restores previous state
```

---

## File Classification

Smart-dogfood classifies files into three categories:

### 1. Template-Only Files (Always Updated)

Files that users should never modify - template improvements applied automatically.

**Examples**:

- `.github/` workflows and templates
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `LICENSE`, `SECURITY.md`
- `docs/*.md` (except custom additions)
- Tooling configs: `.editorconfig`, `.prettierrc`, `ruff.toml`, etc.
- `temp/notes/HANDOFF.md` (template)

**Behavior**: Always replaced with latest template version

### 2. User-Content Files (Preserved)

Files that are entirely user-controlled - never overwritten.

**Examples**:

- `README.md` (your project description)
- `temp/notes/ROADMAP.md` (your plans)
- `temp/notes/NEXT_STEPS.md` (your task list)
- `temp/notes/SELF_OBSERVATIONS.md` (your observations)
- `temp/notes/archive/` (your archived notes)
- `ADRs/002-*.md` and above (your ADRs)
- Custom markdown files in `temp/notes/`

**Behavior**: Created if missing, preserved if exists

### 3. Hybrid Files (Smart Merge)

Files with both template structure and user content - require intelligent merging.

**Examples**:

- `.gitignore` (template patterns + your additions)
- `.dockerignore` (template patterns + your additions)
- `CHANGELOG.md` (template format + your entries)

**Behavior**:

- **Append Mode** (`.gitignore`, `.dockerignore`): New template patterns appended, user patterns preserved
- **Section Merge** (`CHANGELOG.md`): Template sections updated, user entries preserved

---

## Options

### `--dry-run`

Preview changes without applying them. Shows exactly what would be updated, preserved, or merged.

```bash
./smart-dogfood.sh --dry-run
```

**Output Example**:

```
→ [DRY-RUN] Would update (template-only): docs/TESTING.md
  Preserving existing user-content: README.md
→ [DRY-RUN] Would merge (append): .gitignore
```

### `--verbose` / `-v`

Show detailed information about each file processed.

```bash
./smart-dogfood.sh --verbose
```

**Output includes**:

- File classification for each file
- Whether file matches template or differs
- Detailed merge operations

### `--help` / `-h`

Show usage information.

```bash
./smart-dogfood.sh --help
```

---

## How It Works

### 1. Pre-Update Backup

Before any changes, smart-dogfood creates a git stash:

```bash
git stash push -m "dogfood-backup-TIMESTAMP"
```

This allows instant rollback if anything goes wrong.

### 2. File Classification

For each template file, smart-dogfood determines its classification:

```bash
if .github/* or CONTRIBUTING.md or LICENSE:
    → template-only (always update)
elif README.md or temp/notes/ROADMAP.md or ADR 002+:
    → user-content (preserve)
elif .gitignore or CHANGELOG.md:
    → hybrid (smart merge)
```

### 3. Update Strategy

Based on classification:

- **Template-Only**: Copy from `templates/` → workspace
- **User-Content**: Copy only if missing, preserve if exists
- **Hybrid**: Intelligent merge (append new patterns, preserve user content)

### 4. Result

All updates applied safely with user work preserved.

---

## Safety Features

### Automatic Backup

Every run creates a git stash backup **before** making any changes.

**Rollback Command**:

```bash
git stash pop
```

This restores your workspace to the exact state before the update.

### Dry-Run Mode

Test updates without risk:

```bash
./smart-dogfood.sh --dry-run
```

Shows exactly what would change without modifying any files.

### Git Integration

Requires clean git working directory (all changes committed) before running. This ensures:

- No accidental loss of uncommitted work
- Clean rollback if needed
- Clear diff of what changed

---

## Troubleshooting

### "ERROR: Git working directory not clean"

**Problem**: You have uncommitted changes.

**Solution**:

```bash
# Commit your changes
git add -A
git commit -m "Your work"

# Then run smart-dogfood
./smart-dogfood.sh
```

### "Template directory not found"

**Problem**: Script can't find `templates/` directory.

**Solution**: Run from repository root where `templates/` exists.

### Unwanted Changes After Update

**Problem**: Update changed something you didn't want changed.

**Solution**:

```bash
# Rollback entire update
git stash pop

# Or selectively restore specific files
git checkout HEAD -- path/to/file
```

### Merge Conflict in Hybrid File

**Problem**: Smart merge failed for hybrid file.

**Current Behavior**: Falls back to preserving existing file.

**Solution**: Manually merge template improvements from `templates/path/to/file`.

---

## Edge Cases

### Custom Modifications to Template-Only Files

If you've customized a template-only file (e.g., `docs/TESTING.md`), smart-dogfood will overwrite it.

**Workaround**:

1. Move your custom content to a new file (e.g., `docs/PROJECT_TESTING.md`)
2. Let smart-dogfood update the template file
3. Reference your custom file from the template file

**Better Solution** (future): Add `--preserve <file>` flag to override classification.

### New Template Files

When templates add new files, smart-dogfood automatically creates them in your workspace.

**Review New Files**:

```bash
git status  # Shows new files
git diff --cached  # Shows new file content
```

### Deleted Template Files

If a file is removed from templates, smart-dogfood doesn't delete it from your workspace (preserves existing).

**Manual Cleanup**: Review and delete if no longer needed.

---

## Comparison with old workflows

### safe-dogfood.sh (Previous - Removed 2025-12-17)

**Approach**: Run dogfood.sh, then git checkout specific files

**Pros**: Simple wrapper

**Cons**:

- Brittle (hardcoded file list)
- Doesn't scale
- Manual maintenance

**Status**: ✅ Removed (replaced by smart-dogfood.sh)

### dogfood.sh --overwrite (Original)

**Approach**: Blindly replace all files

**Pros**: Simple

**Cons**:

- ❌ Destroys all user work
- ❌ Requires manual backup/restore
- ❌ High risk

**Status**: ⚠️ Still exists for destructive updates (use with caution)

### smart-dogfood.sh (Current)

**Approach**: Intelligent classification and selective updating

**Pros**:

- ✅ Safe (automatic backup)
- ✅ Preserves user work
- ✅ Smart merging
- ✅ Dry-run mode
- ✅ Scales well

**Cons**:

- More complex implementation
- Requires git

**Status**: ✅ **Recommended for all template updates**

---

## Architecture

See **[ADR 002: Smart Template Update System](../ADRs/002-smart-template-updates.md)** for full architectural details.

**Key Decisions**:

- Three-tier file classification
- Git-based change detection
- Stash-based backup mechanism
- Append mode for ignore files
- Dry-run for safety

---

## Examples

### Scenario 1: First Template Update

You've been using the cfpb-exploration template for a month. New template improvements are available.

```bash
# 1. Preview what would change
./smart-dogfood.sh --dry-run

# Output shows:
# → [DRY-RUN] Would update (template-only): docs/TESTING.md
#   Preserving existing user-content: README.md
#   Preserving existing user-content: temp/notes/ROADMAP.md

# 2. Looks good! Apply updates
./smart-dogfood.sh

# 3. Review changes
git diff

# 4. Commit
git add -A && git commit -m "Update from template"
```

### Scenario 2: Rollback After Update

Applied update but don't like the changes.

```bash
# Apply update
./smart-dogfood.sh

# Review and decide to rollback
git diff

# Rollback (restores previous state)
git stash pop

# Now back to state before update
```

### Scenario 3: Regular Template Sync

Keep workspace in sync with template improvements.

```bash
# Weekly or monthly:
./smart-dogfood.sh
git diff
git add -A && git commit -m "Sync with template updates"
```

---

## Future Enhancements

Planned improvements to smart-dogfood:

- **Section merge for CHANGELOG.md**: Intelligent merge of changelog entries
- **Three-way merge**: Use `git merge-file` for complex merges
- **Selective updates**: `./smart-dogfood.sh --only docs/` to update specific areas
- **Force flags**: `--preserve <file>` and `--force-update <file>` to override classification
- **Update notifications**: Check if template has improvements available
- **Version tracking**: Track which template version workspace is at

---

## Related Documentation

- **[ADR 002: Smart Template Update System](../ADRs/002-smart-template-updates.md)** - Architectural decision record
- **[NOTES_AND_ADR_MANAGEMENT.md](./NOTES_AND_ADR_MANAGEMENT.md)** - File organization guidance
- **[ADR 001: Repository Structure](../ADRs/001-repo-structure.md)** - Repository organization

---

## Support

**Issues**: If smart-dogfood doesn't work as expected:

1. Check git status (must be clean)
2. Try `--dry-run` first
3. Use `--verbose` for detailed output
4. Review ADR 002 for classification logic

**Contributing**: To improve file classification or merge strategies, see `smart-dogfood.sh` source code and ADR 002.
