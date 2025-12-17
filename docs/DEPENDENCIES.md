# Dependency Management Guide

**Purpose**: Define how to manage dependencies safely, securely, and maintainably throughout the project lifecycle.

**Scope**: Covers selection, installation, updates, security scanning, and removal of project dependencies.

---

## Table of Contents

- [Philosophy](#philosophy)
- [Selection Criteria](#selection-criteria)
- [Installation](#installation)
- [Version Pinning](#version-pinning)
- [Security](#security)
- [Updates](#updates)
- [Removal](#removal)
- [Language-Specific Guides](#language-specific-guides)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

---

## Philosophy

### Core Principles

1. **Minimize dependencies**: Fewer dependencies = less attack surface, easier maintenance
2. **Justify additions**: Each dependency must earn its place
3. **Pin versions**: Reproducible builds require deterministic dependencies
4. **Keep current**: Outdated dependencies accumulate security debt
5. **License awareness**: Dependencies must have compatible licenses
6. **Security first**: Vulnerable dependencies must be addressed immediately

### The Dependency Decision Tree

```
Do we need this feature?
  ├─ No → Don't add dependency
  └─ Yes
      ├─ Can we implement it simply ourselves?
      │   ├─ Yes (< 100 lines, no complex edge cases) → Implement
      │   └─ No → Continue
      ├─ Does stdlib provide this?
      │   ├─ Yes → Use stdlib
      │   └─ No → Continue
      ├─ Is there a well-maintained dependency?
      │   ├─ Yes → Evaluate (see Selection Criteria)
      │   └─ No → Implement or reconsider need
      └─ Add dependency with justification
```

---

## Selection Criteria

### Before Adding Any Dependency

Evaluate against these criteria:

#### 1. Necessity (Required)

- [ ] **Clear need**: Solves actual problem, not speculative
- [ ] **Significant value**: Saves substantial development time
- [ ] **Not easily implemented**: Would take > 100 lines or has complex edge cases
- [ ] **Not in stdlib**: Standard library doesn't provide this

#### 2. Quality (Required)

- [ ] **Well-maintained**: Recent commits (< 6 months)
- [ ] **Stable**: Version >= 1.0 or widely used pre-1.0
- [ ] **Documented**: Clear README, API docs, examples
- [ ] **Tested**: Has test suite with good coverage
- [ ] **Popular**: Reasonable download count/stars (not cargo-culting, but signal)

#### 3. Security (Required)

- [ ] **No known vulnerabilities**: Check CVE databases
- [ ] **Active security response**: Security issues addressed promptly
- [ ] **Minimal attack surface**: Doesn't do more than needed
- [ ] **Trusted source**: Official registry (npm, PyPI, crates.io, etc.)
- [ ] **Reasonable transitive deps**: Not pulling in 100+ dependencies

#### 4. License (Required)

- [ ] **Compatible license**: Check against project license
- [ ] **Clear licensing**: LICENSE file present and unambiguous
- [ ] **No copyleft conflicts**: GPL dependencies only if project is GPL

**License Compatibility Quick Reference**:

| Project License | Compatible Dependency Licenses                      | Incompatible       |
| --------------- | --------------------------------------------------- | ------------------ |
| MIT             | MIT, Apache 2.0, BSD, ISC, Unlicense                | GPL (unless tool-only) |
| Apache 2.0      | Apache 2.0, MIT, BSD, ISC                           | GPL                |
| GPL             | GPL, LGPL, MIT, Apache 2.0, BSD                     | Proprietary        |
| Proprietary     | MIT, Apache 2.0, BSD, ISC (check contract terms)    | GPL, LGPL          |

#### 5. Maintenance (High Priority)

- [ ] **Single purpose**: Library does one thing well
- [ ] **Stable API**: Not frequently breaking changes
- [ ] **Good governance**: Clear maintainer structure
- [ ] **Community**: Active community for support
- [ ] **Funding**: Sustainable development model (preferred, not required)

#### 6. Technical Fit (High Priority)

- [ ] **Language/runtime compatibility**: Works with our version
- [ ] **Platform support**: Runs on target platforms (Linux, macOS, Windows, etc.)
- [ ] **Size reasonable**: Not megabytes for trivial functionality
- [ ] **Performance acceptable**: No known performance issues
- [ ] **No conflicts**: Doesn't conflict with existing dependencies

### Red Flags

**Do NOT add dependency if**:

- 🚩 No commits in > 1 year (unless extremely stable and mature)
- 🚩 Known unpatched vulnerabilities
- 🚩 Unclear or incompatible license
- 🚩 Pulls in > 50 transitive dependencies
- 🚩 < 0.1.0 version (too immature)
- 🚩 No documentation
- 🚩 Maintainer explicitly abandoned project

---

## Installation

### Process

1. **Propose**: Create GitHub issue describing need and proposed dependency
2. **Evaluate**: Team reviews against selection criteria
3. **Approve**: Get sign-off (PR review for small projects, formal for large)
4. **Install**: Add to dependency file with specific version
5. **Document**: Note in PR why dependency added
6. **Commit lockfile**: Ensure lockfile committed with exact versions

### Language-Specific Commands

See [Language-Specific Guides](#language-specific-guides) for detailed instructions.

**Quick reference**:

```bash
# Python
pip install package-name==1.2.3
# or
poetry add package-name@1.2.3

# Node.js
npm install package-name@1.2.3 --save-exact
# or
yarn add package-name@1.2.3

# Go
go get package-name@v1.2.3

# Rust
cargo add package-name@1.2.3
```

### Documentation Requirements

When adding dependency, document in PR:

```markdown
## Dependency Added: `library-name`

**Purpose**: [Why we need this]

**Alternatives Considered**:

1. Implement ourselves - Rejected because [reason]
2. Use stdlib - Doesn't provide [needed functionality]
3. Library X - Rejected because [reason]

**Selection Justification**:

- Maintained: Last commit 2 days ago
- Popular: 10M downloads/month
- License: MIT (compatible)
- No vulnerabilities: Passed security scan
- Size: 50KB minified

**Version**: 1.2.3 (latest stable)

**Usage**: Will be used for [specific purpose]
```

---

## Version Pinning

### Strategy

**Use exact version pinning for production dependencies:**

```python
# ✅ GOOD - Exact version
requests==2.31.0

# ❌ BAD - Version ranges allow unexpected updates
requests>=2.0.0
requests~=2.31
requests
```

**Exceptions**:

- **Development tools**: Can use looser pinning (linters, formatters)
- **Internal libraries**: May use semantic version ranges if controlled

### Lockfiles

**Always commit lockfiles:**

- Python: `poetry.lock`, `Pipfile.lock`, `requirements-lock.txt`
- Node.js: `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`
- Ruby: `Gemfile.lock`
- Go: `go.sum`
- Rust: `Cargo.lock`

**Why**: Lockfiles ensure identical dependency versions across:

- Development machines
- CI/CD pipelines
- Production deployments
- Team members

### Updating Lockfiles

```bash
# Python (poetry)
poetry update

# Node.js
npm update
yarn upgrade

# Go
go get -u ./...

# Rust
cargo update
```

**Best practice**: Update lockfiles regularly (weekly or biweekly), not randomly when convenient.

---

## Security

### Vulnerability Scanning

#### Automated Scanning

**Set up automated security scanning:**

```yaml
# .github/workflows/security.yml
name: Security Scan

on:
  schedule:
    - cron: '0 0 * * 1'  # Weekly on Monday
  push:
    branches: [main]
  pull_request:

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run security scan
        run: |
          # Language-specific security scanner
          npm audit                    # Node.js
          # or
          pip install safety && safety check  # Python
          # or
          cargo audit                  # Rust
```

#### Manual Scanning

Run before each release:

```bash
# Python
pip install safety
safety check

# Node.js
npm audit
npm audit fix  # Auto-fix if possible

# Ruby
bundle audit

# Go
go list -json -m all | nancy sleuth

# Rust
cargo audit
```

### Vulnerability Response Process

**When vulnerability discovered**:

1. **Assess severity**: Check CVE score and exploitability
2. **Determine impact**: Are we affected? (Check usage)
3. **Prioritize**:
   - **Critical/High**: Fix within 24 hours
   - **Medium**: Fix within 1 week
   - **Low**: Fix in next release cycle
4. **Fix**:
   - Update to patched version if available
   - Apply workaround if no patch
   - Remove dependency if unmaintained
5. **Verify**: Re-scan after fix
6. **Document**: Note in CHANGELOG

### Security Policy

See [SECURITY.md](../SECURITY.md) for reporting vulnerabilities in our code.

**For dependency vulnerabilities**:

- Open GitHub security advisory (private)
- Assign to security team
- Track with `security` label
- Report to dependency maintainers if appropriate

---

## Updates

### Update Strategy

**Regular Updates**: Scheduled dependency updates prevent accumulation of technical debt.

**Recommended Schedule**:

- **Security patches**: Immediately (within 24 hours)
- **Minor versions**: Weekly or biweekly
- **Major versions**: Quarterly or as needed
- **Full audit**: Quarterly

### Update Process

#### 1. Check for Updates

```bash
# Python (poetry)
poetry show --outdated

# Node.js
npm outdated
npx npm-check-updates

# Ruby
bundle outdated

# Go
go list -u -m all

# Rust
cargo outdated
```

#### 2. Review Changes

For each update:

- Read CHANGELOG
- Check for breaking changes
- Review security advisories
- Assess compatibility

#### 3. Update Incrementally

**Don't update all at once** - update one (or small batch) at a time:

```bash
# Python
poetry add package-name@^2.0.0

# Node.js
npm install package-name@latest

# Update all (use caution)
poetry update
npm update
```

#### 4. Test Thoroughly

After updating:

- [ ] Run full test suite
- [ ] Run integration tests
- [ ] Test critical user flows manually
- [ ] Check for deprecation warnings
- [ ] Verify performance (if perf-sensitive)

#### 5. Document and Commit

```bash
git add poetry.lock  # or package-lock.json, etc.
git commit -m "chore(deps): Update package-name from 1.2.3 to 1.3.0

- Reviewed CHANGELOG: No breaking changes
- Tested: All tests pass
- Security: Fixes CVE-2023-XXXXX"
```

### Automated Update Tools

**Dependabot** (GitHub) - Automated dependency PRs:

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"  # or "pip", "cargo", etc.
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    reviewers:
      - "team-leads"
    labels:
      - "dependencies"
```

**Renovate** (Alternative to Dependabot):

- More configurable
- Better for monorepos
- Supports more ecosystems

**Using automated tools**:

- ✅ Review each PR individually
- ✅ Run tests before merging
- ❌ Don't auto-merge without review (even minor updates)

---

## Removal

### When to Remove

Remove dependency if:

- ✅ No longer needed (feature removed)
- ✅ Functionality reimplemented
- ✅ Replaced by better alternative
- ✅ Unmaintained and security risk
- ✅ License incompatibility discovered
- ✅ Causing ongoing issues

### Removal Process

1. **Verify not used**: Search codebase for imports/uses
   ```bash
   # Example searches
   git grep "import package-name"
   git grep "from package-name"
   git grep "require('package-name')"
   ```

2. **Remove imports**: Delete all code using dependency

3. **Uninstall**:
   ```bash
   # Python
   poetry remove package-name
   pip uninstall package-name
   
   # Node.js
   npm uninstall package-name
   yarn remove package-name
   
   # Go
   go get package-name@none
   
   # Rust
   cargo remove package-name
   ```

4. **Test**: Ensure no breakage

5. **Document**: Note in CHANGELOG and PR

---

## Language-Specific Guides

### Python

#### Package Manager: pip + poetry

**Installation**:

```bash
# Add dependency
poetry add requests==2.31.0

# Add dev dependency
poetry add --group dev pytest==7.4.0

# Install from lockfile
poetry install
```

**Dependency Files**:

- `pyproject.toml`: Dependency declarations
- `poetry.lock`: Exact versions (commit this)
- `requirements.txt`: Alternative for pip (if not using poetry)

**Security Scanning**:

```bash
pip install safety
safety check
```

**Update Strategy**:

```bash
# Check outdated
poetry show --outdated

# Update specific package
poetry update requests

# Update all
poetry update
```

**Best Practices**:

- Use `poetry` for dependency management (modern standard)
- Pin exact versions in `pyproject.toml`
- Use virtual environments
- Separate dev dependencies: `poetry add --group dev`
- Type checking: Include type stubs (`types-requests`, etc.)

---

### Node.js/JavaScript/TypeScript

#### Package Manager: npm (or yarn, pnpm)

**Installation**:

```bash
# Add dependency
npm install express@4.18.2 --save-exact

# Add dev dependency
npm install --save-dev jest@29.5.0 --save-exact

# Install from lockfile
npm ci  # Preferred for CI/CD
```

**Dependency Files**:

- `package.json`: Dependency declarations
- `package-lock.json`: Exact versions (commit this)
- `yarn.lock` or `pnpm-lock.yaml`: Alternative lockfiles

**Security Scanning**:

```bash
npm audit
npm audit fix  # Auto-fix if safe
npm audit fix --force  # Force fix (may break things)
```

**Update Strategy**:

```bash
# Check outdated
npm outdated

# Update specific package
npm update express

# Update all (be cautious)
npm update

# Interactive update (with npm-check-updates)
npx npm-check-updates -i
```

**Best Practices**:

- Use `--save-exact` to pin versions
- Use `npm ci` in CI/CD (faster, stricter)
- Audit before each release: `npm audit`
- Consider using `pnpm` (faster, more efficient)
- TypeScript: Include `@types/*` packages

---

### Go

#### Package Manager: Go modules

**Installation**:

```bash
# Add dependency
go get github.com/gin-gonic/gin@v1.9.1

# Install dependencies
go mod download

# Tidy dependencies
go mod tidy
```

**Dependency Files**:

- `go.mod`: Dependency declarations
- `go.sum`: Checksums (commit this)

**Security Scanning**:

```bash
# Install nancy
go install github.com/sonatype-nexus-community/nancy@latest

# Scan
go list -json -m all | nancy sleuth
```

**Update Strategy**:

```bash
# Check outdated
go list -u -m all

# Update specific package
go get github.com/gin-gonic/gin@v1.10.0

# Update all
go get -u ./...

# Update to specific version
go get github.com/gin-gonic/gin@v1.10.0
```

**Best Practices**:

- Always run `go mod tidy` after changes
- Use semantic import versioning for major versions
- Vendor dependencies if building reproducible artifacts: `go mod vendor`
- Pin to specific versions in `go.mod`

---

### Rust

#### Package Manager: Cargo

**Installation**:

```bash
# Add dependency
cargo add serde@1.0.188

# Add dev dependency
cargo add --dev proptest

# Install dependencies
cargo build
```

**Dependency Files**:

- `Cargo.toml`: Dependency declarations
- `Cargo.lock`: Exact versions (commit for binaries, not libraries)

**Security Scanning**:

```bash
cargo install cargo-audit
cargo audit
```

**Update Strategy**:

```bash
# Check outdated
cargo outdated

# Update specific package
cargo update serde

# Update all
cargo update
```

**Best Practices**:

- Commit `Cargo.lock` for binaries/applications
- Don't commit `Cargo.lock` for libraries (per convention)
- Use features to minimize dependencies: `serde = { version = "1.0", default-features = false }`
- Audit regularly: `cargo audit`

---

## CI/CD Integration

### Automated Checks

Add to CI pipeline:

```yaml
# GitHub Actions example
name: Dependencies

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup
        run: |
          # Language-specific setup
          
      - name: Security Scan
        run: |
          npm audit  # or equivalent for your language
          
      - name: Check for outdated deps
        run: |
          npm outdated  # Warning only, don't fail build
        continue-on-error: true

  licenses:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Check Licenses
        run: |
          # Use license checker tool
          npx license-checker --summary
```

### Pre-commit Hooks

Add dependency checks to pre-commit:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: security-scan
        name: Security Scan
        entry: npm audit
        language: system
        pass_filenames: false
        always_run: true
```

### Deployment Verification

Before deploying:

- [ ] No critical vulnerabilities
- [ ] Lockfile committed
- [ ] All tests pass with current dependencies
- [ ] No deprecated dependency warnings

---

## Troubleshooting

### Common Issues

#### Dependency Conflict

**Problem**: Two packages require incompatible versions of the same dependency

**Solution**:

1. Check if one can be updated
2. Check if you can use different versions in isolation (language-dependent)
3. Choose alternative dependency
4. Implement functionality yourself

#### Security Vulnerability with No Fix

**Problem**: CVE in dependency, no patched version available

**Options**:

1. **Wait**: If low severity, wait for patch
2. **Workaround**: Don't use vulnerable functionality
3. **Fork**: Patch yourself (last resort)
4. **Replace**: Switch to alternative dependency
5. **Remove**: Remove feature using dependency

#### Transitive Dependency Issue

**Problem**: Dependency pulls in problematic transitive dependency

**Solution**:

```bash
# Python (poetry) - Override transitive dependency
[tool.poetry.dependencies]
# Force specific version
vulnerable-package = "==1.2.3"

# Node.js - Use overrides in package.json
{
  "overrides": {
    "vulnerable-package": "1.2.3"
  }
}

# Or use resolutions (yarn)
{
  "resolutions": {
    "vulnerable-package": "1.2.3"
  }
}
```

#### Dependency Not Found

**Problem**: Package doesn't exist or version not found

**Check**:

1. Typo in package name?
2. Version exists? (Check registry)
3. Package removed/renamed?
4. Private registry credentials configured?

#### Build Fails After Update

**Problem**: Updated dependency breaks build

**Steps**:

1. Read CHANGELOG for breaking changes
2. Check deprecation warnings
3. Review migration guide
4. If no guide, check GitHub issues
5. Last resort: Revert update, open issue

---

## Best Practices Summary

### Do

✅ Evaluate dependencies thoroughly before adding
✅ Pin exact versions for production
✅ Commit lockfiles
✅ Run security scans regularly
✅ Update dependencies on schedule
✅ Test after updates
✅ Document why dependencies added
✅ Remove unused dependencies
✅ Keep licenses compatible
✅ Monitor for vulnerabilities

### Don't

❌ Add dependencies without justification
❌ Use version ranges in production
❌ Skip security scans
❌ Let dependencies go years without updates
❌ Auto-merge dependency PRs without review
❌ Ignore vulnerability warnings
❌ Commit dependencies to git (except Go vendor, special cases)
❌ Use pre-1.0 dependencies in production without careful evaluation
❌ Forget to test after updates

---

## Related Documentation

- [SECURITY.md](../SECURITY.md): Security policy and vulnerability reporting
- [CONTRIBUTING.md](../CONTRIBUTING.md): General contribution guidelines
- [TESTING.md](TESTING.md): Testing standards
- [Evaluation Framework](evaluation/README.md): Code review standards

---

**Document Version**: 1.0
**Last Updated**: 2025-12-17
**Maintained By**: Development Team
**Feedback**: Open GitHub issue with "dependencies:" prefix
