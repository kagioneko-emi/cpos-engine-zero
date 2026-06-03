from __future__ import annotations

import subprocess

from typing import Any

from .github_diff_review import approve_github_diff_review, create_github_diff_review
from .execution_driver import advance_sandbox_patch_pipeline
from .human_escalation import review_escalation_decision
from .sandbox_patch_plan import _digest
from .sandbox_patch_runner import _hash_commands, _hash_text, _prepare_workspace, validate_validation_commands
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



def _check_generated_patch(diff_text: str) -> dict[str, Any]:
    workspace_tmp, workspace = _prepare_workspace()
    try:
        patch_file = workspace / "generated_patch.diff"
        patch_file.write_text(diff_text, encoding="utf-8")
        check = subprocess.run(["git", "apply", "--check", str(patch_file)], cwd=workspace, capture_output=True, text=True)
        stdout_hash = _hash_text(check.stdout or "")
        stderr_hash = _hash_text(check.stderr or "")
        return {
            "ok": check.returncode == 0,
            "stage": "git_apply_check",
            "exit_code": check.returncode,
            "stdout_sha256": stdout_hash["sha256"],
            "stderr_sha256": stderr_hash["sha256"],
            "stdout_size_bytes": stdout_hash["size_bytes"],
            "stderr_size_bytes": stderr_hash["size_bytes"],
            "workspace_copied": True,
            "patch_applied": False,
            "commands_executed": False,
        }
    finally:
        workspace_tmp.cleanup()


def validate_patch_generation_output(
    store: TaskTapeStore,
    *,
    patch_generation_task_id: str,
    diff_text: str | None = None,
    changed_files: list[str] | None = None,
    validation_commands: list[str] | None = None,
    actor: str = "PatchGenerationHarness",
    reason: str | None = None,
) -> dict[str, Any]:
    """Validate generated patch output in an ephemeral workspace.

    This is a pre-review harness: it checks command policy and `git apply --check`
    only. It never stores raw diff text or raw command output, never mutates the
    live repo, and never runs validation commands.
    """
    plan = _approved_patch_generation_plan(store, patch_generation_task_id)
    if plan is None:
        return {"ok": False, "error": "approved_patch_generation_review_required", "patch_generation_task_id": patch_generation_task_id, "execute_automatically": False}
    if not diff_text:
        return {"ok": False, "error": "diff_text_required", "patch_generation_task_id": patch_generation_task_id, "raw_diff_stored": False, "execute_automatically": False}
    if not isinstance(changed_files, list) or not changed_files:
        return {"ok": False, "error": "changed_files_required", "patch_generation_task_id": patch_generation_task_id, "execute_automatically": False}
    if not isinstance(validation_commands, list) or not validation_commands:
        return {"ok": False, "error": "validation_commands_required", "patch_generation_task_id": patch_generation_task_id, "execute_automatically": False}

    command_policy = validate_validation_commands(validation_commands)
    command_hashes = _hash_commands(validation_commands)
    diff_hash = _hash_text(diff_text)
    apply_check = None
    policy_rejected = not bool(command_policy.get("ok"))
    if not policy_rejected:
        apply_check = _check_generated_patch(diff_text)
    else:
        apply_check = {"ok": False, "stage": "command_policy", "exit_code": 1, "workspace_copied": False, "patch_applied": False, "commands_executed": False}

    success = bool(command_policy.get("ok")) and bool(apply_check.get("ok"))
    failure_kind = None if success else ("policy_rejected" if policy_rejected else "patch_apply")
    payload = {
        "review_type": "sandbox_patch_generation_validation",
        "patch_generation_task_id": patch_generation_task_id,
        "candidate_task_id": plan.get("candidate_task_id"),
        "source_execution_task_id": plan.get("source_execution_task_id"),
        "failure_kind": failure_kind,
        "candidate_strategy": plan.get("candidate_strategy"),
        "actor": actor,
        "reason": reason,
        "diff_sha256": diff_hash["sha256"],
        "diff_size_bytes": diff_hash["size_bytes"],
        "changed_files": list(changed_files),
        "changed_file_count": len(changed_files),
        "validation_command_hashes": command_hashes,
        "validation_command_count": len(command_hashes),
        "command_policy": command_policy,
        "patch_apply_stage": apply_check.get("stage"),
        "patch_apply_exit_code": apply_check.get("exit_code"),
        "patch_apply_stdout_sha256": apply_check.get("stdout_sha256"),
        "patch_apply_stderr_sha256": apply_check.get("stderr_sha256"),
        "patch_apply_stdout_size_bytes": apply_check.get("stdout_size_bytes"),
        "patch_apply_stderr_size_bytes": apply_check.get("stderr_size_bytes"),
        "workspace_copied": apply_check.get("workspace_copied", False),
        "raw_diff_stored": False,
        "diff_text_included": False,
        "raw_outputs_stored": False,
        "patch_applied": False,
        "commands_executed": False,
        "tests_run": False,
        "execute_automatically": False,
        "commit_created": False,
        "pushed": False,
        "pr_created": False,
        "next_step": "create_github_diff_review_from_transient_diff" if success else "revise_generated_diff_before_review",
    }
    payload["validation_sha256"] = _digest(payload)
    status = "validated" if success else "validation_failed"
    event = store.append_event(
        task_id=patch_generation_task_id,
        event="sandbox_patch_generation_output_validated",
        target=f"sandbox://patch-generation/{patch_generation_task_id}/validation",
        status=status,
        payload=payload,
    )
    return {
        "ok": success,
        "task_id": patch_generation_task_id,
        "status": status,
        "event": event.to_dict(),
        "validation": payload,
        "failure_kind": failure_kind,
        "raw_diff_stored": False,
        "diff_text_included": False,
        "raw_outputs_stored": False,
        "patch_applied": False,
        "commands_executed": False,
        "execute_automatically": False,
    }


