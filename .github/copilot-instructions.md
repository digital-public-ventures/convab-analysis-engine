# AGENT INSTRUCTIONS

## Safety rules (workspace hygiene)

- **Always assume changes you didn't make were made by the user**; never undo/revert them without explicit permission.
- Never delete untracked files without explicit permission.
- Never delete the `temp/` or `plans/` directories.

## Terminal Command Best Practices

### CRITICAL: ALWAYS use built-in file creation/editing capabilities like `create_file` NEVER use terminal commands like heredoc for file creation

**Never use `cat > filename << 'EOF' ... EOF` to create scripts or files in the terminal.** Instead use your built-in file creation and editing capabilities FOR ALL FILE CREATION TASKS. Trying to write multi-line files via terminal commands is error-prone and unreliable.

## Critical: Terminal Usage

**NEVER** use heredocs (e.g., `cat <<EOF ... EOF`, `python -c '...'`) in any scripts or commands. They are unreliable in this environment. Instead, **ALWAYS** use your built-in file creation and editing tools. This goes for writing files as well as executing multi-line commands in the terminal.

**ALWAYS** create a script file for any complex multi-line terminal commands, then run that script. This ensures reproducibility and avoids issues with heredocs.

**NEVER** destroy gitignored files. In particular, **NEVER** run `git clean -x` (or `git clean -fdx`) since it deletes ignored local-only files like `AGENTS.md`, `plans/`, and `temp/` artifacts.

**NEVER** run a command in a terminal that has an active process running.

## Critical: Code Writing Requirements

**NEVER** use `git commit --no-verify`

**NEVER** remove any paths from `.gitignore` under any circumstances.

**Local-only planning (DO NOT COMMIT):**

- `plans/ROADMAP.md` and all other files under `plans/` are intentionally **untracked** (gitignored).
- Each developer uses these files locally to plan work. They must **not be pushed** and must **not vary by branch**.
- Do not include `plans/` file changes in commits or PRs.

`temp/` is also local-only (gitignored) and may be used for scratch work.

1. **Before any file changes**: Check current branch (`git branch --show-current`) - never work on `main`. If the user explicitly instructs you to work on the current branch, even if it's `main`, proceed as instructed.
2. **Before starting new work**: Review open PRs (`gh pr list --state open`) to avoid duplication
3. **Create feature branch**: Ensure you are on a new and well-named branch for your task before making any changes
4. **Commit regularly!**: Write clear, concise commit messages; one logical change per commit.
5. **Keep changes PR-sized**: One coherent application change per PR, <400 lines ideally.
6. **When complete**: Review the diff (actual code diffs for each file changed) between your branch and origin main, draft a PR whose title and description follow following `.github/pull_request_template.md` then mark it as ready and request review.

## GitIgnore

**NEVER** remove or modify entries in `.gitignore` without pausing for explicit permission from the user. If you can't pause and ask, always leave `.gitignore` unchanged and stop all tasks.

## Workflow

1. **Before starting work**: Check your local `plans/ROADMAP.md` for the next incomplete task
2. **When starting a task**: Update your local roadmap row with your branch name and mark `[~]` in progress
3. **When PR is created**: Record the PR number/link in your local roadmap
4. **When PR is merged**: Mark the task `[x]` done in your local roadmap
5. **Always work in order**: Tasks have dependencies; complete earlier tasks first

**Roadmap format:**

```markdown
| #   | Task                  | Branch            | PR   | Status      |
| --- | --------------------- | ----------------- | ---- | ----------- |
| 1.1 | [~] Create Dockerfile | feat/docker-setup | #123 | `in review` |
```

A task is **only complete** when its PR status is **merged**. Maintain your local roadmap as part of your workflow (but do not commit it).

## PR Comment Review

If the user asks you to "review the comments for a PR", read `.github/pr-manager/SKILL.md` and follow those instructions.
