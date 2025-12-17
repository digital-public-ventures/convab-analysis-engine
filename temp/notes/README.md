# Notes Directory

**Current Status**: ✅ **Repo Boilerplate has been installed!** - Ready for planning and development!

See **[`./ADRs/001-repo-structure.md`](./ADRs/001-repo-structure.md)** for decision details and see **[`./temp/notes/README.md`](./temp/notes/README.md)** for usage.

---

**Purpose**: Planning documents, strategy analysis, design explorations, and work-in-progress documentation.

## Required Files

**CRITICAL:** The following files MUST always exist in `temp/notes/` root and MUST be updated after each agent request:

- **`ROADMAP.md`** - Long-term planning, major milestones, and strategic direction
- **`NEXT_STEPS.md`** (or `IMMEDIATE_NEXT_STEPS.md`) - Short-term actionable tasks and immediate priorities

These files serve as the project's living memory and ensure continuity across agent sessions. Always update them before completing any significant work.

## What Goes Here

**✅ Include:**

- Strategic planning documents (e.g., `PHASE2_PLANNING.md`, `MIGRATION_STRATEGY.md`)
- Design explorations and architectural analysis (e.g., `DATABASE_REDESIGN_OPTIONS.md`)
- Implementation planning and roadmaps (`ROADMAP.md`, `NEXT_STEPS.md`)
- Research and analysis documents (e.g., `PERFORMANCE_OPTIMIZATION_RESEARCH.md`)
- Work-in-progress documentation that hasn't been formalized yet
- Review and status documents (e.g., `SPRINT_REVIEW_2024_11.md`)
- Agent handoff documents (`HANDOFF.md`)
- Session-specific notes and observations

**❌ Exclude:**

- Architecture Decision Records (ADRs) → Go in `/ADRs/` directory
- Developer-facing documentation → Go in `/docs/`
- API reference documentation → Go in `/docs/API.md`
- Testing documentation → Go in `/docs/TESTING.md`
- Project conventions → Go in `/docs/` or `.cursorrules`

## Organization

**Active Notes** (root of `temp/notes/`):

- Keep only documents related to current, ongoing work
- Move completed work to `archive/YYYY-MM/` after extracting key decisions

**Archive** (`temp/notes/archive/`):

- Organized by month: `archive/2025-10/`, `archive/2025-11/`, etc.
- Each archived file should have a header with: archive date, reason, related ADRs, status

## When to Archive

Archive a note when:

1. The work described is complete
2. Architectural decisions have been extracted to ADRs
3. Any relevant information has been added to formal documentation
4. The note is no longer actively referenced

See `/docs/processes/NOTES_AND_ADR_MANAGEMENT.md` for detailed best practices.
