from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from sandbox.runner import SandboxRunner

from .sandbox_patch_plan import REVIEW_TYPE as PATCH_PLAN_REVIEW_TYPE, _digest
from .task_tape import TaskTapeStore

REVIEW_TYPE = "sandbox_patch_execution"
TERMINAL_EVENTS = {"sandbox_patch_execution_approved", "sandbox_patch_execution_rejected"}


def _hash_text(value: str) -> dict[str, Any]:
    encoded = value.encode("utf-8")
    return {"sha256": hashlib.sha256(encoded).hexdigest(), "size_bytes": len(encoded)}


def _approved_patch_plan(store: TaskTapeStore, task_id: str) -> dict[str, Any] | None:
    events = store.events_for_task(task_id)
    review = next((event for event in events if event.event == "review_required" and event.payload.get("review_type") == PATCH_PLAN_REVIEW_TYPE), None)
    approved = next((event for event in events if event.event == "sandbox_patch_plan_approved" and event.payload.get("review_type") == PATCH_PLAN_REVIEW_TYPE), None)
    if review is None or approved is None:
        return None
    return (review.payload or {}).get("plan") or {}


def _approved_execution_plan(store: TaskTapeStore, task_id: str) -> dict[str, Any] | None:
    events = store.events_for_task(task_id)
    review = next((event for event in events if event.event == "review_required" and event.payload.get("review_type") == REVIEW_TYPE), None)
    approved = next((event for event in events if event.event == "sandbox_patch_execution_approved" and event.payload.get("review_type") == REVIEW_TYPE), None)
    if review is None or approved is None:
        return None
    return (review.payload or {}).get("plan") or {}


def _hash_commands(values: list[str]) -> list[dict[str, Any]]:
    return [_hash_text(value) for value in values]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _workspace_ignore_patterns() -> Any:
    return shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache", "workspace", "certs", "*.jsonl", "hackathon_report.html")


def _prepare_workspace() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    tmpdir = tempfile.TemporaryDirectory(prefix="cpos-sandbox-")
    workspace = Path(tmpdir.name) / "workspace"
    shutil.copytree(_project_root(), workspace, dirs_exist_ok=True, ignore=_workspace_ignore_patterns())
    return tmpdir, workspace


def _apply_patch(workspace: Path, diff_text: str) -> dict[str, Any]:
    patch_file = workspace / "sandbox_patch.diff"
    patch_file.write_text(diff_text, encoding="utf-8")
    check = subprocess.run(["git", "apply", "--check", str(patch_file)], cwd=workspace, capture_output=True, text=True)
    if check.returncode != 0:
        return {
            "ok": False,
            "stage": "check",
            "exit_code": check.returncode,
            "stdout_sha256": _hash_text(check.stdout)["sha256"],
            "stderr_sha256": _hash_text(check.stderr)["sha256"],
        }
    apply = subprocess.run(["git", "apply", "--whitespace=nowarn", str(patch_file)], cwd=workspace, capture_output=True, text=True)
    if apply.returncode != 0:
        return {
            "ok": False,
            "stage": "apply",
            "exit_code": apply.returncode,
            "stdout_sha256": _hash_text(apply.stdout)["sha256"],
            "stderr_sha256": _hash_text(apply.stderr)["sha256"],
        }
    return {
        "ok": True,
        "stage": "apply",
        "exit_code": 0,
        "stdout_sha256": _hash_text(apply.stdout)["sha256"],
        "stderr_sha256": _hash_text(apply.stderr)["sha256"],
    }


def pending_sandbox_patch_executions(store: TaskTapeStore) -> list[dict[str, Any]]:
    terminal_task_ids = {event.task_id for event in store.events() if event.event in TERMINAL_EVENTS and event.payload.get("review_type") == REVIEW_TYPE}
    return [
        event.to_dict()
        for event in store.events()
        if event.event == "review_required" and event.payload.get("review_type") == REVIEW_TYPE and event.task_id not in terminal_task_ids
    ]


def completed_sandbox_patch_executions(store: TaskTapeStore) -> list[dict[str, Any]]:
    return [event.to_dict() for event in store.events() if event.event == "sandbox_patch_execution_completed"]


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


