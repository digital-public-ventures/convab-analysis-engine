# Testing Guide

**Purpose**: Define testing philosophy, organization, patterns, and best practices for maintaining high-quality, reliable code.

---

## Testing Philosophy

### Core Principles

1. **Test Pyramid**: More unit tests, fewer integration tests, minimal end-to-end tests
2. **Fast Feedback**: Tests should run quickly to encourage frequent execution
3. **Reliability**: Tests should be deterministic and not flaky
4. **Maintainability**: Tests are code too - keep them clean and DRY
5. **Documentation**: Tests serve as living documentation of system behavior

### Coverage Targets

- **Unit Tests**: 80%+ coverage of business logic
- **Integration Tests**: Critical paths and component interactions
- **End-to-End Tests**: Key user workflows and critical business processes

**Remember**: 100% coverage doesn't guarantee bug-free code. Focus on meaningful tests over coverage metrics.

---

## Test Organization

### Directory Structure

```
tests/
├── unit/                    # Fast, isolated tests for individual units
│   ├── models/
│   ├── services/
│   ├── utils/
│   └── validators/
├── integration/             # Tests for component interactions
│   ├── api/
│   ├── database/
│   └── services/
├── e2e/                     # End-to-end user workflow tests
│   ├── smoke/              # Critical path smoke tests
│   └── workflows/
├── fixtures/                # Test data and fixtures
│   ├── data/
│   └── factories/
├── mocks/                   # Mock objects and stubs
└── helpers/                 # Test utilities and helpers
    ├── setup.{ext}         # Test environment setup
    └── teardown.{ext}      # Test cleanup
```

### Naming Conventions

**Files**:

- Unit tests: `test_<module>.{ext}` or `<module>_test.{ext}`
- Integration tests: `test_<feature>_integration.{ext}`
- E2E tests: `test_<workflow>_e2e.{ext}`

**Test Functions/Methods**:

- Use descriptive names: `test_user_login_with_valid_credentials`
- Pattern: `test_<what>_<condition>_<expected_result>`

---

## Testing Patterns

### Unit Tests

**Purpose**: Test individual functions, methods, or classes in isolation.

**Characteristics**:

- No external dependencies (databases, APIs, file systems)
- Fast execution (< 100ms per test)
- Use mocks/stubs for dependencies
- Focus on single responsibility

**Example Structure**:

```python
# Python example
def test_calculate_total_with_discount():
    # Arrange: Set up test data
    items = [Item(price=10), Item(price=20)]
    discount = 0.1

    # Act: Execute the function
    total = calculate_total(items, discount)

    # Assert: Verify the result
    assert total == 27.0  # (10 + 20) * 0.9
```

```javascript
// JavaScript example
describe('calculateTotal', () => {
  it('should apply discount correctly', () => {
    // Arrange
    const items = [{ price: 10 }, { price: 20 }];
    const discount = 0.1;

    // Act
    const total = calculateTotal(items, discount);

    // Assert
    expect(total).toBe(27.0);
  });
});
```

### Integration Tests

**Purpose**: Test interactions between multiple components.

**Characteristics**:

- Test component boundaries and interfaces
- May use test databases or in-memory stores
- Slower than unit tests (< 1s per test)
- Verify data flow and contract compliance

**Common Integration Test Types**:

1. **Database Integration**: Test repository/ORM layer with real database
2. **API Integration**: Test HTTP endpoints with request/response validation
3. **Service Integration**: Test service-to-service communication
4. **External System Integration**: Test third-party API integrations (use test/sandbox environments)

### End-to-End Tests

**Purpose**: Test complete user workflows from start to finish.

**Characteristics**:

- Test from user perspective (UI or API)
- Use realistic data and scenarios
- Slowest tests (seconds to minutes)
- Focus on critical business workflows

**Best Practices**:

- Keep E2E tests minimal (5-20 tests for critical paths)
- Run in CI/CD pipeline before deployment
- Use stable test data and environments
- Implement proper cleanup between tests

---

## Mocking and Test Doubles

### Types of Test Doubles

1. **Stub**: Provides predetermined responses
2. **Mock**: Verifies interactions and method calls
3. **Spy**: Wraps real object to track interactions
4. **Fake**: Working implementation with shortcuts (e.g., in-memory database)
5. **Dummy**: Placeholder object that's never actually used

### When to Mock

**✅ Mock**:

- External services (APIs, email, payments)
- Slow operations (file I/O, network calls)
- Non-deterministic behavior (random, timestamps, UUIDs)
- Hard-to-reproduce scenarios (error conditions, edge cases)

**❌ Don't Mock**:

- Simple data structures
- Language/framework built-ins
- Your own domain models (test them directly)
- Everything (over-mocking makes tests brittle)

