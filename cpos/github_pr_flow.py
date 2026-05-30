from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .human_escalation import review_escalation_decision
from .task_tape import TaskTapeStore

REVIEW_TYPE = "github_pr_dry_run"
TERMINAL_EVENTS = {"github_pr_dry_run_approved", "github_pr_dry_run_rejected"}
SECRETISH_KEYS = re.compile(r"(token|secret|password|passwd|api[_-]?key|private[_-]?key|credential)", re.I)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _slug(value: str, *, max_len: int = 48) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower()).strip("-._")
    return (slug or "agent-work")[:max_len]


def _secret_like_paths(obj: Any, prefix: str = "request") -> list[str]:
    paths: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}"
            if SECRETISH_KEYS.search(str(key)) and value not in (None, ""):
                paths.append(path)
            paths.extend(_secret_like_paths(value, path))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            paths.extend(_secret_like_paths(value, f"{prefix}[{idx}]"))
    return paths


def create_github_pr_dry_run(
    store: TaskTapeStore,
    *,
    repo: str,
    title: str,
    issue_url: str | None = None,
    issue_number: int | None = None,
    summary: str | None = None,
    files: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    actor: str = "GitHubPRPlanner",
    base_branch: str = "main",
    dry_run: bool = True,
) -> dict[str, Any]:
    """Create a review-gated GitHub PR plan without touching git/GitHub.

    It does not create branches, commits, pushes, issues, or pull requests. It only
    records metadata and a human approval gate in Task Tape.
    """
    if not dry_run:
        return {"ok": False, "error": "real_github_pr_creation_disabled", "execute_automatically": False}
    if not repo or "/" not in repo:
        return {"ok": False, "error": "repo_owner_name_required", "execute_automatically": False}
    if not title:
        return {"ok": False, "error": "title_required", "execute_automatically": False}
    request = {
        "repo": repo,
        "title": title,
        "issue_url": issue_url,
        "issue_number": issue_number,
        "summary": summary,
        "files": files or [],
        "metadata": metadata or {},
        "actor": actor,
        "base_branch": base_branch,
    }
    blocked_paths = _secret_like_paths(request)
    if blocked_paths:
        return {"ok": False, "error": "secret_like_request_blocked", "blocked_paths": blocked_paths, "execute_automatically": False}

    issue_part = f"issue-{issue_number}" if issue_number is not None else "manual"
    branch_name = f"agent/{issue_part}-{_slug(title)}"
    safe_files = sorted({str(path) for path in (files or []) if str(path).strip()})
    plan = {
        "schema": "cpos.github_pr_dry_run.v1",
        "repo": repo,
        "title": title,
        "issue_url": issue_url,
        "issue_number": issue_number,
        "summary_sha256": _digest(summary or ""),
        "summary_size_bytes": len((summary or "").encode("utf-8")),
        "summary_values_stored": False,
        "candidate_files": safe_files,
        "metadata_keys": sorted(str(key) for key in (metadata or {}).keys()),
        "metadata_sha256": _digest(metadata or {}),
        "metadata_values_stored": False,
        "base_branch": base_branch,
        "proposed_branch": branch_name,
        "proposed_commit_message": f"fix: {_slug(title, max_len=72)}",
        "proposed_pr_title": title,
        "proposed_pr_body_sections": ["Summary", "Validation", "Security", "Rollback"],
        "diff_generated": False,
        "branch_created": False,
        "commit_created": False,
        "pushed": False,
        "pr_created": False,
        "execute_automatically": False,
        "requires_human_approval": True,
        "guardrails": [
            "no raw secrets in request or PR body",
            "no branch/commit/push/PR creation during dry-run",
            "diff generation must be reviewed before real PR creation",
            "use HTTPS GitHub API or gh auth; never embed tokens in remote URLs",
        ],
    }
    plan["plan_sha256"] = _digest(plan)
    human_escalation = review_escalation_decision(
        review_type=REVIEW_TYPE,
        summary=f"GitHub publish planning for {repo}: {title}",
        confidence=0.9,
        risk="high",
        user_confirmation_required=True,
    )
    target = f"github://{repo}/pr-dry-run/{issue_part}"
    task_id = store.create_task(
        target=target,
        action="github_pr_dry_run_request",
        payload={
            "review_type": REVIEW_TYPE,
            "repo": repo,
            "issue_number": issue_number,
            "plan_sha256": plan["plan_sha256"],
            "human_escalation": human_escalation,
            "actor": actor,
        },
    )
    event = store.append_event(
        task_id=task_id,
        event="review_required",
        target=target,
        status="pending_review",
        payload={"review_type": REVIEW_TYPE, "plan": plan, "human_escalation": human_escalation, "actor": actor},
    )
    return {"ok": True, "task_id": task_id, "status": "pending_review", "review": event.to_dict(), "plan": plan, "execute_automatically": False}


def pending_github_pr_reviews(store: TaskTapeStore) -> list[dict[str, Any]]:
    terminal_task_ids = {event.task_id for event in store.events() if event.event in TERMINAL_EVENTS and event.payload.get("review_type") == REVIEW_TYPE}
    rows = []
    for event in store.events():
        if event.event == "review_required" and event.payload.get("review_type") == REVIEW_TYPE and event.task_id not in terminal_task_ids:
            rows.append(event.to_dict())
    return rows


def approve_github_pr_dry_run(store: TaskTapeStore, task_id: str, *, approver: str = "GitHubPRReviewer", reason: str | None = None, confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        return {"ok": False, "error": "confirm_required", "task_id": task_id}
    review = next((row for row in pending_github_pr_reviews(store) if row.get("task_id") == task_id), None)
    if review is None:
        return {"ok": False, "error": "pending_github_pr_review_not_found", "task_id": task_id}
    plan = (review.get("payload") or {}).get("plan") or {}
    event = store.append_event(
        task_id=task_id,
        event="github_pr_dry_run_approved",
        target=review.get("target"),
        status="approved_dry_run_only",
        payload={
            "review_type": REVIEW_TYPE,
            "approved_by": approver,
            "reason": reason,
            "plan_sha256": plan.get("plan_sha256"),
            "next_step": "generate_diff_review_only",
            "branch_created": False,
            "commit_created": False,
            "pushed": False,
            "pr_created": False,
            "execute_automatically": False,
        },
    )
    return {"ok": True, "task_id": task_id, "status": "approved_dry_run_only", "event": event.to_dict(), "pr_created": False, "execute_automatically": False}


def reject_github_pr_dry_run(store: TaskTapeStore, task_id: str, *, reason: str = "manual_reject") -> dict[str, Any]:
    review = next((row for row in pending_github_pr_reviews(store) if row.get("task_id") == task_id), None)
    if review is None:
        return {"ok": False, "error": "pending_github_pr_review_not_found", "task_id": task_id}
    event = store.append_event(
        task_id=task_id,
        event="github_pr_dry_run_rejected",
        target=review.get("target"),
        status="rejected",
        payload={"review_type": REVIEW_TYPE, "reason": reason, "pr_created": False, "execute_automatically": False},
    )
    return {"ok": True, "task_id": task_id, "status": "rejected", "event": event.to_dict(), "pr_created": False, "execute_automatically": False}
