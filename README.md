# cfpb-exploration

CFPB data exploration and analysis

## Quick Start

See [docs/QUICK_START.md](docs/QUICK_START.md) for detailed setup instructions.

## Features

- Feature 1
- Feature 2
- Feature 3

## Repository Structure

This repository follows an agent-friendly three-tier documentation system designed for effective human-agent collaboration:

```
cfpb-exploration/
├── .github/                    # GitHub configuration
│   ├── ISSUE_TEMPLATE/        # Bug reports, feature requests, docs issues
│   ├── PULL_REQUEST_TEMPLATE/ # Specialized PR templates by type
│   ├── copilot-instructions.md # GitHub Copilot workspace guidance
│   └── pull_request_template.md # PR template selector
│
├── ADRs/                      # Architecture Decision Records
│   ├── README.md             # ADR template and best practices
│   └── 001-repo-structure.md # Documentation system decisions
│
├── docs/                      # Developer documentation
│   ├── README.md             # Documentation index and TOC
│   └── QUICK_START.md        # Setup and getting started guide
│
├── temp/                      # Temporary files and agent workspace
│   ├── notes/                # Agent planning and working memory
│   │   ├── README.md         # Notes directory guide
│   │   ├── ROADMAP.md        # Long-term planning (REQUIRED)
│   │   ├── NEXT_STEPS.md     # Immediate tasks (REQUIRED)
│   │   └── archive/          # Completed notes by month (YYYY-MM/)
│   ├── debug/                # Debug scripts and outputs
│   └── output/               # Temporary output files
│
├── [src/app/lib/...]         # Your application code (structure varies)
│
├── .env.example              # Environment variable template
├── .gitignore                # Git ignore patterns
├── CHANGELOG.md              # Version history
├── CODE_OF_CONDUCT.md        # Contributor Covenant
├── CONTRIBUTING.md           # Contribution guidelines
├── LICENSE                   # MIT License
├── README.md                 # This file
└── SECURITY.md               # Security policy
```

### Documentation System

**Three Tiers**:

1. **`/docs/`** - Formal developer documentation (setup, APIs, guides)
2. **`/ADRs/`** - Immutable architectural decision records
3. **`/temp/notes/`** - Agent working memory and planning documents

**Key Principles**:

- `ROADMAP.md` and `NEXT_STEPS.md` are **required** and must always exist
- Archive completed notes to `temp/notes/archive/YYYY-MM/`
- Extract architectural decisions to ADRs before archiving
- ADRs are immutable (create new ADR to supersede, don't edit)

See [ADRs/001-repo-structure.md](ADRs/001-repo-structure.md) for the full rationale behind this structure.

## Development

### Prerequisites

- [List your project's prerequisites]
- [e.g., Python 3.12+, Node.js 20+, Docker, etc.]

### Setup

```bash
# Clone the repository
git clone https://github.com/jimmoffet/cfpb-exploration.git
cd cfpb-exploration

# Install dependencies
[Your installation commands]

# Copy environment variables
cp .env.example .env
# Edit .env with your values

# Run the application
[Your run commands]
```

See [docs/QUICK_START.md](docs/QUICK_START.md) for detailed instructions.

### Running Tests

```bash
[Your test commands]
```

### Code Quality

```bash
[Your lint/format/type-check commands]
```

## Usage

[Add usage examples and documentation]

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Guide

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Make your changes
5. Run quality checks (lint, format, test)
6. Commit with clear messages
7. Push to your fork
8. Open a Pull Request (use appropriate template)

## Documentation

- [Quick Start Guide](docs/QUICK_START.md) - Setup and getting started
- [Architecture Decision Records](ADRs/README.md) - Key architectural decisions
- [Contributing Guidelines](CONTRIBUTING.md) - How to contribute
- [Code of Conduct](CODE_OF_CONDUCT.md) - Community standards
- [Security Policy](SECURITY.md) - Vulnerability reporting

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- **Maintainer**: Jim Moffet (jim@digitalpublic.ventures)
- **Issues**: [GitHub Issues](https://github.com/jimmoffet/cfpb-exploration/issues)
- **Discussions**: [GitHub Discussions](https://github.com/jimmoffet/cfpb-exploration/discussions)

## Acknowledgments

- Built with an agent-friendly cfpb-exploration template
- Documentation structure designed for human-agent collaboration

---

**Note**: This README was generated from a cfpb-exploration template. Update it with your project-specific information.
