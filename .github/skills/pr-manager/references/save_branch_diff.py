#!/usr/bin/env python3
"""Save a full diff and summary between origin/main and the current branch.

Primary goal: prevent under-describing a PR.

Use the generated summary to update the PR title/body so they reflect the *actual* diff vs
`origin/main` (especially when the branch adds entire modules/directories or large wiring).

Local-only convenience script (temp/ is gitignored).

Outputs:
- temp/pr_diffs/<prefix>_full.diff
- temp/pr_diffs/<prefix>_summary.md

Where <prefix> is pr_<number> if a PR can be detected for the current branch,
otherwise branch_<branchname>.

Usage:
  /usr/bin/python3 temp/scripts/save_branch_diff.py
  /usr/bin/python3 temp/scripts/save_branch_diff.py --base origin/main --head HEAD
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> str:
    result = subprocess.run(cmd, cwd=str(cwd), check=False, text=True, capture_output=True)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        raise RuntimeError(
            "Command failed:\n"
            f"  {' '.join(cmd)}\n\n"
            f"stdout:\n{stdout}\n\n"
            f"stderr:\n{stderr}\n"
        )
    return result.stdout


def repo_root(start: Path) -> Path:
    out = run(["git", "rev-parse", "--show-toplevel"], cwd=start).strip()
    return Path(out)


def safe_slug(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-") or "unknown"


def try_get_pr_info(root: Path) -> dict[str, str] | None:
    # `gh pr view` (no number) uses the current branch when possible.
    try:
        raw = run(
            ["gh", "pr", "view", "--json", "number,title,url,baseRefName,headRefName"],
            cwd=root,
        ).strip()
    except Exception:
        return None

    # Minimal JSON parsing to avoid extra deps.
    # Expect keys we asked for; if not present, treat as no PR.
    if not raw.startswith("{"):
        return None

    def pick(key: str) -> str | None:
        match = re.search(rf'"{re.escape(key)}"\s*:\s*"([^"]*)"', raw)
        return match.group(1) if match else None

    number_match = re.search(r"\"number\"\s*:\s*(\d+)", raw)
    if not number_match:
        return None

    return {
        "number": number_match.group(1),
        "title": pick("title") or "",
        "url": pick("url") or "",
        "baseRefName": pick("baseRefName") or "",
        "headRefName": pick("headRefName") or "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Save full git diff and summary for current branch"
    )
    parser.add_argument("--base", default="origin/main", help="Base ref (default: origin/main)")
    parser.add_argument("--head", default="HEAD", help="Head ref (default: HEAD)")
    parser.add_argument(
        "--out",
        default="temp/pr_diffs",
        help="Output directory (default: temp/pr_diffs)",
    )
    args = parser.parse_args()

    root = repo_root(Path.cwd())
    out_dir = (root / args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root).strip()
    head_sha = run(["git", "rev-parse", args.head], cwd=root).strip()

    pr_info = try_get_pr_info(root)
    if pr_info and pr_info.get("number"):
        prefix = f"pr_{pr_info['number']}"
    else:
        prefix = f"branch_{safe_slug(branch)}"

    diff_path = out_dir / f"{prefix}_full.diff"
    summary_path = out_dir / f"{prefix}_summary.md"

    diff = run(["git", "diff", "--binary", f"{args.base}...{args.head}"], cwd=root)
    diff_path.write_text(diff, encoding="utf-8")

    name_status = run(
        ["git", "diff", "--name-status", f"{args.base}...{args.head}"], cwd=root
    ).strip()
    stat = run(["git", "diff", "--stat", f"{args.base}...{args.head}"], cwd=root).strip()
    numstat = run(["git", "diff", "--numstat", f"{args.base}...{args.head}"], cwd=root).strip()

    # If we have a PR, try to include gh's per-file summary fields (when available).
    gh_files_summary = ""
    if pr_info and pr_info.get("number"):
        try:
            gh_files = run(
                [
                    "gh",
                    "pr",
                    "view",
                    pr_info["number"],
                    "--json",
                    "files",
                    "--jq",
                    r'.files[] | \(.path) + " — +" + (\(.additions|tostring))'
                    r' + "/-" + (\(.deletions|tostring))',
                ],
                cwd=root,
            ).strip()
            if gh_files:
                gh_files_summary = gh_files
        except Exception:
            gh_files_summary = ""

    now = dt.datetime.now(tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines: list[str] = []
    lines.append(f"# Diff summary ({prefix})")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "Use this file to ensure the PR title/body match the full diff vs the base branch."
    )
    lines.append(
        "If this summary shows whole new modules/directories, "
        "the PR title/body must mention them explicitly."
    )
    lines.append("")
    lines.append("PR update checklist:")
    lines.append("- Re-read the diffstat and the name-status list")
    lines.append("- Ensure the PR title/body explicitly mention the biggest additions")
    lines.append("- After editing the PR, verify via: `gh pr view <N> --json title,body`")
    lines.append("")
    lines.append(f"Generated: {now}")
    lines.append(f"Base: {args.base}")
    lines.append(f"Head: {args.head} ({head_sha})")
    lines.append(f"Branch: {branch}")
    if pr_info:
        lines.append(f"PR: #{pr_info.get('number', '')} {pr_info.get('url', '')}")
        if pr_info.get("title"):
            lines.append(f"PR Title: {pr_info['title']}")
    lines.append("")

    lines.append("## Files changed (name-status)")
    lines.append("")
    lines.append("```text")
    lines.append(name_status)
    lines.append("```")
    lines.append("")

    lines.append("## Files changed (diffstat)")
    lines.append("")
    lines.append("```text")
    lines.append(stat)
    lines.append("```")
    lines.append("")

    lines.append("## Per-file line counts (numstat)")
    lines.append("")
    lines.append("```text")
    lines.append(numstat)
    lines.append("```")
    lines.append("")

    if gh_files_summary:
        lines.append("## GitHub PR file summary")
        lines.append("")
        lines.append("```text")
        lines.append(gh_files_summary)
        lines.append("```")
        lines.append("")

    lines.append("## Raw diff")
    lines.append("")
    lines.append(f"Saved to: {diff_path.relative_to(root)}")

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(str(diff_path))
    print(str(summary_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
