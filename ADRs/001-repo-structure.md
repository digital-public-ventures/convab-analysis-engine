# ADR 001: Repository Structure and Organization

**Status**: Accepted

**Date**: {{CURRENT_DATE}}

**Decision Maker**: Jim Moffet

**Stakeholders**: Development Team, AI Coding Agents

---

## Context

This repository was initialized using an agent-friendly cfpb-exploration template that emphasizes:

1. **Clear separation of concerns** between developer docs, architectural decisions, and agent planning
2. **Living documentation** that evolves with the project
3. **Agent-friendly workflows** that enable AI assistants to work effectively across sessions
4. **Best practices** for collaborative human-agent development

Key requirements:

- Developers need formal documentation (`docs/`) for setup, APIs, and guides
- Architectural decisions need permanent records (ADRs) for context and rationale
- Agents need planning workspace (`temp/notes/`) for work-in-progress and session continuity
- GitHub workflows benefit from structured PR/issue templates
- Project needs standard community files (LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY)

---

## Decision

Implement a **three-tier documentation system** with clear boundaries and specific purposes:

### 1. `/docs/` - Developer-Facing Documentation

- **Purpose**: Formal, stable documentation for human developers
- **Contents**: Setup guides, API references, architecture overviews, deployment docs
- **Audience**: New developers, contributors, operators
- **Lifecycle**: Updated when features change, kept current with main branch

### 2. `/ADRs/` - Architecture Decision Records

- **Purpose**: Immutable record of significant architectural choices
- **Contents**: Numbered ADRs (001, 002, etc.) documenting key decisions with context and rationale
- **Audience**: Developers, architects, future maintainers
- **Lifecycle**: Write-once, never edit (supersede with new ADR if decision changes)

### 3. `/temp/notes/` - Agent Planning and Working Memory

- **Purpose**: Work-in-progress planning, agent session continuity, ephemeral documentation
- **Contents**:
  - **Required**: `ROADMAP.md` and `NEXT_STEPS.md` (living documents, always present)
  - Strategy docs, design explorations, implementation plans
  - `archive/YYYY-MM/` for completed work
- **Audience**: AI coding agents, developers actively working on features
- **Lifecycle**: Active notes in root, archive when complete, extract decisions to ADRs

### 4. `.github/` - GitHub Integration

- **Purpose**: Pull request templates, issue templates, GitHub-specific configs
- **Contents**:
  - Multiple PR templates (feature, bugfix, chore, docs, hotfix, infra, data-service)
  - Issue templates (bug report, feature request)
  - `copilot-instructions.md` for GitHub Copilot workspace guidance
- **Audience**: Contributors, PR authors, GitHub bots
- **Lifecycle**: Evolves with project workflow needs

### 5. Root-Level Community Files

- **Purpose**: Standard open-source project files
- **Contents**: README.md, LICENSE, CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, CHANGELOG.md
- **Audience**: External contributors, users, security researchers
- **Lifecycle**: Stable, updated infrequently

---

## Consequences

### Positive

✅ **Clear boundaries**: Developers know where to find stable docs, agents know where to plan

✅ **Session continuity**: `ROADMAP.md` and `NEXT_STEPS.md` ensure agents can resume work across sessions

✅ **Historical context**: ADRs preserve "why" behind decisions, preventing revisiting settled questions

✅ **Reduced noise**: `temp/notes/` keeps work-in-progress out of formal documentation

✅ **Scalable**: Archive structure (`temp/notes/archive/YYYY-MM/`) prevents notes directory bloat

✅ **GitHub integration**: Structured templates guide contributors to provide necessary information

✅ **Standard compliance**: Community files (LICENSE, CONTRIBUTING, etc.) signal project maturity

### Negative

❌ **Learning curve**: New contributors must understand three-tier system

❌ **Discipline required**: Agents/developers must actively manage notes (archive, extract to ADRs)

❌ **Overhead**: Maintaining `ROADMAP.md` and `NEXT_STEPS.md` requires consistent updates

