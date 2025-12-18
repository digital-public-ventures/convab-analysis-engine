# GitHub Copilot Instructions for this Project

## BEFORE Starting ANY Work

**⚠️ REQUIRED READING** - Do these steps FIRST, before writing any code:

1. **Read `system_prompt.md`** (5 min) - Project values, priorities, agent personality, decision framework
   - Located in repository root
   - Defines how agents should behave on this project
   - Contains workflow principles and common scenarios
2. **Read `temp/notes/NEXT_STEPS.md`** (2 min) - Current priorities and immediate context
   - What's the current focus?
   - What was just completed?
   - What blockers exist?
3. **Read `docs/evaluation/ACCEPTANCE_CRITERIA.md`** (3 min) - Definition of "done" for your change type
   - Find the section matching your work (feature, bugfix, refactor, docs, etc.)
   - Review what "complete" means for this type of change
   - Keep these criteria in mind during implementation
4. **Review relevant ADRs** (5 min) - Architectural context for your area
   - Check `ADRs/README.md` for active decisions
   - Read ADRs related to your work area
   - Understand why past decisions were made
5. **Scan recent git log** (2 min) - Latest changes and patterns
   - Run: `git log --oneline -10`
   - Understand recent work and momentum
   - Check for related changes or conflicts

**Total time investment**: ~15-20 minutes

**Why this matters**:

- Skipping these docs leads to violating established patterns, missing quality standards, and repeating past mistakes
- These docs exist specifically to guide agent behavior
- Reading them ensures consistency across sessions and agents
- The 15 minutes spent here saves hours of rework later

**If pressed for time**: At minimum, read #1 (system_prompt.md) and #2 (NEXT_STEPS.md)

---

## Development Workflow

