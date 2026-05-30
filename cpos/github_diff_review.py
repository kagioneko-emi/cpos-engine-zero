from __future__ import annotations

import hashlib
import json
from typing import Any

from .github_pr_flow import REVIEW_TYPE as PR_REVIEW_TYPE, _digest, _secret_like_paths
from .human_escalation import review_escalation_decision
from .task_tape import TaskTapeStore

REVIEW_TYPE = "github_diff_review"
TERMINAL_EVENTS = {"github_diff_review_approved", "github_diff_review_rejected"}


def _approved_pr_plan(store: TaskTapeStore, task_id: str) -> dict[str, Any] | None:
    events = store.events_for_task(task_id)
    review = next((event for event in events if event.event == "review_required" and event.payload.get("review_type") == PR_REVIEW_TYPE), None)
    approved = next((event for event in events if event.event == "github_pr_dry_run_approved" and event.payload.get("review_type") == PR_REVIEW_TYPE), None)
    if review is None or approved is None:
        return None
    return (review.payload or {}).get("plan") or {}


def pending_github_diff_reviews(store: TaskTapeStore) -> list[dict[str, Any]]:
    terminal_task_ids = {event.task_id for event in store.events() if event.event in TERMINAL_EVENTS and event.payload.get("review_type") == REVIEW_TYPE}
    return [
        event.to_dict()
        for event in store.events()
        if event.event == "review_required" and event.payload.get("review_type") == REVIEW_TYPE and event.task_id not in terminal_task_ids
    ]


def create_github_diff_review(
    store: TaskTapeStore,
    *,
    source_task_id: str,
    diff_text: str | None = None,
    changed_files: list[str] | None = None,
    validation_commands: list[str] | None = None,
    actor: str = "GitHubDiffPlanner",
    dry_run: bool = True,
) -> dict[str, Any]:
    """Create a metadata-only diff review from an approved PR dry-run plan.

    It never writes files, applies patches, creates commits, pushes, or opens PRs.
    Raw diff text is not stored; only hash, byte size, and line counters are kept.
    """
    if not dry_run:
        return {"ok": False, "error": "real_diff_application_disabled", "execute_automatically": False}
    plan = _approved_pr_plan(store, source_task_id)
    if plan is None:
        return {"ok": False, "error": "approved_pr_dry_run_required", "source_task_id": source_task_id, "execute_automatically": False}
    request = {
        "source_task_id": source_task_id,
        "changed_files": changed_files or [],
        "validation_commands": validation_commands or [],
        "actor": actor,
    }
    blocked_paths = _secret_like_paths(request)
    if blocked_paths:
        return {"ok": False, "error": "secret_like_request_blocked", "blocked_paths": blocked_paths, "execute_automatically": False}

    diff_text = diff_text or ""
    added_lines = sum(1 for line in diff_text.splitlines() if line.startswith("+") and not line.startswith("+++"))
    removed_lines = sum(1 for line in diff_text.splitlines() if line.startswith("-") and not line.startswith("---"))
    safe_changed_files = sorted({str(path) for path in (changed_files or plan.get("candidate_files") or []) if str(path).strip()})
    safe_commands = [str(command) for command in (validation_commands or [])]
    diff_plan = {
        "schema": "cpos.github_diff_review.v1",
        "source_task_id": source_task_id,
        "repo": plan.get("repo"),
        "base_branch": plan.get("base_branch"),
        "proposed_branch": plan.get("proposed_branch"),
        "proposed_pr_title": plan.get("proposed_pr_title"),
        "changed_files": safe_changed_files,
        "validation_commands": safe_commands,
        "diff_sha256": hashlib.sha256(diff_text.encode("utf-8")).hexdigest(),
        "diff_size_bytes": len(diff_text.encode("utf-8")),
        "diff_values_stored": False,
        "added_lines": added_lines,
        "removed_lines": removed_lines,
        "files_written": False,
        "patch_applied": False,
        "tests_run": False,
        "commit_created": False,
        "pushed": False,
        "pr_created": False,
        "execute_automatically": False,
        "requires_human_approval": True,
        "next_step": "sandbox_patch_runner_review",
        "guardrails": [
            "metadata-only diff review",
            "raw diff text is never stored in Task Tape",
            "no filesystem writes during diff review",
            "sandbox patch/test runner must be separately approved",
        ],
    }
    diff_plan["diff_plan_sha256"] = _digest(diff_plan)
    human_escalation = review_escalation_decision(
        review_type=REVIEW_TYPE,
        summary=f"GitHub diff review for {plan.get('repo')} with sandbox follow-up",
        confidence=0.88,
        risk="medium",
        user_confirmation_required=True,
    )
    target = f"github://{plan.get('repo')}/diff-review/{source_task_id}"
    task_id = store.create_task(
        target=target,
        action="github_diff_review_request",
        payload={
            "review_type": REVIEW_TYPE,
            "source_task_id": source_task_id,
            "repo": plan.get("repo"),
            "diff_plan_sha256": diff_plan["diff_plan_sha256"],
            "human_escalation": human_escalation,
            "actor": actor,
        },
    )
    event = store.append_event(
        task_id=task_id,
        event="review_required",
        target=target,
        status="pending_review",
        payload={"review_type": REVIEW_TYPE, "plan": diff_plan, "human_escalation": human_escalation, "actor": actor},
    )
    return {"ok": True, "task_id": task_id, "status": "pending_review", "review": event.to_dict(), "plan": diff_plan, "execute_automatically": False}


def approve_github_diff_review(store: TaskTapeStore, task_id: str, *, approver: str = "GitHubDiffReviewer", reason: str | None = None, confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        return {"ok": False, "error": "confirm_required", "task_id": task_id}
    review = next((row for row in pending_github_diff_reviews(store) if row.get("task_id") == task_id), None)
    if review is None:
        return {"ok": False, "error": "pending_github_diff_review_not_found", "task_id": task_id}
    plan = (review.get("payload") or {}).get("plan") or {}
    event = store.append_event(
        task_id=task_id,
        event="github_diff_review_approved",
        target=review.get("target"),
        status="approved_metadata_only",
        payload={
            "review_type": REVIEW_TYPE,
            "approved_by": approver,
            "reason": reason,
            "diff_plan_sha256": plan.get("diff_plan_sha256"),
            "next_step": "sandbox_patch_runner_review",
            "files_written": False,
            "patch_applied": False,
            "commit_created": False,
            "pushed": False,
            "pr_created": False,
            "execute_automatically": False,
        },
    )
    return {"ok": True, "task_id": task_id, "status": "approved_metadata_only", "event": event.to_dict(), "patch_applied": False, "pr_created": False, "execute_automatically": False}


def reject_github_diff_review(store: TaskTapeStore, task_id: str, *, reason: str = "manual_reject") -> dict[str, Any]:
    review = next((row for row in pending_github_diff_reviews(store) if row.get("task_id") == task_id), None)
    if review is None:
        return {"ok": False, "error": "pending_github_diff_review_not_found", "task_id": task_id}
    event = store.append_event(
        task_id=task_id,
        event="github_diff_review_rejected",
        target=review.get("target"),
        status="rejected",
        payload={"review_type": REVIEW_TYPE, "reason": reason, "patch_applied": False, "pr_created": False, "execute_automatically": False},
    )
    return {"ok": True, "task_id": task_id, "status": "rejected", "event": event.to_dict(), "patch_applied": False, "pr_created": False, "execute_automatically": False}
