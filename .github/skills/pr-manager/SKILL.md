---
name: pr-manager
description: Repeatable workflow for creating, updating, managing, or editing pull requests (PRs) with accurate diff-driven metadata, triaging and responding to review comments, resolving review threads, fetching PR feedback, applying PR fixes, updating PR descriptions, and managing PR lifecycle. Use when working with GitHub pull requests, gh pr commands, PR review workflows, or GitHub GraphQL for PRs.
license: MIT
compatibility: GitHub pull requests, gh CLI, GitHub GraphQL API
triggers: pull request, PR, review comments, gh pr, review threads, create PR, update PR, PR metadata, PR title, PR description, triage comments, resolve threads
version: '1.0.0'
---

# PR Manager Skill

## Purpose

Enable AI agents to:

- Create PRs with accurate diff-driven title and body
- Triage PR review comments systematically
- Resolve PR review threads using GitHub GraphQL
- Apply approved fixes while maintaining PR metadata accuracy
- Maintain local-only roadmap and triage artifacts

## When to Use This Skill

**Always use this skill when:**

- Creating a new pull request
- Updating an existing PR title or description
- Fetching or triaging PR review comments
- Resolving PR review threads
- Replying to PR review comments
- Any workflow involving `gh pr` commands
- Working with GitHub GraphQL for pull requests

**User prompts that should trigger this skill:**

- "create a PR" / "create a pull request"
- "update the PR description" / "update PR metadata"
- "review the PR comments" / "check PR feedback"
- "respond to review feedback" / "reply to PR comments"
- "resolve the review threads" / "close review threads"
- "triage PR comments" / "fetch PR reviews"
- "apply PR fixes" / "implement PR feedback"

This skill is designed to comply with:

- `AGENTS.md` (local-only repo guidance)
- `temp/pr_comments/AGENT_INSTRUCTIONS.md` (local-only PR comment triage process)
- `temp/scripts/save_branch_diff.py` (generating diff summaries for PR metadata)
- `temp/scripts/fetch_pr_comments.py` (fetching PR review comments via GitHub API)

**IF YOU CAN'T FIND THESE FILES LOCALLY** they can be found in `.github/skills/pr-manager/references/` and/or `~/.codex/skills/pr-manager/references/`.

## Global guardrails (must follow)

- **Never work on `main`**. Always check branch first: `git branch --show-current`.
- **Before starting new work**, check for open PRs to avoid duplicating effort: `gh pr list --state open`.
- **Branch management**: if currently on `main`, stop and ask the user to create/check out a feature branch.
- **Never use heredocs** (e.g., `cat <<EOF`). Use editor file tools or `--body-file` with existing files.
- **Never use `git commit --no-verify`**.
- **Never run `git clean -x` / `git clean -fdx`** (destroys local-only `AGENTS.md`, `plans/`, `temp/`).
- **Never commit** anything under `plans/` or `temp/` (both are local-only/gitignored).
- Keep PRs **small and coherent** (aim <400 LOC).

## TodoWriter discipline (mandatory)

For every situation below, use the agent's **TodoWriter** tool to manage execution.

- At the start of a situation, create a todo list that expands the situation's steps into **substeps**.
  - Use a flat list with a consistent prefix so it's easy to track completion, e.g.:
    - `S1.1 Check branch`
    - `S1.2 Check gh auth`
    - `S1.3 List open PRs`
- Maintain strict state:
  - Exactly one item `in_progress` at a time.
  - Mark substeps `completed` immediately after finishing them.
  - Do not move to the next step until all substeps for the current step are `completed`.
- Before declaring a situation done, confirm **all** items for that situation are `completed`.

## Situation 1: Creating the PR (diff-driven title/body)

Goal: create a PR whose title/body accurately reflect the full diff vs `origin/main`, using the local helper script.

### Steps

0. **TodoWriter setup**

   - Create a TodoWriter checklist for Situation 1 (`S1.x`) with substeps for each step below.

1. **Pre-flight checks**

   - `git branch --show-current`
   - `gh auth status`
   - `gh pr list --state open`

2. **Ensure base is up to date**

   - `git fetch origin`

3. **Generate an authoritative diff summary**

   - Run: `/usr/bin/python3 temp/scripts/save_branch_diff.py --base origin/main --head HEAD`
   - This writes:
     - `temp/pr_diffs/<prefix>_full.diff`
     - `temp/pr_diffs/<prefix>_summary.md`

4. **Draft PR title/body from the summary**

   - Read the generated `*_summary.md` and derive:
     - **Title**: name the major addition(s) (e.g., “Terraform: add App Runner module”).
     - **Body**: follow `.github/pull_request_template.md` sections.
   - Write the PR body to a local file under `temp/`, e.g. `temp/pr_body_<branch>.md`.
     - Use editor file tools (no heredocs).
     - Avoid shell interpolation issues by using `--body-file`.

