# Verification Checklist Template

**Purpose**: Self-check before committing changes to ensure quality and completeness.

**Instructions**: Copy this template to `temp/notes/CURRENT_VERIFICATION.md`, complete all applicable sections, and reference in your commit message or PR description.

---

## Change Overview

**Change Type**: [ ] Feature [ ] Bugfix [ ] Refactor [ ] Documentation [ ] Other: \_\_\_\_

**Description**: _Brief summary of what changed_

**Related Issues**: _Links to issues, ADRs, or requirements_

**Agent/Author**: _Your identifier (e.g., "Claude Sonnet 4.5", "GPT-4")_

**Date**: _YYYY-MM-DD_

---

## Core Verification

### 1. Correctness

- [ ] **Primary functionality works**: Tested manually or via automated tests
- [ ] **Edge cases handled**: Considered and tested (empty inputs, nulls, boundaries)
- [ ] **Error handling present**: Graceful degradation, meaningful error messages
- [ ] **No obvious bugs**: Reviewed logic carefully, no red flags

**Evidence**: _Describe tests run, commands executed, or manual verification steps_

```bash
# Example: Commands run to verify
npm test
npm run type-check
curl -X POST http://localhost:3000/api/endpoint -d '{"test": "data"}'
```

**Issues Found**: _Any problems discovered and how you addressed them_

### 2. Testing

- [ ] **Tests added/updated**: New code has corresponding tests
- [ ] **Tests pass**: All tests (unit, integration, e2e) succeed
- [ ] **Coverage adequate**: New code meets project coverage requirements
- [ ] **Test quality**: Tests are clear, focused, and test the right things

**Test Details**:

- Test files created/modified: _List test files_
- Test commands run: _e.g., `pytest`, `npm test`_
- Coverage report: _If available, link or summarize_

### 3. Code Quality

- [ ] **Follows project conventions**: Style, naming, patterns match existing code
- [ ] **No code duplication**: Reused existing functions where appropriate
- [ ] **Clear and readable**: Code is self-documenting or well-commented
- [ ] **Properly scoped**: Functions/classes have single responsibilities
- [ ] **Type safety**: Type hints/annotations added (if applicable)

**Quality Checks Run**:

```bash
# Example: Linting and formatting
npm run lint
npm run format
# or
black .
mypy .
```

### 4. Security & Safety

- [ ] **No secrets committed**: Verified no API keys, passwords, tokens in code
- [ ] **Input validation**: User inputs are validated and sanitized
- [ ] **SQL injection safe**: Parameterized queries or ORM used (if applicable)
- [ ] **XSS prevention**: Output properly escaped (if applicable)
- [ ] **Dependency safety**: New dependencies are from trusted sources

**Security Considerations**: _Describe any security implications of your changes_

### 5. Performance

- [ ] **No obvious bottlenecks**: Considered algorithmic complexity
- [ ] **Efficient database queries**: No N+1 queries, proper indexing (if applicable)
- [ ] **Resource cleanup**: Files closed, connections released, memory freed
- [ ] **Acceptable response times**: Measured or estimated performance impact

**Performance Notes**: _Any performance testing or considerations_

---

## Completeness Verification

### 6. Documentation

- [ ] **Code comments**: Complex logic explained
- [ ] **API documentation**: Public interfaces documented (if applicable)
- [ ] **README updated**: If behavior or setup changed
- [ ] **CHANGELOG updated**: Entry added for user-facing changes
- [ ] **ADR created**: If architectural decision made (see [ADRs/README.md](../../ADRs/README.md))

**Documentation Changes**: _List files updated or created_

### 7. Dependencies & Configuration

- [ ] **Dependencies declared**: New deps added to requirements/package.json
- [ ] **Version pinning**: Dependencies have specified versions
- [ ] **Environment variables**: New env vars documented in `.env.example`
- [ ] **Configuration documented**: Config changes explained

**Dependency Changes**:

- Added: _List new dependencies with versions_
- Removed: _List removed dependencies_
- Updated: _List updated dependencies_

### 8. Backward Compatibility

