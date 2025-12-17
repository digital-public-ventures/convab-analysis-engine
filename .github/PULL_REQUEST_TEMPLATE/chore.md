---
name: "Chore"
about: "Refactors, dependency bumps, minor config changes; no user-facing feature"
---

> **For PR-writing agents**: Report only what was done. Do not check boxes for steps you didn't run.

## Summary
<!-- What maintenance task is this? -->

## Reason
<!-- Tech debt, template sync, security bump, CI reliability, etc. -->

## Changes
- 
- 

## Verification / How to Test
```bash
# exact commands actually run
npm test
pytest
```
- [ ] CI passes locally or in GitHub Actions

## Compliance / Ops
- [ ] No secrets committed
- [ ] Logging unaffected / appropriate
- [ ] Docs or ADRs updated if we changed process/tooling

## Breaking Changes
- [ ] None expected
If there is impact, explain:

## Reviewer Guidance
- Focus on:
  - 
- Generated/vendored to ignore:
  - lockfiles
  - formatter-only diffs