1. ✅ **Complete "BEFORE Starting ANY Work" section above** (don't skip!)
2. Create feature branch
3. Write tests first (TDD preferred)
4. Implement functionality
5. Run quality checks (lint, format, type check, test - adjust commands for your language/tooling)
6. **Before committing**: Complete verification checklist (see "Quality Verification" section below)
7. Update `docs/` if needed (especially ADRs for architectural changes)
8. Review `temp/notes` and move completed or obsolete notes to `temp/notes/archive/`. **DO NOT NOT LEAVE _PHASE_X_COMPLETE.md_ OR _PHASE_X_SUMMARY.md_ FILES IN THE ROOT OF `temp/notes/`**
9. Update `temp/notes/NEXT_STEPS.md` to reflect next actions and short term planning
10. Update `temp/notes/ROADMAP.md` to reflect current status of long term plans and goals
11. Submit PR with verification checklist reference

---

## AFTER Completing Work

**⚠️ REQUIRED - Do these BEFORE moving to next task:**

These steps ensure clean handoff to the next agent/session. The 10-20 minutes spent here saves hours of "What was I working on?" later.

### 1. Complete Verification Checklist (5-15 min)

Choose based on change size:

- **Quick** (< 50 lines): Answer 3 questions (see "Quality Verification" section below)
- **Standard** (50-200 lines): Complete 5-point checklist
- **Full** (> 200 lines or architectural): Complete full `VERIFICATION_CHECKLIST.md`

See "Quality Verification" section below for details.

### 2. Update Session Context (2-5 min) - CRITICAL

**Why this matters**: Next agent relies on `NEXT_STEPS.md` to understand current state. Stale `NEXT_STEPS.md` breaks workflow continuity and wastes time.

**Update `temp/notes/NEXT_STEPS.md` with**:

1. What you just completed (with file references)
2. Current status/decision point
3. What's next (specific, actionable tasks)
4. Key context files to read
5. Blockers (if any)

**Template to use**:

```markdown
## Current Context

✅ **What's Complete**: [Brief summary]
📋 **Current Focus**: [What you're working on now / decision pending]
⚠️ **Blockers**: [Any blockers, or "None"]

## What Just Happened

Session: [session-id or date]
Last Updated: [YYYY-MM-DD]

1. **Deliverable 1**: Brief description (see `path/to/file.md`)
2. **Deliverable 2**: Brief description (see `path/to/file.md`)
3. **Deliverable 3**: Brief description (see `path/to/file.md`)

## Decision Point / Next Actions

Choose one:

**Option A**: [Description]

- [ ] Specific task 1
- [ ] Specific task 2

**Option B**: [Description]

- [ ] Specific task 1
- [ ] Specific task 2

## Key Context for Next Agent

Before starting work, read:

1. `path/to/key/file.md` - [Why it's important]
2. `path/to/another/file.md` - [Why it's important]
3. Decision pending: [What needs to be decided]
```

**Also update `temp/notes/ROADMAP.md`** if phase/milestone changed.

### 3. Archive Completed Notes (1-2 min)

Keep `temp/notes/` root clean - only active work should be there.

```bash
# Move completed notes to archive
mv temp/notes/PHASE_X_COMPLETE.md temp/notes/archive/
mv temp/notes/ANALYSIS_*.md temp/notes/archive/

# Add header to archived files referencing related ADRs
```

**Before archiving**: Extract architectural decisions to ADRs (see "Notes and ADR Management" section).

### 4. Commit with Context (1 min)

Your commit message should include:

- What changed
- Why (link to issue/ADR if applicable)
- Verification completed (quick/standard/full)
- Reference to updated `NEXT_STEPS.md` if significant session work

**Example**:

```bash
git commit -m "feat: Add feature X

Implements [issue/feature description].
See ADR 004 for architectural decision.

Completed standard verification checklist.
Updated NEXT_STEPS.md with current status and decision point."
```

**Total time**: ~10-20 minutes

**Why this matters**: Ensures clean handoff. Without this, the next agent/session will waste time reconstructing context, may miss key decisions, and could duplicate work or break continuity.

---

## Terminal Command Best Practices

### CRITICAL: Background Process Management

The VSCode RunInTerminal function's `isBackground` argument does not create a background process. It simply creates a new terminal. It is critical to use `isBackground: true` to create a new terminals when you already have an existing process and you want to sleep or check on it.

1. **You should prefer writing stdout/stderr to file instead of using `get_terminal_output`**
   - Stream logs to a logs folder and read from there
   - Use `get_terminal_output` only for quick status checks

2. **ALWAYS check if a process is running in a terminal before executing new commands**
   - Use `get_terminal_output` to check the state of any active terminals
   - Never run commands in a terminal that has a background process running
   - If there is a process running, use `isBackground: true` to open a new terminal to sleep or check status

3. **Never use `sleep` command without specifying `isBackground: true`**
   - If you don't use `isBackground: true`, it will interrupt the current process with SIGINT
   - Instead, use `isBackground: true` to wait asynchronously

4. **For sequential operations requiring wait time:**
   - Always use `isBackground: true` for the second and all future commands
   - Use `get_terminal_output` to check status
   - Run subsequent commands in a fresh terminal session that uses `isBackground: true`

### Docker-Specific Guidelines (if using Docker)

1. **Building and starting containers:**

   ```bash
   # CORRECT - runs in background
   docker compose up --build -d
   ```

2. **Checking container status:**

   ```bash
   # Use a separate command after the build completes
   docker compose ps
   ```

   Set `isBackground: true`

3. **Viewing logs:**
   ```bash
   docker compose logs --tail=N service_name
   ```
   Set `isBackground: true`

### Notes and ADR Management

**IMPORTANT:** Keep the repository clean and organized by managing notes and architectural decisions properly. See **[`docs/NOTES_AND_ADR_MANAGEMENT.md`](./docs/NOTES_AND_ADR_MANAGEMENT.md)** for complete best practices.

**Quick Guidelines:**

- **Active work only in `temp/notes/` root** - Keep only notes about current, ongoing work
- **Archive completed work** - Move finished notes to `temp/notes/archive/` after extracting decisions
- **Capture decisions in ADRs** - Before archiving notes, ensure architectural decisions are documented as ADRs
- **Monthly cleanup** - Review and archive stale notes, verify ADR coverage

**Workflow for Completing Work:**

1. **Extract decisions** → Create ADRs for architectural choices
2. **Update docs** → Add to formal documentation if needed
3. **Archive notes** → Move to `temp/notes/archive/` with header referencing ADRs
4. **Never delete** → Archive instead, preserving context

**When to Create an ADR:**

- Database schema changes
- Technology/framework choices
- Architectural patterns (e.g., repository pattern, service layer, event-driven, etc.)
- API design decisions
- Performance/scalability trade-offs
- Cross-cutting concerns (logging, error handling, authentication, etc.)
- Build/deployment architecture
- Third-party service integrations

**Anti-patterns:**

- Leaving completed notes (e.g., `PHASE_X_COMPLETE.md`) in `temp/notes/` root
- Archiving without extracting architectural decisions to ADRs
- Editing accepted ADRs (create superseding ADR instead)
- Creating ADRs for implementation details (only for architectural decisions)

## Key Documentation

**IMPORTANT:** the `docs/` folder is for developer-facing documentation. The `temp/` folder is agent-facing planning docs, summaries, notes and debug scripts.

- **[ADRs](./ADRs/README.md)** - Architecture Decision Records document all major design decisions
- **[Detailed Documentation](./docs/README.md)** - Complete system overview and guides
- **[Scripts Documentation](./scripts/README.md)** - Utility scripts for setup and maintenance, **DO NOT place temporary, debug or testing scripts in `scripts/`**
- **README.md** - User-facing documentation with quick start guide

### Architecture Decision Records (ADRs)

When making architectural decisions, document them as ADRs following the template in `ADRs/README.md`.

**Important**: ADRs are immutable once accepted. Do not edit existing ADRs. Instead:

- Create a new ADR that supersedes the old one
- Reference the original ADR in the new one (e.g., "Supersedes ADR 005")
- Update the old ADR's status to "Superseded by ADR XXX"

This preserves the historical decision-making context and prevents confusion about what was decided when.

## Project Overview

CFPB data exploration and analysis

### Setup and Deployment

See `docs/QUICK_START.md` for setup instructions and `README.md` for deployment details.

### Application Structure

See `README.md` for project structure and organization.

### Language/Framework-Specific Guidelines

**Quality Checks**: Customize this based on your project's language and tooling. Examples:

- **Python**: `black . && ruff check . && mypy . && pytest`
- **Node.js/TypeScript**: `npm run lint && npm run type-check && npm test`
- **Go**: `go fmt ./... && go vet ./... && go test ./...`
- **Rust**: `cargo fmt -- --check && cargo clippy && cargo test`
- **Java**: `mvn checkstyle:check && mvn test`

Adjust the workflow step 5 above to match your project's specific commands.

## Quality Verification

**Before committing**, complete verification based on change size:

### Quick Verification (< 50 lines, simple changes)

Answer these 3 questions:

1. Is it correct? (Does it work as intended?)
2. Is it clear? (Can others understand it?)
3. Is it complete? (Docs updated, no TODOs left?)

### Standard Verification (50-200 lines, typical changes)

Use this 5-point checklist:

- [ ] **Correctness**: Code works as intended, edge cases handled
- [ ] **Tests**: Added/updated tests for new functionality
- [ ] **Documentation**: Updated relevant docs (README, API docs, comments)
- [ ] **Backward Compatibility**: No breaking changes (or properly documented)
- [ ] **Quality**: Follows project conventions, passes lint/format checks

### Full Verification (> 200 lines or architectural changes)

Complete the full verification checklist:

1. Copy `docs/evaluation/VERIFICATION_CHECKLIST.md` to `temp/notes/CURRENT_VERIFICATION.md`
2. Fill out all 13 sections
3. Reference in commit message: "See temp/notes/CURRENT_VERIFICATION.md"
4. Include in PR description

See `docs/evaluation/README.md` for the complete evaluation framework.

---

**Remember**: Quality verification isn't bureaucracy - it's catching issues before they become production bugs. The few minutes spent here save hours of debugging later.
