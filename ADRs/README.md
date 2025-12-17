# ADR Best Practices and Template

This directory contains Architecture Decision Records (ADRs) documenting significant architectural choices made in this project.

## Active ADRs

| ADR                            | Title                                 | Status   | Date             |
| ------------------------------ | ------------------------------------- | -------- | ---------------- |
| [001](./001-repo-structure.md) | Repository Structure and Organization | Accepted | {{CURRENT_DATE}} |

**Note**: This table should be updated as new ADRs are created. ADRs are numbered sequentially (001, 002, 003, etc.).

---

## ADR Template Components

- **Title**: A unique and descriptive title (e.g., `001: Use Redis for Caching`).
- **Status**: The current state of the ADR (e.g., Draft, Accepted, Deprecated).
- **Date**: The date the ADR was created.
- **Decision Maker**: The person(s) responsible for making the decision.
- **Stakeholders**: Anyone affected by or advising on the decision.

### Context

- Describe the problem statement and key drivers (functional and non-functional requirements).
- Briefly outline the situation and the specific challenge.

### Decision

- Clearly state the chosen option.
- Provide justification for the decision, including rationale and how it resolves the problem.

### Consequences

- List the positive and negative outcomes of the decision (trade-offs, risks, extra effort).
- Describe the expected state of the system after implementation.

### Alternatives Considered

- List other options that were considered and explain why they were rejected.

---

## Best Practices for Writing ADRs

- **Focus on one decision**: Keep each ADR focused on a single, significant decision to avoid confusion.
- **Be immutable**: Do not change past ADRs. If a decision needs to be revised, write a new ADR that supersedes the old one, referencing the original.
- **Write in plain language**: Document for your future self and new team members. Avoid jargon and make the document easy to understand.
- **Document the "why"**: Focus on the reasons behind the decision, not just the technical details, to help others understand and adopt the decision later.
- **Keep them concise**: Make meetings focused and keep the documents short and to the point.
- **Be specific**: Each ADR should be about a single decision, not multiple unrelated decisions.
- **Identify the impact**: Clearly state the consequences, including positive and negative impacts, to understand the trade-offs made.
- **Review and update regularly**: Periodically review ADRs to ensure they are still relevant and accurate.

---

## When to Create an ADR

ADRs should document **architectural decisions** that have significant, long-term impact on the system. Not every decision needs an ADR.

### ✅ Create an ADR for:

- **Technology/Framework Choices**: "Use PostgreSQL for primary database", "Use React for frontend framework"
- **Architectural Patterns**: "Implement repository pattern for data access", "Use event-driven architecture"
- **Database Schema Changes**: Major schema redesigns, data modeling decisions
- **API Design Decisions**: REST vs GraphQL, API versioning strategy, authentication approach
- **Infrastructure Choices**: Deployment architecture, containerization strategy, cloud provider selection
- **Performance/Scalability Trade-offs**: Caching strategy, database sharding, async processing
- **Cross-Cutting Concerns**: Logging approach, error handling strategy, authentication/authorization model
- **Third-Party Integrations**: Payment gateway selection, email service provider, analytics platform
- **Build/Deployment Architecture**: CI/CD pipeline design, branching strategy, release process

### ❌ Don't Create an ADR for:

- **Implementation Details**: Variable names, code organization within a module
- **Temporary Decisions**: "Use mock data for testing this week"
- **Obvious Choices**: Using standard library functions, following language idioms
- **Tactical Decisions**: Bug fixes, minor refactorings, optimization tweaks
- **Process Decisions**: Meeting schedules, communication channels (unless architectural)
- **Reversible Decisions**: Decisions that can be easily changed without significant impact

### Granularity Guidelines

**Too Broad** ❌: "ADR: Application Architecture"

- Problem: Tries to document too many decisions at once
- Better: Break into separate ADRs: "Use microservices architecture", "Use PostgreSQL for user data", "Use Redis for session storage"

**Too Narrow** ❌: "ADR: Use camelCase for JavaScript variables"

- Problem: Implementation detail, not architectural
- Better: Document in code style guide (`.cursorrules`, `CONTRIBUTING.md`)

**Just Right** ✅: "ADR: Use Redis for Session Storage"

- Clear scope: Single architectural decision
- Significant impact: Affects scalability, deployment, dependencies
- Justifiable: Has clear alternatives with trade-offs

---

## Superseding ADRs

When a decision needs to be revised or reversed, **never edit the original ADR**. Instead, create a new ADR that supersedes it.

### Process

1. **Create new ADR** with next sequential number
2. **Reference original** in the new ADR's context section
3. **Update original** ADR's status to show it's been superseded
4. **Update ADR table** to reflect both ADRs and their relationship

### Example: Superseding an ADR

**Original ADR (003-use-mongodb.md)**:

```markdown
# ADR 003: Use MongoDB for Primary Database

**Status**: ~~Accepted~~ → **Superseded by [ADR 012](./012-migrate-to-postgresql.md)**
**Date**: 2024-03-15
**Decision Maker**: Backend Team
**Stakeholders**: Engineering, DevOps

## Context

[... original context ...]

## Decision

We will use MongoDB for our primary database.

[... rest of ADR ...]
```

**New ADR (012-migrate-to-postgresql.md)**:

```markdown
# ADR 012: Migrate from MongoDB to PostgreSQL

**Status**: Accepted
**Date**: 2024-11-23
**Decision Maker**: Backend Team, CTO
**Stakeholders**: Engineering, DevOps, Product

**Supersedes**: [ADR 003: Use MongoDB for Primary Database](./003-use-mongodb.md)

## Context

In ADR 003, we chose MongoDB for flexibility with document storage. After 8 months of production use, we've encountered several issues:

- Complex joins require application-level logic
- Limited transaction support causes data consistency issues
- Query performance degrades with relational patterns
- Team expertise is stronger in SQL databases

Our data model has stabilized and is now more relational than document-oriented.

## Decision

We will migrate from MongoDB to PostgreSQL for our primary database.

[... rest of ADR ...]

## Migration Plan

[... details of migration approach ...]
```

**Updated ADR Table**:

```markdown
| ADR                                   | Title                              | Status                | Date       |
| ------------------------------------- | ---------------------------------- | --------------------- | ---------- |
| [003](./003-use-mongodb.md)           | Use MongoDB for Primary DB         | Superseded by ADR 012 | 2024-03-15 |
| [012](./012-migrate-to-postgresql.md) | Migrate from MongoDB to PostgreSQL | Accepted              | 2024-11-23 |
```

### Why Not Edit Original ADRs?

- **Historical Context**: Preserves why the original decision made sense at the time
- **Decision Evolution**: Shows how thinking evolved with new information
- **Audit Trail**: Maintains complete history for compliance/review
- **Learning**: Helps team understand what changed and why
