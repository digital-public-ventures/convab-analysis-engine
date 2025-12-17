# Scripts

Utility scripts for project maintenance, setup, and agent operations.

---

## Overview

This directory contains shell scripts that automate common tasks and provide utilities for both humans and AI agents. These scripts follow POSIX-compliant shell scripting best practices and include safety checks.

**Design Principles**:

- **Idempotent**: Safe to run multiple times
- **Verbose**: Clear output about what's happening
- **Safe defaults**: Require explicit flags for destructive operations
- **Well-documented**: Each script includes usage information

---

## Available Scripts

### `context-dump.sh`

**Purpose**: Generate a comprehensive project context document for quickly onboarding new AI agents or developers.

**What it does**:

1. Extracts project overview from README.md
2. Generates directory structure (tree view)
3. Lists all key documentation files with descriptions
4. Shows recent git commits and file changes
5. Displays current git branch and status
6. Detects technology stack (Node.js, Python, Go, Rust, etc.)
7. Includes environment configuration details
8. Lists available scripts and automation

**Usage**:

```bash
# Generate context dump to default file (PROJECT_CONTEXT.md)
./scripts/context-dump.sh

# Generate to custom file
./scripts/context-dump.sh CUSTOM_CONTEXT.md

# Generate and view immediately
./scripts/context-dump.sh && cat PROJECT_CONTEXT.md
```

**Output**: Markdown file with comprehensive project information

**When to use**:

- ✅ Starting a new agent session in an unfamiliar project
- ✅ Onboarding a new team member
- ✅ Creating documentation for project handoff
- ✅ Debugging "agent can't find X" issues
- ✅ Generating project overview for documentation

**Requirements**:

- Git repository (optional but recommended)
- Bash 4.0+
- Optional: `tree` command for better directory visualization
- Optional: `jq` for parsing JSON package manifests

**Output format**:

```markdown
# Project Context Dump

## Project Overview
## Directory Structure
## Key Documentation Files
## Agent Guidance Files
## Recent Changes
## Git Status
## Technology Stack
## Environment Configuration
## Available Scripts
## Key Configuration Files
## Quick Start
```

**Example output excerpt**:

```markdown
## Recent Changes

**Last 20 commits**:

```text
b35e2c9 docs: Complete Session 1 compliance tracking
532a2f2 feat: Implement GitHub Actions CI/CD workflows
b85e985 Update NEXT_STEPS.md with compliance tracking
```

## Technology Stack

### Node.js/JavaScript

- **Runtime**: Node.js
- **Version**: v20.11.0
- **Key Dependencies**:
  - express
  - typescript

**Pro tips**:

- Run this at the start of each session if project structure has changed
- Include in CI/CD to track project evolution
- Commit output to `temp/output/` for debugging agent sessions
- Use as template for generating custom project reports

---

## Adding New Scripts

When adding new utility scripts to this directory:

### 1. Follow the Template

```bash
#!/bin/bash
# script-name.sh: Brief one-line description
#
# Purpose: Detailed explanation of what this script does
# Usage: ./scripts/script-name.sh [options]

set -e  # Exit on error

# Colors for output
CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

info() {
    echo -e "${CYAN}→ $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}" >&2
}

# Script logic here
```

### 2. Include Usage Documentation

Add a `--help` flag that prints:

- What the script does
- Required arguments
- Optional flags
- Examples
- Prerequisites

### 3. Add Safety Checks

- Validate required tools/commands exist
- Check for required files/directories
- Confirm destructive operations
- Provide dry-run mode when appropriate

### 4. Update This README

Add a section documenting:

- Script purpose
- Usage examples
- When to use it
- Requirements
- Output format

### 5. Make Executable

```bash
chmod +x scripts/your-script.sh
```

---

## Script Categories

### Setup & Installation

Scripts that help initialize the development environment.

**Future scripts**:

- `setup-dev-env.sh`: Install dependencies and configure environment
- `validate-env.sh`: Check that all required tools are installed

### Maintenance & Cleanup

Scripts for project maintenance tasks.

**Future scripts**:

- `cleanup-temp.sh`: Archive old files in `temp/notes/`
- `update-deps.sh`: Update and test all dependencies

### Agent Operations

Scripts specifically designed for AI agent workflows.

**Current**:

- ✅ `context-dump.sh`: Generate project context for agents

**Future scripts**:

- `session-log.sh`: Create timestamped log of agent session
- `verify-changes.sh`: Run all quality checks before commit

### Build & Deploy

Scripts for building and deploying the application.

**Future scripts**:

- `build.sh`: Build application for production
- `test-all.sh`: Run complete test suite

---

## Best Practices

### For Script Authors

1. **Use `set -e`**: Exit on first error unless you handle errors explicitly
2. **Use `set -u`**: Treat unset variables as errors
3. **Use `set -o pipefail`**: Catch errors in pipelines
4. **Quote variables**: Always use `"$VAR"` instead of `$VAR`
5. **Validate inputs**: Check that required arguments are provided
6. **Provide feedback**: Use `info()`, `success()`, `error()` functions
7. **Exit codes**: Return 0 for success, non-zero for failure
8. **Document everything**: Assume someone unfamiliar will use it

### For Script Users

1. **Read the help**: Run `script.sh --help` first
2. **Check requirements**: Ensure you have all prerequisites
3. **Use dry-run**: Test with `--dry-run` if available
4. **Review output**: Scripts provide detailed feedback
5. **Report issues**: File issues if scripts fail or behave unexpectedly

---

## Troubleshooting

### Script Permission Denied

```bash
# Make script executable
chmod +x scripts/script-name.sh
```

### Script Not Found

```bash
# Run from project root
cd /path/to/project
./scripts/script-name.sh

# Or use absolute path
bash /path/to/project/scripts/script-name.sh
```

### Command Not Found

Scripts will report missing dependencies:

```bash
❌ Error: 'tree' command not found. Install with: brew install tree
```

Follow the suggested installation command.

### Script Fails on macOS

Ensure you're using Bash 4.0+:

```bash
bash --version
```

If needed, install modern bash via Homebrew:

```bash
brew install bash
```

---

## Integration with Makefile

Many scripts are wrapped in Makefile targets for convenience:

```bash
# Instead of ./scripts/context-dump.sh
make context

# Run all quality checks
make check

# Run tests
make test
```

See `Makefile` for all available targets.

---

## Contributing

When contributing new scripts:

1. Follow the template and conventions above
2. Test on macOS, Linux, and (if applicable) Windows/WSL
3. Add usage examples to this README
4. Update the Makefile if appropriate
5. Include tests in CI/CD workflow

---

## Related Documentation

- **[Agent Operations](../docs/AGENT_OPERATIONS.md)**: Multi-agent coordination patterns
- **[Agent Safety](../docs/AGENT_SAFETY.md)**: Safety guidelines for agents
- **[Development Guide](../docs/QUICK_START.md)**: Setup and development workflow
- **[Environment Setup](../docs/ENVIRONMENT.md)**: System dependencies and toolchain

---

**Note**: This is a living document. As scripts are added, updated, or removed, keep this README synchronized.
