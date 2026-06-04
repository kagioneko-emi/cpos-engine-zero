from __future__ import annotations

import hashlib
from typing import Any

from .agent_adapter import intake_external_agent_action
from .auto_fix_candidate import create_auto_fix_candidate
from .demo_readiness import build_competitive_demo_readiness
from .diff_review_draft import create_diff_review_draft
from .github_diff_review import approve_github_diff_review, create_github_diff_review
from .github_pr_flow import approve_github_pr_dry_run, create_github_pr_dry_run
from .patch_generation_review import create_patch_generation_review
from .sandbox_patch_plan import approve_sandbox_patch_plan, create_sandbox_patch_plan
from .sandbox_patch_runner import (
    approve_sandbox_patch_execution_retry,
    create_sandbox_patch_execution,
    create_sandbox_patch_execution_retry_review,
    create_sandbox_patch_replan_template,
)
from .task_tape import TaskTapeStore


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _command_hash(command: str) -> dict[str, Any]:
    return {"index": 0, "sha256": _sha256(command), "size_bytes": len(command.encode("utf-8"))}


def _step(name: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "ok": bool(result.get("ok")),
        "task_id": result.get("task_id"),
        "status": result.get("status"),
        "error": result.get("error"),
        "execute_automatically": result.get("execute_automatically", False),
    }


def _append_demo_failed_execution(store: TaskTapeStore, *, actor: str, reason: str | None = None) -> dict[str, Any]:
    validation_command = "pytest -q tests/test_demo_readiness.py"
    validation_hash = _command_hash(validation_command)
    task_id = store.create_task(
        target="sandbox://execution/demo-fixture-failed-run",
        action="sandbox_demo_failed_execution_fixture",
        payload={
            "review_type": "sandbox_patch_execution",
            "demo_fixture": True,
            "reason": reason,
            "raw_diff_stored": False,
            "raw_outputs_stored": False,
            "actor": actor,
        },
    )
    event = store.append_event(
        task_id=task_id,
        event="sandbox_patch_execution_completed",
        target="sandbox://execution/demo-fixture-failed-run",
        status="completed_with_failures",
        payload={
            "review_type": "sandbox_patch_execution",
            "demo_fixture": True,
            "success": False,
            "failure_kind": "validation_command",
            "workspace_copied": True,
            "patch_applied": True,
            "commands_executed": True,
            "tests_run": True,
            "validation_command_count": 1,
            "validation_command_hashes": [validation_hash],
            "command_results": [
                {
                    "command_index": 0,
                    "command_sha256": validation_hash["sha256"],
                    "exit_code": 1,
                    "stdout_sha256": _sha256("demo stdout metadata placeholder"),
                    "stderr_sha256": _sha256("demo stderr metadata placeholder"),
                    "stdout_size_bytes": 128,
                    "stderr_size_bytes": 64,
                    "sandbox_backend": "demo-metadata-only",
                    "sandbox_mode": "strict",
                    "isolated": True,
                    "fallback_used": False,
                }
            ],
            "patch_apply_stage": "apply",
            "patch_apply_exit_code": 0,
            "patch_apply_stdout_sha256": _sha256("demo patch apply stdout metadata placeholder"),
            "patch_apply_stderr_sha256": _sha256(""),
            "raw_diff_stored": False,
            "raw_outputs_stored": False,
            "command_outputs_stored": False,
            "execute_automatically": False,
            "live_repo_patch": False,
            "commit_created": False,
            "pushed": False,
            "pr_created": False,
            "actor": actor,
            "reason": reason,
        },
    )
    return {"ok": True, "task_id": task_id, "status": "completed_with_failures", "event": event.to_dict(), "execute_automatically": False}


