# Smoke Tests

**Purpose**: Fast, critical-path tests to catch obvious regressions before detailed review.

**Target Time**: < 30 seconds total execution

**Philosophy**: Smoke tests are not comprehensive. They verify the application is "not on fire" - basic functionality works. Full test suite provides comprehensive coverage.

---

## Quick Start

### Running Smoke Tests

```bash
# Manual execution (language-specific)
npm run smoke-test          # Node.js
pytest tests/smoke/         # Python
go test ./smoke/...         # Go
cargo test --test smoke     # Rust

# Or use project script (if available)
./scripts/smoke-test.sh
```

### Expected Output

```
✅ Smoke Test 1: Application starts
✅ Smoke Test 2: Health check responds
✅ Smoke Test 3: Database connection works
✅ Smoke Test 4: Authentication flow succeeds
✅ Smoke Test 5: Critical API endpoint returns data

All smoke tests passed in 12.3 seconds
```

---

## Universal Smoke Tests

These apply to most projects regardless of tech stack.

### 1. Application Starts

**Purpose**: Verify application can boot without crashing

**Test**:

```bash
# Start application
npm start &          # Node.js
python app.py &      # Python
./binary &           # Compiled binary

# Wait for startup
sleep 5

# Check process is running
ps aux | grep [a]pp.py

# Cleanup
kill $!
```

**Success**: Application process starts and stays running for at least 5 seconds

**Failure signals**:

- Immediate crash
- Import/dependency errors
- Configuration errors
- Port already in use

### 2. Health Check Endpoint

**Purpose**: Verify application responds to HTTP requests

**Test**:

```bash
# Start application in background
npm start &
APP_PID=$!
sleep 5

# Hit health check endpoint
curl -f http://localhost:3000/health

# Cleanup
kill $APP_PID
```

**Expected Response**:

```json
{
  "status": "ok",
  "timestamp": "2025-12-17T10:30:00Z"
}
```

**Success**: HTTP 200 response with valid JSON

**Failure signals**:

- Connection refused
- 500 Internal Server Error
- Timeout
- Invalid JSON response

### 3. Database Connection

**Purpose**: Verify application can connect to database

**Test**:

```bash
# Set database URL (use test database)
export DATABASE_URL="postgresql://user:pass@localhost:5432/testdb"

# Run connection test
npm run db:ping       # Node.js
python -m app.db_check  # Python
./bin/db-health-check   # Binary
```

**Expected Output**:

```
✓ Database connection successful
✓ Schema version: 42
✓ Connection pool: 5/10 active
```

**Success**: Successful connection and basic query

**Failure signals**:

- Connection refused
- Authentication failed
- Database doesn't exist
- Schema mismatch

### 4. Critical User Flow

**Purpose**: Verify end-to-end functionality of most important feature

**Example (E-commerce)**:

```bash
# Create test user
curl -X POST http://localhost:3000/api/auth/register \
  -d '{"email": "smoke@test.com", "password": "testpass123"}'

# Login
TOKEN=$(curl -X POST http://localhost:3000/api/auth/login \
  -d '{"email": "smoke@test.com", "password": "testpass123"}' \
  | jq -r '.token')

# Add item to cart
curl -X POST http://localhost:3000/api/cart \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"product_id": "test-product", "quantity": 1}'

# Checkout
curl -X POST http://localhost:3000/api/checkout \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"payment_method": "test"}'

# Verify order created
curl http://localhost:3000/api/orders \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.orders[0].status'  # Should be "pending"
```

**Success**: All API calls return 200, order created

**Failure signals**:

- Any 4xx/5xx response
- Authentication failure
- Data not persisted
- Business logic error

### 5. Static Assets Load

**Purpose**: Verify frontend assets are accessible (if web app)

**Test**:

```bash
# Check main page loads
curl -f http://localhost:3000/ | grep "<title>"

# Check CSS loads
curl -f http://localhost:3000/static/css/main.css

# Check JS loads
curl -f http://localhost:3000/static/js/app.js

# Check images load
curl -f http://localhost:3000/static/images/logo.png
```

**Success**: All assets return 200 and have expected content type

**Failure signals**:

- 404 Not Found
- Wrong content type
- Build artifacts missing

---

## Tech Stack-Specific Smoke Tests

### Python/Django/Flask