def execute_sandbox_patch_run(
    store: TaskTapeStore,
    *,
    task_id: str,
    diff_text: str,
    validation_commands: list[str],
    actor: str = "SandboxPatchExecutor",
    runner_mode: str | None = None,
) -> dict[str, Any]:
    """Apply the patch in an ephemeral workspace and run validation commands.

    Raw patch text and command output are never stored in Task Tape; only hashes,
    sizes, exit codes, and status flags are recorded.
    """
    plan = _approved_execution_plan(store, task_id)
    if plan is None:
        return {"ok": False, "error": "approved_sandbox_patch_execution_required", "task_id": task_id, "execute_automatically": False}

    expected_hashes = list(plan.get("validation_command_hashes", []))
    provided_hashes = _hash_commands(validation_commands)
    if len(expected_hashes) != len(provided_hashes) or [item["sha256"] for item in expected_hashes] != [item["sha256"] for item in provided_hashes]:
        return {"ok": False, "error": "validation_commands_mismatch", "task_id": task_id, "execute_automatically": False}

    workspace_tmp, workspace = _prepare_workspace()
    patch_result = {"ok": False, "stage": "unknown", "exit_code": 0, "stdout_sha256": None, "stderr_sha256": None}
    command_results: list[dict[str, Any]] = []
    try:
        patch_result = _apply_patch(workspace, diff_text)
        if not patch_result.get("ok"):
            event = store.append_event(
                task_id=task_id,
                event="sandbox_patch_execution_completed",
                target=f"sandbox://execution/{task_id}",
                status="failed_patch_apply",
                payload={
                    "review_type": REVIEW_TYPE,
                    "actor": actor,
                    "patch_applied": False,
                    "commands_executed": False,
                    "tests_run": False,
                    "workspace_copied": True,
                    "workspace_type": plan.get("workspace_type"),
                    "patch_apply_stage": patch_result.get("stage"),
                    "patch_apply_exit_code": patch_result.get("exit_code"),
                    "patch_apply_stdout_sha256": patch_result.get("stdout_sha256"),
                    "patch_apply_stderr_sha256": patch_result.get("stderr_sha256"),
                    "validation_command_hashes": expected_hashes,
                    "validation_command_count": len(expected_hashes),
                    "execute_automatically": False,
                },
            )
            return {"ok": False, "task_id": task_id, "status": "failed_patch_apply", "event": event.to_dict(), "workspace_copied": True, "patch_applied": False, "commands_executed": False, "execute_automatically": False}

        runner = SandboxRunner(str(_project_root() / "sandbox" / "Dockerfile.python"), mode=runner_mode or os.environ.get("CPOS_SANDBOX_MODE", "strict"))
        for command in validation_commands:
            command_result = runner.run_command(str(workspace), command)
            stdout_hash = _hash_text(command_result.get("stdout", ""))
            stderr_hash = _hash_text(command_result.get("stderr", ""))
            command_results.append({
                "command_sha256": _hash_text(command)["sha256"],
                "command_size_bytes": len(command.encode("utf-8")),
                "exit_code": command_result.get("exit_code"),
                "stdout_sha256": stdout_hash["sha256"],
                "stderr_sha256": stderr_hash["sha256"],
                "stdout_size_bytes": stdout_hash["size_bytes"],
                "stderr_size_bytes": stderr_hash["size_bytes"],
                "sandbox_backend": (command_result.get("sandbox") or {}).get("backend"),
                "sandbox_mode": (command_result.get("sandbox") or {}).get("mode"),
                "isolated": (command_result.get("sandbox") or {}).get("isolated"),
                "fallback_used": (command_result.get("sandbox") or {}).get("fallback_used"),
            })
            if command_result.get("exit_code") != 0:
                break

        success = patch_result.get("ok") and all(item.get("exit_code") == 0 for item in command_results)
        status = "completed_success" if success else "completed_with_failures"
        event = store.append_event(
            task_id=task_id,
            event="sandbox_patch_execution_completed",
            target=f"sandbox://execution/{task_id}",
            status=status,
            payload={
                "review_type": REVIEW_TYPE,
                "actor": actor,
                "patch_applied": patch_result.get("ok"),
                "commands_executed": True,
                "tests_run": bool(command_results),
                "workspace_copied": True,
                "workspace_type": plan.get("workspace_type"),
                "patch_apply_stage": patch_result.get("stage"),
                "patch_apply_exit_code": patch_result.get("exit_code"),
                "patch_apply_stdout_sha256": patch_result.get("stdout_sha256"),
                "patch_apply_stderr_sha256": patch_result.get("stderr_sha256"),
                "validation_command_hashes": expected_hashes,
                "validation_command_count": len(expected_hashes),
                "command_results": command_results,
                "success": success,
                "execute_automatically": False,
            },
        )
        return {
            "ok": success,
            "task_id": task_id,
            "status": status,
            "event": event.to_dict(),
            "workspace_copied": True,
            "patch_applied": bool(patch_result.get("ok")),
            "commands_executed": bool(command_results),
            "tests_run": bool(command_results),
            "command_results": command_results,
            "execute_automatically": False,
        }
    finally:
        workspace_tmp.cleanup()


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


if __name__ == "__main__":
    pass
