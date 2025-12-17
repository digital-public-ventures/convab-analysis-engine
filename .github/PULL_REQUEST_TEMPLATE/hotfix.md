---
name: "Hotfix"
about: "Emergency fix to keep main deployable"
---

> **For PR-writing agents**: Keep this minimal and accurate.

## Summary
<!-- What is broken in prod/staging that this fixes right now? -->

## Incident / Issue
- Fixes #123

## Fix Description
<!-- What changed, and why this is the minimal safe change. -->

## Post-Deploy Verification
```bash
# commands actually run after deploy
```
- [ ] Verified in target environment
- [ ] Monitoring/logs checked

## Compliance / Ops
- [ ] No secrets committed
- [ ] Logging is appropriate and helpful for incident review
- [ ] Follow-up ADR / incident report to be filed

## Reviewer Guidance
- Focus on the minimal change set
- Ignore generated files
- This should merge to `main` to restore deployability