```python
# tests/smoke/test_smoke.py
import pytest
import requests
from myapp import create_app, db

def test_app_starts():
    """Smoke test: Application starts"""
    app = create_app('testing')
    assert app is not None

def test_health_check():
    """Smoke test: Health check responds"""
    app = create_app('testing')
    client = app.test_client()
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'ok'

def test_database_connection():
    """Smoke test: Database connection works"""
    app = create_app('testing')
    with app.app_context():
        result = db.session.execute('SELECT 1')
        assert result is not None

def test_critical_endpoint():
    """Smoke test: Critical API returns data"""
    app = create_app('testing')
    client = app.test_client()
    
    # Create test user
    client.post('/api/auth/register', json={
        'email': 'smoke@test.com',
        'password': 'testpass123'
    })
    
    # Login
    response = client.post('/api/auth/login', json={
        'email': 'smoke@test.com',
        'password': 'testpass123'
    })
    token = response.json['token']
    
    # Hit critical endpoint
    response = client.get('/api/users/me',
        headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    assert 'email' in response.json
```

**Run**: `pytest tests/smoke/ -v`

### Node.js/Express

```javascript
// tests/smoke/smoke.test.js
const request = require('supertest');
const app = require('../../src/app');
const db = require('../../src/db');

describe('Smoke Tests', () => {
  afterAll(async () => {
    await db.close();
  });

  test('Application starts', () => {
    expect(app).toBeDefined();
  });

  test('Health check responds', async () => {
    const response = await request(app).get('/health');
    expect(response.status).toBe(200);
    expect(response.body.status).toBe('ok');
  });

  test('Database connection works', async () => {
    const result = await db.query('SELECT 1 as test');
    expect(result.rows[0].test).toBe(1);
  });

  test('Critical endpoint returns data', async () => {
    // Register user
    await request(app)
      .post('/api/auth/register')
      .send({ email: 'smoke@test.com', password: 'testpass123' });

    // Login
    const loginResponse = await request(app)
      .post('/api/auth/login')
      .send({ email: 'smoke@test.com', password: 'testpass123' });

    const token = loginResponse.body.token;

    // Hit critical endpoint
    const response = await request(app)
      .get('/api/users/me')
      .set('Authorization', `Bearer ${token}`);

    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('email');
  });
});
```

**Run**: `npm run smoke-test` (configure in package.json: `"smoke-test": "jest tests/smoke/"`)

### Go

```go
// smoke/smoke_test.go
package smoke

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/yourorg/yourapp/app"
	"github.com/yourorg/yourapp/db"
)

func TestApplicationStarts(t *testing.T) {
	server := app.NewServer()
	if server == nil {
		t.Fatal("Application failed to start")
	}
}

func TestHealthCheck(t *testing.T) {
	server := app.NewServer()
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	server.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("Expected 200, got %d", w.Code)
	}
}

func TestDatabaseConnection(t *testing.T) {
	database, err := db.Connect()
	if err != nil {
		t.Fatalf("Database connection failed: %v", err)
	}
	defer database.Close()

	var result int
	err = database.QueryRow("SELECT 1").Scan(&result)
	if err != nil {
		t.Fatalf("Database query failed: %v", err)
	}
	if result != 1 {
		t.Fatalf("Expected 1, got %d", result)
	}
}
```

**Run**: `go test ./smoke/... -v`

### Rust

```rust
// tests/smoke.rs
use myapp::{App, db};

#[test]
fn test_app_starts() {
    let app = App::new();
    assert!(app.is_ok());
}

#[test]
fn test_health_check() {
    let app = App::new().unwrap();
    let response = app.request("/health").send().unwrap();
    assert_eq!(response.status(), 200);
    assert_eq!(response.json()["status"], "ok");
}

#[test]
fn test_database_connection() {
    let conn = db::connect().unwrap();
    let result: i32 = conn.query_row("SELECT 1", [], |row| row.get(0)).unwrap();
    assert_eq!(result, 1);
}
```

**Run**: `cargo test --test smoke`

---

## Smoke Test Checklist

Use this when manually testing critical paths:

### Web Application

- [ ] **Homepage loads**: Navigate to root URL, page renders
- [ ] **Login works**: Enter credentials, redirected to dashboard
- [ ] **Main feature works**: Execute primary user workflow
- [ ] **Navigation works**: All main nav links functional
- [ ] **Logout works**: Logout, redirected to login page

### API Service

- [ ] **Health endpoint responds**: `GET /health` returns 200
- [ ] **Authentication works**: Can obtain token with valid credentials
- [ ] **Main endpoint works**: Primary API endpoint returns expected data
- [ ] **Error handling works**: Invalid requests return appropriate errors
- [ ] **Rate limiting works**: Excessive requests get rate-limited

### CLI Tool

- [ ] **Help text displays**: `app --help` shows usage
- [ ] **Version displays**: `app --version` shows version
- [ ] **Main command works**: Primary command executes successfully
- [ ] **Error messages clear**: Invalid usage shows helpful error
- [ ] **Exit codes correct**: Success = 0, errors = non-zero

### Database Application

- [ ] **Migrations run**: `migrate up` succeeds
- [ ] **Connection works**: Application connects to database
- [ ] **Queries execute**: Basic CRUD operations work
- [ ] **Transactions work**: Rollback on error, commit on success
- [ ] **Rollback works**: `migrate down` succeeds