5. **Create the PR**

   - Ensure branch is pushed: `git push -u origin <branch>`
   - Create PR:
     - `gh pr create --base main --head <branch> --title "<TITLE>" --body-file temp/pr_body_<branch>.md`

6. **Verify PR metadata**
   - `gh pr view <PR_NUMBER> --json title,body`
   - Confirm the title/body explicitly mention the biggest additions shown in the diff summary.

## Situation 2: Reviewing PR comments (push → fetch → if no comments, sleep 600s → fetch → triage)

Goal: after pushing a PR, wait briefly for reviews/checks to land, then fetch all PR review comments into a single file and triage with the user.

### Steps

0. **TodoWriter setup**

   - Create a TodoWriter checklist for Situation 2 (`S2.x`) with substeps for each step below.

1. **Push current changes**

   - `git status --porcelain` (confirm only intended files)
   - `git push`

2. **Fetch PR comments (sleep 600s if none exist)**

   - If the comments exist, proceed to step 3.
   - if no comments exist yet, sleep for 600s, then proceed to step 3.

3. **Fetch PR comments (must follow local instructions)**

   - Read and comply with `temp/pr_comments/AGENT_INSTRUCTIONS.md`.
   - Run:
     - `/usr/bin/python3 temp/scripts/fetch_pr_comments.py <PR_NUMBER> --out temp/pr_comments`
   - Immediately rename the generated file:
     - `mv temp/pr_comments/pr_<PR_NUMBER>/comments.md temp/pr_comments/pr_<PR_NUMBER>/pr_comments.md`
   - Ensure the folder contains **only** `pr_comments.md`.

4. **Triage (in the file)**

   - Open `temp/pr_comments/pr_<PR_NUMBER>/pr_comments.md`.
   - Append a `## Triage` section at the bottom, one bullet per comment:
     - `- <short label> — <decision> — <one sentence why>`
   - Decisions must be one of:
     - **address now** (clear correctness/security/high-value low-risk DX)
     - **defer** (needs design decision / broader refactor)
     - **ignore** (low-value or incorrect)
     - **already fixed**
   - If **defer**, include where it will be recorded in `plans/ROADMAP.md` (local-only).

5. **Mandatory stop point**
   - After creating `pr_comments.md` + triage:
     - **Do not change repository code**.
     - Ask the user which items to address now vs defer.

## Situation 3: After triage approval (apply fixes + push + refresh PR title/body)

Goal: implement only the approved “address now” items, then ensure PR metadata still matches the diff.

### Steps

0. **TodoWriter setup**

   - Create a TodoWriter checklist for Situation 3 (`S3.x`) with substeps for each step below.

1. **Record deferrals (local-only)**

   - If the user approved deferring items, record them in `plans/ROADMAP.md`.
   - Confirm `plans/` changes stay uncommitted.

2. **Implement approved fixes**

   - Make minimal, targeted changes.
   - Run the most relevant validations/tests for touched areas.

3. **Commit and push**

   - `git status --porcelain` (confirm only intended files)
   - `git add <paths>`
   - `git commit -m "<clear message>"`
   - `git push`

4. **Update PR title/body if needed**

   - Re-run: `/usr/bin/python3 temp/scripts/save_branch_diff.py --base origin/main --head HEAD`
   - If the diff scope changed materially (new module, wiring, security behavior), update PR body:
     - Edit the local body file under `temp/`.
     - `gh pr edit <PR_NUMBER> --title "<TITLE>"` (if needed)
     - `gh pr edit <PR_NUMBER> --body-file <TEMP_BODY_FILE>`

5. **Verify PR metadata (mandatory)**

   - `gh pr view <PR_NUMBER> --json title,body`
   - Confirm it matches the diff summary.

6. **Optional (after user sign-off): archive triage artifacts**
   - Only after:
     - triage is complete and user-approved,
     - all approved “address now” items are implemented,
     - PR title/body verified and user agrees.
   - Move:
     - `temp/pr_comments/pr_<PR_NUMBER>/` → `temp/pr_comments/archive/pr_<PR_NUMBER>/`
     - `temp/pr_diffs/pr_<PR_NUMBER>_*` → `temp/pr_diffs/archive/`

## Situation 4: Reply to review comments + resolve threads (GraphQL)

Goal: once approved “address now” items are implemented and pushed (or explicitly deferred), reply on the PR with the triage outcome and resolve the corresponding review threads.

### Steps

0. **TodoWriter setup**

    - Create a TodoWriter checklist for Situation 4 (`S4.x`) with substeps for each step below.

