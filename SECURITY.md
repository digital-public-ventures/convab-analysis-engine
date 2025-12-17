# Security Policy

## Supported Versions

This section indicates which versions of cfpb-exploration are currently receiving security updates.

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |

**Note**: Update this table as you release versioned releases (e.g., 1.x, 2.x).

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please follow these steps:

### Do NOT:

- Open a public GitHub issue for security vulnerabilities
- Disclose the vulnerability publicly before it has been addressed
- Test the vulnerability on production systems or other users' data

### Do:

1. **Email security details** to jim@digitalpublic.ventures with subject line "SECURITY: [Brief Description]"
2. **Include details**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Affected versions (if known)
   - Your suggested fix (if any)
3. **Wait for confirmation** - We aim to respond within 48 hours

### What to Expect

- **Initial Response**: Within 48 hours acknowledging receipt
- **Status Update**: Within 5 business days with preliminary assessment
- **Resolution Timeline**: Depends on severity and complexity
  - Critical vulnerabilities: 7-14 days
  - High severity: 30 days
  - Medium/Low severity: 60-90 days

### Disclosure Policy

- We request that you give us reasonable time to fix the vulnerability before public disclosure
- We will credit you for the discovery (unless you prefer to remain anonymous)
- Once a fix is available, we will:
  1. Release a patch
  2. Update CHANGELOG.md with security advisory
  3. Publish a security advisory on GitHub
  4. Credit the reporter (if desired)

### Security Update Notifications

Security updates will be announced via:

- GitHub Security Advisories
- Release notes in CHANGELOG.md
- Git tags for security patches

Subscribe to repository releases to stay informed.

## Security Best Practices

### For Users

- Always use the latest version of cfpb-exploration
- Keep dependencies up to date
- Review and follow security recommendations in documentation
- Use strong authentication and authorization practices
- Protect sensitive configuration files (e.g., `.env`)
- Regular security audits of your deployment

### For Contributors

- Never commit secrets (API keys, passwords, tokens) to the repository
- Use `.env` files for local secrets (excluded by `.gitignore`)
- Run security checks before submitting PRs
- Follow secure coding practices for your language/framework
- Report any security concerns during code review

### For Maintainers

- Review dependencies regularly for known vulnerabilities
- Enable Dependabot or similar automated security scanning
- Require code review for all changes
- Use branch protection on `main`
- Follow principle of least privilege for access controls
- Regularly audit third-party integrations

## Known Security Considerations

<!-- Update this section with any known security considerations, limitations, or recommendations specific to your project -->

- **Environment Variables**: Ensure `.env` files are never committed. Use `.env.example` as a template
- **Dependencies**: Run dependency audits regularly (e.g., `npm audit`, `pip-audit`, etc.)
- **Authentication**: If your project includes authentication, document security requirements
- **Data Storage**: If storing sensitive data, document encryption and access control requirements

## Security Tooling

Consider integrating these tools into your project:

- **Dependency Scanning**: Dependabot, Snyk, or similar
- **Static Analysis**: Language-specific security linters
- **Secrets Detection**: git-secrets, TruffleHog, or similar
- **CI/CD Security**: GitHub Security scanning, CodeQL

## Contact

For security concerns: jim@digitalpublic.ventures

For general inquiries: See [CONTRIBUTING.md](CONTRIBUTING.md)

---

Thank you for helping keep cfpb-exploration secure!
