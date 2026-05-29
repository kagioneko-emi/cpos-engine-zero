from __future__ import annotations

import hashlib
from typing import Any

from .sandbox_patch_plan import REVIEW_TYPE as PATCH_PLAN_REVIEW_TYPE, _digest
from .task_tape import TaskTapeStore

REVIEW_TYPE = "sandbox_patch_execution"
TERMINAL_EVENTS = {"sandbox_patch_execution_approved", "sandbox_patch_execution_rejected"}


def _approved_patch_plan(store: TaskTapeStore, task_id: str) -> dict[str, Any] | None:
    events = store.events_for_task(task_id)
    review = next((event for event in events if event.event == "review_required" and event.payload.get("review_type") == PATCH_PLAN_REVIEW_TYPE), None)
    approved = next((event for event in events if event.event == "sandbox_patch_plan_approved" and event.payload.get("review_type") == PATCH_PLAN_REVIEW_TYPE), None)
    if review is None or approved is None:
        return None
    return (review.payload or {}).get("plan") or {}


def _hash_commands(values: list[str]) -> list[dict[str, Any]]:
    rows = []
    for value in values:
        rows.append({
            "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
            "size_bytes": len(value.encode("utf-8")),
        })
    return rows


def pending_sandbox_patch_executions(store: TaskTapeStore) -> list[dict[str, Any]]:
    terminal_task_ids = {event.task_id for event in store.events() if event.event in TERMINAL_EVENTS and event.payload.get("review_type") == REVIEW_TYPE}
    return [
        event.to_dict()
        for event in store.events()
        if event.event == "review_required" and event.payload.get("review_type") == REVIEW_TYPE and event.task_id not in terminal_task_ids
    ]


def create_sandbox_patch_execution(
    store: TaskTapeStore,
    *,
    patch_task_id: str,
    actor: str = "SandboxPatchRunner",
    dry_run: bool = True,
) -> dict[str, Any]:
    """Create an approval-gated execution plan for an approved sandbox patch plan.

    This is metadata-only: it does not apply patches or run commands. The actual
    runner is reserved for a future isolated executor.
    """
    if not dry_run:
        return {"ok": False, "error": "real_sandbox_patch_execution_disabled", "execute_automatically": False}
    patch_plan = _approved_patch_plan(store, patch_task_id)
    if patch_plan is None:
        return {"ok": False, "error": "approved_sandbox_patch_plan_required", "patch_task_id": patch_task_id, "execute_automatically": False}

    validation_command_hashes = list(patch_plan.get("validation_command_hashes", []))
    validation_command_count = int(patch_plan.get("validation_command_count", len(validation_command_hashes)))
    execution_plan = {
        "schema": "cpos.sandbox_patch_execution.v1",
        "patch_task_id": patch_task_id,
        "source_task_id": patch_plan.get("source_task_id"),
        "diff_task_id": patch_plan.get("diff_task_id"),
        "repo": patch_plan.get("repo"),
        "base_branch": patch_plan.get("base_branch"),
        "proposed_branch": patch_plan.get("proposed_branch"),
        "changed_files": list(patch_plan.get("changed_files", [])),
        "diff_sha256": patch_plan.get("diff_sha256"),
        "sandbox_plan_sha256": patch_plan.get("sandbox_plan_sha256"),
        "workspace_type": patch_plan.get("workspace_type"),
        "runner_mode": "strict",
        "validation_command_hashes": validation_command_hashes,
        "validation_command_count": validation_command_count,
        "workspace_copied": False,
        "patch_applied": False,
        "commands_executed": False,
        "tests_run": False,
        "command_outputs_stored": False,
        "commit_created": False,
        "pushed": False,
        "pr_created": False,
        "execute_automatically": False,
        "requires_human_approval": True,
        "next_step": "isolated_runner_ready",
        "guardrails": [
            "workspace copy only; never patch live repo",
            "run in strict sandbox mode by default",
            "store hashes/metadata only; never store raw outputs or secrets",
            "commit/push/PR creation remain separately gated",
        ],
    }
    execution_plan["sandbox_execution_sha256"] = _digest(execution_plan)
    target = f"sandbox://execution/{patch_task_id}"
    task_id = store.create_task(
        target=target,
        action="sandbox_patch_execution_request",
        payload={
            "review_type": REVIEW_TYPE,
            "patch_task_id": patch_task_id,
            "repo": patch_plan.get("repo"),
            "sandbox_execution_sha256": execution_plan["sandbox_execution_sha256"],
            "actor": actor,
        },
    )
    event = store.append_event(
        task_id=task_id,
        event="review_required",
        target=target,
        status="pending_review",
        payload={"review_type": REVIEW_TYPE, "plan": execution_plan, "actor": actor},
    )
    return {"ok": True, "task_id": task_id, "status": "pending_review", "review": event.to_dict(), "plan": execution_plan, "execute_automatically": False}


def approve_sandbox_patch_execution(store: TaskTapeStore, task_id: str, *, approver: str = "SandboxPatchRunnerReviewer", reason: str | None = None, confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        return {"ok": False, "error": "confirm_required", "task_id": task_id}
    review = next((row for row in pending_sandbox_patch_executions(store) if row.get("task_id") == task_id), None)
    if review is None:
        return {"ok": False, "error": "pending_sandbox_patch_execution_not_found", "task_id": task_id}
    plan = (review.get("payload") or {}).get("plan") or {}
    event = store.append_event(
        task_id=task_id,
        event="sandbox_patch_execution_approved",
        target=review.get("target"),
        status="approved_execution_plan_only",
        payload={
            "review_type": REVIEW_TYPE,
            "approved_by": approver,
            "reason": reason,
            "sandbox_execution_sha256": plan.get("sandbox_execution_sha256"),
            "next_step": "isolated_runner_ready",
            "workspace_copied": False,
            "patch_applied": False,
            "commands_executed": False,
            "tests_run": False,
            "commit_created": False,
            "pushed": False,
            "pr_created": False,
            "execute_automatically": False,
        },
    )
    return {"ok": True, "task_id": task_id, "status": "approved_execution_plan_only", "event": event.to_dict(), "workspace_copied": False, "patch_applied": False, "commands_executed": False, "pr_created": False, "execute_automatically": False}


def reject_sandbox_patch_execution(store: TaskTapeStore, task_id: str, *, reason: str = "manual_reject") -> dict[str, Any]:
    review = next((row for row in pending_sandbox_patch_executions(store) if row.get("task_id") == task_id), None)
    if review is None:
        return {"ok": False, "error": "pending_sandbox_patch_execution_not_found", "task_id": task_id}
    event = store.append_event(
        task_id=task_id,
        event="sandbox_patch_execution_rejected",
        target=review.get("target"),
        status="rejected",
        payload={"review_type": REVIEW_TYPE, "reason": reason, "workspace_copied": False, "patch_applied": False, "commands_executed": False, "pr_created": False, "execute_automatically": False},
    )
    return {"ok": True, "task_id": task_id, "status": "rejected", "event": event.to_dict(), "workspace_copied": False, "patch_applied": False, "commands_executed": False, "pr_created": False, "execute_automatically": False}
