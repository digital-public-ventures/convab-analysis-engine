---
name: "Data / Service Module"
about: "Pipelines, ETL tasks, data-model changes inside a larger workspace"
---

> **For PR-writing agents**: Describe only the schema/data impacts actually in this PR.

## Summary
<!-- What data flow or service module changed? -->

## Related Issue
- Fixes #123

## Data / Schema Impact
- New tables/views:
- Modified tables/views:
- Backfill required: yes/no (describe)
- Migration plan:

## Verification / How to Test
```bash
# exact commands/notebook runs, do not invent
pytest tests/data
python jobs/my_etl.py --dry-run
```
- [ ] Verified on sample/local data
- [ ] Checked that the orchestrator can import the DAG/module

## Compliance / Ops
- [ ] No secrets committed
- [ ] PII handled according to project rules
- [ ] ADR / data contract updated if schema changed

## Breaking Changes
- [ ] This introduces a breaking change
Describe:

## Reviewer Guidance
- Focus on:
  - correctness of transformations
  - migration/backfill safety
- Ignore generated code:
  - SQL autoformat
  - notebook output cells
