# Next Steps

**Last Updated**: {{CURRENT_DATE}}
**Session ID**: [Generate unique ID, e.g., feature-name-001 or YYYYMMDD-NNN]
**Agent/User**: [Your name/identifier]
**Status**: [NOT_STARTED / IN_PROGRESS / BLOCKED / COMPLETED]
**Working Branch**: [Branch name, usually 'main' initially]

---

## Current Context

**What Just Happened**: [Brief summary of recent work or session start]

**Focus**: [Current priority or milestone]

**Blockers**: [None / List any blockers]

---

## Current Status

✅ **Repository Initialized**: Agent-friendly structure in place
📋 **Next**: Define project goals and begin development

---

## Immediate Actions (This Session)

### 1. Define Project Scope (15-30 min)

**Goal**: Clarify what this project will do

**Tasks**:

1. Update `README.md` with project description
2. Document key features or goals
3. Identify initial technical stack
4. List any immediate dependencies or tools needed

### 2. Set Up Development Environment (30-60 min)

**Tasks**:

1. [ ] Install necessary tools and dependencies
2. [ ] Configure development environment
3. [ ] Set up any required external services
4. [ ] Test basic toolchain (build, test, run)
5. [ ] Update `.env.example` with actual environment variables needed

### 3. Create Initial Project Structure (30 min)

**Tasks**:

1. [ ] Create source code directories (e.g., `src/`, `lib/`, `app/`)
2. [ ] Add basic configuration files (e.g., `package.json`, `pyproject.toml`, `Cargo.toml`)
3. [ ] Set up test framework
4. [ ] Add any language-specific tooling configs

### 4. First Commit (5 min)

**Tasks**:

1. [ ] Review all files
2. [ ] Ensure no secrets in `.env` or elsewhere
3. [ ] Commit initial structure
4. [ ] Push to remote (if applicable)

---

## Follow-Up Tasks (Next Session)

### Development

- [ ] Implement [first feature or component]
- [ ] Write tests for [component]
- [ ] Set up CI/CD pipeline (GitHub Actions, etc.)
- [ ] Add pre-commit hooks

### Documentation

- [ ] Complete `docs/QUICK_START.md` with setup instructions
- [ ] Document architecture in `docs/ARCHITECTURE.md`
- [ ] Add API documentation (if applicable)
- [ ] Update `README.md` with usage examples

### Planning

- [ ] Create detailed roadmap in `ROADMAP.md`
- [ ] Define success criteria for v1.0
- [ ] Identify potential architectural decisions needing ADRs

---

## Validation Checklist

Before considering setup complete:

- [ ] Project builds successfully
- [ ] Tests run (even if minimal)
- [ ] README.md clearly explains what the project does
- [ ] QUICK_START.md has accurate setup instructions
- [ ] All placeholders ({{VARIABLES}}) have been replaced
- [ ] .gitignore covers common files for your language/framework
- [ ] No secrets committed to repository

---

## Questions to Answer

Document any open questions that need resolution:

1. **[Question 1]**: [Context and why it matters]
2. **[Question 2]**: [Context and possible options]

---

## Blockers

List anything preventing progress:

- [ ] **Blocker 1**: [Description and who can unblock]
- [ ] **Blocker 2**: [Description and potential workaround]

---

## Recent Work Completed

### Repository Setup ({{CURRENT_DATE}})

**What**: Initialized repository from agent-friendly cfpb-exploration template

**Deliverables**:

- Three-tier documentation system (docs/, ADRs/, temp/notes/)
- GitHub PR and issue templates
- Community files (LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY)
- ADR 001: Repository Structure and Organization

**Next**: Begin defining project scope and technical approach

---

## Notes

- Keep this file focused on immediate and near-term actions
- Move completed sections to archive when they're no longer relevant
- Update after each work session
- Long-term strategic items belong in `ROADMAP.md`
- Extract architectural decisions to ADRs before archiving
