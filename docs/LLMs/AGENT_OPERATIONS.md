# Agent Operations Guide

**Purpose**: Multi-agent coordination patterns, handoff protocols, and operational best practices for agent-assisted development.

**Last Updated**: 2025-12-17

---

## Table of Contents

- [Overview](#overview)
- [Multi-Agent Coordination Patterns](#multi-agent-coordination-patterns)
- [Handoff Protocol](#handoff-protocol)
- [Conflict Resolution](#conflict-resolution)
- [Session Boundaries](#session-boundaries)
- [Context Preservation](#context-preservation)
- [Communication Patterns](#communication-patterns)

---

## Overview

Modern software development increasingly involves multiple AI agents working with humans. This guide establishes patterns for effective coordination, clear handoffs, and productive collaboration.

**Core Principles**:

1. **Explicit > Implicit**: Document decisions, don't assume context
2. **Atomic Commits**: Each commit should be self-contained
3. **Clear Boundaries**: Know when to hand off vs continue
4. **Preserve Context**: Future agents/humans need to understand why

---

## Multi-Agent Coordination Patterns

### Pattern 1: Sequential Handoff

**When**: One agent completes a task, another continues

**Process**:

```text
Agent A:
├─ Complete discrete task
├─ Update NEXT_STEPS.md with status
├─ Create HANDOFF.md with context
├─ Commit all changes
└─ Signal completion

Agent B:
├─ Read HANDOFF.md
├─ Review NEXT_STEPS.md
├─ Check git log for recent changes
├─ Continue from clear state
└─ Archive HANDOFF.md when understood
```

**Requirements**:

- Clean git state (no uncommitted changes)
- Updated NEXT_STEPS.md reflecting completion
- HANDOFF.md with comprehensive context
- All temp files cleaned or documented

**Example**:

```markdown
<!-- temp/notes/HANDOFF.md -->

# Handoff: Feature X Implementation Complete

**From**: Claude Sonnet 4.5
**To**: Next agent/developer
**Date**: 2025-12-17
**Branch**: feature-x

## What Was Done

- Implemented user authentication (see `src/auth.py`)
- Created tests (85% coverage, see `tests/test_auth.py`)
- Updated API docs (see `docs/API.md`)
- Created ADR 004 for session management approach

## Current State

- ✅ All tests passing
- ✅ Lint checks clean
- ✅ PR #42 opened and ready for review
- ⚠️ Waiting on security review before merge

## What's Next

See NEXT_STEPS.md for prioritized tasks. Most urgent:

1. Address security review feedback (ETA: 2 days)
2. Add rate limiting (low priority)
3. Consider adding 2FA (future enhancement)

## Context & Decisions

- Chose JWT tokens over sessions (see ADR 004)
- Password hashing uses bcrypt with cost factor 12
- Session timeout: 24 hours (configurable via env var)

## Blockers

- Waiting on security team review
- Need env var documentation (add to ENVIRONMENT.md)

## Files to Review

- `src/auth.py` - Main implementation
- `tests/test_auth.py` - Test suite
- `docs/API.md` - Updated endpoint docs
- `ADRs/004-session-management.md` - Design decisions
```

### Pattern 2: Parallel Work (Different Areas)

**When**: Multiple agents work simultaneously on non-overlapping features

**Process**:

```text
Setup:
├─ Create feature branches from main
├─ Document ownership in NEXT_STEPS.md
└─ Define clear boundaries

Agent A (branch: feature-x):
├─ Work on feature X
├─ Commit to feature-x branch
└─ PR when complete

Agent B (branch: feature-y):
├─ Work on feature Y
├─ Commit to feature-y branch
└─ PR when complete

Merge:
├─ Review PRs independently
├─ Merge one at a time
└─ Resolve any conflicts
```

**Requirements**:

- Clear feature boundaries (no file overlap)
- Separate branches per agent/feature
- Regular rebasing to catch conflicts early
- Communication about shared resources

**Coordination File**:

```markdown
<!-- temp/notes/PARALLEL_WORK.md -->

# Parallel Work - Active

## Agent A: Authentication (feature-auth)

**Files**: src/auth/\*, tests/test_auth.py
**Status**: In progress
**ETA**: 2025-11-24

## Agent B: Database Migration (feature-db)

**Files**: migrations/_, src/db/_, tests/test_db.py
**Status**: In progress
**ETA**: 2025-11-25

## Shared Resources

- `src/models.py` - LOCKED by Agent A until 2025-12-17 18:00
- Database schema - Both need coordination (see #slack-eng)

## Conflict Prevention

- Agent A: Work on auth models first
- Agent B: Wait for auth models, then add DB tables
```

### Pattern 3: Pair Programming (Same Task)

**When**: Complex task benefits from multiple perspectives

**Process**:

```text
Agent A (Driver):
├─ Implement solution
├─ Narrate approach
└─ Commit frequently

Agent B (Navigator):
├─ Review in real-time
├─ Suggest improvements
├─ Catch edge cases
└─ Update documentation

Both:
├─ Maintain shared NEXT_STEPS.md
└─ Document decisions in ADRs
```

**Requirements**:

- Real-time communication channel
- Shared screen/editor access
- Clear role definition (driver vs navigator)
- Frequent role switching

### Pattern 4: Review & Iterate

**When**: One agent implements, another reviews and refines

**Process**:

```text
Agent A (Implementation):
├─ Create initial solution
├─ Commit to review-branch
├─ Mark as "READY FOR REVIEW"
└─ Create REVIEW_REQUEST.md

Agent B (Reviewer):
├─ Read REVIEW_REQUEST.md
├─ Analyze implementation
├─ Suggest improvements
├─ Commit refinements
└─ Update review status

Agent A (Final):
├─ Review changes
├─ Approve or discuss
└─ Merge when satisfied
```

**Review Request Template**:

```markdown
<!-- temp/notes/REVIEW_REQUEST.md -->

# Review Request: Feature X

**Implementer**: Claude Sonnet 4.5
**Reviewer**: GPT-5.1 Codex (or next available agent)
**Date**: 2025-12-17
**Branch**: feature-x

## What to Review

1. **Correctness**: Does it solve the problem?
2. **Edge Cases**: Are errors handled properly?
3. **Performance**: Any obvious bottlenecks?
4. **Maintainability**: Is it clear and well-documented?
5. **Tests**: Adequate coverage?

## Areas of Concern

- Error handling in `process_payment()` - is it robust enough?
- Performance of database query in `get_user_history()` - needs optimization?
- Type hints are incomplete in `utils.py` - can you add them?

## Questions

- Should we cache `get_user_history()` results?
- Is the retry logic too aggressive?
- Better name for `ProcessResult` class?

## Files

- `src/payments.py` (main implementation)
- `tests/test_payments.py` (test suite)
- `docs/API.md` (documentation)

## Success Criteria

- [ ] No obvious bugs
- [ ] Error paths covered
- [ ] Performance acceptable (< 200ms per request)
- [ ] Documentation complete
- [ ] Type hints added
```

---

## Handoff Protocol

### When to Hand Off

**Good Times**:

- Task completion (feature done, tests passing)
- Natural breakpoint (end of day, phase complete)
- Stuck on blocker (waiting for external input)
- Context limit reached (too much complexity)
- Expertise mismatch (need specialized knowledge)

**Bad Times**:

- Mid-implementation (incomplete feature)
- Broken state (tests failing, build broken)
- No documentation (future agent will be lost)
- Uncommitted changes (state unclear)

### Handoff Checklist

Before handing off:

- [ ] **Clean State**: No uncommitted changes
- [ ] **Tests Pass**: All checks green
- [ ] **Docs Updated**: Changes reflected in documentation
- [ ] **Context Saved**: HANDOFF.md created with full context
- [ ] **NEXT_STEPS Updated**: Clear actions for next agent
- [ ] **ADRs Created**: Architectural decisions documented
- [ ] **Temp Files Cleaned**: Debug files archived or deleted
- [ ] **Commit Messages Clear**: Git history tells the story

### Handoff Document Structure

Use this template for `temp/notes/HANDOFF.md`:

```markdown
# Handoff: [Task/Feature Name]

**From**: [Your agent name/version]
**To**: [Next agent or "next available"]
**Date**: [YYYY-MM-DD]
**Branch**: [current branch name]
**Commit**: [latest commit hash]

## Executive Summary

[2-3 sentences: what was accomplished, current state, what's next]

## What Was Completed

- [Specific accomplishment 1]
- [Specific accomplishment 2]
- [Specific accomplishment 3]

## Current State

- ✅ [Completed items]
- ⏳ [In-progress items]
- ⚠️ [Blocked items]
- ❌ [Known issues]

## What's Next

[Prioritized list of next actions - also update NEXT_STEPS.md]

1. [Most urgent task]
2. [Second priority]
3. [Nice to have]

## Important Context

### Decisions Made

- [Key decision 1] - See ADR XXX
- [Key decision 2] - See commit abc123
- [Key decision 3] - Discussed in comments

### Open Questions

- [Unresolved question 1]
- [Unresolved question 2]

### Gotchas / Warnings

- [Thing to be careful about]
- [Known limitation]
- [Tricky part of implementation]

## Files Modified

- `path/to/file1.py` - [what changed]
- `path/to/file2.py` - [what changed]
- `docs/guide.md` - [what changed]

## Testing Notes

- [How to test the changes]
- [What edge cases to watch for]
- [Performance considerations]

## External Dependencies

- [Waiting on: security review]
- [Blocked by: API key from vendor]
- [Requires: database migration]

## References

- ADR XXX: [Decision title]
- Issue #42: [Issue title]
- PR #100: [PR title]
- Commit abc123: [Commit message]
```

---

## Conflict Resolution

### Git Conflicts

**Prevention**:

- Pull frequently from main
- Communicate about shared files
- Use feature branches
- Rebase before major changes

**Resolution Process**:

1. **Understand Both Sides**:
   - Read commit messages
   - Check ADRs for context
   - Ask if unclear (create issue)

2. **Identify Intent**:
   - What was each agent trying to accomplish?
   - Are the changes complementary or contradictory?

3. **Merge Strategy**:
   - **Compatible**: Keep both changes
   - **Contradictory**: Document in ADR, choose based on project goals
   - **Overlapping**: Refactor to accommodate both

4. **Test Thoroughly**:
   - Run full test suite
   - Check integration
   - Verify nothing broken

5. **Document Resolution**:
   - Update commit message with resolution rationale
   - Create ADR if architectural decision needed
   - Update affected documentation

### Semantic Conflicts

**What**: Code merges cleanly but logic conflicts

**Example**:

```python
# Agent A: Add validation
def process_data(data):
    if not validate(data):
        raise ValueError("Invalid data")
    return transform(data)

# Agent B: Add caching (different file)
@cache
def validate(data):
    # Now cached, but Agent A's error handling assumes immediate validation
    return check_schema(data)
```

**Detection**:

- Tests fail after clean merge
- Unexpected behavior
- Performance regression
- Logic errors

**Resolution**:

1. Identify the conflict source
2. Determine correct behavior
3. Refactor to fix
4. Add integration tests
5. Document the resolution

### Design Conflicts

**What**: Two agents implement incompatible approaches

**Example**:

- Agent A: Uses async/await
- Agent B: Uses callbacks
- Both modify same subsystem

**Resolution**:

1. **Pause Work**: Don't make it worse
2. **Review ADRs**: Was there guidance?
3. **Evaluate Approaches**:
   - Performance implications
   - Maintainability
   - Team preference
   - Ecosystem fit
4. **Make Decision**: Create ADR
5. **Refactor**: Align on chosen approach
6. **Update Docs**: Prevent future conflicts

---

## Session Boundaries

### Session Start Protocol

**Actions**:

1. **Read Context**:
   - `temp/notes/NEXT_STEPS.md` - What to do
   - `temp/notes/HANDOFF.md` - Context from previous session
   - `temp/notes/ROADMAP.md` - Long-term direction
   - Recent git log - What changed

2. **Verify State**:
   - `git status` - Clean?
   - `git log -5` - Recent activity
   - Run tests - All passing?
   - Check CI - Build green?

3. **Update Session Metadata**:

   ```markdown
   **Session ID**: [unique-id]
   **Agent**: [your name/version]
   **Status**: STARTING
   **Branch**: [current branch]
   **Started**: [timestamp]
   ```

4. **Acknowledge Handoff**:
   - Mark HANDOFF.md as read
   - Archive if appropriate
   - Ask questions if unclear

### Session End Protocol

**Actions**:

1. **Save Progress**:
   - Commit all changes
   - Push to remote (if applicable)
   - Update NEXT_STEPS.md

2. **Document State**:
   - Create HANDOFF.md if handing off
   - Update SELF_OBSERVATIONS.md if meta-project
   - Archive completed temp notes

3. **Clean Up**:
   - Remove debug files
   - Archive logs to temp/output/
   - Clear temp/debug/ if appropriate

4. **Update Session Metadata**:

   ```markdown
   **Status**: COMPLETE
   **Ended**: [timestamp]
   **Next Session**: [what should be done]
   ```

5. **Verify Handoff**:
   - [ ] Clean git state
   - [ ] Tests passing
   - [ ] Docs updated
   - [ ] Context preserved
   - [ ] NEXT_STEPS clear

---

## Context Preservation

### Critical Information

**Always Preserve**:

- **Decisions**: Why things are the way they are (ADRs)
- **Constraints**: Limitations and boundaries
- **Dependencies**: What depends on what
- **Gotchas**: Non-obvious problems
- **Intent**: What were you trying to accomplish

### Context Files

**Mandatory**:

- `temp/notes/NEXT_STEPS.md` - Current work
- `temp/notes/ROADMAP.md` - Long-term plan
- `ADRs/` - Architectural decisions
- Commit messages - Incremental story

**Optional**:

- `temp/notes/HANDOFF.md` - Rich handoff context
- `temp/notes/SELF_OBSERVATIONS.md` - Meta-learnings
- `temp/notes/PHASE_X_*.md` - Phase documentation
- `temp/notes/DEBUG_*.md` - Debugging traces

### Context Decay Prevention

**Problem**: Information gets lost over time

**Solutions**:

1. **Write It Down**: Don't rely on memory
2. **Regular Updates**: NEXT_STEPS.md after each session
3. **Periodic Cleanup**: Archive old notes monthly
4. **ADR Creation**: Promote important notes to ADRs
5. **Commit Messages**: Make history readable

---

## Communication Patterns

### Async Communication (Different Times)

**Tools**:

- HANDOFF.md - Rich context transfer
- NEXT_STEPS.md - Current priorities
- Git commits - Incremental progress
- ADRs - Decisions and rationale
- Issues/PRs - Discussions and reviews

**Best Practices**:

- Over-document rather than under-document
- Assume future reader has no context
- Link to related resources
- Explain "why" not just "what"

### Sync Communication (Same Time)

**Tools**:

- Shared editor (pair programming)
- Real-time chat (Slack, Discord)
- Voice/video (for complex discussions)
- Screen share (for debugging)

**Best Practices**:

- Record decisions in ADRs after discussion
- Summarize conversations in commits
- Update docs immediately
- Archive chat logs if important

### Human-Agent Communication

**Agent to Human**:

- Clear status updates
- Explicit questions when blocked
- Documented decision points
- References to context (ADRs, code)

**Human to Agent**:

- Provide clear requirements
- Point to relevant docs
- Explain constraints and preferences
- Give feedback on approaches

---

## Anti-Patterns

### ❌ Silent Handoff

**Bad**: Stopping work without documentation

**Good**: Create HANDOFF.md, update NEXT_STEPS.md

### ❌ Dirty Handoff

**Bad**: Uncommitted changes, failing tests, broken build

**Good**: Clean state, all green, clear commit history

### ❌ Assuming Context

**Bad**: "They'll figure it out from the code"

**Good**: Explicit documentation of decisions and gotchas

### ❌ Ignoring Previous Work

**Bad**: Starting over without reading history

**Good**: Review HANDOFF.md, git log, ADRs before starting

### ❌ Working in Isolation

**Bad**: No communication, surprise conflicts

**Good**: Update NEXT_STEPS.md, coordinate on shared files

---

## See Also

- [Agent Safety Guide](AGENT_SAFETY.md)
- [Notes and ADR Management](NOTES_AND_ADR_MANAGEMENT.md)
- [Observability Guide](OBSERVABILITY.md)
- [Environment Setup](ENVIRONMENT.md)
