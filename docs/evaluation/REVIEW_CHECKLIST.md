# PR Review Checklist

**Purpose**: Structured guidance for thorough code review of agent-generated or human-generated changes.

**Usage**: Use this checklist when reviewing pull requests. Not all items apply to every PR—adapt based on change type and complexity.

---

## Quick Reference by Change Type

| Change Type          | Focus Areas                  | Key Sections               |
| -------------------- | ---------------------------- | -------------------------- |
| Feature Addition     | Tests, docs, compatibility   | 1-4, 7-8                   |
| Bug Fix              | Root cause, regression tests | 1, 3, 5                    |
| Refactoring          | Behavior preservation        | 1, 3, 6                    |
| Performance          | Measurements, trade-offs     | 1, 3, 9                    |
| Documentation        | Accuracy, clarity            | 8                          |
| Configuration        | Migration, rollback          | 2, 4, 8                    |
| Security Fix         | Vulnerability coverage       | 1, 2, 5, 10                |
| Database Migration   | Rollback, performance        | 2, 4, 9                    |

---

## Review Process

### 1. Initial Assessment (2-5 minutes)

Before diving into code details, check:

#### PR Description

- [ ] **Clear description**: What changed and why
- [ ] **Links provided**: Related issues, ADRs, documentation
- [ ] **Verification checklist**: Agent completed [VERIFICATION_CHECKLIST.md](./VERIFICATION_CHECKLIST.md)
- [ ] **Breaking changes noted**: If any, with migration plan
- [ ] **Testing evidence**: Test results, smoke test runs, manual verification

#### Changes Overview

- [ ] **Scope appropriate**: PR focused on single logical change
- [ ] **Size manageable**: < 500 lines preferred, > 1000 lines justify or split
- [ ] **File organization**: Changes make sense (no random formatting in unrelated files)
- [ ] **Git history clean**: Commits are logical, not "fix typo" spam

**Red flags at this stage**:

- ⛔ No description or generic "fixed bug"
- ⛔ Massive PR with unrelated changes
- ⛔ No tests for code changes
- ⛔ Verification checklist missing or incomplete

**Action**: Request improvements before detailed review if red flags present.

---

### 2. Correctness & Logic (10-20 minutes)

#### Core Functionality

- [ ] **Solves stated problem**: Change addresses the issue/requirement
- [ ] **Logic is sound**: Algorithm and business logic are correct
- [ ] **Edge cases handled**: Boundary conditions, empty inputs, null values considered
- [ ] **Error handling**: Errors caught gracefully with meaningful messages
- [ ] **No obvious bugs**: Careful read-through reveals no logical errors

#### Data Flow

- [ ] **Inputs validated**: User inputs sanitized and validated
- [ ] **Outputs correct**: Functions return expected types and values
- [ ] **State management**: Shared state modified safely (concurrency considered)
- [ ] **Resource cleanup**: Files closed, connections released, memory freed

#### Security

- [ ] **No security vulnerabilities**: SQL injection, XSS, CSRF, etc. prevented
- [ ] **Authentication checked**: Protected endpoints require auth
- [ ] **Authorization enforced**: Users can only access what they should
- [ ] **Secrets handled safely**: No hardcoded passwords, API keys in env vars
- [ ] **Input sanitization**: User data escaped/validated before use

**Code smell examples**:

```python
# ⛔ BAD: SQL injection risk
query = f"SELECT * FROM users WHERE email = '{user_email}'"

# ✅ GOOD: Parameterized query
query = "SELECT * FROM users WHERE email = %s"
cursor.execute(query, (user_email,))
```

```javascript
// ⛔ BAD: No error handling
const data = JSON.parse(input);

// ✅ GOOD: Graceful error handling
let data;
try {
  data = JSON.parse(input);
} catch (error) {
  return { error: 'Invalid JSON format' };
}
```

---

### 3. Testing (5-15 minutes)

#### Test Coverage

- [ ] **Tests added**: New code has corresponding tests
- [ ] **Tests meaningful**: Test logic, not implementation details
- [ ] **Edge cases tested**: Boundary conditions, errors, invalid inputs
- [ ] **Regression tests**: Bug fixes have regression tests
- [ ] **Coverage adequate**: Meets project requirements (typically 80%+)

