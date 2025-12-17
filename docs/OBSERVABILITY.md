# Observability Guide

**Purpose**: Guidelines for log storage, artifact organization, debugging traces, and operational monitoring in agent-assisted development.

**Last Updated**: 2025-12-17

---

## Table of Contents

- [Overview](#overview)
- [Log Management](#log-management)
- [Artifact Organization](#artifact-organization)
- [Debugging Traces](#debugging-traces)
- [Monitoring and Metrics](#monitoring-and-metrics)
- [Troubleshooting](#troubleshooting)

---

## Overview

Observability is critical for understanding system behavior, debugging issues, and maintaining operational excellence. This guide establishes conventions for where outputs go and how to organize diagnostic information.

**Core Principles**:

1. **Structured Logging**: Consistent format across all components
2. **Centralized Storage**: Predictable locations for all artifacts
3. **Retention Policies**: Keep what's useful, archive the rest
4. **Privacy First**: Never log secrets or PII
5. **Actionable Insights**: Logs should help solve problems

---

## Log Management

### Log Locations

**Development**:

```
temp/
├── output/          # General output files
│   ├── logs/        # Application logs
│   ├── reports/     # Test/coverage reports
│   └── artifacts/   # Build artifacts
├── debug/           # Debug-specific traces
│   ├── session-{id}/  # Session-specific debugging
│   └── core-dumps/    # Crash dumps
└── notes/           # Agent working memory
    └── archive/     # Historical context
```

**Production**:

- Use proper log aggregation (CloudWatch, Datadog, ELK stack)
- Rotate logs automatically
- Set appropriate retention periods
- Monitor log volume and costs

### Log Levels

Use consistent log levels across the project:

**CRITICAL/FATAL**: System unusable, requires immediate attention

```python
logger.critical("Database connection failed - cannot serve requests")
```

**ERROR**: Operation failed, but system continues

```python
logger.error("Failed to process payment for order %s", order_id)
```

**WARNING**: Something unexpected, but not necessarily wrong

```python
logger.warning("API rate limit at 80%% capacity")
```

**INFO**: Normal operations, important events

```python
logger.info("User %s logged in successfully", username)
```

**DEBUG**: Detailed diagnostic information

```python
logger.debug("Query executed in %dms: %s", duration, query)
```

**TRACE**: Very verbose, granular debugging

```python
logger.trace("Processing item %d of %d", current, total)
```

### Structured Logging

**Best Practice**: Use structured formats (JSON) over plain text

```python
# ❌ BAD: Unstructured
logger.info("User john123 logged in from 192.168.1.1 at 2025-12-17T10:30:00")

# ✅ GOOD: Structured
logger.info("User login", extra={
    "event": "user_login",
    "user_id": "john123",
    "ip_address": "192.168.1.1",
    "timestamp": "2025-12-17T10:30:00Z",
    "session_id": "abc123"
})
```

**Benefits**:

- Easy to parse and query
- Consistent across services
- Enables powerful filtering
- Machine-readable

### Log Rotation

**Configuration Example** (`logrotate.conf`):

```
temp/output/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 user group
}
```

**Manual Rotation**:

```bash
# Archive old logs
find temp/output/logs/ -name "*.log" -mtime +7 -exec gzip {} \;
mv temp/output/logs/*.gz temp/output/logs/archive/

# Clean very old logs
find temp/output/logs/archive/ -name "*.gz" -mtime +30 -delete
```

### What NOT to Log

**Never Log**:

- Passwords or password hashes
- API keys, tokens, secrets
- Credit card numbers
- Social security numbers
- Personal health information
- Private keys
- Session tokens
- Authentication cookies

**Redaction Example**:

```python
import re

def redact_sensitive(message):
    # Redact credit cards
    message = re.sub(r'\d{4}-\d{4}-\d{4}-\d{4}', '****-****-****-****', message)
    # Redact API keys
    message = re.sub(r'sk_live_\w{32}', 'sk_live_[REDACTED]', message)
    return message

logger.info(redact_sensitive(user_input))
```

---

## Artifact Organization

### Directory Structure

```
temp/
├── output/
│   ├── logs/
│   │   ├── app.log              # Current application log
│   │   ├── error.log            # Error-only log
│   │   ├── access.log           # HTTP access log
│   │   └── archive/             # Rotated logs
│   │       ├── app.log.2025-11-22.gz
│   │       └── app.log.2025-11-21.gz
│   ├── reports/
│   │   ├── coverage/            # Test coverage HTML
│   │   ├── test-results.xml     # JUnit XML
│   │   └── lighthouse/          # Performance reports
│   ├── artifacts/
│   │   ├── builds/              # Compiled binaries
│   │   ├── packages/            # Distributable packages
│   │   └── docker/              # Docker images
│   └── metrics/
│       ├── performance.json     # Benchmark results
│       └── resource-usage.csv   # CPU/memory logs
├── debug/
│   ├── session-20251123-001/   # Today's first debug session
│   │   ├── trace.log
│   │   ├── memory-profile.prof
│   │   └── request-dumps/
│   └── core-dumps/              # Crash dumps (if enabled)
└── notes/
    ├── DEBUG_issue_42.md        # Active debugging notes
    └── archive/
        └── 2025-11/
            └── DEBUG_issue_42_resolved.md
```

### Naming Conventions

**Logs**:

- `{component}.log` - Current log
- `{component}.log.{date}` - Rotated log
- `{component}-{level}.log` - Level-specific log

**Reports**:

- `{type}-{date}.{format}` - Test reports
- `coverage-{date}/` - Coverage reports
- `benchmark-{date}.json` - Performance data

**Debug Sessions**:

- `session-{date}-{number}/` - Debug session directory
- `trace-{timestamp}.log` - Trace files
- `dump-{timestamp}.{format}` - Memory/core dumps

### Cleanup Scripts

**Automated Cleanup** (`scripts/cleanup.sh`):

```bash
#!/bin/bash
# Clean up old artifacts and logs

# Remove logs older than 30 days
find temp/output/logs/archive/ -name "*.gz" -mtime +30 -delete

# Remove debug sessions older than 7 days
find temp/debug/ -type d -name "session-*" -mtime +7 -exec rm -rf {} +

# Remove old reports (keep last 10)
cd temp/output/reports/
ls -t | tail -n +11 | xargs rm -f

# Archive notes monthly (see NOTES_AND_ADR_MANAGEMENT.md)
# Manual process - review before archiving

echo "✓ Cleanup complete"
```

**Add to cron** (optional):

```bash
# Run cleanup weekly
0 2 * * 0 /path/to/project/scripts/cleanup.sh
```

---

## Debugging Traces

### Session Organization

When debugging, create a dedicated session directory:

```bash
# Create debug session
SESSION_ID="session-$(date +%Y%m%d)-001"
mkdir -p "temp/debug/$SESSION_ID"

# Set up logging
export DEBUG_SESSION="$SESSION_ID"
export DEBUG_LOG="temp/debug/$SESSION_ID/trace.log"

echo "Debug session: $SESSION_ID" > "$DEBUG_LOG"
echo "Started: $(date)" >> "$DEBUG_LOG"
```

### Trace File Contents

**Example `trace.log`**:

```
=== Debug Session: session-20251123-001 ===
Started: 2025-12-17 10:30:00
Issue: API endpoint /users/:id returning 500
Branch: main (commit abc123)
Agent: Claude Sonnet 4.5

--- Request Details ---
Method: GET
URL: /api/users/42
Headers:
  Authorization: Bearer [REDACTED]
  Content-Type: application/json

--- Response ---
Status: 500 Internal Server Error
Body: {"error": "Database connection failed"}

--- Stack Trace ---
Traceback (most recent call last):
  File "src/api/users.py", line 42, in get_user
    user = db.query(User).filter_by(id=user_id).first()
  File "src/db.py", line 15, in query
    raise ConnectionError("Database unavailable")
ConnectionError: Database unavailable

--- Investigation ---
10:31 - Checked database status: DOWN
10:32 - Verified connection string: correct
10:33 - Checked database logs: connection pool exhausted
10:35 - Root cause: connection leak in background jobs
10:40 - Fix: Added connection context managers
10:42 - Deployed fix
10:43 - Verified: endpoint now returns 200

--- Resolution ---
Issue: Connection pool exhaustion
Fix: Commit def456 - Add db connection context managers
Status: RESOLVED
```

### Debug Note Template

Create `temp/notes/DEBUG_{issue}.md` for complex debugging:

````markdown
# Debug: {Issue Title}

**Date**: 2025-12-17
**Session**: session-20251123-001
**Status**: IN_PROGRESS
**Severity**: HIGH

## Problem

[Clear description of the issue]

## Symptoms

- [Observable behavior 1]
- [Observable behavior 2]

## Reproduction Steps

1. [Step 1]
2. [Step 2]
3. [Expected vs actual result]

## Investigation

### Hypotheses

1. **Database connection issue**
   - Evidence: Connection pool metrics show exhaustion
   - Test: Restart database → Still fails
   - Conclusion: Not the database itself

2. **Connection leak in code**
   - Evidence: Connections increase over time
   - Test: Added logging, found unclosed connections
   - Conclusion: **ROOT CAUSE**

### Timeline

- 10:30 - Issue reported
- 10:31 - Started investigation
- 10:35 - Identified root cause
- 10:40 - Deployed fix
- 10:43 - Verified resolution

## Root Cause

Connection objects not properly closed in background job `sync_users()`.

## Solution

Added context manager to ensure connections are always closed:

```python
# Before (BUGGY)
def sync_users():
    conn = db.get_connection()
    users = conn.execute("SELECT * FROM users")
    # Connection never closed!

# After (FIXED)
def sync_users():
    with db.get_connection() as conn:
        users = conn.execute("SELECT * FROM users")
    # Connection automatically closed
```
````

## Prevention

- [ ] Add linter rule to catch unclosed connections
- [ ] Add connection pool monitoring alerts
- [ ] Document connection management in CONTRIBUTING.md

## Related

- Commit: def456
- PR: #123
- Issue: #42

## Archive

When resolved, move to `temp/notes/archive/2025-11/DEBUG_issue_resolved.md`

````

---

## Monitoring and Metrics

### Application Metrics

**Key Metrics to Track**:

1. **Performance**:
   - Request latency (p50, p95, p99)
   - Throughput (requests/second)
   - Error rate (%)

2. **Resources**:
   - CPU usage (%)
   - Memory usage (MB)
   - Disk I/O (MB/s)
   - Network I/O (MB/s)

3. **Business**:
   - Active users
   - Conversion rate
   - Transaction volume

**Instrumentation Example** (Python):
```python
import time
from prometheus_client import Counter, Histogram

request_count = Counter('http_requests_total', 'Total HTTP requests')
request_duration = Histogram('http_request_duration_seconds', 'HTTP request latency')

def handle_request():
    request_count.inc()
    start = time.time()
    try:
        response = process_request()
        return response
    finally:
        request_duration.observe(time.time() - start)
````

### Health Checks

**Endpoint**: `/health`

```python
@app.route('/health')
def health_check():
    checks = {
        "database": check_database(),
        "cache": check_cache(),
        "queue": check_queue(),
    }

    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return jsonify({
        "status": "healthy" if all_healthy else "unhealthy",
        "checks": checks,
        "timestamp": datetime.now().isoformat()
    }), status_code

def check_database():
    try:
        db.execute("SELECT 1")
        return True
    except Exception:
        return False
```

### Alerts

**Configure alerts for**:

- Error rate > 1%
- Response time p95 > 500ms
- CPU usage > 80%
- Memory usage > 90%
- Disk space < 10%

---

## Troubleshooting

### Common Issues

#### High Memory Usage

**Diagnose**:

```bash
# Check memory usage
ps aux | grep python | sort -k4 -r | head -5

# Profile memory
python -m memory_profiler script.py

# Get heap dump
import psutil
process = psutil.Process()
print(process.memory_info())
```

**Common Causes**:

- Memory leaks (unclosed connections, circular references)
- Large data structures in memory
- Caching too much data

#### Slow Queries

**Diagnose**:

```sql
-- PostgreSQL: Find slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

**Solutions**:

- Add database indexes
- Optimize query logic
- Use connection pooling
- Cache frequent queries

#### High Error Rate

**Diagnose**:

```bash
# Check error logs
grep ERROR temp/output/logs/app.log | tail -20

# Group errors by type
grep ERROR temp/output/logs/app.log | \
  cut -d: -f3 | sort | uniq -c | sort -rn
```

**Solutions**:

- Fix bugs causing errors
- Add retry logic for transient failures
- Improve error handling
- Add circuit breakers

---

## Best Practices

### ✅ DO

- Log at appropriate levels
- Use structured logging (JSON)
- Rotate logs regularly
- Monitor key metrics
- Set up alerts
- Document debugging sessions
- Archive old logs
- Redact sensitive data

### ❌ DON'T

- Log secrets or PII
- Log everything at DEBUG level in production
- Let logs grow unbounded
- Ignore warning signs
- Debug in production without backups
- Leave debug code in production

---

## See Also

- [Agent Operations](AGENT_OPERATIONS.md)
- [Agent Safety](AGENT_SAFETY.md)
- [Environment Setup](ENVIRONMENT.md)