- [ ] **API compatibility**: Existing API contracts maintained (or documented as breaking)
- [ ] **Database migrations**: Migration scripts provided and tested
- [ ] **Configuration backward compatible**: Old configs still work or migration path provided
- [ ] **Deprecation warnings**: Old features marked for deprecation if applicable

**Breaking Changes**: _List any breaking changes and mitigation strategies_

---

## Integration Verification

### 9. System Integration

- [ ] **Integrates with existing features**: Doesn't break existing functionality
- [ ] **Regression tests pass**: Verified existing tests still pass
- [ ] **No unintended side effects**: Considered impacts on other components
- [ ] **Smoke tests pass**: Critical paths still work (see [SMOKE.md](./SMOKE.md))

**Integration Testing**:

```bash
# Commands run to verify integration
npm run test:integration
# or
make test-all
```

### 10. Git & Review Readiness

- [ ] **Clean git history**: Commits are logical, not cluttered with "fix typo" commits
- [ ] **Descriptive commit messages**: Follow project conventions
- [ ] **PR description complete**: Explains what, why, and how
- [ ] **Review guidance provided**: Noted areas needing extra scrutiny
- [ ] **Branch up to date**: Merged/rebased with main/master

**Commit Summary**: _List commit messages or link to branch_

---

## Context & Notes

### 11. Assumptions & Decisions

**Assumptions Made**: _What did you assume about requirements, behavior, or environment?_

**Design Decisions**: _Why did you choose this approach vs. alternatives?_

**Known Limitations**: _What doesn't this change address? Future work needed?_

### 12. Testing Environment

**Environment Details**:

- OS: _e.g., macOS 14, Ubuntu 22.04, Windows 11_
- Language/Runtime Version: _e.g., Python 3.11, Node 20.x_
- Database Version: _If applicable_
- Browser: _If frontend changes_

**Configuration Used**: _Any special setup or configuration for testing_

### 13. Review Guidance

**Areas Needing Extra Scrutiny**: _Where should reviewers focus attention?_

**Questions for Reviewer**: _Anything you're uncertain about?_

**Suggested Reviewers**: _Who has relevant expertise?_

---

## Final Self-Assessment

### Overall Confidence

**Confidence Level**: [ ] High [ ] Medium [ ] Low

**Reasoning**: _Why do you have this confidence level?_

### Unresolved Issues

**Blockers**: _Anything preventing this from being merged?_

**Open Questions**: _Issues needing discussion or decisions?_

**Follow-up Work**: _What should be done next? Create issues for tracking._

---

## Sign-Off

**I verify that**:

- [ ] I have honestly completed this checklist
- [ ] All applicable items are checked or explained
- [ ] I have run relevant tests and they pass
- [ ] This change is ready for review

**Agent/Author**: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

**Date**: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

---

## Checklist Usage Notes

### Adapting This Checklist

**For small changes** (< 50 lines, simple bugfix):

- Focus on sections 1-3 and 9-10
- Skip or summarize other sections

**For medium changes** (50-200 lines, feature addition):

- Complete all sections thoroughly
- Provide detailed evidence

**For large changes** (> 200 lines, architectural):

- Consider breaking into smaller PRs
- Extra emphasis on sections 6, 8, and 11
- Create ADR before implementation

### When to Skip Items

It's okay to skip items if:

- **Not applicable**: e.g., "Database migrations" when no DB changes
- **Clearly irrelevant**: e.g., "Browser testing" for CLI tool

**Important**: If you skip an item, add a note explaining why (e.g., "N/A - no database changes").

### Getting Help

- **Unsure about an item?** → Ask in PR description or create discussion
- **Item doesn't make sense for your change?** → Explain why in notes
- **Found this checklist lacking?** → Propose additions via GitHub issue

---

**Template Version**: 1.0
**Last Updated**: 2025-12-17
**Related**: [ACCEPTANCE_CRITERIA.md](./ACCEPTANCE_CRITERIA.md), [SMOKE.md](./SMOKE.md), [REVIEW_CHECKLIST.md](./REVIEW_CHECKLIST.md)
