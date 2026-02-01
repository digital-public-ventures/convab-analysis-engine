# QA Review Report Template

Use this template for all QA review reports. Save reports to `temp/qa/reports/qa-review-<date>-<feature>.md`.

---

```markdown
# QA Review: <Feature Name>

**Review Date:** YYYY-MM-DD
**Reviewer:** QA Agent
**Implementation Branch:** <branch-name>
**Plan Document:** <link-to-plan>

---

## Executive Summary

Brief assessment of implementation quality and completeness.

### Overall Assessment: **<PASS|PARTIAL|FAIL>**

| Requirement Category | Status |
|---------------------|--------|
| <Requirement 1> | PASS/FAIL |
| <Requirement 2> | PASS/FAIL |

---

## Task Requirements Analysis

### Original Requirements (verbatim)
> Quote the original task requirements

### Key Interpretation
What do these requirements actually mean?

---

## Implementation Analysis

### What Was Built
Describe the implementation with file references.

### Critical Findings
Document gaps between requirements and implementation.

---

## Test Execution Results

### Existing Tests
Pass/fail summary

### QA Contract Tests
Results from your test scripts

---

## Issues Found

### P0 - Critical: <Issue Title>

**Description:** What's wrong
**Location:** File and line references
**Requirement Violated:** Which requirement this breaks
**Impact:** What happens because of this issue

**Definition of Done:**
1. Specific action item
2. Another action item
3. How to verify the fix

---

### P2 - Medium: <Issue Title>
...

### P3 - Low: <Issue Title>
...

---

## Prioritized Action Items

### Must Fix (P0)
| # | Issue | Definition of Done | Effort |
|---|-------|-------------------|--------|

### Should Fix (P2)
| # | Issue | Definition of Done | Effort |
|---|-------|-------------------|--------|

### Could Fix (P3)
| # | Issue | Definition of Done | Effort |
|---|-------|-------------------|--------|

---

## Conclusion

Summary and recommendation.
```

---

## Follow-Up Review Section

Add this section after implementation tasks are completed:

```markdown
---

## Follow-Up Review

**Date:** YYYY-MM-DD
**Implementation Completed By:** <agent/user>

### Issue Resolution Status

| Issue ID | Status | Verification |
|----------|--------|--------------|
| P0-001 | RESOLVED | Test X passes |
| P2-001 | RESOLVED | Code reviewed |
| P3-001 | DEFERRED | Documented for future |

### New Issues Discovered
(If any)

### Final Assessment

**Status:** APPROVED / NEEDS WORK

<Summary of findings>
```

---

## Final Application Implementation Status

Add this section when implementation has been partially completed:

```markdown
## Final Application Implementation Status

**Updated:** YYYY-MM-DD (Post-Review)

### Changes Made
Describe what was implemented.

### Remaining Work
What still needs to be done.

### Updated Status

| Item | Status |
|------|--------|
| <Item 1> | COMPLETE |
| <Item 2> | PENDING |
```

---

## QA Facilitation Status

Always include this section to clarify QA boundaries:

```markdown
## QA Facilitation Status

### File Modification Restrictions
<Document the restrictions and that they will NOT be lifted>

### Assigning Implementation Tasks
<Explain that modifications must be assigned as separate tasks>

### Recommended Task Assignments

| Task ID | Description | Files Affected | Priority |
|---------|-------------|----------------|----------|
| IMPL-001 | <description> | `file.py` | P0 |

### QA Verification Process
<Describe how to request follow-up QA>
```
