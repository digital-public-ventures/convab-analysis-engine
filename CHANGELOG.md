# Changelog

All notable changes to cfpb-exploration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial project structure from agent-friendly cfpb-exploration template
- Three-tier documentation system (docs/, ADRs/, temp/notes/)
- ADR 001: Repository Structure and Organization
- GitHub PR templates (feature, bugfix, chore, docs, hotfix, infra, data-service)
- Community files (LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY)

### Changed

### Deprecated

### Removed

### Fixed

### Security

---

## How to Update This Changelog

### Categories

- **Added** - New features
- **Changed** - Changes to existing functionality
- **Deprecated** - Soon-to-be removed features
- **Removed** - Removed features
- **Fixed** - Bug fixes
- **Security** - Security vulnerability fixes

### Guidelines

- Add new entries to [Unreleased] section
- When releasing, move [Unreleased] items to a new version section
- Include links to relevant PRs or issues
- Keep entries concise but informative
- Order entries by significance (most important first)

### Example Entry

```markdown
## [1.0.0] - 2025-12-17

### Added

- User authentication with JWT tokens (#42)
- API rate limiting (#45)

### Fixed

- Memory leak in background worker (#48)

### Security

- Updated dependencies to patch CVE-2025-XXXX (#50)
```

[Unreleased]: https://github.com/jimmoffet/cfpb-exploration/compare/v1.0.0...HEAD
