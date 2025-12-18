# Agent Safety Guide

**Purpose**: Safety guardrails, prohibited operations, and security best practices for agent-assisted development.

**Last Updated**: 2025-12-17

---

## Table of Contents

- [Core Safety Principles](#core-safety-principles)
- [Prohibited Operations](#prohibited-operations)
- [Secret and Credential Handling](#secret-and-credential-handling)
- [Data Loss Prevention](#data-loss-prevention)
- [Safe Defaults](#safe-defaults)
- [Recovery Procedures](#recovery-procedures)
- [Security Checklist](#security-checklist)

---

## Core Safety Principles

### 1. **Explicit Confirmation for Destructive Operations**

**Rule**: Never perform irreversible operations without explicit confirmation or safety mechanisms.

**Examples**:

- `rm -rf` commands
- `DROP DATABASE` statements
- Force pushing to shared branches (`git push --force`)
- Deleting production resources
- Modifying live data

**Safe Approach**:

```bash
# ❌ DANGEROUS
rm -rf node_modules/

# ✅ SAFE: Check first, then delete
ls -la node_modules/ && echo "Ready to delete" && rm -rf node_modules/

# ✅ SAFER: Move to trash instead
mv node_modules/ ~/.trash/node_modules_$(date +%s)

# ✅ SAFEST: Use project scripts that include checks
make clean
```

### 2. **Prefer Reversible Operations**

**Rule**: Choose operations that can be undone.

**Examples**:

- Git commits > Direct file deletion
- Feature flags > Code deletion
- Database migrations > Direct schema changes
- Moving files > Deleting files

### 3. **Verify Before Execute**

**Rule**: Check state before making changes.

**Checklist**:

- [ ] Is this the correct branch?
- [ ] Is this the correct environment (dev/staging/prod)?
- [ ] Are there uncommitted changes?
- [ ] Have I backed up important data?
- [ ] Do I have rollback capability?

### 4. **Minimize Blast Radius**

**Rule**: Limit the scope of potentially dangerous operations.

**Strategies**:

- Test in feature branches first
- Use staging environments
- Implement gradual rollouts
- Enable kill switches
- Monitor during deployment

---

## Prohibited Operations

### 🚫 **Never Do These Without Human Approval**

#### 1. Force Push to Shared Branches

```bash
# ❌ PROHIBITED
git push --force origin main
git push --force origin develop

# ✅ ALLOWED (if necessary and approved)
# Force push to personal feature branch only
git push --force origin feature/my-branch
```

**Why**: Overwrites history, can lose teammates' work

**Alternative**:

- Revert commits instead of rewriting history
- Create new commits to fix issues
- Use `git push --force-with-lease` with extreme caution

#### 2. Delete Production Data

```bash
# ❌ PROHIBITED
DELETE FROM users;
DROP TABLE orders;
TRUNCATE payments;
```

**Why**: Irreversible data loss

**Alternative**:

- Archive to backup table first
- Use soft deletes (is_deleted flag)
- Test in staging environment
- Require explicit human approval

#### 3. Remove Critical Files

```bash
# ❌ PROHIBITED
rm -rf .git/
rm -rf node_modules/ package.json
rm -rf src/
```

**Why**: Can break repository or build

**Alternative**:

- Use `git clean -fdx` for git-ignored files
- Use package manager commands (npm clean-install)
- Use project cleanup scripts

#### 4. Modify Production Configuration Directly

```bash
# ❌ PROHIBITED
vim /etc/nginx/nginx.conf  # on production
echo "DEBUG=true" >> .env.production
```

**Why**: Can cause outages, expose secrets

**Alternative**:

- Use infrastructure-as-code (Terraform, Ansible)
- Deploy configuration changes through CI/CD
- Test configuration in staging first

#### 5. Commit Secrets

```bash
# ❌ PROHIBITED
git add .env
git add secrets.json
git add config/credentials.yml

# ❌ PROHIBITED in code
API_KEY = "sk_live_abc123"
PASSWORD = "hunter2"
```

**Why**: Exposed in git history forever

**Prevention**:

- Use `.gitignore` for secret files
- Use environment variables
- Use secret management tools (AWS Secrets Manager, Vault)
- Scan commits with pre-commit hooks

#### 6. Run Unvetted Scripts from Internet

```bash
# ❌ PROHIBITED
curl https://random-site.com/script.sh | sh
wget -O- https://unknown.com/install | bash
```

**Why**: Can execute malicious code

**Alternative**:

- Download script first
- Review contents
- Use official sources only
- Verify checksums/signatures

#### 7. Disable Security Features

```bash
# ❌ PROHIBITED
git config --global http.sslVerify false
pip install --trusted-host
npm audit --audit-level=none

# ❌ PROHIBITED in code
verify=False  # in requests.get()
SSL_VERIFY_NONE
```

**Why**: Opens security vulnerabilities

**Alternative**:

- Fix certificate issues properly
- Address audit warnings
- Use proper SSL certificates

---

## Secret and Credential Handling

### Never Commit These

**Files to Exclude**:

- `.env` (environment variables)
- `secrets.json`, `credentials.yml`
- SSH private keys (`id_rsa`, `*.pem`)
- API keys and tokens
- Database passwords
- SSL certificates (private keys)
- Cloud provider credentials (`~/.aws/credentials`)

**Patterns to Avoid**:

```python
# ❌ NEVER
API_KEY = "sk_live_1234567890abcdef"
PASSWORD = "my_password"
database_url = "postgres://user:pass@host/db"

# ✅ CORRECT
import os
API_KEY = os.environ["API_KEY"]
PASSWORD = os.environ["PASSWORD"]
database_url = os.environ["DATABASE_URL"]
```

### Proper Secret Management

**Development**:

```bash
# 1. Create .env.example (template, no secrets)
cat > .env.example << EOF
API_KEY=your_api_key_here
DATABASE_URL=postgres://localhost/mydb
REDIS_URL=redis://localhost:6379
EOF

# 2. Add .env to .gitignore
echo ".env" >> .gitignore

# 3. Copy template for local use
cp .env.example .env

# 4. Fill in real secrets (never commit)
vim .env
```

**Production**:

- Use secret management service (AWS Secrets Manager, HashiCorp Vault)
- Inject secrets at runtime via environment variables
- Rotate secrets regularly
- Audit secret access

### Secret Scanning

**Pre-commit Hook**:

```bash
# .git/hooks/pre-commit
#!/bin/bash
# Scan for potential secrets before committing

if git diff --cached | grep -iE "password|api_key|secret|token"; then
    echo "⚠️  Potential secret detected!"
    echo "Review staged changes carefully."
    exit 1
fi
```

**Tools**:

- `git-secrets` (AWS)
- `gitleaks`
- `trufflehog`
- GitHub secret scanning

---

## Data Loss Prevention

### Backup Before Destructive Operations

**Always Create Backups For**:

- Database migrations
- Large refactoring
- File deletions
- Configuration changes

**Backup Strategies**:

```bash
# 1. Database backup
pg_dump mydb > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. File backup
cp -r important_dir/ important_dir.backup.$(date +%Y%m%d)

# 3. Git stash (for uncommitted work)
git stash save "backup before major refactor"

# 4. Create backup branch
git checkout -b backup/before-major-change
git checkout main
```

### Use Git for Everything

**Benefits**:

- Every change is tracked
- Easy rollback (`git revert`, `git reset`)
- History preserved
- Can recover deleted files

**Best Practices**:

```bash
# Commit frequently
git add -A
git commit -m "WIP: checkpoint before risky change"

# Create feature branches for experiments
git checkout -b experiment/new-approach

# Tag important milestones
git tag -a v1.0.0 -m "Release 1.0.0"
```

### Recovery Options

**If You Accidentally Delete Something**:

```bash
# 1. Check if file is staged/committed
git status
git log -- deleted_file.py

# 2. Restore from git
git restore deleted_file.py
git checkout HEAD~1 -- deleted_file.py

# 3. Check reflog for lost commits
git reflog
git checkout <commit-hash>

# 4. Check system trash/recycle bin
# macOS: ~/.Trash
# Linux: ~/.local/share/Trash

# 5. Use file recovery tools (last resort)
# extundelete, testdisk, photorec
```

**If You Force-Pushed and Lost Commits**:

```bash
# 1. Check reflog (local copy)
git reflog

# 2. Restore lost commit
git cherry-pick <lost-commit-hash>

# 3. Ask teammates to push their copy
# (if they haven't pulled the force-push yet)
```

---

## Safe Defaults

### File Operations

```bash
# ✅ Use -i (interactive) for destructive operations
rm -i important_file.txt
mv -i source.txt dest.txt
cp -i original.txt backup.txt

# ✅ Use -n (no-clobber) to prevent overwriting
cp -n source.txt dest.txt  # Won't overwrite if dest exists

# ✅ Use trash instead of rm
trash file.txt  # Can recover from trash
```

### Git Operations

```bash
# ✅ Use --dry-run to preview
git clean -fdx --dry-run

# ✅ Use --force-with-lease instead of --force
git push --force-with-lease origin feature-branch

# ✅ Check what you're committing
git diff --staged
git status

# ✅ Use revert instead of reset for shared branches
git revert <commit-hash>
```

### Database Operations

```sql
-- ✅ Always use transactions
BEGIN;
DELETE FROM old_data WHERE created_at < '2020-01-01';
-- Review count: SELECT COUNT(*) FROM old_data WHERE created_at < '2020-01-01';
COMMIT;  -- or ROLLBACK if wrong

-- ✅ Test on copy first
CREATE TABLE users_backup AS SELECT * FROM users;
-- Test changes on users_backup
-- If good, apply to users

-- ✅ Use soft deletes
ALTER TABLE users ADD COLUMN deleted_at TIMESTAMP;
UPDATE users SET deleted_at = NOW() WHERE id = 123;
-- Instead of: DELETE FROM users WHERE id = 123;
```

### Deployment Operations

```bash
# ✅ Deploy to staging first
make deploy-staging
# Test thoroughly
make deploy-production

# ✅ Use blue-green deployments
# Keep old version running until new version validated

# ✅ Enable feature flags
# Can disable problematic features without redeployment

# ✅ Monitor during rollout
# Watch error rates, performance metrics

# ✅ Have rollback plan ready
make rollback-production
```

---

## Recovery Procedures

### Emergency Rollback

**Web Application**:

```bash
# 1. Identify last good commit
git log --oneline

# 2. Revert to last good version
git revert <bad-commit-hash>

# 3. Deploy immediately
make deploy-production

# 4. Verify rollback
curl https://api.example.com/health
```

**Database Migration Gone Wrong**:

```sql
-- 1. Check if migration has down/rollback
-- Run rollback migration
rake db:rollback

-- 2. If no rollback exists, restore from backup
-- Stop application
psql mydb < backup_20251123.sql

-- 3. Verify data integrity
SELECT COUNT(*) FROM users;
SELECT MAX(id) FROM orders;

-- 4. Restart application
```

### Lost Work Recovery

**Uncommitted Changes**:

```bash
# Check if file is still in working directory
ls -la

# Check git status
git status

# Check if staged
git diff --staged

# Restore from index
git restore --staged file.txt
git restore file.txt
```

**Deleted Branch**:

```bash
# Find deleted branch in reflog
git reflog | grep branch-name

# Recreate branch
git checkout -b branch-name <commit-hash>
```

**Corrupted Repository**:

```bash
# 1. Clone fresh copy from remote
git clone <repo-url> repo-fresh
cd repo-fresh

# 2. Copy uncommitted work from corrupted repo
cp ../repo-old/modified-file.txt .

# 3. Verify integrity
git fsck --full
```

---

## Security Checklist

### Before Committing

- [ ] No secrets in code or config files
- [ ] `.env` and secret files in `.gitignore`
- [ ] No hardcoded passwords or API keys
- [ ] Sensitive data properly encrypted
- [ ] Debug/verbose logging disabled
- [ ] No commented-out credentials

### Before Deploying

- [ ] Dependencies scanned for vulnerabilities (`npm audit`, `pip-audit`)
- [ ] Security headers configured (CSP, HSTS, X-Frame-Options)
- [ ] Authentication and authorization working
- [ ] Input validation in place
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output escaping)
- [ ] Rate limiting configured
- [ ] HTTPS enforced
- [ ] Secrets loaded from environment/secret manager
- [ ] Error messages don't leak sensitive info

### Before Deleting

- [ ] Confirmed correct file/directory
- [ ] Backup created
- [ ] Verified not in use
- [ ] Checked for dependencies
- [ ] Git history preserved (committed first)
- [ ] Team notified if shared resource

### Before Merging

- [ ] Tests passing
- [ ] Code reviewed
- [ ] No conflicts
- [ ] Branch up-to-date with main
- [ ] CI/CD checks green
- [ ] Breaking changes documented

---

## Incident Response

### If You Accidentally Commit Secrets

**Immediate Actions**:

```bash
# 1. ROTATE THE SECRET IMMEDIATELY
# Revoke API key, change password, etc.

# 2. Remove from git history (if not yet pushed)
git reset --soft HEAD~1
git restore --staged .env
git commit -m "Your actual changes"

# 3. If already pushed, use git-filter-repo
# Install: pip install git-filter-repo
git filter-repo --invert-paths --path .env

# 4. Force push (coordinate with team!)
git push --force-with-lease

# 5. Notify team and security
# Everyone needs to re-clone or rebase
```

**If Secret Already Exposed**:

1. Rotate secret immediately
2. Review access logs for unauthorized use
3. Notify security team
4. Document in incident report
5. Implement controls to prevent recurrence

### If You Delete Important Data

**Immediate Actions**:

```bash
# 1. STOP - Don't make it worse
# Don't run more commands

# 2. Check git history
git log -- deleted_file

# 3. Restore from git
git restore deleted_file
# or
git checkout HEAD~1 -- deleted_file

# 4. If not in git, check backups
ls ~/.Trash/
ls backups/

# 5. If database, restore from backup
pg_restore -d mydb backup.sql
```

---

## Best Practices Summary

### ✅ DO

- Use version control for everything
- Commit frequently
- Test in non-production first
- Create backups before risky operations
- Use `.gitignore` for secrets
- Review diffs before committing
- Use safe defaults (`-i`, `--dry-run`)
- Ask when uncertain
- Document destructive operations
- Have rollback plans

### ❌ DON'T

- Commit secrets or credentials
- Force push to shared branches without coordination
- Delete without backup
- Modify production directly
- Disable security features
- Trust unverified scripts
- Assume you can't make mistakes
- Work in production when tired
- Skip testing
- Ignore warnings

---

## Emergency Contacts

**When to Escalate**:

- Production outage
- Security breach
- Data loss
- Secrets exposed
- Critical bug in production

**How to Escalate**:

1. Stop destructive actions
2. Document what happened
3. Notify team lead/on-call engineer
4. Follow incident response plan
5. Preserve evidence for postmortem

---

## See Also

- [Agent Operations Guide](AGENT_OPERATIONS.md)
- [Environment Setup](ENVIRONMENT.md)
- [Observability Guide](OBSERVABILITY.md)
- [Git Best Practices](https://git-scm.com/book/en/v2)