def advance_patch_generation_to_execution_review(
    store: TaskTapeStore,
    *,
    patch_generation_task_id: str,
    source_task_id: str | None,
    diff_text: str | None = None,
    changed_files: list[str] | None = None,
    validation_commands: list[str] | None = None,
    actor: str = "PatchGenerationSafeAdvance",
    reason: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Validate generated diff, create/approve diff review, and open execution review.

    This is a one-click safe route from an approved patch-generation review to a
    pending sandbox execution review. It requires explicit confirmation because it
    approves the metadata-only GitHub diff review and sandbox patch plan. It does
    not approve execution, run commands, mutate the live repo, commit, push, or
    create a PR.
    """
    if not confirm:
        return {"ok": False, "error": "confirm_required", "patch_generation_task_id": patch_generation_task_id, "execute_automatically": False}

    steps: list[dict[str, Any]] = []
    validation = validate_patch_generation_output(
        store,
        patch_generation_task_id=patch_generation_task_id,
        diff_text=diff_text,
        changed_files=changed_files,
        validation_commands=validation_commands,
        actor=actor,
        reason=reason or "safe_advance_validate_generated_patch",
    )
    steps.append({"name": "validate_patch_generation_output", "ok": bool(validation.get("ok")), "task_id": validation.get("task_id"), "status": validation.get("status"), "error": validation.get("error")})
    if not validation.get("ok"):
        return {
            "ok": False,
            "status": "patch_generation_validation_failed",
            "patch_generation_task_id": patch_generation_task_id,
            "steps": steps,
            "step_count": len(steps),
            "failure_kind": validation.get("failure_kind"),
            "raw_diff_stored": False,
            "diff_text_included": False,
            "raw_outputs_stored": False,
            "patch_applied": False,
            "commands_executed": False,
            "execute_automatically": False,
        }

    diff_review = create_github_diff_review_from_patch_generation(
        store,
        patch_generation_task_id=patch_generation_task_id,
        source_task_id=source_task_id,
        diff_text=diff_text,
        changed_files=changed_files,
        validation_commands=validation_commands,
        actor=actor,
        reason=reason or "safe_advance_create_github_diff_review",
    )
    steps.append({"name": "create_github_diff_review", "ok": bool(diff_review.get("ok")), "task_id": diff_review.get("task_id"), "status": diff_review.get("status"), "error": diff_review.get("error")})
    if not diff_review.get("ok"):
        return {
            "ok": False,
            "status": "github_diff_review_creation_failed",
            "patch_generation_task_id": patch_generation_task_id,
            "steps": steps,
            "step_count": len(steps),
            "raw_diff_stored": False,
            "diff_text_included": False,
            "raw_outputs_stored": False,
            "patch_applied": False,
            "commands_executed": False,
            "execute_automatically": False,
        }

    diff_task_id = str(diff_review["task_id"])
    diff_approval = approve_github_diff_review(
        store,
        diff_task_id,
        approver=actor,
        reason=reason or "safe_advance_approve_diff_review_metadata_only",
        confirm=True,
    )
    steps.append({"name": "approve_github_diff_review", "ok": bool(diff_approval.get("ok")), "task_id": diff_approval.get("task_id"), "status": diff_approval.get("status"), "error": diff_approval.get("error")})
    if not diff_approval.get("ok"):
        return {
            "ok": False,
            "status": "github_diff_review_approval_failed",
            "patch_generation_task_id": patch_generation_task_id,
            "github_diff_review_task_id": diff_task_id,
            "steps": steps,
            "step_count": len(steps),
            "raw_diff_stored": False,
            "diff_text_included": False,
            "raw_outputs_stored": False,
            "patch_applied": False,
            "commands_executed": False,
            "execute_automatically": False,
        }

    advanced = advance_sandbox_patch_pipeline(
        store,
        diff_task_id=diff_task_id,
        actor=actor,
        approve_plan=True,
        approve_execution=False,
        run=False,
        reason=reason or "safe_advance_to_execution_review",
    )
    steps.extend(advanced.get("steps") or [])
    ok = bool(advanced.get("ok")) and advanced.get("status") == "pending_sandbox_patch_execution_review"
    link_payload = {
        "review_type": "sandbox_patch_generation_safe_advance",
        "patch_generation_task_id": patch_generation_task_id,
        "source_execution_task_id": (validation.get("validation") or {}).get("source_execution_task_id"),
        "candidate_task_id": (validation.get("validation") or {}).get("candidate_task_id"),
        "github_diff_review_task_id": diff_task_id,
        "patch_task_id": advanced.get("patch_task_id"),
        "execution_task_id": advanced.get("execution_task_id"),
        "status": advanced.get("status"),
        "step_count": len(steps),
        "raw_diff_stored": False,
        "diff_text_included": False,
        "raw_outputs_stored": False,
        "patch_applied": False,
        "commands_executed": False,
        "execute_automatically": False,
        "commit_created": False,
        "pushed": False,
        "pr_created": False,
        "next_step": "approve_sandbox_execution_then_run_with_transient_diff" if ok else "inspect_safe_advance_failure",
    }
    link_payload["safe_advance_sha256"] = _digest(link_payload)
    event = store.append_event(
        task_id=patch_generation_task_id,
        event="sandbox_patch_generation_advanced_to_execution_review",
        target=f"sandbox://patch-generation/{patch_generation_task_id}/execution-review/{advanced.get('execution_task_id') or '-'}",
        status="execution_review_ready" if ok else "advance_failed",
        payload=link_payload,
    )
    return {
        "ok": ok,
        "status": "execution_review_ready" if ok else str(advanced.get("status") or "advance_failed"),
        "patch_generation_task_id": patch_generation_task_id,
        "source_execution_task_id": (validation.get("validation") or {}).get("source_execution_task_id"),
        "candidate_task_id": (validation.get("validation") or {}).get("candidate_task_id"),
        "github_diff_review_task_id": diff_task_id,
        "patch_task_id": advanced.get("patch_task_id"),
        "execution_task_id": advanced.get("execution_task_id"),
        "steps": steps,
        "step_count": len(steps),
        "event": event.to_dict(),
        "raw_diff_stored": False,
        "diff_text_included": False,
        "raw_outputs_stored": False,
        "patch_applied": False,
        "commands_executed": False,
        "execute_automatically": False,
        "commit_created": False,
        "pushed": False,
        "pr_created": False,
    }

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
