---
name: "Bugfix"
about: "Fix a defect without introducing unrelated changes"
---

> **For PR-writing agents**: Do **not** fabricate commands, screenshots, checkboxes, or ADR updates. Only report what is actually in the commits.

## Summary
<!-- What was broken and in what context (API, UI, data service)? -->

## Related Issue
- Fixes #123

## Root Cause
<!-- What specifically caused the bug? -->

## Reproduction
1. 
2. 

## Verification / How to Test
```bash
# exact commands actually run
pytest tests/...
npm test
curl http://localhost:8000/endpoint --data ...
```
- [ ] Verified regression no longer occurs
- [ ] Verified no new 4xx/5xx in logs (if applicable)

## UI / Screenshots (if applicable)
<!-- before / after, or n/a -->

## Compliance / Ops
- [ ] No secrets committed
- [ ] Logging improved or kept consistent
- [ ] Docs updated if behavior visible to users
- [ ] ADR updated if the fix changes prior design intent

## Breaking Changes
- [ ] This introduces a breaking change
If yes, describe:

## Reviewer Guidance
- Focus on:
  - 
- Generated/vendored to ignore:
  - 