#### Test Quality

- [ ] **Tests pass**: All tests succeed locally and in CI
- [ ] **Tests are isolated**: Don't depend on execution order
- [ ] **Clear test names**: Describe what's being tested
- [ ] **Arrange-Act-Assert**: Tests follow logical structure
- [ ] **No flaky tests**: Tests are deterministic and repeatable

#### Test Types

Check appropriate test types exist:

- [ ] **Unit tests**: Individual functions/methods
- [ ] **Integration tests**: Components working together
- [ ] **E2E tests**: Full user workflows (if applicable)
- [ ] **Smoke tests**: Critical paths covered (see [SMOKE.md](./SMOKE.md))

**Test smell examples**:

```python
# ⛔ BAD: Vague test name
def test_user():
    ...

# ✅ GOOD: Descriptive test name
def test_user_registration_fails_with_invalid_email():
    ...
```

```javascript
// ⛔ BAD: Testing implementation details
expect(component.state.internalCounter).toBe(5);

// ✅ GOOD: Testing behavior
expect(component.find('.counter').text()).toBe('5');
```

---

### 4. Code Quality (10-15 minutes)

#### Readability

- [ ] **Self-documenting**: Code is clear without comments
- [ ] **Comments explain why**: Not what (code shows what)
- [ ] **Naming clear**: Variables, functions, classes have meaningful names
- [ ] **Consistent style**: Follows project conventions
- [ ] **Appropriate abstraction**: Not over-engineered or under-abstracted

#### Structure