---

## Creating Project-Specific Smoke Tests

### 1. Identify Critical Paths

Ask: "What are the 3-5 things that MUST work for this app to be useful?"

**Examples**:

- **E-commerce**: Browse → Add to cart → Checkout
- **Social media**: Login → Create post → View feed
- **Analytics**: Ingest data → Query data → Generate report
- **DevOps tool**: Connect to server → Deploy application → Verify deployment

### 2. Write Minimal Tests

Focus on happy path only. Edge cases and error conditions are for full test suite.

**Good smoke test**:

```python
def test_user_can_complete_checkout():
    """User can add item to cart and complete checkout"""
    user = create_test_user()
    product = create_test_product()
    
    cart = user.add_to_cart(product, quantity=1)
    order = user.checkout(cart, payment_method='test')
    
    assert order.status == 'completed'
```

**Too detailed for smoke test**:

```python
def test_checkout_with_discount_and_split_payment():
    """Complex checkout scenario with multiple coupons"""
    # Too specific for smoke test - belongs in full test suite
```

### 3. Keep Execution Fast

**Techniques**:

- Use test fixtures instead of seeding large datasets
- Mock external services (payment processors, email)
- Use in-memory database for unit smoke tests
- Run against minimal infrastructure
- Skip slow operations (full indexing, batch jobs)

**Target**: Each smoke test < 5 seconds, total suite < 30 seconds

### 4. Make Output Clear

**Good output**:

```
✅ Smoke Test: User authentication works
✅ Smoke Test: File upload succeeds  
✅ Smoke Test: Data export generates valid CSV
✅ Smoke Test: Admin dashboard loads

All 4 smoke tests passed in 8.2 seconds
```

**Poor output**:

```
test_auth_flow ... ok
test_upload ... ok
test_export ... ok
test_dashboard ... ok

Ran 4 tests in 8.2s
```

---

## Automation

### GitHub Actions Example

```yaml
# .github/workflows/smoke-tests.yml
name: Smoke Tests

on: [push, pull_request]

jobs:
  smoke:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup environment
        run: |
          npm install  # or pip install, etc.
          
      - name: Start services
        run: |
          docker-compose up -d postgres redis
          
      - name: Run smoke tests
        run: |
          npm run smoke-test
        timeout-minutes: 2  # Fail if takes > 2 minutes
        
      - name: Cleanup
        if: always()
        run: docker-compose down
```

### Pre-commit Hook

```bash
# .git/hooks/pre-push
#!/bin/bash
# Run smoke tests before pushing

echo "Running smoke tests..."
npm run smoke-test

if [ $? -ne 0 ]; then
    echo "❌ Smoke tests failed. Fix before pushing."
    exit 1
fi

echo "✅ Smoke tests passed"
exit 0
```

---

## Troubleshooting

### Smoke Tests Failing

1. **Run full test suite**: `npm test` or equivalent
   - If full suite passes, smoke tests may be too strict
   - If full suite fails, fix underlying issues first

2. **Check environment**: Smoke tests often fail due to environment issues
   - Database not running
   - Wrong environment variables
   - Missing dependencies
   - Port conflicts

3. **Isolate failing test**: Run one smoke test at a time
   - `pytest tests/smoke/test_auth.py -v`
   - Check test output for specific error

4. **Review recent changes**: Did code change break critical path?
   - Use `git diff` to review changes
   - Temporarily revert suspect changes

### Smoke Tests Too Slow

1. **Profile execution**: Identify slow tests
   - `pytest tests/smoke/ --durations=10`
   - Focus optimization on slowest tests

2. **Optimize setup/teardown**: Reuse fixtures where possible
3. **Mock external services**: Don't call real APIs in smoke tests
4. **Use faster database**: SQLite in-memory for smoke tests
5. **Parallelize**: Run independent tests concurrently

---

## Best Practices

### Do

✅ Test critical paths only
✅ Keep tests fast (< 30s total)
✅ Make tests independent
✅ Use clear test names
✅ Run before every commit
✅ Run in CI/CD pipeline
✅ Update when critical paths change

### Don't

❌ Test every edge case (that's for full suite)
❌ Make tests dependent on each other
❌ Use production databases or services
❌ Skip smoke tests ("I'll fix it later")
❌ Let smoke tests get slow
❌ Ignore failing smoke tests
❌ Test non-critical features

---

**Document Version**: 1.0
**Last Updated**: 2025-12-17
**Related**: [VERIFICATION_CHECKLIST.md](./VERIFICATION_CHECKLIST.md), [REVIEW_CHECKLIST.md](./REVIEW_CHECKLIST.md), [../TESTING.md](../TESTING.md)