### Mocking Best Practices

```python
# Python example with pytest and unittest.mock
from unittest.mock import Mock, patch

def test_send_notification_calls_email_service():
    # Create a mock email service
    mock_email_service = Mock()

    # Inject the mock
    notifier = NotificationService(email_service=mock_email_service)

    # Execute
    notifier.send_notification(user_id=123, message="Hello")

    # Verify the interaction
    mock_email_service.send_email.assert_called_once_with(
        to="user@example.com",
        subject="Notification",
        body="Hello"
    )
```

```javascript
// JavaScript example with Jest
jest.mock('./emailService');

test('send notification calls email service', () => {
  // Create mock
  const mockSend = jest.fn();
  emailService.sendEmail = mockSend;

  // Execute
  const notifier = new NotificationService(emailService);
  notifier.sendNotification(123, 'Hello');

  // Verify
  expect(mockSend).toHaveBeenCalledWith({
    to: 'user@example.com',
    subject: 'Notification',
    body: 'Hello',
  });
});
```

---

## Test Data Management

### Fixtures and Factories

**Fixtures**: Pre-defined, reusable test data

```python
# Python pytest fixture
@pytest.fixture
def sample_user():
    return User(
        id=1,
        username="testuser",
        email="test@example.com"
    )

def test_user_profile(sample_user):
    assert sample_user.username == "testuser"
```

**Factories**: Generate test data programmatically

```python
# Python factory example
class UserFactory:
    @staticmethod
    def create(username="testuser", email=None):
        email = email or f"{username}@example.com"
        return User(username=username, email=email)

def test_multiple_users():
    user1 = UserFactory.create("alice")
    user2 = UserFactory.create("bob")
    assert user1.email == "alice@example.com"
```

### Test Database Strategies

1. **In-Memory Database**: Fast, isolated (SQLite in-memory, H2)
2. **Test Database**: Real database instance, reset between tests
3. **Transactions**: Wrap tests in transactions, rollback after each test
4. **Containerized Database**: Docker container, consistent environment

**Best Practice**: Use database migrations in tests to ensure schema consistency.

---

## CI/CD Integration

### Test Pipeline Structure

```yaml
# Example CI pipeline
stages:
  - lint # Code style and static analysis
  - unit # Fast unit tests
  - integration # Integration tests
  - e2e # End-to-end tests (optional, can be gated)
  - coverage # Coverage report and enforcement
```

### Running Tests in CI

**Key Considerations**:

- **Parallelization**: Split tests across multiple runners
- **Caching**: Cache dependencies (node_modules, pip cache)
- **Test Isolation**: Ensure tests don't interfere with each other
- **Timeouts**: Set reasonable timeouts to catch hanging tests
- **Failure Handling**: Fail fast on critical tests, continue for coverage

### Coverage Enforcement

```bash
# Example: Fail if coverage drops below threshold
pytest --cov=src --cov-fail-under=80

# JavaScript/Jest
jest --coverage --coverageThreshold='{"global": {"lines": 80}}'
```

---

## Testing Best Practices

### DO ✅

- **Write tests first (TDD)**: When possible, write tests before implementation
- **Test behavior, not implementation**: Focus on what the code does, not how
- **Use descriptive test names**: `test_user_cannot_login_with_invalid_password`
- **One assertion per test**: Or at least one logical concept per test
- **Test edge cases**: Empty inputs, null values, boundary conditions
- **Keep tests independent**: Tests should not depend on execution order
- **Use factories for complex objects**: Avoid duplicating object creation
- **Clean up after tests**: Reset state, close connections, delete temp files
- **Run tests frequently**: Before commits, during development

### DON'T ❌

- **Don't test framework code**: Trust that Flask, Django, React, etc. work
- **Don't test third-party libraries**: Test your usage of them, not the library itself
- **Don't write brittle tests**: Tests shouldn't break with minor refactoring
- **Don't ignore flaky tests**: Fix or remove them, don't skip
- **Don't test everything**: Focus on business logic and critical paths
- **Don't mock everything**: Over-mocking makes tests meaningless
- **Don't duplicate production code**: Keep test logic simple
- **Don't commit disabled tests**: Fix or remove failing tests

---

## Language-Specific Testing Tools

### Python

- **Test Frameworks**: pytest, unittest, nose2
- **Mocking**: unittest.mock, pytest-mock
- **Coverage**: coverage.py, pytest-cov
- **Fixtures**: pytest fixtures, factory_boy
- **E2E**: Selenium, Playwright, Behave (BDD)

```bash
# Run tests with pytest
pytest tests/

# With coverage
pytest --cov=src --cov-report=html tests/

# Specific test file
pytest tests/unit/test_models.py

# Specific test
pytest tests/unit/test_models.py::test_user_creation
```