1. **Fetch thread + comment IDs (GraphQL query)**

    - Review-thread resolution and comment replies require GitHub GraphQL node IDs.
    - Use `-F number=<PR_NUMBER>` so the PR number is passed as an Int: - Fetch the PR id + thread ids + comment ids:

             `gh api graphql \

      -f query='query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){pullRequest(number:$number){id reviewThreads(first:100){nodes{id isResolved comments(first:50){nodes{id databaseId body author{login}}}}}}}}' \
      -f owner='<OWNER>' \
      -f name='<REPO>' \
      -F number=<PR_NUMBER>`

    - Record (copy) the relevant IDs:
      - `pullRequest.id` (example: `PR_kwDO…`)
      - Each `reviewThreads.nodes[].id` (example: `PRRT_kwDO…`)
      - Each `comments.nodes[].id` (example: `PRRC_kwDO…`)

2. **Reply to an inline review comment (GraphQL mutation)**

    - Use `addPullRequestReviewComment` with `inReplyTo` set to the **comment node id** you’re replying to:

           `gh api graphql \

      -f query='mutation($pr:ID!,$body:String!,$inReplyTo:ID!){addPullRequestReviewComment(input:{pullRequestId:$pr, body:$body, inReplyTo:$inReplyTo}){comment{url}}}' \
      -f pr='<PULL_REQUEST_NODE_ID>' \
      -f inReplyTo='<REVIEW_COMMENT_NODE_ID>' \
      -f body='Triage: <address now|defer|ignore|already fixed>. <1–2 sentences explaining what we did or why we deferred.>'`

    - Keep replies short, and match the decision recorded in `temp/pr_comments/pr_<PR_NUMBER>/pr_comments.md`.

3. **Resolve the review thread (GraphQL mutation)**

    - After replying (and pushing any “address now” fixes), resolve the thread:

           `gh api graphql \

      -f query='mutation($threadId:ID!){resolveReviewThread(input:{threadId:$threadId}){thread{id isResolved}}}' \
      -f threadId='<REVIEW_THREAD_NODE_ID>'`

4. **Verify threads are resolved (GraphQL query)**

    - Re-run a minimal query to confirm `isResolved: true` for all threads:

           `gh api graphql \

      -f query='query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){pullRequest(number:$number){reviewThreads(first:100){nodes{id isResolved}}}}}' \
      -f owner='<OWNER>' \
      -f name='<REPO>' \
      -F number=<PR_NUMBER>`

## Notes

- Prefer `--body-file` for PR text to avoid shell interpolation (especially backticks).
- Never commit Terraform init artifacts (e.g., `.terraform/`, `.terraform.lock.hcl`) unless the repo explicitly expects them.

## Situation 5: Submit PR review summary (comment-only) + stop on failure

Goal: post a single comment-style PR review summarizing what changed (or what was deferred) after implementing fixes and resolving threads.

Notes:

- This is **not** an approval. Use a comment-only review so it works even when approvals are restricted.
- Depending on repository permissions and whether you are the PR author, GitHub may reject submitting a review.

### Steps

0. **TodoWriter setup**

   - Create a TodoWriter checklist for Situation 5 (`S5.x`) with substeps for each step below.

1. **Write the review body (local file)**

   - Create `temp/pr_review_<PR_NUMBER>.md` using editor tools.
   - Keep it short (3–8 lines): what changed, what was deferred, what to re-check.

2. **Submit the review comment**

   - Run:
     - `gh pr review <PR_NUMBER> --comment --body-file temp/pr_review_<PR_NUMBER>.md`

3. **Stop point (mandatory on failure)**
   - If the command fails for any reason (auth, permissions, author-review restriction):
     - **Do not attempt alternative APIs or repeated retries.**
     - **Stop and wait for the user** to decide the next action (e.g., post a normal PR comment instead, or have a maintainer submit the review).

## Situation 6: Update local roadmap with completed work (local-only)

Goal: keep the local migration roadmap in sync with the work you completed.

Notes:

- The roadmap is local-only and gitignored (commonly `plans/ROADMAP.md`). Some developers may keep a separate local copy under `temp/`.
- **Never commit** roadmap updates.

### Steps

0. **TodoWriter setup**

   - Create a TodoWriter checklist for Situation 6 (`S6.x`) with substeps for each step below.

1. **Update the roadmap entry**

   - If a PR was created: add the PR number/link and set Status (e.g., `in review`).
   - If the PR was merged: mark the task `[x]` and set Status to `merged`.

2. **Verify it stays uncommitted**
   - Run `git status --porcelain` and confirm no `plans/` or `temp/` files are staged/committed.
