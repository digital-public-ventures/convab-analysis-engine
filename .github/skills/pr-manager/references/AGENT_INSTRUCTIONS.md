# PR comment triage — agent instructions (local-only)

This folder is local-only scratch space (gitignored). Do not add or commit anything under `temp/`.

## Goal

Given one or more PR numbers, pull all PR comments into a single markdown file per PR, then produce a short triage assessment.

**Hard requirements (follow strictly):**

1. Use the script at `temp/scripts/fetch_pr_comments.py`.
2. For each PR `N`, write output into `temp/pr_comments/pr_N/`.
3. Inside each `temp/pr_comments/pr_N/`, create **exactly one** new file named `pr_comments.md`.
4. Do **not** write `comments.md` (that name is reserved by older/archived work).
5. Do **not** modify anything under `temp/pr_comments/archive/`.
6. After creating `pr_comments.md` and your initial triage notes, **STOP** and ask the user to review and provide guidance before making any code changes.

## Fetching comments

### Prereqs

- GitHub CLI is installed and authenticated (`gh auth status`).
- You are in the repo root.

### Command

Run the fetch script for a PR and write into `temp/pr_comments`:

```bash
/usr/bin/python3 temp/scripts/fetch_pr_comments.py <PR_NUMBER> --out temp/pr_comments
```

This will create `temp/pr_comments/pr_<PR_NUMBER>/comments.md` (script’s default behavior).

### Rename to the required filename

Immediately after running the script, rename the generated file to the required `pr_comments.md`:

```bash
mv temp/pr_comments/pr_<PR_NUMBER>/comments.md temp/pr_comments/pr_<PR_NUMBER>/pr_comments.md
```

Then ensure that folder contains **only** `pr_comments.md` (delete any extra artifacts if they exist).

## Evaluating comments (triage guidance)

Read `temp/pr_comments/pr_<PR_NUMBER>/pr_comments.md` and classify each item with a decision:

- **address now**: clear correctness bug, security issue, or high-value DX fix with low risk.
- **defer**: reasonable suggestion but needs design decision, broader refactor, or coordination.
- **ignore**: incorrect/duplicate/low-value nit.
- **already fixed**: the codebase already satisfies the comment.

When deciding, prefer:

- Correctness and security over style.
- Small, non-breaking improvements.
- Avoid scope creep: do not start implementing deferred items.

### Mandatory deferral tracking

Whenever the user decides to **defer** an item, you **must** record it in:

- `plans/DEFERRED_MAINTENANCE.md`

Include enough context to understand later (where/what/why defer, plus any follow-up ideas).

## Output format (per PR)

At the bottom of `pr_comments.md`, append a short section:

- `## Triage`
  - A bulleted list with one line per comment.

### Triage bullet formatting (action first, loud)

Each bullet **must** start with a bold, uppercase action tag so the recommended action is the first thing reviewers see:

- `**ADDRESS NOW**`
- `**DEFER**`
- `**IGNORE**`
- `**ALREADY FIXED**`

Then use the following structure:

- `- **<ACTION>** — <short label> — <one sentence why>`

Examples:

- `- **ADDRESS NOW** — AUTH_PROVIDER_MODE default — Avoid .strip() on None when env var is unset.`
- `- **DEFER** — S3 client init timing — Larger refactor; record in plans/ROADMAP.md.`

For any item marked **defer**, include (in the same bullet) a short note about how/where it will be recorded in `plans/ROADMAP.md` (eg “Added as Phase 2 task 2.14”).

Keep it brief.

## Stop point (mandatory)

Once `pr_comments.md` exists for the requested PR(s) and triage notes are appended:

1. Do not open PRs.
2. Do not change repository code.
3. Ask the user to review the triage notes and tell you which items to address now vs defer.

## Required workflow after user sign-off

Once the user has reviewed triage and explicitly decided what to **defer** vs **address now**, follow this sequence:

1. **Confer with user** (confirm the final decisions).
2. **Record deferrals** in `plans/DEFERRED_MAINTENANCE.md` (mandatory; include where/what/why defer).
3. **Implement “ADDRESS NOW” items** (minimal, targeted fixes + relevant tests).
4. **Reply to each PR comment and resolve threads**:

- Reply to every inline review comment with the outcome (**IGNORED**, **DEFERRED**, **ADDRESSED**, or **ALREADY FIXED**).
- Resolve the corresponding review threads after replying.
- If there are non-inline issue comments in the PR conversation, add a PR comment noting the outcome (GitHub doesn’t support “replying” to issue comments as threads).

After the user approves and you implement changes, you must also update the PR title/body (if a PR exists) so it accurately reflects the full diff vs `origin/main`. Treat this as a required deliverable, not a nice-to-have.

Guidance for PR updates:

- Before editing a PR title/body, re-check the full change scope against `origin/main` (use `git diff --stat origin/main...HEAD`).
- If the diff includes whole new modules/directories or large wiring changes, the PR title/body must mention them explicitly (don’t summarize large additions as “small improvements”).
- Preferred workflow: run `/usr/bin/python3 temp/scripts/save_branch_diff.py` and use the generated summary file to drive the PR description.

PR update verification (mandatory):

- After editing the PR, run `gh pr view <PR_NUMBER> --json title,body` and confirm the title/body explicitly mention the major additions shown in the diff summary.
- Do not proceed to archiving until the PR title/body is verified and the user agrees it looks correct.

## Archive (after sign-off)

After the user has reviewed `pr_comments.md` and signed off on next steps, archive the folder by moving it to:

`temp/pr_comments/archive/pr_<PR_NUMBER>/`

Do not archive before the user signs off.

Do not archive before:

1. PR comment triage is complete and approved,
2. all approved “address now” items are implemented,
3. PR title/body have been updated and verified (see above).

When archiving, ensure there are no leftover `temp/pr_comments/pr_<PR_NUMBER>*` folders/files outside `archive/` (move the entire folder, not individual files).

Also archive any generated diff artifacts for that PR by moving:

`temp/pr_diffs/pr_<PR_NUMBER>_*`

into:

`temp/pr_diffs/archive/`
