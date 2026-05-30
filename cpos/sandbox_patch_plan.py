from __future__ import annotations

import hashlib
import json
from typing import Any

from .github_diff_review import REVIEW_TYPE as DIFF_REVIEW_TYPE, _digest
from .human_escalation import review_escalation_decision
from .task_tape import TaskTapeStore

REVIEW_TYPE = "sandbox_patch_plan"
TERMINAL_EVENTS = {"sandbox_patch_plan_approved", "sandbox_patch_plan_rejected"}


def _approved_diff_plan(store: TaskTapeStore, task_id: str) -> dict[str, Any] | None:
    events = store.events_for_task(task_id)
    review = next((event for event in events if event.event == "review_required" and event.payload.get("review_type") == DIFF_REVIEW_TYPE), None)
    approved = next((event for event in events if event.event == "github_diff_review_approved" and event.payload.get("review_type") == DIFF_REVIEW_TYPE), None)
    if review is None or approved is None:
        return None
    return (review.payload or {}).get("plan") or {}


def _hash_list(values: list[Any]) -> list[dict[str, Any]]:
    rows = []
    for value in values:
        text = str(value)
        rows.append({
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "size_bytes": len(text.encode("utf-8")),
        })
    return rows


def pending_sandbox_patch_plans(store: TaskTapeStore) -> list[dict[str, Any]]:
    terminal_task_ids = {event.task_id for event in store.events() if event.event in TERMINAL_EVENTS and event.payload.get("review_type") == REVIEW_TYPE}
    return [
        event.to_dict()
        for event in store.events()
        if event.event == "review_required" and event.payload.get("review_type") == REVIEW_TYPE and event.task_id not in terminal_task_ids
    ]


def create_sandbox_patch_plan(
    store: TaskTapeStore,
    *,
    diff_task_id: str,
    actor: str = "SandboxPatchPlanner",
    dry_run: bool = True,
) -> dict[str, Any]:
    """Create a review-gated sandbox patch/test execution plan.

    This does not apply patches or run commands. It converts an approved diff review
    into an auditable execution gate for a later isolated runner.
    """
    if not dry_run:
        return {"ok": False, "error": "real_sandbox_execution_disabled", "execute_automatically": False}
    diff_plan = _approved_diff_plan(store, diff_task_id)
    if diff_plan is None:
        return {"ok": False, "error": "approved_diff_review_required", "diff_task_id": diff_task_id, "execute_automatically": False}

    validation_commands = [str(command) for command in diff_plan.get("validation_commands", [])]
    plan = {
        "schema": "cpos.sandbox_patch_plan.v1",
        "diff_task_id": diff_task_id,
        "source_task_id": diff_plan.get("source_task_id"),
        "repo": diff_plan.get("repo"),
        "base_branch": diff_plan.get("base_branch"),
        "proposed_branch": diff_plan.get("proposed_branch"),
        "changed_files": list(diff_plan.get("changed_files", [])),
        "diff_sha256": diff_plan.get("diff_sha256"),
        "diff_size_bytes": diff_plan.get("diff_size_bytes"),
        "validation_command_hashes": _hash_list(validation_commands),
        "validation_command_count": len(validation_commands),
        "validation_values_stored": False,
        "network_disabled_required": True,
        "project_write_allowed": False,
        "workspace_type": "ephemeral_copy",
        "requires_isolation": True,
        "patch_applied": False,
        "commands_executed": False,
        "tests_run": False,
        "commit_created": False,
        "pushed": False,
        "pr_created": False,
        "execute_automatically": False,
        "requires_human_approval": True,
        "next_step": "isolated_patch_apply_and_validation",
        "guardrails": [
            "never apply patches to the live repository",
            "use an ephemeral workspace copy only",
            "disable network during validation",
            "store command hashes/results only; never store secrets",
            "commit/push/PR creation remain separately gated",
        ],
    }
    plan["sandbox_plan_sha256"] = _digest(plan)
    human_escalation = review_escalation_decision(
        review_type=REVIEW_TYPE,
        summary=f"Sandbox patch plan for {diff_plan.get('repo')}",
        confidence=0.86,
        risk="medium",
        user_confirmation_required=True,
    )
    target = f"sandbox://github-diff/{diff_task_id}"
    task_id = store.create_task(
        target=target,
        action="sandbox_patch_plan_request",
        payload={
            "review_type": REVIEW_TYPE,
            "diff_task_id": diff_task_id,
            "repo": diff_plan.get("repo"),
            "sandbox_plan_sha256": plan["sandbox_plan_sha256"],
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


def approve_sandbox_patch_plan(store: TaskTapeStore, task_id: str, *, approver: str = "SandboxPatchReviewer", reason: str | None = None, confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        return {"ok": False, "error": "confirm_required", "task_id": task_id}
    review = next((row for row in pending_sandbox_patch_plans(store) if row.get("task_id") == task_id), None)
    if review is None:
        return {"ok": False, "error": "pending_sandbox_patch_plan_not_found", "task_id": task_id}
    plan = (review.get("payload") or {}).get("plan") or {}
    event = store.append_event(
        task_id=task_id,
        event="sandbox_patch_plan_approved",
        target=review.get("target"),
        status="approved_plan_only",
        payload={
            "review_type": REVIEW_TYPE,
            "approved_by": approver,
            "reason": reason,
            "sandbox_plan_sha256": plan.get("sandbox_plan_sha256"),
            "next_step": "isolated_patch_apply_and_validation",
            "patch_applied": False,
            "commands_executed": False,
            "commit_created": False,
            "pushed": False,
            "pr_created": False,
            "execute_automatically": False,
        },
    )
    return {"ok": True, "task_id": task_id, "status": "approved_plan_only", "event": event.to_dict(), "patch_applied": False, "commands_executed": False, "pr_created": False, "execute_automatically": False}


def reject_sandbox_patch_plan(store: TaskTapeStore, task_id: str, *, reason: str = "manual_reject") -> dict[str, Any]:
    review = next((row for row in pending_sandbox_patch_plans(store) if row.get("task_id") == task_id), None)
    if review is None:
        return {"ok": False, "error": "pending_sandbox_patch_plan_not_found", "task_id": task_id}
    event = store.append_event(
        task_id=task_id,
        event="sandbox_patch_plan_rejected",
        target=review.get("target"),
        status="rejected",
        payload={"review_type": REVIEW_TYPE, "reason": reason, "patch_applied": False, "commands_executed": False, "pr_created": False, "execute_automatically": False},
    )
    return {"ok": True, "task_id": task_id, "status": "rejected", "event": event.to_dict(), "patch_applied": False, "commands_executed": False, "pr_created": False, "execute_automatically": False}
