# cfpb-exploration Documentation

Welcome to the cfpb-exploration documentation. This directory contains formal, developer-facing documentation for understanding, using, and contributing to the project.

## Table of Contents

### Getting Started

- [Quick Start Guide](QUICK_START.md) - Setup instructions and first steps
- Architecture Overview (coming soon) - High-level system design
- Installation Guide (coming soon) - Detailed installation instructions

### Guides

- User Guide (coming soon) - How to use cfpb-exploration
- Developer Guide (coming soon) - Development setup and workflows
- API Reference (coming soon) - API documentation
- Configuration Guide (coming soon) - Configuration options

### Reference

- [Architecture Decision Records](../ADRs/README.md) - Why we made key decisions
- Troubleshooting (coming soon) - Common issues and solutions
- FAQ (coming soon) - Frequently asked questions

### Operations

- Deployment Guide (coming soon) - How to deploy cfpb-exploration
- Monitoring Guide (coming soon) - Observability and monitoring
- Backup & Recovery (coming soon) - Data management

## Documentation Standards

### When to Document

Document when:

- Adding new features that users/developers will interact with
- Making architectural decisions (create ADR in `/ADRs/`)
- Changing APIs or interfaces
- Updating setup/deployment procedures
- Answering questions more than once

### Where to Document

**`/docs/`** (this directory) - For:

- Setup and installation guides
- User-facing documentation
- API references
- How-to guides and tutorials
- Operational documentation

**`/ADRs/`** - For:

- Architectural decisions
- Technology choices
- Design patterns
- Trade-off analysis

**`/temp/notes/`** - For:

- Work-in-progress planning
- Agent session continuity
- Design explorations (before formalizing)
- Implementation notes (archive when complete)

**Code comments** - For:

- Complex algorithms
- Non-obvious implementation choices
- TODOs and FIXMEs
- API documentation (docstrings)

### Documentation Style Guide

**General**:

- Write in present tense ("The system does..." not "The system will do...")
- Use active voice ("Run the command" not "The command should be run")
- Be concise but complete
- Include examples
- Keep up to date (stale docs are worse than no docs)

**Structure**:

- Start with a brief overview
- Include a table of contents for long documents
- Use clear section headings
- Add code examples with explanations
- Provide "Next Steps" at the end

**Code Examples**:

```bash
# Always include explanatory comments
command --with-flag  # Explain what this does

# Show expected output when helpful
echo "Expected output"
```

**Formatting**:

- Use **bold** for emphasis and UI elements
- Use `code formatting` for commands, filenames, variables
- Use > blockquotes for important notes
- Use - or \* for unordered lists
- Use 1. 2. 3. for sequential steps

### Maintaining Documentation

**Review Cycle**:

- Update docs when code changes
- Review quarterly for accuracy
- Archive outdated content (don't delete)
- Link between related documents

**Version Control**:

- Documentation changes go through PR review
- Update CHANGELOG.md for significant doc changes
- Tag documentation versions with releases

**Templates**:

New document template:

```markdown
# [Document Title]

Brief description of what this document covers.

## Prerequisites

What the reader should know or have before reading.

## [Main Section]

Content here.

### [Subsection]

More detailed content.

## Examples

Real-world examples.

## Troubleshooting

Common issues and solutions.

## Next Steps

- Link to related documentation
- Suggest what to read/do next

## References

- Links to external resources
- Related ADRs
```

## Contributing to Documentation

Documentation improvements are always welcome! To contribute:

1. Follow the style guide above
2. Test any code examples
3. Check links work
4. Use the `?template=docs.md` PR template
5. Ask for review from someone familiar with the topic

See [CONTRIBUTING.md](../CONTRIBUTING.md) for general contribution guidelines.

## Need Help?

- **Can't find what you need?** [Open an issue](https://github.com/jimmoffet/cfpb-exploration/issues/new?template=documentation.md)
- **Found an error?** Submit a PR with the fix
- **Have a question?** [Start a discussion](https://github.com/jimmoffet/cfpb-exploration/discussions)

---

**Last Updated**: {{CURRENT_DATE}}
