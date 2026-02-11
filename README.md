# DPV Sensemaking

**A generic response analysis platform for intelligently parsing free-text response data from diverse sources**

Sensemaking is designed to ingest complaints, comments, feedback, and other response data from various sources (CFPB complaints, regulations.gov public comments, surveys, etc.), normalize them to a shared analysis framework, and extract structured insights using LLM-powered analysis.

## Vision

The core goal is to build a **generic response analyzer** that can:

1. **Parse diverse input schemas** - Each data source has its own CSV schema with different columns, but all share a free-text narrative field
2. **Normalize to a common format** - Map source-specific fields to a shared analysis model while preserving source-specific metadata
3. **Extract structured insights** - Use LLMs to analyze narratives, extract themes, sentiment, entities, and categorical dimensions
4. **Handle attachments** - Process PDF, DOCX, and other document attachments referenced by URL or file path
5. **Support iterative development** - Feature flags for quick iteration with sample data

## Current Data Sources

### CFPB Exploration (`src/cfpb_exploration/`)

Analysis of Consumer Financial Protection Bureau complaint data. Contains consumer narratives about financial products and services.

### Regulations.gov Exploration (`src/regs_dot_gov_exploration/`)

Analysis of public comments submitted to federal regulatory dockets. Initial focus on CFPB-2023-0038 (Medical Payment Products RFI) - comments from patients, healthcare providers, and industry stakeholders about medical credit cards and financing.

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Setup

```bash
# Clone the repository
git clone https://github.com/jimmoffet/sensemaking.git
cd sensemaking

# Install dependencies with uv
uv sync --extra dev

# Or with pip
pip install -e ".[dev]"

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys (GEMINI_API_KEY required)

# Run linting
ruff check .
ruff format .

# Run type checking
mypy .

# Run tests
pytest
```

### Environment Configuration

Key environment variables:

```bash
# Required
GEMINI_API_KEY=your-gemini-api-key

# Development flags
USE_HEAD=true  # Use small sample data for fast iteration
```

## Repository Structure

```
sensemaking/
├── .github/                    # GitHub configuration
│   ├── agents/                 # Agent role definitions
│   ├── skills/                 # Custom skills
│   ├── ISSUE_TEMPLATE/         # Bug reports, feature requests
│   ├── PULL_REQUEST_TEMPLATE/  # PR templates
│   └── copilot-instructions.*  # AI agent guidance
│
├── ADRs/                       # Architecture Decision Records (immutable)
│
├── docs/                       # Developer documentation
│   ├── README.md               # Documentation index
│   └── QUICK_START.md          # Setup guide
│
├── src/                        # Source code
│   ├── cfpb_exploration/       # CFPB complaint analysis
│   │   ├── data/               # Input CSV data
│   │   ├── output/             # Analysis results
│   │   ├── prompts/            # LLM prompt templates
│   │   ├── schemas/            # Generated JSON schemas
│   │   ├── data_processor.py   # CSV parsing utilities
│   │   └── main.py             # Analysis orchestrator
│   │
│   ├── regs_dot_gov_exploration/  # Regulations.gov analysis
│   │   ├── data/               # Input data
│   │   │   ├── responses.csv   # Full dataset
│   │   │   └── head/           # Sample data for development
│   │   ├── output/             # Analysis results
│   │   ├── prompts/            # LLM prompt templates
│   │   ├── data_processor.py   # Schema-specific parsing
│   │   ├── attachment_processor.py  # PDF/DOCX extraction
│   │   └── main.py             # Analysis orchestrator
│   │
│   └── utilities/              # Shared modules
│       ├── llm/                # LLM client wrappers
│       └── schema_generator.py # Dynamic schema generation
│
├── temp/                       # Temporary files (gitignored)
│   ├── notes/                  # Agent working memory
│   ├── plans/                  # Execution plans
│   └── output/                 # Temporary outputs
│
├── tests/                      # Test suite
│
├── pyproject.toml              # Project configuration
├── ruff.toml                   # Ruff linter configuration
├── mypy.ini                    # MyPy type checker configuration
├── .env.example                # Environment template
├── AGENTS.md                   # Shared agent instructions
└── README.md                   # This file
```

## Development Tools

| Tool           | Purpose                                           |
| -------------- | ------------------------------------------------- |
| **uv**         | Fast Python package manager with lockfile support |
| **ruff**       | Primary linter and formatter (line length: 120)   |
| **mypy**       | Static type checker (strict mode)                 |
| **pytest**     | Test framework with async and coverage support    |
| **pre-commit** | Git hook framework for automated checks           |

### Key Commands

```bash
# Package management
uv sync --extra dev          # Install all dependencies
uv add <package>             # Add a dependency

# Code quality
ruff check .                 # Lint code
ruff check . --fix           # Auto-fix linting issues
ruff format .                # Format code

# Type checking
mypy .                       # Run type checker

# Testing
pytest                       # Run all tests
pytest -v                    # Verbose output
pytest --cov                 # With coverage report
```

## Architecture Principles

### Data Source Encapsulation

Each data source (`cfpb_exploration`, `regs_dot_gov_exploration`, etc.) encapsulates:

- **Schema-specific parsing** - CSV column mappings specific to that source
- **Field normalization** - Map to common analysis fields (id, narrative, metadata)
- **Attachment handling** - Source-specific attachment URL patterns

### Shared Utilities

The `utilities/` module provides:

- **LLM clients** - Wrappers for Gemini API with rate limiting
- **Schema generation** - Dynamic JSON schema creation from sample data
- **Response parsing** - Extract structured JSON from LLM responses

### Development Workflow

- Use `USE_HEAD=true` to work with small sample datasets
- Each source has a `data/head/` folder with headers + sample rows
- Run full analysis only after validating with sample data

## Documentation

- [Quick Start Guide](docs/QUICK_START.md) - Setup and getting started
- [Architecture Decision Records](ADRs/README.md) - Key architectural decisions
- [Contributing Guidelines](CONTRIBUTING.md) - How to contribute
- [Agent Instructions](AGENTS.md) - AI agent collaboration guide

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- **Maintainer**: Jim Moffet (<jim@digitalpublic.ventures>)
- **Issues**: [GitHub Issues](https://github.com/jimmoffet/sensemaking/issues)