- [ ] **Single responsibility**: Functions/classes do one thing well
- [ ] **DRY (Don't Repeat Yourself)**: No unnecessary duplication
- [ ] **Proper scope**: Variables and functions have minimal scope
- [ ] **Cohesion**: Related code is grouped together
- [ ] **Coupling**: Loose coupling between modules

#### Language Features

- [ ] **Idiomatic code**: Uses language features appropriately
- [ ] **Type safety**: Type hints/annotations present (if applicable)
- [ ] **Modern syntax**: Uses current language version idioms
- [ ] **Performance-conscious**: Appropriate data structures and algorithms

**Code quality examples**:

```python
# ⛔ BAD: Magic numbers, unclear logic
def calculate(x):
    if x > 100:
        return x * 0.85
    return x * 0.95

# ✅ GOOD: Named constants, clear intent
BULK_DISCOUNT = 0.15
STANDARD_DISCOUNT = 0.05
BULK_THRESHOLD = 100

def calculate_price_with_discount(price):
    if price > BULK_THRESHOLD:
        return price * (1 - BULK_DISCOUNT)
    return price * (1 - STANDARD_DISCOUNT)
```

```javascript
// ⛔ BAD: Nested callbacks
getData((data) => {
  processData(data, (result) => {
    saveResult(result, (saved) => {
      console.log('Done');
    });
  });
});

// ✅ GOOD: Async/await
async function handleData() {
  const data = await getData();
  const result = await processData(data);
  await saveResult(result);
  console.log('Done');
}
```

---

### 5. Backward Compatibility (5-10 minutes)

#### API Compatibility

- [ ] **No breaking changes**: Existing API contracts maintained
- [ ] **Deprecation warnings**: Old features marked before removal
- [ ] **Version incremented**: API version bumped if breaking
- [ ] **Migration path**: Guide provided for breaking changes

#### Data Compatibility

- [ ] **Schema migrations**: Database changes have up/down migrations
- [ ] **Data preservation**: Existing data not lost or corrupted
- [ ] **Config compatibility**: Old configurations still work or upgrade path provided
- [ ] **Rollback possible**: Changes can be undone if needed

#### Behavior Compatibility

- [ ] **Existing tests pass**: Regression tests verify no breakage
- [ ] **Feature flags**: New behavior gated if experimental
- [ ] **Default behavior preserved**: Changes are opt-in when possible

**Compatibility considerations**:

```python
# ⛔ BAD: Breaking change without version bump
def get_user(id):  # Changed from get_user(email)
    # Breaks existing callers
    ...

# ✅ GOOD: Maintain compatibility with new parameter
def get_user(email=None, id=None):  # Supports both old and new
    if id:
        return User.get_by_id(id)
    elif email:
        return User.get_by_email(email)
    else:
        raise ValueError("Must provide email or id")
```

---

### 6. Performance (5-10 minutes)

#### Efficiency

- [ ] **No obvious bottlenecks**: O(n²) algorithms avoided where possible
- [ ] **Database queries optimized**: No N+1 queries, proper indexes
- [ ] **Caching considered**: Expensive operations cached appropriately
- [ ] **Resource usage reasonable**: Memory, CPU, network usage acceptable

#### Measurements

- [ ] **Baseline compared**: Performance before/after documented (if relevant)
- [ ] **Benchmarks added**: Performance-critical code has benchmarks
- [ ] **Load tested**: High-traffic features tested under load
- [ ] **No regressions**: Existing functionality not significantly slower

#### Scalability

- [ ] **Scales with data**: Works with large datasets
- [ ] **Scales with users**: Handles concurrent users
- [ ] **Bounded resources**: No unbounded loops, memory leaks, etc.

**Performance red flags**:

```python
# ⛔ BAD: N+1 query problem
users = User.all()
for user in users:
    orders = Order.where(user_id=user.id).all()  # N queries

# ✅ GOOD: Single query with join
users_with_orders = User.joins(:orders).all()  # 1 query
```

```javascript
// ⛔ BAD: Synchronous in loop
for (const file of files) {
  await processFile(file);  // Serial, slow
}

// ✅ GOOD: Parallel processing
await Promise.all(files.map(file => processFile(file)));
```

---

### 7. Documentation (5-10 minutes)

#### Code Documentation

- [ ] **Public APIs documented**: Functions/classes have docstrings/JSDoc
- [ ] **Complex logic explained**: Non-obvious code has comments
- [ ] **Parameters documented**: Types, constraints, defaults noted
- [ ] **Examples provided**: Usage examples for complex functions

#### Project Documentation

- [ ] **README updated**: If setup/usage changed
- [ ] **CHANGELOG updated**: User-facing changes noted
- [ ] **API docs updated**: If API changed
- [ ] **ADR created**: If architectural decision made
- [ ] **Migration guide**: If breaking changes introduced

#### Documentation Quality

- [ ] **Accurate**: Docs match implementation
- [ ] **Complete**: All aspects covered
- [ ] **Clear**: Written for target audience
- [ ] **Examples work**: Code examples are tested

**Documentation examples**:

```python
# ⛔ BAD: Useless docstring
def calculate(x, y):
    """Calculate something"""
    return x * y + 10

# ✅ GOOD: Informative docstring
def calculate_order_total(subtotal: float, tax_rate: float) -> float:
    """
    Calculate order total including tax.
    
    Args:
        subtotal: Order subtotal before tax (must be >= 0)
        tax_rate: Tax rate as decimal (e.g., 0.08 for 8%)
    
    Returns:
        Total order amount including tax
        
    Raises:
        ValueError: If subtotal is negative
        
    Example:
        >>> calculate_order_total(100.0, 0.08)
        108.0
    """
    if subtotal < 0:
        raise ValueError("Subtotal must be non-negative")
    return subtotal * (1 + tax_rate)
```

---

### 8. Dependencies & Configuration (5 minutes)

#### Dependency Management

- [ ] **Justified additions**: New dependencies are necessary
- [ ] **Versions pinned**: Specific versions, not ranges
- [ ] **License compatible**: New deps have compatible licenses
- [ ] **Security checked**: No known vulnerabilities (npm audit, safety check)
- [ ] **Maintained**: Dependencies are actively maintained

#### Configuration

- [ ] **Environment variables documented**: Added to `.env.example`
- [ ] **Defaults provided**: Sensible defaults for optional config
- [ ] **Validation present**: Config values validated at startup
- [ ] **Secrets externalized**: No secrets in code

**Dependency review questions**:

1. Can we accomplish this without a new dependency?
2. Is this dependency well-maintained (recent commits)?
3. How many transitive dependencies does it add?
4. What's the license?
5. Are there security advisories?

---

### 9. Architecture & Design (10-15 minutes)

#### Design Decisions

- [ ] **Appropriate solution**: Design matches problem complexity
- [ ] **Follows patterns**: Consistent with project architecture
- [ ] **ADR created**: Significant decisions documented
- [ ] **Alternatives considered**: Trade-offs explained

#### System Impact

- [ ] **Integrates cleanly**: Fits naturally into existing system
- [ ] **No architectural drift**: Maintains system coherence
- [ ] **Future-friendly**: Doesn't paint into corner
- [ ] **Technical debt**: If introduced, acknowledged and tracked

#### Code Organization

- [ ] **Proper layering**: Presentation, business logic, data access separated
- [ ] **Dependency direction**: Dependencies point inward (dependency inversion)
- [ ] **Modules cohesive**: Related functionality grouped
- [ ] **Interfaces clear**: Clean boundaries between components

**Architecture considerations**:

- Is this change adding complexity that's justified?
- Does it follow established patterns or introduce new ones?
- Will this be easy to maintain in 6 months?
- Are we solving today's problem without overengineering?

---

### 10. Security & Safety (5-10 minutes)

#### Security Checklist

- [ ] **Input validation**: All user inputs validated
- [ ] **Output encoding**: HTML/SQL/JS properly escaped
- [ ] **Authentication**: Protected resources require auth
- [ ] **Authorization**: Users can only access allowed resources
- [ ] **HTTPS enforced**: Sensitive data sent over secure connections
- [ ] **CSRF protection**: Forms have CSRF tokens (if applicable)
- [ ] **Rate limiting**: APIs have rate limits
- [ ] **Secrets safe**: No hardcoded credentials, use env vars
- [ ] **Dependencies safe**: No known vulnerabilities

#### Common Vulnerabilities

Check for OWASP Top 10:

- [ ] **Injection**: SQL, NoSQL, LDAP, OS command injection
- [ ] **Broken Authentication**: Session management, password storage
- [ ] **Sensitive Data Exposure**: Encryption, secure transmission
- [ ] **XML External Entities (XXE)**: XML parser configuration
- [ ] **Broken Access Control**: Authorization checks
- [ ] **Security Misconfiguration**: Default passwords, debug mode
- [ ] **XSS**: Cross-site scripting prevention
- [ ] **Insecure Deserialization**: Safe deserialization
- [ ] **Using Components with Known Vulnerabilities**: Dependency scanning
- [ ] **Insufficient Logging**: Security events logged

**Security review questions**:

1. What could go wrong if a malicious user tries this?
2. What's the worst case if this component is compromised?
3. Is sensitive data properly protected?
4. Are we following security best practices?

---

## Review Decision

### After completing checklist:

#### ✅ Approve

Approve if:

- All critical items checked or explained
- Tests pass and coverage adequate
- Documentation complete
- No major concerns
- Minor issues can be addressed in follow-up

**Template comment**:

```markdown
✅ **Approved with minor suggestions**

Great work! Code is solid and tests cover the main scenarios.

Minor suggestions (optional):
- Consider extracting `calculate_discount()` to a helper
- Might add example to README for the new feature

Smoke tests passed: [link to CI run]
```

#### 💬 Request Changes

Request changes if:

- Critical bugs found
- Tests missing or inadequate
- Security concerns
- Major architectural issues
- Documentation incomplete for user-facing changes

**Template comment**:

```markdown
🔄 **Changes requested**

Thanks for the PR! Found a few issues that need addressing before merge:

**Critical:**
1. SQL injection vulnerability in user search (line 45)
2. Missing tests for error handling paths

**Important:**
3. Breaking API change not documented in CHANGELOG
4. Missing migration rollback script

**Optional:**
5. Consider renaming `process()` to something more descriptive

Please address critical and important items. Happy to review again once updated!
```

#### 🤔 Needs Discussion

Comment for discussion if:

- Unclear if approach is correct
- Design trade-offs need team input
- Scope seems off
- Architectural implications uncertain

**Template comment**:

```markdown
🤔 **Needs discussion**

Implementation looks solid, but want to discuss the approach:

**Questions:**
1. Should this be behind a feature flag?
2. Have we considered impact on mobile clients?
3. Is this the right abstraction level?

Let's discuss synchronously or in comments. @team-leads thoughts?
```

---

## Special Considerations

### Reviewing Agent-Generated Code

Agents may have different patterns than humans. Pay extra attention to:

- [ ] **Assumption validation**: Did agent make correct assumptions?
- [ ] **Completeness**: All aspects of task addressed (code, tests, docs)?
- [ ] **Context awareness**: Does change fit project conventions?
- [ ] **Over-engineering**: Sometimes agents over-abstract

**Helpful approach**: Ask "Why was this approach chosen?" Agent should have documented reasoning.

### Large PRs

For PRs > 500 lines:

1. **Request breakdown**: Ask for smaller PRs if possible
2. **Focus review**: Prioritize critical sections
3. **Multiple passes**: Don't try to review everything at once
4. **Leverage tools**: Use code review tools for diffs, comments

### Refactoring PRs

Refactoring needs extra care:

- [ ] **No behavior change**: Tests pass without modification
- [ ] **Incremental**: Not big-bang rewrite
- [ ] **Reversible**: Can roll back if issues found

**Pro tip**: Use `git diff --ignore-all-space` to hide formatting changes.

### Performance PRs

- [ ] **Measurements provided**: Before/after benchmarks
- [ ] **Significant improvement**: Optimization worth complexity added
- [ ] **No correctness trade-off**: Still correct after optimization

---

## Review Efficiency Tips

### Before Review

1. **Pull latest**: `git pull origin main`
2. **Check out PR branch**: `git checkout feature-branch`
3. **Run tests locally**: Verify tests pass on your machine
4. **Review description**: Read PR description thoroughly

### During Review

1. **Start with tests**: Review tests first to understand intent
2. **Main logic second**: Focus on core changes
3. **Details last**: Formatting, naming, etc. at the end
4. **Use review tools**: GitHub suggestions, inline comments

### After Review

1. **Be specific**: Point to lines, suggest fixes
2. **Be kind**: Assume good intent, constructive feedback
3. **Balance**: Nitpicks vs. real issues
4. **Follow up**: Track if requested changes made

### Time Management

- **Small PR (< 100 lines)**: 15-30 minutes
- **Medium PR (100-300 lines)**: 30-60 minutes
- **Large PR (300-500 lines)**: 1-2 hours
- **Very large PR (> 500 lines)**: Request breakdown or multiple reviewers

---

## Review Comments Examples

### 🟢 Good Review Comments

```markdown
**Correctness issue** (line 42):
This will fail if `data` is None. Consider adding:
```python
if data is None:
    return []
```

**Performance concern** (line 78):
This query will be slow for large datasets due to N+1 problem.
Suggestion: Use eager loading:
```python
users = User.joins(:orders).where(...)
```

**Architecture question** (line 120):
Should this logic be in the controller or extracted to a service class?
Relates to our discussion in ADR 005 about service layer pattern.

**Nit** (line 200):
Consider more descriptive variable name: `filtered_active_users` instead of `fau`
(Not blocking, just suggestion for clarity)
```

### 🔴 Avoid These Comment Patterns

```markdown
❌ "This is wrong." (Not helpful - explain why and suggest fix)

❌ "We don't do it this way." (Explain project convention or link to style guide)

❌ "Why did you do it like this?" (Sounds accusatory - ask neutrally)

❌ "Just use X library." (Explain trade-offs, don't mandate without discussion)
```

---

## Continuous Improvement

### After Each Review

- **Track time**: How long did review take?
- **Note patterns**: Recurring issues to address in templates
- **Update checklist**: Add items for new patterns

### Monthly Review Retrospective

- **What slowed reviews?** → Improve process
- **What issues were missed?** → Strengthen checklist
- **What worked well?** → Amplify

---

**Checklist Version**: 1.0
**Last Updated**: 2025-12-17
**Related**: [VERIFICATION_CHECKLIST.md](./VERIFICATION_CHECKLIST.md), [ACCEPTANCE_CRITERIA.md](./ACCEPTANCE_CRITERIA.md), [SMOKE.md](./SMOKE.md)
