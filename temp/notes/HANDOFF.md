# Handoff Template

**From**: [Your name/agent identifier]
**To**: [Recipient name or "next available"]
**Date**: [YYYY-MM-DD]
**Session ID**: [session-id]
**Branch**: [current-branch]
**Commit**: [latest-commit-hash]

---

## Executive Summary

[2-3 sentences summarizing what was accomplished, current state, and what comes next]

---

## What Was Completed

- [ ] [Specific task 1 - completed]
- [ ] [Specific task 2 - completed]
- [ ] [Specific task 3 - completed]

---

## Current State

**Status**:

- ✅ [Completed/working items]
- ⏳ [In-progress items]
- ⚠️ [Blocked items]
- ❌ [Known issues]

**Tests**: [All passing / X failing / Not run]
**Build**: [Green / Red / Unknown]
**Branch**: [Clean / Uncommitted changes]

---

## What's Next

### Immediate Priorities

1. **[Highest priority task]**
   - Why: [Rationale]
   - Estimate: [Time estimate]
   - Blockers: [None / List blockers]

2. **[Second priority task]**
   - Why: [Rationale]
   - Estimate: [Time estimate]
   - Blockers: [None / List blockers]

3. **[Third priority task]**
   - Why: [Rationale]
   - Estimate: [Time estimate]
   - Blockers: [None / List blockers]

### Also See

- `temp/notes/NEXT_STEPS.md` for detailed task breakdown
- `temp/notes/ROADMAP.md` for long-term direction

---

## Important Context

### Decisions Made

1. **[Decision 1]**
   - Why: [Rationale]
   - See: [ADR XXX / Commit abc123 / Discussion link]

2. **[Decision 2]**
   - Why: [Rationale]
   - See: [ADR XXX / Commit abc123 / Discussion link]

### Open Questions

- [ ] [Question 1 that needs resolution]
- [ ] [Question 2 that needs resolution]
- [ ] [Question 3 that needs resolution]

### Gotchas / Warnings

- ⚠️ [Important thing to be aware of]
- ⚠️ [Tricky part of the implementation]
- ⚠️ [Known limitation or constraint]

---

## Files Modified

### Core Changes

- `path/to/file1.ext` - [Brief description of changes]
- `path/to/file2.ext` - [Brief description of changes]
- `path/to/file3.ext` - [Brief description of changes]

### Configuration

- `.env.example` - [Added new environment variables]
- `config/settings.yml` - [Updated configuration]

### Documentation

- `docs/API.md` - [Updated endpoint documentation]
- `README.md` - [Added setup instructions]
- `ADRs/XXX-decision.md` - [Created new ADR]

### Tests

- `tests/test_feature.py` - [Added tests for new feature]
- `tests/test_integration.py` - [Updated integration tests]

---

## Testing Notes

### How to Test

```bash
# 1. Setup (if needed)
make setup

# 2. Run tests
make test

# 3. Manual testing
# [Specific steps to verify the changes work]
```

### Known Issues

- [ ] [Test that's flaky - needs investigation]
- [ ] [Feature that needs more testing]

### Performance Considerations

- [Memory usage increased/decreased by X%]
- [Response time improved/degraded by X ms]
- [Database queries optimized/need optimization]

---

## External Dependencies

### Waiting On

- [ ] [External dependency 1 - ETA: date]
- [ ] [External dependency 2 - ETA: date]

### Blocking

- [ ] [This work blocks: other task/team]
- [ ] [This work blocks: deployment]

### Coordinating With

- [Team/person 1 - working on related feature]
- [Team/person 2 - needs to review changes]

---

## References

### Related Work

- ADR XXX: [Decision title and link]
- Issue #XXX: [Issue title and link]
- PR #XXX: [PR title and link]
- Commit abc123: [Commit message]

### Documentation

- [External documentation link]
- [API documentation link]
- [Design document link]

### Discussions

- [Slack thread link]
- [Email thread summary]
- [Meeting notes link]

---

## Session Notes

### Approach Taken

[Brief explanation of the approach used and why]

### Alternatives Considered

1. **[Alternative 1]**
   - Pros: [Benefits]
   - Cons: [Drawbacks]
   - Why not: [Reason for not choosing]

2. **[Alternative 2]**
   - Pros: [Benefits]
   - Cons: [Drawbacks]
   - Why not: [Reason for not choosing]

### Lessons Learned

- [Insight 1]
- [Insight 2]
- [Thing that worked well]
- [Thing that didn't work well]

---

## Handoff Checklist

Before considering this handoff complete:

- [ ] All changes committed
- [ ] Tests passing
- [ ] Code reviewed (if applicable)
- [ ] Documentation updated
- [ ] `NEXT_STEPS.md` updated
- [ ] `ROADMAP.md` updated (if major milestone)
- [ ] Temp files cleaned up or documented
- [ ] ADRs created for architectural decisions
- [ ] This handoff document complete

---

## Contact

**For Questions**:

- [Preferred contact method]
- [Availability hours]
- [Backup contact if urgent]

**Response Time**:

- [Expected response time]

---

## Archive Instructions

When this handoff is complete:

1. Mark as read/acknowledged
2. Move to `temp/notes/archive/YYYY-MM/`
3. Add archival header with resolution details

**Archival Header Template**:

```markdown
---
**ARCHIVED**: [Date]
**Recipient**: [Who received the handoff]
**Outcome**: [Success / Partial / Blocked]
**Follow-up**: [What happened next]
---
```
