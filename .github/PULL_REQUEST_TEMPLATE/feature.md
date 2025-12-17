---
name: "Feature"
about: "Add a new capability (backend, frontend, or service module) to a deployable main"
---

> **For PR-writing agents**: Do **not** fabricate commands, screenshots, checkboxes, or ADR updates. Only report steps and artifacts actually present in the commits/branch. Your goal is accuracy, not completeness.

## Summary
<!-- Plain-language description of what this feature adds. -->

## Related Issue
- Fixes #123
- Related to #

## Motivation / Context
<!-- Why we need this change (user need, stakeholder, ADR, spec). Link planning files if present. -->

## Changes
- 
- 
- 

## Verification / How to Test
<!-- Paste the exact commands actually run. Agents: do not invent commands. -->
```bash
# example
npm test
pytest
curl http://localhost:8000/health
```
- [ ] Verified locally against current `main` behavior
- [ ] If API: endpoint exercised
- [ ] If frontend: UI loaded without console errors

## UI / Screenshots (if applicable)
<!-- before / after, or n/a -->

## Compliance / Ops
- [ ] No secrets committed
- [ ] Logging is appropriate (no PII, structured where relevant)
- [ ] Docs updated (README, runbooks) if user flow changed
- [ ] ADR added/updated if architecture or API changed
- [ ] Security review / threat surface considered

## Breaking Changes
- [ ] This introduces a breaking change
If yes, describe impact and migration path:

## Reviewer Guidance
- Focus on:
  - 
  - 
- Generated or vendored code to ignore:
  - e.g. `package-lock.json`, `poetry.lock`, generated client
- This PR targets `main`, which is expected to stay deployable.

## Notes
<!-- rollout notes, flags to enable, data/backfill needed -->
