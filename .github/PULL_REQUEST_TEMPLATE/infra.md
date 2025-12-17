---
name: "Infra / CI"
about: "GitHub Actions, Terraform modules, pipelines, or deployment descriptors"
---

> **For PR-writing agents**: Include only actual plans/runs that were executed.

## Summary
<!-- What infra/CI asset changed? -->

## Related Issue
- Fixes #123

## Changes
- 
- 

## Verification / How to Test
```bash
# exact commands or plan outputs, do not invent
terraform init && terraform plan
act -j ci
```
- [ ] Plan or dry-run attached/pasted
- [ ] Affected environments identified

## Compliance / Ops
- [ ] No secrets committed (check workflow/env blocks)
- [ ] Logging and retention unchanged or documented
- [ ] ADR updated if this is a pattern change

## Breaking Changes
- [ ] This introduces a breaking change (e.g. renamed resources)
If yes, describe:

## Reviewer Guidance
- Focus on:
  - 
- Generated to ignore:
  - `.terraform.lock.hcl`
  - action/cache updates