def create_competitive_demo_fixture(
    store: TaskTapeStore,
    *,
    actor: str = "CompetitiveDemoFixture",
    reason: str | None = None,
    confirm: bool = False,
    mcp_registry: Any | None = None,
) -> dict[str, Any]:
    """Create a metadata-only demo chain for readiness screenshots/tests.

    The fixture uses existing review-gated planning functions plus one synthetic
    failed execution metadata event. It never runs commands, applies patches,
    mutates the live repo, commits, pushes, creates PRs, or stores raw diff/output
    values. `confirm=true` is required because it writes demo events to Task Tape.
    """
    if not confirm:
        return {"ok": False, "error": "confirm_required", "execute_automatically": False}

    steps: list[dict[str, Any]] = []
    validation_commands = ["pytest -q tests/test_demo_readiness.py"]
    transient_diff = "diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n@@\n-demo readiness placeholder\n+demo readiness placeholder\n"

    agent_action = intake_external_agent_action(
        store,
        agent_name="demo-external-agent",
        event_type="command_request",
        commands=validation_commands,
        changed_files=["README.md"],
        metadata={"risk": "medium", "requires_human_approval": True, "demo_fixture": True},
        actor=actor,
    )
    steps.append(_step("create_external_agent_adapter_review", agent_action))

    agent_result = intake_external_agent_action(
        store,
        agent_name="demo-external-agent",
        event_type="execution_result",
        execution_result={"status": "failed", "output_redacted": True},
        commands=validation_commands,
        changed_files=["README.md"],
        metadata={"success": False, "exit_code": 1, "failure_kind": "validation_command", "duration_ms": 1200, "demo_fixture": True},
        actor=actor,
    )
    steps.append(_step("record_external_agent_execution_result", agent_result))

    pr = create_github_pr_dry_run(
        store,
        repo="kagioneko/cpos-engine-zero",
        title="CPOS competitive demo fixture",
        files=["README.md"],
        summary="metadata-only competitive demo fixture",
        actor=actor,
    )
    steps.append(_step("create_github_pr_dry_run", pr))
    if not pr.get("ok"):
        return {"ok": False, "steps": steps, "execute_automatically": False}

    approved_pr = approve_github_pr_dry_run(store, pr["task_id"], approver=actor, reason=reason, confirm=True)
    steps.append(_step("approve_github_pr_dry_run", approved_pr))

    diff = create_github_diff_review(
        store,
        source_task_id=pr["task_id"],
        diff_text=transient_diff,
        changed_files=["README.md"],
        validation_commands=validation_commands,
        actor=actor,
    )
    steps.append(_step("create_github_diff_review", diff))
    if not diff.get("ok"):
        return {"ok": False, "steps": steps, "execute_automatically": False}

    approved_diff = approve_github_diff_review(store, diff["task_id"], approver=actor, reason=reason, confirm=True)
    steps.append(_step("approve_github_diff_review", approved_diff))

    plan = create_sandbox_patch_plan(store, diff_task_id=diff["task_id"], actor=actor)
    steps.append(_step("create_sandbox_patch_plan", plan))
    if not plan.get("ok"):
        return {"ok": False, "steps": steps, "execute_automatically": False}

    approved_plan = approve_sandbox_patch_plan(store, plan["task_id"], approver=actor, reason=reason, confirm=True)
    steps.append(_step("approve_sandbox_patch_plan", approved_plan))

    execution = create_sandbox_patch_execution(store, patch_task_id=plan["task_id"], actor=actor)
    steps.append(_step("create_ready_to_run_execution_review", execution))

    failed = _append_demo_failed_execution(store, actor=actor, reason=reason)
    steps.append(_step("append_failed_execution_metadata", failed))

    retry = create_sandbox_patch_execution_retry_review(store, source_task_id=failed["task_id"], actor=actor, reason=reason)
    steps.append(_step("create_retry_review", retry))
    if not retry.get("ok"):
        return {"ok": False, "steps": steps, "execute_automatically": False}

    approved_retry = approve_sandbox_patch_execution_retry(store, retry["task_id"], approver=actor, reason=reason, confirm=True)
    steps.append(_step("approve_retry_review", approved_retry))

    replan = create_sandbox_patch_replan_template(store, retry_task_id=retry["task_id"], actor=actor, reason=reason)
    steps.append(_step("create_replan_template", replan))
    if not replan.get("ok"):
        return {"ok": False, "steps": steps, "execute_automatically": False}

    candidate = create_auto_fix_candidate(store, replan_task_id=replan["task_id"], actor=actor, reason=reason)
    steps.append(_step("create_auto_fix_candidate", candidate))
    if not candidate.get("ok"):
        return {"ok": False, "steps": steps, "execute_automatically": False}

    patch_generation = create_patch_generation_review(store, candidate_task_id=candidate["task_id"], actor=actor, reason=reason)
    steps.append(_step("create_patch_generation_review", patch_generation))

    draft = create_diff_review_draft(store, candidate_task_id=candidate["task_id"], actor=actor, reason=reason)
    steps.append(_step("create_diff_review_draft", draft))

    readiness = build_competitive_demo_readiness(store, mcp_registry=mcp_registry)
    return {
        "ok": all(step.get("ok") for step in steps),
        "status": "competitive_demo_fixture_created",
        "steps": steps,
        "step_count": len(steps),
        "task_ids": {step["name"]: step.get("task_id") for step in steps if step.get("task_id")},
        "readiness": readiness,
        "metadata_only": True,
        "raw_diff_stored": False,
        "raw_outputs_stored": False,
        "execute_automatically": False,
        "live_repo_patch": False,
        "commit_created": False,
        "pushed": False,
        "pr_created": False,
    }