### JavaScript/TypeScript

- **Test Frameworks**: Jest, Mocha, Vitest
- **Assertions**: Chai, Jest matchers
- **Mocking**: Jest, Sinon
- **Coverage**: Jest, Istanbul, c8
- **E2E**: Playwright, Cypress, Puppeteer

```bash
# Run tests with Jest
npm test

# With coverage
npm test -- --coverage

# Watch mode
npm test -- --watch

# Specific test file
npm test -- user.test.ts
```

### Go

- **Test Framework**: Built-in testing package
- **Mocking**: gomock, testify/mock
- **Coverage**: Built-in coverage tool
- **E2E**: testcontainers-go

```bash
# Run tests
go test ./...

# With coverage
go test -cover ./...

# Verbose output
go test -v ./...

# Specific package
go test ./pkg/user
```

### Rust

- **Test Framework**: Built-in test framework
- **Mocking**: mockall, mockito
- **Coverage**: tarpaulin, grcov
- **E2E**: Built-in integration tests

```bash
# Run tests
cargo test

# With coverage (requires tarpaulin)
cargo tarpaulin --out Html

# Specific test
cargo test test_user_creation

# Integration tests only
cargo test --test integration_tests
```

---

## Debugging Failed Tests

### Common Failure Patterns

1. **Flaky Tests**: Tests that pass/fail inconsistently
   - **Causes**: Race conditions, timing issues, external dependencies
   - **Solutions**: Add explicit waits, use mocks, ensure proper cleanup

2. **Environment-Specific Failures**: Tests pass locally, fail in CI
   - **Causes**: Different OS, missing dependencies, environment variables
   - **Solutions**: Use Docker for consistency, check CI environment setup

3. **Test Order Dependencies**: Tests pass individually, fail together
   - **Causes**: Shared state, global variables, incomplete cleanup
   - **Solutions**: Ensure test isolation, use setup/teardown properly

### Debugging Strategies

```bash
# Run single test with verbose output
pytest -vv tests/unit/test_user.py::test_login

# Run with debugging
pytest --pdb tests/unit/test_user.py

# Print detailed failure info
pytest -vv --tb=long

# Run last failed tests only
pytest --lf
```

---

## Performance Testing

### Load Testing

**Tools**: JMeter, Locust, k6, Artillery

**When to Load Test**:

- Before production deployment
- After significant performance changes
- Periodically to catch regressions

### Benchmark Testing

**Purpose**: Measure performance of specific functions or operations.

```python
# Python example with pytest-benchmark
def test_calculation_performance(benchmark):
    result = benchmark(expensive_calculation, n=1000)
    assert result > 0
```

---

## Security Testing

### Automated Security Checks

- **Dependency Scanning**: Check for vulnerable dependencies (npm audit, safety, cargo audit)
- **SAST**: Static Application Security Testing (Bandit, ESLint security plugins)
- **Secret Scanning**: Detect committed secrets (git-secrets, trufflehog)

### Security Test Cases

- **Input Validation**: Test with malicious inputs (SQL injection, XSS)
- **Authentication**: Test auth bypass, weak passwords, session handling
- **Authorization**: Test privilege escalation, access control
- **Rate Limiting**: Test API rate limits and DOS protection

---

## Test Maintenance

### When to Update Tests

- **After bug fixes**: Add regression test before fixing bug
- **During refactoring**: Update tests to match new implementation
- **When requirements change**: Update tests to reflect new behavior
- **When tests become flaky**: Fix or remove, don't ignore

### Refactoring Tests

**Signs tests need refactoring**:

- Lots of duplicated setup code
- Tests are hard to understand
- Tests break with small code changes
- Tests are slow without good reason

**Refactoring techniques**:

- Extract common setup to fixtures/helpers
- Use factories for test data
- Split large test files into smaller ones
- Remove obsolete tests

---

## Additional Resources

### Books

- "Test Driven Development: By Example" by Kent Beck
- "Growing Object-Oriented Software, Guided by Tests" by Steve Freeman & Nat Pryce
- "Working Effectively with Legacy Code" by Michael Feathers

### Online Resources

- [Testing Best Practices (Martin Fowler)](https://martinfowler.com/testing/)
- [Test Pyramid (Martin Fowler)](https://martinfowler.com/articles/practical-test-pyramid.html)
- Language-specific testing docs (pytest, Jest, Go testing, etc.)

---

## Project-Specific Testing Notes

<!--
Add project-specific testing conventions, tools, and practices here:
- Custom test utilities
- Project-specific mocking patterns
- Integration test setup instructions
- E2E test environment configuration
-->

**TODO**: Document project-specific testing setup and conventions after initial development.