❌ **Duplication risk**: Information could theoretically appear in multiple tiers (mitigated by clear guidelines)

### Expected State

After adopting this structure:

- **Developers** find setup instructions in `docs/QUICK_START.md`
- **Agents** check `temp/notes/NEXT_STEPS.md` for immediate tasks
- **Architects** reference ADRs for decision rationale
- **Contributors** use PR templates to provide complete information
- **Users** read README.md for project overview and usage
- **Security researchers** follow `SECURITY.md` for vulnerability reporting

---

## Alternatives Considered

### Alternative 1: Flat Documentation Structure

All documentation in `/docs/` without separation of concerns.

**Rejected Reason**:

- ADRs would get lost among guides and references
- No clear place for agent working memory
- Work-in-progress would pollute stable documentation

### Alternative 2: Single "Documentation" Directory

All docs, ADRs, and notes in one location with subdirectories.

**Rejected Reason**:

- ADRs are architectural artifacts, not just documentation
- Mixing stable docs with ephemeral notes causes confusion
- Less discoverable (deeper nesting)

### Alternative 3: No Agent-Specific Structure

Rely on developers to manage planning docs ad-hoc.

**Rejected Reason**:

- Agents lose context between sessions without `ROADMAP.md`/`NEXT_STEPS.md`
- No clear pattern for archiving completed work
- Planning docs would clutter root directory or get lost

### Alternative 4: GitHub Wiki for Documentation

Use GitHub's wiki feature instead of `/docs/`.

**Rejected Reason**:

- Wiki content not versioned with code
- Can't review documentation changes in PRs
- Less portable (tied to GitHub)
- Harder for agents to read/write

---

## Implementation Details

### Required Files Created by Bootstrapper

**Root:**

- `README.md` - Project overview, quick start, structure
- `LICENSE` - MIT License
- `CONTRIBUTING.md` - Contribution guidelines
- `CODE_OF_CONDUCT.md` - Contributor Covenant
- `SECURITY.md` - Security policy and vulnerability reporting
- `CHANGELOG.md` - Version history (initially empty)
- `.gitignore` - Standard ignores for common tools
- `.env.example` - Environment variable template

**Documentation:**

- `docs/README.md` - Documentation index and TOC
- `docs/QUICK_START.md` - Setup instructions skeleton

**ADRs:**

- `ADRs/README.md` - ADR template and best practices
- `ADRs/001-repo-structure.md` - This ADR

**Agent Planning:**

- `temp/notes/README.md` - Notes directory guide
- `temp/notes/ROADMAP.md` - Long-term planning (initially skeletal)
- `temp/notes/NEXT_STEPS.md` - Immediate tasks (initially skeletal)
- `temp/notes/archive/.gitkeep` - Preserve archive directory

**GitHub:**

- `.github/pull_request_template.md` - Template selector
- `.github/PULL_REQUEST_TEMPLATE/` - 7 specialized PR templates
- `.github/ISSUE_TEMPLATE/` - Bug and feature request templates
- `.github/copilot-instructions.md` - Workspace-level Copilot guidance

### Variable Substitution

The bootstrapper performs simple string replacement on these variables:

- `cfpb-exploration` - Repository/project name
- `CFPB data exploration and analysis` - One-line project description
- `Jim Moffet` - Primary author/maintainer name
- `jim@digitalpublic.ventures` - Primary author email
- `{{YEAR}}` - Current year (for copyright)
- `{{CURRENT_DATE}}` - Current date in YYYY-MM-DD format

---

## Related ADRs

None (this is the first ADR, documenting the structure itself)

---

## Notes

- This structure is language and framework agnostic
- Projects can extend with language-specific additions (e.g., `docs/api/` for API docs)
- The `scripts/` directory (if created) is for permanent utility scripts, NOT temporary debug scripts (those go in `temp/`)
- Community files use industry-standard templates adapted for this project structure
- License choice (MIT) was made by project creator; can be changed before first commit
