from __future__ import annotations

from typing import Any

from .github_diff_review import create_github_diff_review
from .human_escalation import review_escalation_decision
from .sandbox_patch_plan import _digest
from .task_tape import TaskTapeStore

REVIEW_TYPE = "sandbox_patch_generation"
TERMINAL_EVENTS = {"sandbox_patch_generation_approved", "sandbox_patch_generation_rejected"}


def _auto_fix_candidate_for_task(store: TaskTapeStore, task_id: str) -> dict[str, Any] | None:
    events = store.events_for_task(task_id)
    created = next(
        (
            event
            for event in events
            if event.event == "sandbox_auto_fix_candidate_created"
            and event.payload.get("review_type") == "sandbox_auto_fix_candidate"
        ),
        None,
    )
    if created is None:
        return None
    return (created.payload or {}).get("candidate") or {}


def pending_patch_generation_reviews(store: TaskTapeStore) -> list[dict[str, Any]]:
    terminal_task_ids = {
        event.task_id
        for event in store.events()
        if event.event in TERMINAL_EVENTS and event.payload.get("review_type") == REVIEW_TYPE
    }
    return [
        event.to_dict()
        for event in store.events()
        if event.event == "review_required"
        and event.payload.get("review_type") == REVIEW_TYPE
        and event.task_id not in terminal_task_ids
    ]


def _generation_hints(candidate: dict[str, Any]) -> list[str]:
    failure_kind = str(candidate.get("failure_kind") or "")
    if failure_kind == "patch_apply":
        return ["generate unified diff compatible with git apply --check", "verify file paths against current base"]
    if failure_kind == "validation_command":
        return ["change smallest code path tied to failed validation metadata", "preserve prior validation command scope"]
    if failure_kind == "policy_rejected":
        return ["adjust validation command or runner policy input, not product code by default"]
    if failure_kind == "sandbox_unavailable":
        return ["repair sandbox environment before generating product-code diff"]
    return ["review failure metadata before generating a minimal patch"]


