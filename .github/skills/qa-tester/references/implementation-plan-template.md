# Implementation Plan Template

Create implementation plans when QA review identifies P0 or P2 issues. Save to `temp/qa/reports/implementation-plan-<feature>.md`.

---

````markdown
# Implementation Plan: <Feature>

**Created:** YYYY-MM-DD
**Source:** QA Review <link>
**Target:** Code Writer Agent

---

## Overview

Brief description of what needs to be done.

## Prerequisites

What's already in place that the implementation builds on.

---

## Task 1: <Task Title> (Priority)

**File:** `path/to/file.py`
**Function/Class:** `function_name` (lines X-Y)

### Current Implementation

```python
# Show what exists now
```

### Required Changes

Describe what needs to change and why.

### Target Implementation

```python
# Show the target code
```

### Definition of Done

- [ ] Checkbox item 1
- [ ] Checkbox item 2

---

## Task 2: <Task Title> (Priority)

...

---

## Execution Order

1. Task X - Reason for order
2. Task Y - Depends on Task X
3. Task Z - Can be done anytime

---

## Verification

After completing all tasks, run:

```bash
<verification commands>
```

Expected results.

---

## Files Modified

| File            | Changes           |
| --------------- | ----------------- |
| path/to/file.py | Brief description |

```

```
````
