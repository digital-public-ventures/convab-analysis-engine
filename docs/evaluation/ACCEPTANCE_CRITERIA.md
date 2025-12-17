# Acceptance Criteria Templates

**Purpose**: Define what "done" looks like for different types of changes before starting work.

**Usage**: Review the appropriate template before beginning work. Copy relevant criteria to your task tracking (e.g., GitHub issue, `temp/notes/NEXT_STEPS.md`) and check off as you complete each item.

---

## Quick Reference

| Change Type                                | Use When                                                    | Key Focus Areas                   |
| ------------------------------------------ | ----------------------------------------------------------- | --------------------------------- |
| [Feature Addition](#feature-addition)      | Adding new functionality                                    | Tests, docs, backward compat      |
| [Bug Fix](#bug-fix)                        | Fixing incorrect behavior                                   | Root cause, regression prevention |
| [Refactoring](#refactoring)                | Improving code structure                                    | Behavior preservation, testing    |
| [Performance](#performance-optimization)   | Optimizing speed/resource usage                             | Measurements, benchmarks          |
| [Documentation](#documentation)            | Updating docs only                                          | Accuracy, examples, completeness  |
| [Configuration](#configuration-change)     | Changing settings/config                                    | Migration, backward compat        |
| [Dependency Update](#dependency-update)    | Upgrading/adding dependencies                               | Security, compatibility           |
| [Security Fix](#security-fix)              | Addressing security vulnerability                           | Fix verification, disclosure      |
| [Database Migration](#database-migration)  | Schema or data changes                                      | Rollback, zero-downtime           |
| [API Change](#api-change)                  | Modifying public APIs                                       | Versioning, contracts             |

---

## Feature Addition

**Definition**: Adding new functionality that didn't exist before.

### Acceptance Criteria

#### Functionality

- [ ] Feature works as specified in requirements
- [ ] All acceptance criteria from the original request are met
- [ ] Edge cases identified and handled appropriately
- [ ] Error messages are clear and actionable
- [ ] Feature can be disabled/toggled if appropriate (feature flag)

#### Testing

- [ ] Unit tests cover main functionality (aim for 80%+ coverage)
- [ ] Integration tests verify feature works with system
- [ ] Edge case tests included (empty input, max values, invalid data)
- [ ] Error handling tested explicitly
- [ ] Existing tests still pass (no regressions)

#### Documentation

- [ ] Code comments explain complex logic
- [ ] Public API documented (if applicable)
- [ ] README updated with feature description and usage
- [ ] CHANGELOG entry added
- [ ] Architecture decision recorded (ADR) if significant design choice

#### Integration

- [ ] Feature integrates cleanly with existing codebase
- [ ] No breaking changes to existing APIs (or documented/versioned if unavoidable)
- [ ] Configuration/environment variables documented in `.env.example`
- [ ] Database migrations provided and tested (if applicable)

#### User Experience (if applicable)

- [ ] UI/UX follows existing patterns
- [ ] Responsive design works on target devices
- [ ] Accessibility requirements met (WCAG 2.1 AA if web)
- [ ] Error states handled gracefully

#### Code Quality

- [ ] Follows project coding standards
- [ ] No code duplication
- [ ] Functions have single responsibility
- [ ] Type hints/annotations added (language-dependent)
- [ ] Linting and formatting checks pass

**Example**: Adding user export feature

```markdown
### Acceptance Criteria: User Export Feature

- [ ] Users can export their data as JSON
- [ ] Users can export their data as CSV
- [ ] Export includes all user-generated content
- [ ] Large exports (>10MB) are handled via async job
- [ ] Export available for download for 7 days
- [ ] Email notification sent when export ready
- [ ] Unit tests for export formatting
- [ ] Integration test for full export flow
- [ ] API endpoint documented in OpenAPI spec
- [ ] README updated with export feature section
```

---

## Bug Fix

**Definition**: Correcting incorrect behavior to match intended functionality.

### Acceptance Criteria

#### Root Cause Analysis

- [ ] Root cause identified and documented
- [ ] Reproduced bug reliably before fix
- [ ] Understand why bug wasn't caught by existing tests

#### Fix

- [ ] Bug no longer reproduces after fix
- [ ] Fix addresses root cause, not just symptoms
- [ ] Fix is minimal and focused (doesn't refactor unnecessarily)
- [ ] No new bugs introduced by the fix

#### Testing

- [ ] Regression test added to prevent bug from recurring
- [ ] Test reproduces original bug (fails without fix, passes with fix)
- [ ] Related scenarios tested to ensure comprehensive fix
- [ ] Existing tests still pass

#### Documentation

- [ ] Bug and fix explained in commit message
- [ ] CHANGELOG entry if user-facing bug
- [ ] Comment added if code needs clarification due to subtle bug
- [ ] GitHub issue linked and closed

#### Verification

- [ ] Tested in environment where bug occurred (if possible)
- [ ] Verified fix doesn't break edge cases
- [ ] Performance impact considered (fix shouldn't make things slower)

**Example**: Fixing duplicate email notifications

```markdown
### Acceptance Criteria: Fix Duplicate Emails

- [ ] Root cause: Race condition in notification worker
- [ ] Reproduced bug consistently with test script
- [ ] Added idempotency key to notification system
- [ ] Regression test added: `test_notification_idempotency`
- [ ] Verified no duplicate notifications sent in test environment
- [ ] Existing notification tests still pass
- [ ] Commit message explains race condition and fix
- [ ] Closes #issue-number
```

---

## Refactoring

**Definition**: Improving code structure without changing external behavior.

### Acceptance Criteria

#### Behavior Preservation

- [ ] All existing tests pass without modification
- [ ] External behavior unchanged (APIs, outputs, side effects)
- [ ] Performance characteristics similar (no significant regression)
- [ ] Smoke tests pass

#### Code Improvement

- [ ] Code is more readable/maintainable after refactoring
- [ ] Reduced code duplication
- [ ] Improved separation of concerns
- [ ] Simplified complex logic
- [ ] Better adherence to SOLID principles (if applicable)

#### Testing

- [ ] Existing test suite provides confidence
- [ ] New tests added if coverage gaps identified
- [ ] Tests run faster (if refactor touched test code)

#### Documentation

- [ ] Code comments updated if logic changed
- [ ] Commit message explains motivation for refactor
- [ ] ADR created if architectural pattern changed

#### Safety

- [ ] Changes are incremental (avoid big-bang refactors)
- [ ] Can be reverted cleanly if issues found
- [ ] No subtle behavior changes introduced

**Example**: Refactoring payment processing logic

```markdown
### Acceptance Criteria: Refactor Payment Processing

- [ ] All payment tests pass unchanged
- [ ] Payment processing behavior identical to before
- [ ] Extracted 3 reusable functions from monolithic process_payment()
- [ ] Reduced cyclomatic complexity from 15 to 8
- [ ] Removed 200 lines of duplicate validation code
- [ ] Type hints added to all functions
- [ ] Integration tests still pass
- [ ] Performance testing shows no regression
- [ ] Commit message explains refactoring motivation
```

---

## Performance Optimization

**Definition**: Improving speed, resource usage, or scalability.

### Acceptance Criteria

#### Measurement

- [ ] Baseline performance measured before optimization
- [ ] Target performance goal defined (e.g., "< 200ms response time")
- [ ] Performance after optimization measured and compared
- [ ] Improvement quantified (e.g., "50% faster", "uses 30% less memory")

#### Optimization

- [ ] Bottleneck identified through profiling
- [ ] Optimization addresses actual bottleneck
- [ ] Algorithm complexity improved (if applicable)
- [ ] Resource usage reduced (memory, CPU, network, I/O)

#### Correctness

- [ ] All tests still pass
- [ ] Behavior unchanged (results are identical)
- [ ] Edge cases still handled correctly
- [ ] No race conditions introduced

#### Verification

- [ ] Benchmarks added to track performance over time
- [ ] Tested under realistic load (not just toy data)
- [ ] Performance regression tests added
- [ ] Monitoring/metrics updated to track optimization

#### Documentation

- [ ] Performance characteristics documented
- [ ] Benchmark results included in PR
- [ ] Trade-offs explained (e.g., memory for speed)
- [ ] CHANGELOG notes performance improvement

**Example**: Optimizing database query performance

```markdown
### Acceptance Criteria: Optimize User Query

- [ ] Baseline: Query takes 2.5s for 100K users
- [ ] Target: Query should take < 500ms
- [ ] Identified missing index on user.created_at
- [ ] Added index, tested migration on staging
- [ ] Measured: Query now takes 180ms (93% improvement)
- [ ] All user tests pass unchanged
- [ ] Added benchmark: `benchmark_user_query_performance`
- [ ] Query plan documented in code comment
- [ ] CHANGELOG notes 7x performance improvement
```

---

## Documentation

**Definition**: Adding or updating documentation without code changes.

### Acceptance Criteria

#### Accuracy

- [ ] Information is technically correct
- [ ] Code examples work as written
- [ ] Commands run successfully
- [ ] Links are valid and point to correct resources
- [ ] Version-specific information clearly marked

#### Completeness

- [ ] Covers all aspects of the topic
- [ ] Examples provided for common use cases
- [ ] Edge cases or gotchas mentioned
- [ ] Prerequisites clearly stated
- [ ] Related documentation linked

#### Clarity

- [ ] Written for target audience (beginners, advanced users, etc.)
- [ ] Technical jargon explained or avoided
- [ ] Step-by-step instructions for processes
- [ ] Screenshots/diagrams included where helpful
- [ ] Formatting is consistent and readable

#### Structure

- [ ] Follows project documentation style guide
- [ ] Table of contents for long documents
- [ ] Logical organization (general to specific)
- [ ] Cross-references to related docs
- [ ] Searchable (good headings, keywords)

#### Maintenance

- [ ] Outdated information removed or updated
- [ ] Document versioning noted if applicable
- [ ] Last updated date included
- [ ] Maintainer/contact information provided

**Example**: Documenting API authentication

```markdown
### Acceptance Criteria: API Authentication Docs

- [ ] Authentication methods explained (API key, OAuth2)
- [ ] Code examples in Python, JavaScript, cURL
- [ ] All examples tested and work
- [ ] Error responses documented with examples
- [ ] Rate limiting information included
- [ ] Links to related docs (API reference, quickstart)
- [ ] Screenshots of getting API key from dashboard
- [ ] Security best practices noted
- [ ] Last updated: 2025-12-17
```

---

## Configuration Change

**Definition**: Modifying application configuration, settings, or environment variables.

### Acceptance Criteria

#### Change Impact

- [ ] Impact of change fully understood
- [ ] All environments considered (dev, staging, prod)
- [ ] Backward compatibility assessed
- [ ] Migration path provided if breaking

#### Documentation

- [ ] Configuration change documented in README or deployment guide
- [ ] `.env.example` updated with new variables
- [ ] Default values specified
- [ ] Valid value ranges/formats explained
- [ ] Migration instructions provided

#### Testing

- [ ] Tested with new configuration values
- [ ] Tested with old configuration (if backward compatible)
- [ ] Tested with missing configuration (fails gracefully)
- [ ] Tested with invalid values (proper error messages)

#### Deployment

- [ ] Configuration changes noted in CHANGELOG
- [ ] Deployment instructions updated
- [ ] Environment variable changes communicated to ops team
- [ ] Rollback plan documented

**Example**: Adding cache configuration

```markdown
### Acceptance Criteria: Add Redis Cache Config

- [ ] New env vars: REDIS_URL, REDIS_TTL, CACHE_ENABLED
- [ ] `.env.example` updated with defaults
- [ ] App works with cache enabled
- [ ] App works with cache disabled (fallback to direct DB)
- [ ] Invalid REDIS_URL fails gracefully with clear error
- [ ] README section added: "Caching Configuration"
- [ ] Deployment guide updated with Redis setup
- [ ] CHANGELOG notes cache feature addition
- [ ] Tested on staging with Redis
```

---

## Dependency Update

**Definition**: Upgrading, adding, or removing project dependencies.

### Acceptance Criteria

#### Due Diligence

- [ ] Dependency necessity justified (for additions)
- [ ] Alternative dependencies considered
- [ ] License compatibility verified (no GPL in MIT project, etc.)
- [ ] Dependency reputation checked (downloads, maintenance, security)
- [ ] Transitive dependencies reviewed

#### Version Selection

- [ ] Version pinned (not using `^` or `~` for production)
- [ ] Changelog reviewed for breaking changes
- [ ] Security advisories checked
- [ ] Compatibility with existing dependencies verified

#### Testing

- [ ] All tests pass with new dependency version
- [ ] Application builds successfully
- [ ] Integration points with dependency tested
- [ ] No deprecation warnings
- [ ] Performance impact assessed

#### Documentation

- [ ] Dependency added to requirements/package.json with version
- [ ] CHANGELOG notes dependency change
- [ ] README updated if setup process changed
- [ ] Lockfile committed (package-lock.json, poetry.lock, etc.)

#### Security

- [ ] Security scan run (npm audit, safety check, etc.)
- [ ] Known vulnerabilities addressed
- [ ] Dependency source verified (official registry)

**Example**: Upgrading database driver

```markdown
### Acceptance Criteria: Upgrade psycopg2 to psycopg3

- [ ] Reviewed psycopg3 changelog for breaking changes
- [ ] Updated connection string format
- [ ] All database tests pass
- [ ] Connection pooling still works
- [ ] No performance regression (tested with benchmark)
- [ ] Updated requirements.txt with psycopg3==3.1.8
- [ ] poetry.lock updated and committed
- [ ] No security vulnerabilities (ran safety check)
- [ ] CHANGELOG notes upgrade and breaking changes
- [ ] Migration guide added to docs/
```

---

## Security Fix

**Definition**: Addressing a security vulnerability.

### Acceptance Criteria

#### Vulnerability Understanding

- [ ] Vulnerability fully understood (attack vector, impact)
- [ ] Severity assessed (CVSS score or equivalent)
- [ ] Affected versions identified
- [ ] Exploitability evaluated

#### Fix Implementation

- [ ] Vulnerability fixed and verified
- [ ] Fix addresses root cause, not just symptoms
- [ ] No new vulnerabilities introduced
- [ ] Minimal code changes (focused fix)

#### Testing

- [ ] Exploit attempt blocked by fix
- [ ] Security test added to prevent regression
- [ ] Existing functionality unaffected
- [ ] Penetration test or security scan performed

#### Disclosure

- [ ] Security advisory drafted (if public disclosure needed)
- [ ] CVE assigned (if applicable)
- [ ] Disclosure timing coordinated
- [ ] Users notified if vulnerability was exploited

#### Documentation

- [ ] SECURITY.md updated if reporting process affected
- [ ] CHANGELOG notes security fix (without exploit details)
- [ ] Internal post-mortem conducted
- [ ] Lessons learned documented

**Example**: Fixing SQL injection vulnerability

```markdown
### Acceptance Criteria: Fix SQL Injection in Search

- [ ] Vulnerability confirmed: User input directly interpolated in query
- [ ] Severity: HIGH (allows database read/write)
- [ ] Fixed: Replaced string formatting with parameterized queries
- [ ] Tested: SQL injection attempts now blocked
- [ ] Security test added: `test_search_sql_injection_prevention`
- [ ] All search tests pass
- [ ] Code review by security team
- [ ] CHANGELOG: "Security: Fixed SQL injection in search endpoint"
- [ ] Security advisory published
- [ ] Users notified to upgrade immediately
```

---

## Database Migration

**Definition**: Changes to database schema or data.

### Acceptance Criteria

#### Migration Safety

- [ ] Migration is reversible (down migration provided)
- [ ] Migration tested on production-like dataset
- [ ] Migration is idempotent (can run multiple times safely)
- [ ] Migration has reasonable execution time (< 30s for small tables)
- [ ] Zero-downtime strategy if production (blue-green, read replicas, etc.)

#### Data Integrity

- [ ] Data loss prevented (backups taken)
- [ ] Data validation before and after migration
- [ ] Foreign key constraints maintained
- [ ] Indexes added for new columns (if queried)
- [ ] No orphaned data created

#### Testing

- [ ] Migration runs successfully on development database
- [ ] Migration runs successfully on staging database
- [ ] Application works with migrated schema
- [ ] Rollback tested and works
- [ ] Data integrity verified post-migration

#### Documentation

- [ ] Migration script documented (comments explaining changes)
- [ ] Deployment instructions updated
- [ ] Rollback procedure documented
- [ ] CHANGELOG notes schema changes

#### Performance

- [ ] Migration doesn't lock tables excessively
- [ ] Query performance measured before/after
- [ ] Indexes added for new queries
- [ ] No N+1 query patterns introduced

**Example**: Adding user_preferences table

```markdown
### Acceptance Criteria: Add user_preferences Table

- [ ] Migration script creates user_preferences table
- [ ] Foreign key to users table with ON DELETE CASCADE
- [ ] Indexes on user_id and preference_key
- [ ] Down migration drops table cleanly
- [ ] Tested on development: migrated 10K users successfully
- [ ] Tested on staging: migrated 1M users in 15 seconds
- [ ] Application reads preferences correctly
- [ ] Rollback tested: application reverts to defaults
- [ ] CHANGELOG: "Database: Added user_preferences table"
- [ ] Deployment doc updated with migration step
```

---

## API Change

**Definition**: Modifying a public API (REST, GraphQL, gRPC, SDK, etc.).

### Acceptance Criteria

#### Compatibility

- [ ] Backward compatibility maintained (or breaking change justified and versioned)
- [ ] Existing API clients continue to work
- [ ] Deprecation warnings added for sunset endpoints
- [ ] Migration guide provided for breaking changes

#### Design

- [ ] API design follows RESTful/GraphQL/gRPC conventions
- [ ] Consistent with existing API patterns
- [ ] Error responses well-defined and consistent
- [ ] Pagination implemented for list endpoints (if applicable)

#### Documentation

- [ ] OpenAPI/GraphQL schema updated
- [ ] API reference documentation updated
- [ ] Code examples provided
- [ ] Authentication/authorization requirements documented
- [ ] Rate limiting noted

#### Testing

- [ ] API tests added for new endpoints
- [ ] Existing API tests still pass
- [ ] Error cases tested (400, 401, 403, 404, 500)
- [ ] Integration tests with sample client

#### Versioning

- [ ] API version incremented if breaking change
- [ ] Version documented in URL or header
- [ ] Changelog specifies version changes
- [ ] Old versions sunset plan documented

**Example**: Adding pagination to users endpoint

```markdown
### Acceptance Criteria: Add Pagination to /api/users

- [ ] Backward compatible: /api/users still returns first 100 users
- [ ] New query params: ?page=1&per_page=50
- [ ] Response includes pagination metadata (total, pages, current_page)
- [ ] OpenAPI spec updated with pagination params
- [ ] API docs include pagination examples
- [ ] Tests for page 1, last page, invalid page
- [ ] Performance tested: 50 users per page takes < 100ms
- [ ] CHANGELOG: "API: Added pagination to /api/users endpoint"
- [ ] Migration guide: "Use ?page=1&per_page=50 for paginated results"
```

---

## Custom Criteria

For change types not covered above, create custom criteria following this template:

### [Change Type Name]

**Definition**: _Brief description_

#### Acceptance Criteria

**Category 1**: _e.g., Functionality, Safety, etc._

- [ ] Criterion 1
- [ ] Criterion 2

**Category 2**:

- [ ] Criterion 1
- [ ] Criterion 2

**Example**: _Concrete example with filled-out checklist_

---

## Using Acceptance Criteria

### Before Starting Work

1. **Read relevant template**: Match your work to a template above
2. **Copy criteria**: Add to GitHub issue or `temp/notes/NEXT_STEPS.md`
3. **Customize**: Remove non-applicable items, add project-specific ones
4. **Review with team**: Clarify unclear criteria before proceeding

### During Work

- **Track progress**: Check off items as you complete them
- **Surface blockers**: Note items you can't complete and why
- **Ask questions**: If criteria unclear, seek clarification

### Before Submitting PR

- **Verify completion**: All criteria checked or explained
- **Include in PR**: Reference criteria in PR description
- **Self-review**: Use [VERIFICATION_CHECKLIST.md](./VERIFICATION_CHECKLIST.md)

---

**Template Version**: 1.0
**Last Updated**: 2025-12-17
**Related**: [VERIFICATION_CHECKLIST.md](./VERIFICATION_CHECKLIST.md), [REVIEW_CHECKLIST.md](./REVIEW_CHECKLIST.md)