def create_patch_generation_review(
    store: TaskTapeStore,
    *,
    candidate_task_id: str,
    actor: str = "PatchGenerationPlanner",
    reason: str | None = None,
) -> dict[str, Any]:
    candidate = _auto_fix_candidate_for_task(store, candidate_task_id)
    if candidate is None:
        return {"ok": False, "error": "auto_fix_candidate_required", "candidate_task_id": candidate_task_id, "execute_automatically": False}

    plan = {
        "schema": "cpos.sandbox_patch_generation_review.v1",
        "candidate_task_id": candidate_task_id,
        "replan_task_id": candidate.get("replan_task_id"),
        "retry_task_id": candidate.get("retry_task_id"),
        "source_execution_task_id": candidate.get("source_execution_task_id"),
        "failure_kind": candidate.get("failure_kind"),
        "candidate_strategy": candidate.get("candidate_strategy"),
        "confidence": candidate.get("confidence"),
        "candidate_steps": candidate.get("candidate_steps") or [],
        "generation_hints": _generation_hints(candidate),
        "required_transient_inputs": [
            "source_task_id",
            "generated_diff_text",
            "changed_files",
            "validation_commands",
            "review_reason",
        ],
        "target_api": "POST /sandbox/patch-generations/<task_id>/create-github-diff-review",
        "raw_diff_stored": False,
        "raw_outputs_stored": False,
        "raw_patch_stored": False,
        "diff_text_included": False,
        "execute_automatically": False,
        "patch_applied": False,
        "commands_executed": False,
        "commit_created": False,
        "pushed": False,
        "pr_created": False,
        "requires_human_approval": True,
        "reason": reason,
        "guardrails": [
            "review authorizes patch generation attempt metadata only",
            "generated diff text must be transient input and must not be stored in Task Tape",
            "downstream GitHub diff review and sandbox execution gates still apply",
            "no automatic patch apply, command execution, commit, push, or PR creation",
        ],
    }
    plan["patch_generation_plan_sha256"] = _digest(plan)
    human_escalation = review_escalation_decision(
        review_type=REVIEW_TYPE,
        summary=f"Patch generation review for failed sandbox execution {candidate.get('source_execution_task_id') or '-'}",
        confidence=float(candidate.get("confidence") or 0.6),
        risk="medium",
        user_confirmation_required=True,
    )
    target = f"sandbox://patch-generation/{candidate_task_id}"
    task_id = store.create_task(
        target=target,
        action="sandbox_patch_generation_review_request",
        payload={
            "review_type": REVIEW_TYPE,
            "candidate_task_id": candidate_task_id,
            "source_execution_task_id": candidate.get("source_execution_task_id"),
            "patch_generation_plan_sha256": plan["patch_generation_plan_sha256"],
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


def approve_patch_generation_review(store: TaskTapeStore, task_id: str, *, approver: str = "PatchGenerationReviewer", reason: str | None = None, confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        return {"ok": False, "error": "confirm_required", "task_id": task_id}
    review = next((row for row in pending_patch_generation_reviews(store) if row.get("task_id") == task_id), None)
    if review is None:
        return {"ok": False, "error": "pending_patch_generation_review_not_found", "task_id": task_id}
    plan = (review.get("payload") or {}).get("plan") or {}
    event = store.append_event(
        task_id=task_id,
        event="sandbox_patch_generation_approved",
        target=review.get("target"),
        status="approved_metadata_only",
        payload={
            "review_type": REVIEW_TYPE,
            "approved_by": approver,
            "reason": reason,
            "patch_generation_plan_sha256": plan.get("patch_generation_plan_sha256"),
            "raw_diff_stored": False,
            "execute_automatically": False,
            "patch_applied": False,
            "commit_created": False,
            "pushed": False,
            "pr_created": False,
        },
    )
    return {"ok": True, "task_id": task_id, "status": "approved_metadata_only", "event": event.to_dict(), "execute_automatically": False}


def reject_patch_generation_review(store: TaskTapeStore, task_id: str, *, reason: str = "manual_reject") -> dict[str, Any]:
    review = next((row for row in pending_patch_generation_reviews(store) if row.get("task_id") == task_id), None)
    if review is None:
        return {"ok": False, "error": "pending_patch_generation_review_not_found", "task_id": task_id}
    event = store.append_event(
        task_id=task_id,
        event="sandbox_patch_generation_rejected",
        target=review.get("target"),
        status="rejected",
        payload={"review_type": REVIEW_TYPE, "reason": reason, "raw_diff_stored": False, "execute_automatically": False},
    )
    return {"ok": True, "task_id": task_id, "status": "rejected", "event": event.to_dict(), "execute_automatically": False}


def _approved_patch_generation_plan(store: TaskTapeStore, task_id: str) -> dict[str, Any] | None:
    events = store.events_for_task(task_id)
    review = next((event for event in events if event.event == "review_required" and event.payload.get("review_type") == REVIEW_TYPE), None)
    approved = next((event for event in events if event.event == "sandbox_patch_generation_approved" and event.payload.get("review_type") == REVIEW_TYPE), None)
    if review is None or approved is None:
        return None
    return (review.payload or {}).get("plan") or {}


def create_github_diff_review_from_patch_generation(
    store: TaskTapeStore,
    *,
    patch_generation_task_id: str,
    source_task_id: str | None,
    diff_text: str | None = None,
    changed_files: list[str] | None = None,
    validation_commands: list[str] | None = None,
    actor: str = "PatchGenerationRouter",
    reason: str | None = None,
) -> dict[str, Any]:
    plan = _approved_patch_generation_plan(store, patch_generation_task_id)
    if plan is None:
        return {"ok": False, "error": "approved_patch_generation_review_required", "patch_generation_task_id": patch_generation_task_id, "execute_automatically": False}
    if not source_task_id:
        return {"ok": False, "error": "approved_pr_dry_run_source_required", "patch_generation_task_id": patch_generation_task_id, "execute_automatically": False}
    if not diff_text:
        return {"ok": False, "error": "diff_text_required", "patch_generation_task_id": patch_generation_task_id, "raw_diff_stored": False, "execute_automatically": False}
    if not isinstance(changed_files, list) or not changed_files:
        return {"ok": False, "error": "changed_files_required", "patch_generation_task_id": patch_generation_task_id, "execute_automatically": False}
    if not isinstance(validation_commands, list) or not validation_commands:
        return {"ok": False, "error": "validation_commands_required", "patch_generation_task_id": patch_generation_task_id, "execute_automatically": False}

    result = create_github_diff_review(
        store,
        source_task_id=source_task_id,
        diff_text=diff_text,
        changed_files=changed_files,
        validation_commands=validation_commands,
        actor=actor,
        dry_run=True,
    )
    if not result.get("ok"):
        result.setdefault("patch_generation_task_id", patch_generation_task_id)
        result.setdefault("raw_diff_stored", False)
        result.setdefault("execute_automatically", False)
        return result

    diff_plan = result.get("plan") or {}
    link_payload = {
        "review_type": "sandbox_patch_generation_to_github_diff_review",
        "patch_generation_task_id": patch_generation_task_id,
        "github_diff_review_task_id": result.get("task_id"),
        "source_task_id": source_task_id,
        "candidate_task_id": plan.get("candidate_task_id"),
        "source_execution_task_id": plan.get("source_execution_task_id"),
        "failure_kind": plan.get("failure_kind"),
        "diff_plan_sha256": diff_plan.get("diff_plan_sha256"),
        "diff_sha256": diff_plan.get("diff_sha256"),
        "diff_size_bytes": diff_plan.get("diff_size_bytes"),
        "changed_file_count": len(diff_plan.get("changed_files") or []),
        "validation_command_count": len(diff_plan.get("validation_commands") or []),
        "reason": reason,
        "raw_diff_stored": False,
        "diff_text_included": False,
        "raw_outputs_stored": False,
        "execute_automatically": False,
        "patch_applied": False,
        "commit_created": False,
        "pushed": False,
        "pr_created": False,
    }
    link_event = store.append_event(
        task_id=result["task_id"],
        event="sandbox_patch_generation_linked_to_github_diff_review",
        target=f"sandbox://patch-generation/{patch_generation_task_id}/github-diff-review/{result['task_id']}",
        status="linked_metadata_only",
        payload=link_payload,
    )
    result["patch_generation_task_id"] = patch_generation_task_id
    result["patch_generation_link"] = link_event.to_dict()
    result["raw_diff_stored"] = False
    result["diff_text_included"] = False
    return result
