# Roadmap

**Project**: cfpb-exploration

**Last Updated**: {{CURRENT_DATE}}

---

## Overview

This document tracks the long-term strategic direction and major milestones for cfpb-exploration. It serves as a living document that evolves with the project and ensures continuity across development sessions.

**Purpose**: Provide high-level planning, communicate project vision, and track progress on major initiatives.

---

## Recently Completed

### ✅ Project Initialization (Complete - {{CURRENT_DATE}})

**What**: Set up agent-friendly repository structure with three-tier documentation system

**Deliverables**:

- Repository structure (docs/, ADRs/, temp/notes/)
- Community files (LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY)
- GitHub templates (PR and issue templates)
- ADR 001: Repository Structure and Organization
- Living documents (this ROADMAP.md and NEXT_STEPS.md)

**Documentation**: See `ADRs/001-repo-structure.md`

---

## Current Focus

### 🎯 Phase 1: [Your Next Major Initiative]

**Status**: Not started
**Effort**: TBD

**Goals**:

1. [Goal 1]
2. [Goal 2]
3. [Goal 3]

**Success Criteria**:

- [Criterion 1]
- [Criterion 2]
- [Criterion 3]

**Blocking Issues**: None currently

---

## Cyclical Improvement Process

**Overview**: For projects that use themselves (like template repositories), a meta-process enables continuous improvement through self-observation and iteration.

**Core Workflow**:

```text
1. DESIGN → Create guidance/features
   ├─ Add new documentation
   ├─ Create configuration files
   ├─ Update templates or ADRs
   └─ Commit changes

2. APPLY → Integrate changes into workspace
   ├─ Run setup/bootstrap scripts
   ├─ Preserve custom work
   ├─ Import improvements
   └─ Commit applied changes

3. OBSERVE → Track actual usage
   ├─ Is guidance being followed?
   ├─ Are features being used?
   ├─ What works / doesn't work?
   └─ Document findings

4. ADJUST → Fix problems
   ├─ If guidance is unclear → Update it
   ├─ If features are awkward → Redesign them
   ├─ If things are ignored → Make them more prominent
   └─ Loop back to step 1
```

**Key Insight**: Dogfooding reveals what works in practice vs what looks good in theory.

For agent-assisted projects: Track observations in `temp/notes/SELF_OBSERVATIONS.md` to maintain a record of what guidance is effective vs what gets ignored.

---

## Short-Term Roadmap (Next 1-2 Months)

### 1. [Initiative Name]

**Priority**: High/Medium/Low
**Effort**: [X hours/days/weeks]
**Owner**: [Team member or unassigned]

**Description**: [What needs to be done and why]

**Tasks**:

- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

**Dependencies**: [Any blockers or prerequisites]

### 2. [Another Initiative]

**Priority**: High/Medium/Low
**Effort**: [X hours/days/weeks]

[Repeat structure above]

---

## Medium-Term Roadmap (2-6 Months)

### 1. [Larger Feature or Initiative]

**Description**: [High-level description]

**Key Objectives**:

- Objective 1
- Objective 2
- Objective 3

**Expected Outcomes**: [What success looks like]

### 2. [Another Initiative]

[Repeat structure]

---

## Long-Term Vision (6-12 Months)

### [Strategic Goal 1]

**Vision**: [Describe the end state]

**Why It Matters**: [Business/user value]

**Major Milestones**:

1. Milestone 1
2. Milestone 2
3. Milestone 3

### [Strategic Goal 2]

[Repeat structure]

---

## Technical Debt & Maintenance

### High Priority

- [ ] [Technical debt item 1]
- [ ] [Technical debt item 2]

### Medium Priority

- [ ] [Technical debt item 3]
- [ ] [Technical debt item 4]

### Low Priority

- [ ] [Nice-to-have refactoring]
- [ ] [Performance optimization]

---

## Known Limitations

Document known constraints, limitations, or areas needing future attention:

1. **[Limitation 1]**: [Description and potential impact]
2. **[Limitation 2]**: [Description and potential impact]

---

## Dependencies & Prerequisites

List external dependencies, infrastructure needs, or prerequisites:

- [Dependency 1]: [Why needed and current status]
- [Dependency 2]: [Why needed and current status]

---

## Success Metrics

Define how you'll measure progress and success:

### Current Phase Metrics

- [ ] Metric 1: [Target]
- [ ] Metric 2: [Target]

### Long-Term Metrics

- Metric 1: [Target by date]
- Metric 2: [Target by date]

---

## Notes

- Update this roadmap after completing major milestones
- Archive old sections to `temp/notes/archive/YYYY-MM/` when no longer relevant
- Extract architectural decisions to ADRs before archiving
- Review quarterly to ensure alignment with project goals
- Keep focused on strategic items; tactical details belong in NEXT_STEPS.md
