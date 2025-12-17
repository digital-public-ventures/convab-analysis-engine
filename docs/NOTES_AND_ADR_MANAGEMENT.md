# Notes and ADR Management Best Practices

**Purpose**: Guide for managing ephemeral notes, permanent documentation, and architectural decisions in agent-assisted workspaces.

**Last Updated**: 2025-12-17

---

## Table of Contents

- [Quick Decision Tree](#quick-decision-tree)
- [When to Create What](#when-to-create-what)
- [Note Lifecycle](#note-lifecycle)
- [ADR Lifecycle](#adr-lifecycle)
- [Documentation Lifecycle](#documentation-lifecycle)
- [Monthly Maintenance](#monthly-maintenance)

---

## Quick Decision Tree

```
Is this information needed beyond this session?
│
├─ NO → Create note in temp/notes/
│   │
│   └─ Is this about current work?
│       ├─ YES → Update NEXT_STEPS.md
│       └─ NO → Create new note file
│
└─ YES → Is this an architectural decision?
    │
    ├─ YES → Create ADR in ADRs/
    │   │
    │   └─ Examples:
    │       • Database schema changes
    │       • Framework/library choices
    │       • API design patterns
    │       • Security approaches
    │       • Build/deployment architecture
    │
    └─ NO → Add to docs/
        │
        └─ Examples:
            • Setup instructions
            • API usage guides
            • Deployment procedures
            • Contribution guidelines
```

---

## When to Create What

### temp/notes/ - Ephemeral Working Memory

**Purpose**: Agent planning, session context, debugging traces, temporary analysis.

**Create a note when**:

- Planning multi-step work that spans sessions
- Debugging complex issues and need to track hypotheses
- Analyzing problems before deciding on solutions
- Coordinating work between multiple agents
- Exploring design options (before ADR)

**File naming conventions**:

- `PHASE_N_*.md` - Phase-specific planning/summaries
- `DEBUG_*.md` - Debugging traces
- `ANALYSIS_*.md` - Problem analysis
- `SPIKE_*.md` - Exploratory research
- Dated files: `2025-12-17_feature_research.md`

**Lifespan**: Days to weeks. Archive when:

- Work is completed
- Issue is resolved
- Analysis informs an ADR
- Session context is no longer relevant

### ADRs/ - Architectural Decision Records

**Purpose**: Permanent record of significant architectural decisions and their context.

**Create an ADR when deciding**:

- **Data architecture**: Database choice, schema design, caching strategy
- **Technology selection**: Frameworks, libraries, build tools, deployment platforms
- **Architectural patterns**: Microservices vs monolith, event-driven vs request-response, layering
- **API design**: REST vs GraphQL, versioning strategy, authentication approach
- **Performance/scalability**: Load balancing, horizontal vs vertical scaling, CDN usage
- **Cross-cutting concerns**: Logging, monitoring, error handling, security model
- **Build/deployment**: CI/CD pipeline, container orchestration, infrastructure as code
- **Third-party integrations**: Payment processors, analytics, email services

**Do NOT create ADRs for**:

- Implementation details (function signatures, variable names)
- Bug fixes (unless they reveal architectural issues)
- Refactoring (unless changing patterns)
- Dependency updates (unless major version with breaking changes)
- Configuration values (unless the configuration strategy itself is architectural)

**ADR template**: See `ADRs/README.md`

**Lifespan**: Permanent. ADRs are **immutable** once accepted.

- To change a decision: Create new ADR that supersedes the old one
- Update old ADR status to "Superseded by ADR XXX"
- Reference original ADR in new ADR

### docs/ - Developer Documentation

**Purpose**: Stable, maintained documentation for developers using/contributing to the project.

**Create documentation when**:

- Setting up the project (QUICK_START.md)
- Explaining system architecture (README.md)
- Documenting APIs or interfaces
- Writing contribution guidelines
- Describing deployment procedures
- Explaining testing strategies

**Update frequency**: When behavior changes, new features added, or setup process modified.

**Lifespan**: Maintained indefinitely. Update as project evolves.

---

## Note Lifecycle

### 1. Creation

Create notes freely during active work:

```bash
# Planning a new feature
echo "# Feature X Planning" > temp/notes/PHASE_2_feature_x.md

# Debugging an issue
echo "# Debug: API timeout" > temp/notes/DEBUG_api_timeout.md

# Exploring options
echo "# Database Options Analysis" > temp/notes/ANALYSIS_database_options.md
```

### 2. Active Use

While working:

- Keep NEXT_STEPS.md updated with current tasks
- Update ROADMAP.md when priorities shift
- Add context to phase notes as you learn
- Document hypotheses in debug notes

### 3. Completion

When work finishes:

**Step 1: Extract decisions** → Create ADRs for any architectural choices

```bash
# If you chose PostgreSQL over MongoDB based on your analysis
# Create ADR before archiving the analysis note
```

**Step 2: Update documentation** → Add to docs/ if behavior changed

**Step 3: Archive the note** → Move to temp/notes/archive/

```bash
# Organize by year/month
mkdir -p temp/notes/archive/2025-11
mv temp/notes/PHASE_2_feature_x.md temp/notes/archive/2025-11/

# Add archival header to the note
```

**Archival header template**:

```markdown
---
**ARCHIVED**: 2025-12-17
**Reason**: Feature X completed and deployed
**Outcome**: Success - feature working as expected
**ADRs Created**: ADR 003 (PostgreSQL choice), ADR 004 (API design)
**Documentation Updated**: docs/API.md, docs/QUICK_START.md
---

# [Original note content follows...]
```

### 4. Archive Maintenance

Archives are **not trash** - they preserve context:

- Why decisions were made
- What alternatives were considered
- What problems were encountered
- How they were solved

**Do not delete archived notes**. They provide valuable context for:

- Understanding historical decisions
- Debugging similar issues
- Onboarding new team members
- Learning from past mistakes

---

## ADR Lifecycle

### 1. Creation

Use the template from `ADRs/README.md`:

```bash
# Next ADR number
NEXT_NUM=$(ls ADRs/*.md | grep -v README | wc -l | xargs -I {} expr {} + 1)

# Create from template
cat > ADRs/$(printf "%03d" $NEXT_NUM)-short-title.md << 'EOF'
# ADR XXX: [Title]

**Status**: Proposed
**Date**: 2025-12-17
**Decision Makers**: [Names]
**Consulted**: [Names]
**Informed**: [Names]

## Context and Problem Statement
...
EOF
```

### 2. Drafting

Fill in all sections:

- Context: What forces are at play?
- Decision: What did you decide?
- Consequences: What are the implications?
- Alternatives: What else did you consider?

### 3. Review

Before accepting:

- Have stakeholders reviewed it?
- Are consequences clearly understood?
- Are alternatives documented?

### 4. Acceptance

Change status to "Accepted" and commit:

```bash
# Update status in ADR file
sed -i '' 's/Status: Proposed/Status: Accepted/' ADRs/003-decision.md

# Commit
git add ADRs/003-decision.md
git commit -m "ADR 003: Accept database choice decision"
```

### 5. Superseding (if needed)

To change an accepted decision:

1. Create new ADR with updated decision
2. Reference original: "Supersedes ADR 003"
3. Update original ADR status: "Status: Superseded by ADR 008"
4. Explain why the change was needed

**Example**:

```markdown
# ADR 008: Migrate from PostgreSQL to MongoDB

**Status**: Accepted
**Date**: 2025-12-15
**Supersedes**: ADR 003

## Context

Since ADR 003 (PostgreSQL choice), our data access patterns have changed significantly...

## Why the Change?

ADR 003 was correct given the information at the time. However:

- Our workload is now 90% read-heavy with flexible schema needs
- PostgreSQL JSON queries are hitting performance limits
- MongoDB's aggregation pipeline better matches our analytics needs

## Decision

Migrate to MongoDB for the following components...
```

---

## Documentation Lifecycle

### 1. Creation

Create documentation when:

- Building a new feature with user-facing behavior
- Establishing setup procedures
- Defining contribution guidelines

### 2. Maintenance

Update docs when:

- Setup process changes
- API contracts change
- New features are added
- Deployment procedures change

### 3. Review

Periodically check:

- Are setup instructions still accurate?
- Do examples still work?
- Are screenshots up to date?
- Are links still valid?

---

## Monthly Maintenance

**First day of each month**: Review and clean up notes.

### Checklist

- [ ] Review all files in `temp/notes/` root
- [ ] Archive completed work:
  - [ ] Extract architectural decisions → Create ADRs
  - [ ] Update docs/ if behavior changed
  - [ ] Add archival header
  - [ ] Move to `temp/notes/archive/YYYY-MM/`
- [ ] Review ROADMAP.md:
  - [ ] Mark completed phases
  - [ ] Adjust timelines if needed
  - [ ] Add new phases if priorities changed
- [ ] Review NEXT_STEPS.md:
  - [ ] Clear completed tasks
  - [ ] Reprioritize remaining work
  - [ ] Add new immediate tasks
- [ ] Review ADRs:
  - [ ] Any need status updates?
  - [ ] Any need to be superseded?
- [ ] Review docs:
  - [ ] Test setup instructions
  - [ ] Verify examples work
  - [ ] Update stale content

### Script Helper

```bash
#!/bin/bash
# monthly_cleanup.sh - Helper for monthly maintenance

CURRENT_MONTH=$(date +%Y-%m)
ARCHIVE_DIR="temp/notes/archive/$CURRENT_MONTH"

mkdir -p "$ARCHIVE_DIR"

echo "📋 Monthly Notes Cleanup - $CURRENT_MONTH"
echo ""
echo "Files in temp/notes/ (excluding ROADMAP, NEXT_STEPS, README):"
echo ""

find temp/notes/ -maxdepth 1 -type f \
  ! -name "ROADMAP.md" \
  ! -name "NEXT_STEPS.md" \
  ! -name "README.md" \
  -exec ls -lh {} \;

echo ""
echo "Review each file and decide:"
echo "  1. Is work complete? → Archive it"
echo "  2. Does it contain architectural decisions? → Create ADR first"
echo "  3. Does it update behavior? → Update docs/ first"
echo ""
echo "Then move to: $ARCHIVE_DIR/"
```

---

## Anti-Patterns to Avoid

### ❌ Leaving Completed Notes in Root

**Bad**:

```
temp/notes/
├── PHASE_1_COMPLETE.md    # ← Stale
├── PHASE_1_SUMMARY.md     # ← Stale
├── DEBUG_solved.md        # ← Stale
└── NEXT_STEPS.md
```

**Good**:

```
temp/notes/
├── NEXT_STEPS.md
├── ROADMAP.md
└── archive/
    └── 2025-11/
        ├── PHASE_1_COMPLETE.md
        ├── PHASE_1_SUMMARY.md
        └── DEBUG_solved.md
```

### ❌ Archiving Without Extracting Decisions

**Bad**: Archive `ANALYSIS_database_options.md` without creating ADR

**Good**:

1. Create ADR 003: Database Choice (PostgreSQL)
2. Add archival header referencing ADR 003
3. Archive the analysis note

### ❌ Editing Accepted ADRs

**Bad**: Edit ADR 003 to change the decision

**Good**:

1. Create ADR 008 that supersedes ADR 003
2. Update ADR 003 status: "Superseded by ADR 008"
3. Explain in ADR 008 why the change was needed

### ❌ Creating ADRs for Implementation Details

**Bad**: ADR 015: Use camelCase for JavaScript variables

**Good**: Add to .eslintrc or .editorconfig instead

### ❌ Never Updating Documentation

**Bad**: Add feature, never update docs/

**Good**: Update docs/ in same PR as feature

---

## Summary

**Three-tier system**:

1. **temp/notes/** - Ephemeral (days to weeks)
   - Planning, debugging, exploration
   - Archive when complete

2. **ADRs/** - Permanent and immutable
   - Architectural decisions only
   - Supersede rather than edit

3. **docs/** - Maintained indefinitely
   - Developer-facing documentation
   - Update as project evolves

**Key principles**:

- Notes are temporary → Archive frequently
- ADRs are permanent → Never edit, supersede instead
- Docs are living → Keep up to date
- Always extract decisions before archiving notes
- Monthly cleanup prevents clutter
- Archives preserve context, never delete

---

## See Also

- [ADR Template](../ADRs/README.md)
- [Repository Structure (ADR 001)](../ADRs/001-repo-structure.md)
- [Quick Start Guide](QUICK_START.md)
