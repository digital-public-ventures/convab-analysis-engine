# Quick Start Guide

Get cfpb-exploration up and running in minutes.

## Prerequisites

Before you begin, ensure you have:

- [Prerequisite 1] - [Why you need it]
- [Prerequisite 2] - [Why you need it]
- [Prerequisite 3] - [Why you need it]

**Operating System Support**:

- ✅ macOS (tested on version X+)
- ✅ Linux (tested on Ubuntu XX.XX+)
- ✅ Windows (tested on Windows XX via WSL/native)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/jimmoffet/cfpb-exploration.git
cd cfpb-exploration
```

### 2. Install Dependencies

**[Your Language/Framework]**:

```bash
# Example for different languages:

# Python
pip install -r requirements.txt
# or
poetry install

# Node.js
npm install
# or
yarn install

# Go
go mod download

# Rust
cargo build
```

### 3. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
# Required variables:
#   - VARIABLE_1: [Description]
#   - VARIABLE_2: [Description]
```

**Environment Variables**:

| Variable | Required | Default | Description    |
| -------- | -------- | ------- | -------------- |
| `VAR_1`  | Yes      | -       | [What it does] |
| `VAR_2`  | No       | `value` | [What it does] |

See [`.env.example`](../.env.example) for all available options.

### 4. Initialize the Application

```bash
# Run any setup scripts
[Your setup commands]

# For example:
# - Database migrations
# - Seed data
# - Build steps
```

### 5. Verify Installation

```bash
# Run tests to ensure everything is working
[Your test command]

# Expected output:
# [What success looks like]
```

## Running the Application

### Development Mode

```bash
[Your development run command]

# Example output:
# Server running on http://localhost:8000
# Press Ctrl+C to stop
```

The application should now be available at: [Your URL]

### Production Mode

```bash
[Your production run command]
```

See [Deployment Guide](DEPLOYMENT.md) for production deployment instructions.

## Basic Usage

### Example 1: [Common Task]

```bash
# Command to perform common task
[command]

# Expected output:
[output]
```

### Example 2: [Another Common Task]

```bash
[command]
```

## Project Structure

```
cfpb-exploration/
├── [src/app/lib/]    # Your source code
├── [tests/]          # Test files
├── [config/]         # Configuration files
├── docs/             # Documentation (you are here)
├── ADRs/             # Architecture decisions
└── temp/notes/       # Planning and agent workspace
```

See [main README](../README.md#repository-structure) for detailed structure explanation.

## Development Workflow

1. **Create a branch**: `git checkout -b feature/your-feature`
2. **Write tests first** (TDD recommended)
3. **Implement your changes**
4. **Run quality checks**:
   ```bash
   [Your lint/format/test commands]
   ```
5. **Commit your changes**: Clear, descriptive commit messages
6. **Push and create PR**: Use appropriate PR template

See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed guidelines.

## Common Commands

```bash
# Run tests
[test command]

# Run linter
[lint command]

# Format code
[format command]

# Type check (if applicable)
[type check command]

# Build for production
[build command]

# View logs
[logs command]
```

## Troubleshooting

### Problem: [Common Issue 1]

**Symptoms**: [What you see]

**Solution**:

```bash
[Fix command]
```

### Problem: [Common Issue 2]

**Symptoms**: [What you see]

**Solution**: [Steps to fix]

### Problem: Port Already in Use

**Symptoms**: Error message about port already in use

**Solution**:

```bash
# Find process using the port
lsof -i :[PORT]  # macOS/Linux
# or
netstat -ano | findstr :[PORT]  # Windows

# Kill the process or use a different port
```

### Still Having Issues?

- Check [Troubleshooting Guide](TROUBLESHOOTING.md) for more solutions
- Search [existing issues](https://github.com/jimmoffet/cfpb-exploration/issues)
- Ask in [Discussions](https://github.com/jimmoffet/cfpb-exploration/discussions)
- Open a [bug report](https://github.com/jimmoffet/cfpb-exploration/issues/new?template=bug_report.md)

## Next Steps

Now that you're up and running:

- Read the [User Guide](USER_GUIDE.md) for detailed usage
- Review [Architecture Overview](ARCHITECTURE.md) to understand the system
- Check out [API Documentation](API.md) for API reference
- Explore [Architecture Decision Records](../ADRs/README.md) for context on design choices
- See [ROADMAP.md](../temp/notes/ROADMAP.md) for upcoming features

## Getting Help

- **Documentation**: [docs/](README.md)
- **Issues**: [GitHub Issues](https://github.com/jimmoffet/cfpb-exploration/issues)
- **Discussions**: [GitHub Discussions](https://github.com/jimmoffet/cfpb-exploration/discussions)
- **Email**: jim@digitalpublic.ventures

---

**Last Updated**: {{CURRENT_DATE}}

[Back to Documentation Index](README.md) | [Main README](../README.md)
