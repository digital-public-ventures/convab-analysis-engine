# Agent Evaluation Framework

**Purpose**: Systematic verification of agent-generated changes to ensure correctness, completeness, safety, and quality.

**Architecture Decision**: See [ADR 003](../../ADRs/003-agent-evaluation-framework.md)

---

## Quick Start

### For Agents Creating Changes

1. **Before starting work**: Review [ACCEPTANCE_CRITERIA.md](./ACCEPTANCE_CRITERIA.md) for your change type
2. **During development**: Keep acceptance criteria in mind
3. **Before committing**: Complete [VERIFICATION_CHECKLIST.md](./VERIFICATION_CHECKLIST.md)
4. **Include in PR**: Link to completed checklist or embed in PR description

### For Human Reviewers

1. **Check verification**: Ensure agent completed verification checklist
2. **Run smoke tests**: Execute relevant tests from [SMOKE.md](./SMOKE.md)
3. **Use review checklist**: Follow [REVIEW_CHECKLIST.md](./REVIEW_CHECKLIST.md) for thorough review
4. **Provide feedback**: Reference framework terms for consistency

---

## Framework Overview

### Three-Tier Approach

```
┌─────────────────────────────────────────────────────┐
│  Tier 1: Pre-Commit Verification (Agent Self-Check) │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  → Verification Checklist                           │
│  → Acceptance Criteria                              │
│  → Self-Test Prompts                                │
│  Goal: Agents verify their own work                 │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  Tier 2: Smoke Testing (Fast Validation)            │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  → Critical Path Tests                              │
│  → Health Checks                                    │
│  → Quick Regression Checks                          │
│  Goal: Catch obvious issues in < 30 seconds         │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  Tier 3: Comprehensive Review (Review Time)         │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  → PR Review Checklist                              │
│  → Architecture Assessment                          │
│  → Performance Validation                           │
│  Goal: Thorough quality assessment                  │
└─────────────────────────────────────────────────────┘
```

---

## Documents in This Framework

### Core Templates

| Document                                              | Purpose                                   | Used By       | When              |
| ----------------------------------------------------- | ----------------------------------------- | ------------- | ----------------- |
| [VERIFICATION_CHECKLIST.md](./VERIFICATION_CHECKLIST.md) | Self-check before committing              | Agents        | Before commit     |
| [ACCEPTANCE_CRITERIA.md](./ACCEPTANCE_CRITERIA.md)    | Define "done" for different change types  | Agents        | Before starting   |
| [SMOKE.md](./SMOKE.md)                                | Fast critical path tests                  | Both          | Before PR         |
| [REVIEW_CHECKLIST.md](./REVIEW_CHECKLIST.md)          | Comprehensive PR review guide             | Reviewers     | During PR review  |

### Future Additions

- `scripts/smoke-test.sh` - Automated smoke test runner
- `scripts/verify.sh` - Pre-commit verification automation
- `EXPERIMENTS.md` - Track performance/behavior experiments
- `BENCHMARKS.md` - Performance testing guidance

---

## Workflow Examples

### Example 1: Agent Adding New Feature

```bash
# 1. Check acceptance criteria for features
cat docs/evaluation/ACCEPTANCE_CRITERIA.md  # Read "Feature Addition" section

# 2. Implement feature with tests
# ... development work ...

# 3. Complete verification checklist
# Copy VERIFICATION_CHECKLIST.md to temp/notes/CURRENT_VERIFICATION.md
# Fill out each section

# 4. Run smoke tests
# Check SMOKE.md for relevant tests
npm test  # or appropriate test command

# 5. Commit with checklist reference
git commit -m "feat: Add user export feature

See temp/notes/CURRENT_VERIFICATION.md for verification details"

# 6. Include in PR description
# Link or embed verification checklist
```

### Example 2: Human Reviewing Agent PR

```bash
# 1. Check verification checklist was completed
# Look for verification checklist in PR description or temp/notes/

# 2. Run smoke tests
cat docs/evaluation/SMOKE.md  # Find relevant tests
./scripts/smoke-test.sh  # Or manual execution

# 3. Use review checklist
cat docs/evaluation/REVIEW_CHECKLIST.md  # Follow structured review

# 4. Verify acceptance criteria met
# Check against criteria from ACCEPTANCE_CRITERIA.md

# 5. Approve or request changes with specific feedback
```

---

## Philosophy

### Verification vs. Testing

**Testing** answers: "Does the code work?"

**Verification** answers: "Did we complete the task correctly?"

Verification includes:

- Code correctness (covered by tests)
- Documentation completeness
- Architectural coherence
- Security considerations
- Performance implications
- Backward compatibility

### Trust but Verify

This framework doesn't imply distrust of agents. It provides:

