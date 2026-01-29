#!/usr/bin/env python3

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class Repo:
    owner: str
    name: str


def _run(cmd: list[str]) -> str:
    result = subprocess.run(
        cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    return result.stdout


def _detect_repo_from_git_remote() -> Repo:
    # Supports common remotes:
    # - https://github.com/owner/repo.git
    # - git@github.com:owner/repo.git
    remote = _run(["git", "config", "--get", "remote.origin.url"]).strip()
    if not remote:
        raise SystemExit("Could not detect repo from git remote.origin.url; pass --repo owner/name")

    https = re.match(r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$", remote)
    if https:
        return Repo(owner=https.group("owner"), name=https.group("repo"))

    ssh = re.match(r"^git@github\.com:(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$", remote)
    if ssh:
        return Repo(owner=ssh.group("owner"), name=ssh.group("repo"))

    raise SystemExit(f"Unrecognized GitHub remote format: {remote!r}; pass --repo owner/name")


def _gh_api_json(endpoint: str) -> Any:
    # Use --paginate to fetch all pages.
    out = _run(["gh", "api", endpoint, "--paginate"])
    try:
        return json.loads(out) if out.strip() else []
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse JSON from `gh api {endpoint}`: {exc}")


def _write_markdown(
    path: Path,
    pr_number: int,
    repo: Repo,
    issue_comments: list[dict[str, Any]],
    review_comments: list[dict[str, Any]],
) -> None:
    def fmt_dt(value: Optional[str]) -> str:
        if not value:
            return ""
        try:
            # GitHub returns ISO-8601.
            return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
        except Exception:
            return value

    lines: list[str] = []
    lines.append(f"# PR #{pr_number} comments ({repo.owner}/{repo.name})")
    lines.append("")
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append("")

    lines.append("## Issue comments (PR conversation)")
    lines.append("")
    lines.append(f"Count: {len(issue_comments)}")
    lines.append("")
    for c in issue_comments:
        user = (c.get("user") or {}).get("login") or "unknown"
        created = fmt_dt(c.get("created_at"))
        body = (c.get("body") or "").rstrip()
        url = c.get("html_url") or ""
        lines.append(f"### {user} — {created}")
        if url:
            lines.append(f"{url}")
        lines.append("")
        lines.append(body)
        lines.append("")

    lines.append("## Review comments (inline)")
    lines.append("")
    lines.append(f"Count: {len(review_comments)}")
    lines.append("")
    for c in review_comments:
        user = (c.get("user") or {}).get("login") or "unknown"
        created = fmt_dt(c.get("created_at"))
        path_ = c.get("path") or ""
        line = c.get("line")
        side = c.get("side")
        body = (c.get("body") or "").rstrip()
        url = c.get("html_url") or ""

        loc = path_
        if line is not None:
            loc = f"{loc}:{line}"
        if side:
            loc = f"{loc} ({side})"

        lines.append(f"### {user} — {created}")
        if loc.strip(":"):
            lines.append(f"Location: {loc}")
        if url:
            lines.append(f"{url}")
        lines.append("")
        lines.append(body)
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _cleanup_output_dir(output_dir: Path, keep_filename: str = "comments.md") -> None:
    # Best-effort cleanup: remove any previously generated artifacts except the markdown.
    # Only deletes regular files directly under output_dir.
    for child in output_dir.iterdir():
        if not child.is_file():
            continue
        if child.name == keep_filename:
            continue
        child.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch GitHub PR issue comments and inline review comments via `gh`, "
            "and write them under temp/pr_comments/pr_<N>."
        )
    )
    parser.add_argument("pr", type=int, help="Pull request number (e.g., 12)")
    parser.add_argument(
        "--repo",
        help="Repository in owner/name form (default: inferred from git remote.origin.url)",
        default=None,
    )
    parser.add_argument(
        "--out",
        help="Output root directory (default: temp/pr_comments)",
        default="temp/pr_comments",
    )

    args = parser.parse_args()

    repo: Repo
    if args.repo:
        if "/" not in args.repo:
            raise SystemExit("--repo must be in owner/name form")
        owner, name = args.repo.split("/", 1)
        repo = Repo(owner=owner, name=name)
    else:
        repo = _detect_repo_from_git_remote()

    pr_number = args.pr
    out_root = Path(args.out)
    out_dir = out_root / f"pr_{pr_number}"
    out_dir.mkdir(parents=True, exist_ok=True)

    issue_comments = _gh_api_json(f"repos/{repo.owner}/{repo.name}/issues/{pr_number}/comments")
    review_comments = _gh_api_json(f"repos/{repo.owner}/{repo.name}/pulls/{pr_number}/comments")

    _write_markdown(out_dir / "comments.md", pr_number, repo, issue_comments, review_comments)
    _cleanup_output_dir(out_dir, keep_filename="comments.md")

    print(json.dumps({"output_dir": str(out_dir), "comments_md": str(out_dir / "comments.md")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
