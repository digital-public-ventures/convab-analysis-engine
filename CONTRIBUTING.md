# Contributing to cfpb-exploration

Thank you for considering contributing to cfpb-exploration! This document provides guidelines and instructions for contributing.

## Code of Conduct

This project adheres to the Contributor Covenant [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce** the problem
- **Expected behavior** vs actual behavior
- **Environment details** (OS, versions, etc.)
- **Screenshots or logs** if applicable

Use the bug report issue template when available.

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide detailed description** of the proposed functionality
- **Explain why this enhancement would be useful**
- **List any alternatives** you've considered

Use the feature request issue template when available.

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Follow the development workflow** outlined in `.github/copilot-instructions.md`
3. **Write tests** for new functionality (TDD preferred)
4. **Run quality checks** before submitting (lint, format, type check, tests)
5. **Update documentation** as needed (README, docs/, ADRs for architectural changes)
6. **Use the appropriate PR template** (feature, bugfix, chore, etc.)
7. **Keep commits atomic** and write clear commit messages
8. **Update CHANGELOG.md** if your change affects users

#### PR Guidelines

- PRs should be focused on a single concern
- Include tests demonstrating the fix or feature works
- Follow existing code style and conventions
- Keep PRs reasonably sized (large PRs are hard to review)
- Respond to review feedback promptly
- Ensure CI passes before requesting review

#### PR Templates

This repo uses multiple PR templates. Add `?template=<name>.md` to your PR URL:

- `feature.md` - New features
- `bugfix.md` - Bug fixes
- `chore.md` - Refactors, dependency updates, minor config changes
- `docs.md` - Documentation-only changes
- `hotfix.md` - Emergency fixes
- `infra.md` - Infrastructure/CI changes
- `data-service.md` - Data pipeline/ETL changes

Choose the template that best fits your changes.

## Development Workflow

### Setup

See [docs/QUICK_START.md](docs/QUICK_START.md) for detailed setup instructions.

### Branch Naming

Use descriptive branch names with prefixes:

- `feature/` - New features (e.g., `feature/add-user-auth`)
- `bugfix/` - Bug fixes (e.g., `bugfix/fix-login-redirect`)
- `chore/` - Maintenance tasks (e.g., `chore/update-dependencies`)
- `docs/` - Documentation changes (e.g., `docs/update-readme`)
- `hotfix/` - Emergency fixes (e.g., `hotfix/security-patch`)

### Commit Messages

Write clear, concise commit messages:

```
Short summary (50 chars or less)

More detailed explanation if needed. Wrap at 72 characters.
Explain the problem this commit solves and why you chose
this approach.

- Bullet points are okay
- Use present tense ("Add feature" not "Added feature")
- Reference issues and PRs liberally

Fixes #123
```

### Testing

- Write tests for new functionality
- Ensure existing tests pass
- Aim for high test coverage on critical paths
- Include integration tests for complex features

### Documentation

Update documentation when:

- Adding new features (README.md, docs/)
- Changing APIs or interfaces
- Making architectural decisions (create ADR)
- Changing setup/deployment process
- Adding dependencies or requirements

### Architecture Decision Records (ADRs)

For significant architectural decisions:

1. Create a new ADR in `ADRs/` directory
2. Use the next sequential number (e.g., `002-your-decision.md`)
3. Follow the template in `ADRs/README.md`
4. Include context, decision, consequences, and alternatives
5. Update `ADRs/README.md` index table

ADRs are immutable once accepted. To change a decision, create a new ADR that supersedes the old one.

### Notes and Planning

The `temp/notes/` directory is for work-in-progress planning and agent memory:

- Keep only active work in the root
- Archive completed work to `temp/notes/archive/YYYY-MM/`
- Extract architectural decisions to ADRs before archiving
- Update `ROADMAP.md` and `NEXT_STEPS.md` after significant changes

## Style Guide

### General

- Follow existing code style and conventions
- Use clear, descriptive names for variables, functions, and classes
- Keep functions small and focused
- Write self-documenting code, add comments for complex logic
- Avoid unnecessary complexity

### Language-Specific

Refer to `.github/copilot-instructions.md` for language-specific guidelines and quality check commands.

## Getting Help

- **Questions**: Open a GitHub Discussion or issue
- **Chat**: [Link to community chat if available]
- **Email**: jim@digitalpublic.ventures for private inquiries

## Recognition

Contributors will be recognized in:

- GitHub contributors page
- CHANGELOG.md for significant contributions
- README.md (optional contributors section)

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see [LICENSE](LICENSE)).

---

Thank you for contributing to cfpb-exploration! 🎉