1. **Clarity**: Clear definition of "done"
2. **Consistency**: Same standards for all changes
3. **Learning**: Agents improve by seeing good verification
4. **Efficiency**: Catch issues before review, not during

### Lightweight by Default

Checklists should be:

- ✅ Quick to complete (< 5 minutes)
- ✅ Focused on high-value checks
- ✅ Adaptable to task complexity
- ❌ Not bureaucratic overhead

**Guideline**: If verification takes longer than the change itself, simplify the checklist.

---

## Best Practices

### For Agents

1. **Read acceptance criteria first**: Know what "done" looks like before starting
2. **Complete checklist honestly**: If you can't check a box, explain why
3. **Include verification in commits**: Make it easy for reviewers to see what you verified
4. **Link to smoke tests run**: Show which tests you executed
5. **Document assumptions**: If unclear, state what you assumed

### For Reviewers

1. **Check verification first**: Don't start detailed review if verification is incomplete
2. **Use checklist as guide**: Adapt to change complexity
3. **Provide specific feedback**: Reference checklist items when requesting changes
4. **Acknowledge good verification**: Positive feedback improves agent learning
5. **Update checklists**: If you find recurring gaps, update templates

### For Project Maintainers

1. **Keep templates current**: Review quarterly, update as patterns emerge
2. **Track metrics**: Monitor verification completion rates and issue detection
3. **Evolve gradually**: Add complexity only when justified
4. **Make it easy**: Automate what's automatable
5. **Celebrate wins**: Share examples of verification catching issues

---

## Customization

### Adding Project-Specific Checks

Create `docs/evaluation/PROJECT_SPECIFIC.md` with:

```markdown
# Project-Specific Evaluation Criteria

## Database Changes

- [ ] Migration tested with rollback
- [ ] Indexes added for new queries
- [ ] No N+1 query patterns introduced

## API Changes

- [ ] OpenAPI spec updated
- [ ] Versioning strategy followed
- [ ] Backward compatibility verified
```

### Adapting to Tech Stack

Smoke tests and verification steps should reflect your stack:

- **Python**: Virtual environment, pytest, type hints
- **Node.js**: Dependencies, Jest, linting
- **Go**: go vet, go test, formatting
- **Rust**: cargo test, clippy, formatting

See [SMOKE.md](./SMOKE.md) for language-specific examples.

---

## Metrics and Improvement

### Key Metrics to Track

**Adoption Metrics**:

- % of agent PRs with completed verification checklist
- % of PRs passing smoke tests on first try

**Quality Metrics**:

- Bugs found post-merge (agent vs human)
- PR iteration count (agent vs human)
- Time from PR creation to approval

**Efficiency Metrics**:

- Average time to complete verification
- Smoke test execution time
- Review time per PR

### Continuous Improvement

**Monthly Review Questions**:

1. Are agents completing verification checklists consistently?
2. What issues are verification catching vs. missing?
3. Are checklists too heavy or too light?
4. Which smoke tests provide most value?
5. What new patterns should we add?

**Signals for Update**:

- ⚠️ Same type of bug found repeatedly → Add checklist item
- ⚠️ Agents skipping sections → Checklist too detailed
- ⚠️ Reviews still finding obvious issues → Strengthen smoke tests
- ✅ Verification consistently thorough → System working

---

## Integration with Other Docs

This evaluation framework complements:

- **[docs/TESTING.md](../TESTING.md)**: Testing philosophy and test organization
- **[docs/AGENT_OPERATIONS.md](../AGENT_OPERATIONS.md)**: Multi-agent coordination
- **[.github/PULL_REQUEST_TEMPLATE/](../../.github/PULL_REQUEST_TEMPLATE/)**: PR submission standards
- **[ADRs/](../../ADRs/)**: Architectural decision history

**Rule of thumb**: If TESTING.md says "what to test", this framework says "did you test it?"

---

## Getting Help

### Questions About Framework

- **Not sure which checklist to use?** → Start with [ACCEPTANCE_CRITERIA.md](./ACCEPTANCE_CRITERIA.md)
- **Checklist item unclear?** → Create GitHub issue or ask in PR
- **Need custom verification?** → Document in PR description, propose checklist update

### Proposing Changes

1. Open GitHub issue describing problem
2. Propose specific checklist/template change
3. Show example of how it would have caught an issue
4. Submit PR with updated template

---

## References

- **ADR**: [003-agent-evaluation-framework.md](../../ADRs/003-agent-evaluation-framework.md)
- **Original Recommendations**: See archived template reviews
- **Related**: [docs/TESTING.md](../TESTING.md), [docs/AGENT_OPERATIONS.md](../AGENT_OPERATIONS.md)

---

**Last Updated**: 2025-12-17
**Maintained By**: Development Team
**Feedback**: Open GitHub issue with "evaluation:" prefix
