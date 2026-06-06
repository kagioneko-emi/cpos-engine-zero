from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .base import sensor_event

_CREDENTIAL_IN_URL = re.compile(r"(https?://)([^/@\s]+)@", re.IGNORECASE)
_TOKENISH = re.compile(r"(gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|x-access-token:[^/@\s]+)", re.IGNORECASE)


def _run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)


def redact_remote_url(url: str | None) -> tuple[str | None, bool]:
    if not url:
        return None, False
    credential_risk = False
    redacted = url.strip()
    if _CREDENTIAL_IN_URL.search(redacted):
        credential_risk = True
        redacted = _CREDENTIAL_IN_URL.sub(r"\1<redacted>@", redacted)
    if _TOKENISH.search(redacted):
        credential_risk = True
        redacted = _TOKENISH.sub("<redacted>", redacted)
    return redacted, credential_risk


def parse_branch_status(line: str) -> dict[str, Any]:
    info: dict[str, Any] = {"branch": None, "upstream": None, "ahead": 0, "behind": 0}
    if not line.startswith("## "):
        return info
    body = line[3:]
    if "..." in body:
        branch, rest = body.split("...", 1)
        info["branch"] = branch.strip() or None
        upstream = rest.split(" [", 1)[0].strip()
        info["upstream"] = upstream or None
    else:
        info["branch"] = body.split(" ", 1)[0].strip() or None
    ahead_match = re.search(r"ahead (\d+)", line)
    behind_match = re.search(r"behind (\d+)", line)
    if ahead_match:
        info["ahead"] = int(ahead_match.group(1))
    if behind_match:
        info["behind"] = int(behind_match.group(1))
    return info


def observe_git_repo(repo: str | Path = ".", remote: str = "origin") -> dict[str, Any]:
    repo_path = Path(repo).resolve()
    status = _run_git(repo_path, ["status", "--short", "--branch"])
    remote_result = _run_git(repo_path, ["remote", "get-url", remote])
    head_result = _run_git(repo_path, ["rev-parse", "--short", "HEAD"])

    if status.returncode != 0:
        return sensor_event(
            source="git",
            event_type="git_observation_failed",
            target=repo_path,
            summary="git status observation failed",
            risk="medium",
            confidence=0.7,
            source_of_truth=["git status --short --branch"],
            requires_human_review=False,
            suggested_next_action="review_git_repository_path",
            metadata={"returncode": status.returncode, "stderr_digest_only": True},
        )

    status_lines = [line for line in status.stdout.splitlines() if line.strip()]
    branch_line = status_lines[0] if status_lines and status_lines[0].startswith("## ") else ""
    changed_lines = [line for line in status_lines if not line.startswith("## ")]
    branch = parse_branch_status(branch_line)
    redacted_remote, remote_secret_risk = redact_remote_url(remote_result.stdout.strip() if remote_result.returncode == 0 else None)
    head_short = head_result.stdout.strip() if head_result.returncode == 0 else None

    event_type = "git_clean"
    risk = "low"
    requires_review = False
    suggested = "continue_observing"
    if remote_secret_risk:
        event_type = "remote_secret_risk_detected"
        risk = "high"
        requires_review = True
        suggested = "rotate_or_remove_credential_from_remote"
    elif branch.get("behind", 0):
        event_type = "git_behind"
        risk = "medium"
        suggested = "review_before_sync"
    elif branch.get("ahead", 0):
        event_type = "git_ahead"
        risk = "medium"
        suggested = "ask_before_push"
    elif changed_lines:
        event_type = "git_dirty"
        risk = "medium"
        suggested = "review_changes_before_action"

    if event_type == "git_clean":
        summary = f"{branch.get('branch') or 'repo'} clean and origin synced"
    elif event_type == "git_dirty":
        summary = f"repo has {len(changed_lines)} changed status line(s)"
    elif event_type == "git_ahead":
        summary = f"{branch.get('branch') or 'branch'} is ahead by {branch.get('ahead', 0)} commit(s)"
    elif event_type == "git_behind":
        summary = f"{branch.get('branch') or 'branch'} is behind by {branch.get('behind', 0)} commit(s)"
    else:
        summary = "remote URL may contain credential material and was redacted"

    return sensor_event(
        source="git",
        event_type=event_type,
        target=repo_path,
        summary=summary,
        risk=risk,
        confidence=0.95,
        source_of_truth=["git status --short --branch", f"git remote get-url {remote}"],
        requires_human_review=requires_review,
        suggested_next_action=suggested,
        metadata={
            "branch": branch.get("branch"),
            "upstream": branch.get("upstream"),
            "ahead": branch.get("ahead", 0),
            "behind": branch.get("behind", 0),
            "changed_status_count": len(changed_lines),
            "status_codes": sorted({line[:2] for line in changed_lines}),
            "remote": remote,
            "remote_url_redacted": redacted_remote,
            "remote_secret_risk_detected": remote_secret_risk,
            "head_short": head_short,
            "raw_status_stored": False,
            "raw_diff_stored": False,
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only metadata-only git sensor.")
    parser.add_argument("--repo", default=".", help="Repository path to observe.")
    parser.add_argument("--remote", default="origin", help="Remote name to inspect.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    event = observe_git_repo(args.repo, remote=args.remote)
    if args.json:
        print(json.dumps(event, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{event['event_type']}: {event['summary']}")


if __name__ == "__main__":
    main()
