from __future__ import annotations

from typing import Any

from .sandbox_patch_plan import create_sandbox_patch_plan, approve_sandbox_patch_plan
from .sandbox_patch_runner import (
    create_sandbox_patch_execution,
    approve_sandbox_patch_execution,
    execute_sandbox_patch_run,
    create_sandbox_patch_execution_retry_review,
    approve_sandbox_patch_execution_retry,
    create_sandbox_patch_replan_template,
    create_sandbox_replan_diff_intake,
)
from .task_tape import TaskTapeStore


def advance_sandbox_patch_pipeline(
    store: TaskTapeStore,
    *,
    diff_task_id: str,
    diff_text: str | None = None,
    validation_commands: list[str] | None = None,
    actor: str = "ExecutionDriver",
    approve_plan: bool = False,
    approve_execution: bool = False,
    run: bool = False,
    runner_mode: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Advance an approved diff through the sandbox execution pipeline.

    This is the safe execution driver for the review-gated sandbox path. It can
    create the next reviews and, only with explicit confirmation flags, approve
    them and run the already-approved sandbox execution in an ephemeral copy.

    Raw diff text and raw command output are never stored by this driver; raw
    diff text is accepted only as transient input for the isolated run.
    """
    steps: list[dict[str, Any]] = []

    plan_result = create_sandbox_patch_plan(
        store,
        diff_task_id=diff_task_id,
        actor=actor,
        dry_run=True,
    )
    steps.append(_step("create_sandbox_patch_plan", plan_result))
    if not plan_result.get("ok"):
        return _result(False, "sandbox_patch_plan_failed", steps)

    patch_task_id = str(plan_result["task_id"])
    if not approve_plan:
        return _result(True, "pending_sandbox_patch_plan_review", steps, patch_task_id=patch_task_id)

    plan_approval = approve_sandbox_patch_plan(
        store,
        patch_task_id,
        approver=actor,
        reason=reason or "execution_driver_approve_plan",
        confirm=True,
    )
    steps.append(_step("approve_sandbox_patch_plan", plan_approval))
    if not plan_approval.get("ok"):
        return _result(False, "sandbox_patch_plan_approval_failed", steps, patch_task_id=patch_task_id)

    execution_result = create_sandbox_patch_execution(
        store,
        patch_task_id=patch_task_id,
        actor=actor,
        dry_run=True,
    )
    steps.append(_step("create_sandbox_patch_execution_review", execution_result))
    if not execution_result.get("ok"):
        return _result(False, "sandbox_patch_execution_review_failed", steps, patch_task_id=patch_task_id)

    execution_task_id = str(execution_result["task_id"])
    if not approve_execution:
        return _result(
            True,
            "pending_sandbox_patch_execution_review",
            steps,
            patch_task_id=patch_task_id,
            execution_task_id=execution_task_id,
        )

    execution_approval = approve_sandbox_patch_execution(
        store,
        execution_task_id,
        approver=actor,
        reason=reason or "execution_driver_approve_execution",
        confirm=True,
    )
    steps.append(_step("approve_sandbox_patch_execution", execution_approval))
    if not execution_approval.get("ok"):
        return _result(
            False,
            "sandbox_patch_execution_approval_failed",
            steps,
            patch_task_id=patch_task_id,
            execution_task_id=execution_task_id,
        )

    if not run:
        return _result(
            True,
            "approved_sandbox_execution_ready",
            steps,
            patch_task_id=patch_task_id,
            execution_task_id=execution_task_id,
        )

    if diff_text is None:
        return _result(
            False,
            "diff_text_required_for_run",
            steps,
            patch_task_id=patch_task_id,
            execution_task_id=execution_task_id,
        )
    if validation_commands is None:
        return _result(
            False,
            "validation_commands_required_for_run",
            steps,
            patch_task_id=patch_task_id,
            execution_task_id=execution_task_id,
        )

    run_result = execute_sandbox_patch_run(
        store,
        task_id=execution_task_id,
        diff_text=diff_text,
        validation_commands=validation_commands,
        actor=actor,
        runner_mode=runner_mode,
    )
    steps.append(_step("run_sandbox_patch_execution", run_result))
    return _result(
        bool(run_result.get("ok")),
        str(run_result.get("status") or run_result.get("error") or "sandbox_run_completed"),
        steps,
        patch_task_id=patch_task_id,
        execution_task_id=execution_task_id,
        run_status=run_result.get("status"),
        failure_kind=run_result.get("failure_kind"),
    )


def advance_failed_sandbox_replan(
    store: TaskTapeStore,
    *,
    source_execution_task_id: str,
    actor: str = "ExecutionDriver",
    approve_retry: bool = False,
    create_replan_template: bool = False,
    create_diff_intake: bool = False,
    reason: str | None = None,
) -> dict[str, Any]:
    """Advance a failed sandbox execution toward the next safe diff intake.

    This does not rerun, patch, commit, push, or store raw outputs. It converts a
    completed failed sandbox execution into reviewable retry/replan metadata and,
    when explicitly requested, a checklist for the next human-supplied diff.
    """
    steps: list[dict[str, Any]] = []

    retry_result = create_sandbox_patch_execution_retry_review(
        store,
        source_task_id=source_execution_task_id,
        actor=actor,
        reason=reason,
    )
    steps.append(_step("create_sandbox_patch_execution_retry_review", retry_result))
    if not retry_result.get("ok"):
        return _result(False, "sandbox_retry_review_failed", steps, source_execution_task_id=source_execution_task_id, workspace_reused=False)

    retry_task_id = str(retry_result["task_id"])
    if not approve_retry:
        return _result(True, "pending_sandbox_retry_review", steps, source_execution_task_id=source_execution_task_id, retry_task_id=retry_task_id, workspace_reused=False)

    retry_approval = approve_sandbox_patch_execution_retry(
        store,
        retry_task_id,
        approver=actor,
        reason=reason or "execution_driver_approve_retry",
        confirm=True,
    )
    steps.append(_step("approve_sandbox_patch_execution_retry", retry_approval))
    if not retry_approval.get("ok"):
        return _result(False, "sandbox_retry_approval_failed", steps, source_execution_task_id=source_execution_task_id, retry_task_id=retry_task_id, workspace_reused=False)

    if not create_replan_template:
        return _result(True, "approved_sandbox_retry_ready", steps, source_execution_task_id=source_execution_task_id, retry_task_id=retry_task_id, workspace_reused=False)

    replan_result = create_sandbox_patch_replan_template(
        store,
        retry_task_id=retry_task_id,
        actor=actor,
        reason=reason,
    )
    steps.append(_step("create_sandbox_patch_replan_template", replan_result))
    if not replan_result.get("ok"):
        return _result(False, "sandbox_replan_template_failed", steps, source_execution_task_id=source_execution_task_id, retry_task_id=retry_task_id, workspace_reused=False)

    replan_task_id = str(replan_result["task_id"])
    if not create_diff_intake:
        return _result(True, "sandbox_replan_template_created", steps, source_execution_task_id=source_execution_task_id, retry_task_id=retry_task_id, replan_task_id=replan_task_id, workspace_reused=False)

    intake_result = create_sandbox_replan_diff_intake(
        store,
        replan_task_id=replan_task_id,
        actor=actor,
        reason=reason,
    )
    steps.append(_step("create_sandbox_replan_diff_intake", intake_result))
    if not intake_result.get("ok"):
        return _result(False, "sandbox_diff_intake_failed", steps, source_execution_task_id=source_execution_task_id, retry_task_id=retry_task_id, replan_task_id=replan_task_id, workspace_reused=False)

    return _result(
        True,
        "sandbox_diff_intake_created",
        steps,
        source_execution_task_id=source_execution_task_id,
        retry_task_id=retry_task_id,
        replan_task_id=replan_task_id,
        diff_intake_task_id=intake_result.get("task_id"),
        workspace_reused=False,
    )


def _step(name: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "step": name,
        "ok": bool(result.get("ok")),
        "status": result.get("status"),
        "error": result.get("error"),
        "task_id": result.get("task_id"),
        "execute_automatically": False,
        "metadata_only": True,
    }


def _result(ok: bool, status: str, steps: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {
        "ok": ok,
        "status": status,
        "steps": steps,
        "step_count": len(steps),
        "metadata_only": True,
        "raw_diff_stored": False,
        "raw_outputs_stored": False,
        "workspace_type": "ephemeral_copy",
        "commit_created": False,
        "pushed": False,
        "pr_created": False,
        "execute_automatically": False,
        **extra,
    }
