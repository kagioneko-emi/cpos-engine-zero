from __future__ import annotations

import hashlib
import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from sandbox.runner import SandboxRunner

from .human_escalation import review_escalation_decision
from .sandbox_patch_plan import REVIEW_TYPE as PATCH_PLAN_REVIEW_TYPE, _digest
from .task_tape import TaskTapeStore

REVIEW_TYPE = "sandbox_patch_execution"
RETRY_REVIEW_TYPE = "sandbox_patch_execution_retry"
REPLAN_REVIEW_TYPE = "sandbox_patch_replan_template"
DIFF_INTAKE_REVIEW_TYPE = "sandbox_replan_diff_intake"
TERMINAL_EVENTS = {"sandbox_patch_execution_approved", "sandbox_patch_execution_rejected"}
RETRY_TERMINAL_EVENTS = {"sandbox_patch_execution_retry_approved", "sandbox_patch_execution_retry_rejected"}
DANGEROUS_COMMAND_CHARS = set(";&|`$<>\n\r")
VALID_RUNNER_MODES = {"strict", "permissive", "local-dev"}
ALLOWED_VALIDATION_COMMAND_PREFIXES = (
    ("pytest",),
    ("python", "-m", "pytest"),
    ("python3", "-m", "pytest"),
    (".venv/bin/pytest",),
    (".venv/bin/python", "-m", "pytest"),
)


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


def _command_prefix_allowed(parts: list[str]) -> bool:
    return any(tuple(parts[: len(prefix)]) == prefix for prefix in ALLOWED_VALIDATION_COMMAND_PREFIXES)


def validate_validation_commands(commands: list[str]) -> dict[str, Any]:
    for index, command in enumerate(commands):
        if not isinstance(command, str) or not command.strip():
            return {"ok": False, "error": "validation_command_empty", "command_index": index}
        if any(char in command for char in DANGEROUS_COMMAND_CHARS):
            return {
                "ok": False,
                "error": "validation_command_disallowed_shell_syntax",
                "command_index": index,
                "command_sha256": _hash_text(command)["sha256"],
            }
        try:
            parts = shlex.split(command)
        except ValueError:
            return {
                "ok": False,
                "error": "validation_command_parse_failed",
                "command_index": index,
                "command_sha256": _hash_text(command)["sha256"],
            }
        if not _command_prefix_allowed(parts):
            return {
                "ok": False,
                "error": "validation_command_prefix_not_allowed",
                "command_index": index,
                "command_sha256": _hash_text(command)["sha256"],
                "allowed_prefixes": [" ".join(prefix) for prefix in ALLOWED_VALIDATION_COMMAND_PREFIXES],
            }
    return {"ok": True}


def resolve_runner_mode(requested_mode: str | None) -> dict[str, Any]:
    mode = (requested_mode or os.environ.get("CPOS_SANDBOX_MODE", "strict") or "strict").lower()
    if mode not in VALID_RUNNER_MODES:
        mode = "strict"
    if mode == "local-dev" and os.environ.get("CPOS_ALLOW_LOCAL_DEV_RUN", "").lower() not in {"1", "true", "yes"}:
        return {"ok": False, "error": "local_dev_runner_mode_requires_explicit_opt_in", "runner_mode": mode}
    return {"ok": True, "runner_mode": mode}


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


def ready_to_run_sandbox_patch_executions(store: TaskTapeStore) -> list[dict[str, Any]]:
    """Return pending execution reviews as a metadata-only ready-to-run queue.

    This helper does not approve reviews, copy workspaces, apply patches, run
    commands, or persist raw diff/output values. It only makes the final human
    gate easy to find after safe-advance flows create pending execution reviews.
    """
    rows: list[dict[str, Any]] = []
    for review in pending_sandbox_patch_executions(store):
        payload = review.get("payload") or {}
        plan = payload.get("plan") or {}
        task_id = str(review.get("task_id") or "")
        rows.append({
            "schema": "cpos.sandbox_ready_to_run_execution_review.v1",
            "task_id": task_id,
            "review_type": REVIEW_TYPE,
            "status": review.get("status"),
            "timestamp": review.get("timestamp"),
            "target": review.get("target"),
            "repo": plan.get("repo"),
            "patch_task_id": plan.get("patch_task_id"),
            "diff_task_id": plan.get("diff_task_id"),
            "source_task_id": plan.get("source_task_id"),
            "changed_files": list(plan.get("changed_files", [])),
            "changed_file_count": len(plan.get("changed_files", [])),
            "validation_command_count": int(plan.get("validation_command_count", 0) or 0),
            "validation_command_hashes": list(plan.get("validation_command_hashes", [])),
            "validation_values_stored": False,
            "runner_mode": plan.get("runner_mode") or "strict",
            "sandbox_execution_sha256": plan.get("sandbox_execution_sha256"),
            "human_escalation": payload.get("human_escalation"),
            "next_step": "explicit_approve_then_transient_diff_run",
            "approval_endpoint": f"/sandbox/executions/{task_id}/approve",
            "run_endpoint": f"/sandbox/executions/{task_id}/run",
            "rejection_endpoint": f"/sandbox/executions/{task_id}/reject",
            "requires_explicit_approval": True,
            "requires_transient_diff_text": True,
            "requires_validation_commands": True,
            "workspace_copied": False,
            "patch_applied": False,
            "commands_executed": False,
            "tests_run": False,
            "raw_diff_stored": False,
            "raw_outputs_stored": False,
            "command_outputs_stored": False,
            "execute_automatically": False,
            "live_repo_patch": False,
            "commit_created": False,
            "pushed": False,
            "pr_created": False,
            "metadata_only": True,
        })
    return rows


def completed_sandbox_patch_executions(store: TaskTapeStore) -> list[dict[str, Any]]:
    return [event.to_dict() for event in store.events() if event.event == "sandbox_patch_execution_completed"]



def _latest_completed_execution_event(store: TaskTapeStore, task_id: str) -> dict[str, Any] | None:
    matches = [event.to_dict() for event in store.events_for_task(task_id) if event.event == "sandbox_patch_execution_completed"]
    return matches[-1] if matches else None


def _first_failed_command(command_results: list[dict[str, Any]]) -> dict[str, Any] | None:
    for index, result in enumerate(command_results):
        if result.get("exit_code") != 0:
            return {
                "command_index": index,
                "command_sha256": result.get("command_sha256"),
                "exit_code": result.get("exit_code"),
                "stdout_sha256": result.get("stdout_sha256"),
                "stderr_sha256": result.get("stderr_sha256"),
                "stdout_size_bytes": result.get("stdout_size_bytes"),
                "stderr_size_bytes": result.get("stderr_size_bytes"),
                "sandbox_backend": result.get("sandbox_backend"),
                "sandbox_mode": result.get("sandbox_mode"),
                "isolated": result.get("isolated"),
                "fallback_used": result.get("fallback_used"),
            }
    return None


def classify_sandbox_execution_failure(payload: dict[str, Any], status: str | None = None) -> str:
    if payload.get("policy_rejected"):
        return "policy_rejected"
    if not payload.get("patch_applied"):
        return "patch_apply"
    command_results = payload.get("command_results") or []
    for result in command_results:
        sandbox_backend = result.get("sandbox_backend")
        exit_code = result.get("exit_code")
        if sandbox_backend in {"none", None} and exit_code == 125:
            return "sandbox_unavailable"
        if result.get("isolated") is False and result.get("fallback_used") is False and exit_code == 125:
            return "sandbox_unavailable"
    if any(result.get("exit_code") != 0 for result in command_results):
        return "validation_command"
    if status and status not in {"completed_success", "template_created"}:
        return "sandbox_unavailable"
    return "unknown"


def pending_sandbox_patch_execution_retries(store: TaskTapeStore) -> list[dict[str, Any]]:
    terminal_task_ids = {event.task_id for event in store.events() if event.event in RETRY_TERMINAL_EVENTS and event.payload.get("review_type") == RETRY_REVIEW_TYPE}
    return [
        event.to_dict()
        for event in store.events()
        if event.event == "review_required" and event.payload.get("review_type") == RETRY_REVIEW_TYPE and event.task_id not in terminal_task_ids
    ]


def create_sandbox_patch_execution_retry_review(
    store: TaskTapeStore,
    *,
    source_task_id: str,
    actor: str = "SandboxPatchRetryPlanner",
    reason: str | None = None,
) -> dict[str, Any]:
    completed = _latest_completed_execution_event(store, source_task_id)
    if completed is None:
        return {"ok": False, "error": "completed_sandbox_execution_required", "source_task_id": source_task_id, "execute_automatically": False}
    payload = completed.get("payload") or {}
    if payload.get("success") is True or completed.get("status") == "completed_success":
        return {"ok": False, "error": "failed_sandbox_execution_required", "source_task_id": source_task_id, "execute_automatically": False}

    command_results = payload.get("command_results") or []
    failed_command = _first_failed_command(command_results)
    retry_plan = {
        "schema": "cpos.sandbox_patch_execution_retry.v1",
        "source_execution_task_id": source_task_id,
        "source_execution_status": completed.get("status"),
        "source_event_id": completed.get("id"),
        "failure_kind": classify_sandbox_execution_failure(payload, completed.get("status")),
        "patch_applied": payload.get("patch_applied"),
        "commands_executed": payload.get("commands_executed"),
        "tests_run": payload.get("tests_run"),
        "workspace_copied": payload.get("workspace_copied"),
        "patch_apply_stage": payload.get("patch_apply_stage"),
        "patch_apply_exit_code": payload.get("patch_apply_exit_code"),
        "patch_apply_stdout_sha256": payload.get("patch_apply_stdout_sha256"),
        "patch_apply_stderr_sha256": payload.get("patch_apply_stderr_sha256"),
        "validation_command_hashes": payload.get("validation_command_hashes") or [],
        "validation_command_count": payload.get("validation_command_count", 0),
        "failed_command": failed_command,
        "retry_strategy": "create_new_diff_or_validation_plan_before_rerun",
        "raw_outputs_stored": False,
        "raw_patch_stored": False,
        "workspace_reused": False,
        "execute_automatically": False,
        "requires_human_approval": True,
        "next_step": "review_failure_metadata_then_create_new_sandbox_patch_plan",
        "reason": reason,
        "guardrails": [
            "retry review uses failure metadata only; no raw stdout/stderr",
            "do not reuse ephemeral workspace",
            "do not rerun automatically",
            "new patch/diff content must pass the full review chain again",
        ],
    }
    retry_plan["retry_plan_sha256"] = _digest(retry_plan)
    human_escalation = review_escalation_decision(
        review_type=RETRY_REVIEW_TYPE,
        summary=f"Sandbox execution retry review for {source_task_id}",
        confidence=0.78,
        risk="medium",
        user_confirmation_required=True,
    )
    target = f"sandbox://execution-retry/{source_task_id}"
    task_id = store.create_task(
        target=target,
        action="sandbox_patch_execution_retry_request",
        payload={
            "review_type": RETRY_REVIEW_TYPE,
            "source_execution_task_id": source_task_id,
            "retry_plan_sha256": retry_plan["retry_plan_sha256"],
            "human_escalation": human_escalation,
            "actor": actor,
        },
    )
    event = store.append_event(
        task_id=task_id,
        event="review_required",
        target=target,
        status="pending_review",
        payload={"review_type": RETRY_REVIEW_TYPE, "plan": retry_plan, "human_escalation": human_escalation, "actor": actor},
    )
    return {"ok": True, "task_id": task_id, "status": "pending_review", "review": event.to_dict(), "plan": retry_plan, "execute_automatically": False}


def approve_sandbox_patch_execution_retry(store: TaskTapeStore, task_id: str, *, approver: str = "SandboxPatchRetryReviewer", reason: str | None = None, confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        return {"ok": False, "error": "confirm_required", "task_id": task_id}
    review = next((row for row in pending_sandbox_patch_execution_retries(store) if row.get("task_id") == task_id), None)
    if review is None:
        return {"ok": False, "error": "pending_sandbox_patch_execution_retry_not_found", "task_id": task_id}
    plan = (review.get("payload") or {}).get("plan") or {}
    event = store.append_event(
        task_id=task_id,
        event="sandbox_patch_execution_retry_approved",
        target=review.get("target"),
        status="approved_retry_plan_only",
        payload={
            "review_type": RETRY_REVIEW_TYPE,
            "approved_by": approver,
            "reason": reason,
            "source_execution_task_id": plan.get("source_execution_task_id"),
            "retry_plan_sha256": plan.get("retry_plan_sha256"),
            "next_step": "create_new_diff_or_validation_plan_before_rerun",
            "execute_automatically": False,
            "raw_outputs_stored": False,
            "workspace_reused": False,
            "commit_created": False,
            "pushed": False,
            "pr_created": False,
        },
    )
    return {"ok": True, "task_id": task_id, "status": "approved_retry_plan_only", "event": event.to_dict(), "execute_automatically": False}


def reject_sandbox_patch_execution_retry(store: TaskTapeStore, task_id: str, *, reason: str = "manual_reject") -> dict[str, Any]:
    review = next((row for row in pending_sandbox_patch_execution_retries(store) if row.get("task_id") == task_id), None)
    if review is None:
        return {"ok": False, "error": "pending_sandbox_patch_execution_retry_not_found", "task_id": task_id}
    event = store.append_event(
        task_id=task_id,
        event="sandbox_patch_execution_retry_rejected",
        target=review.get("target"),
        status="rejected",
        payload={"review_type": RETRY_REVIEW_TYPE, "reason": reason, "execute_automatically": False},
    )
    return {"ok": True, "task_id": task_id, "status": "rejected", "event": event.to_dict(), "execute_automatically": False}


def _approved_retry_plan(store: TaskTapeStore, task_id: str) -> dict[str, Any] | None:
    events = store.events_for_task(task_id)
    review = next((event for event in events if event.event == "review_required" and event.payload.get("review_type") == RETRY_REVIEW_TYPE), None)
    approved = next((event for event in events if event.event == "sandbox_patch_execution_retry_approved" and event.payload.get("review_type") == RETRY_REVIEW_TYPE), None)
    if review is None or approved is None:
        return None
    return (review.payload or {}).get("plan") or {}


def sandbox_patch_replan_templates(store: TaskTapeStore) -> list[dict[str, Any]]:
    return [event.to_dict() for event in store.events() if event.event == "sandbox_patch_replan_template_created"]


def create_sandbox_patch_replan_template(
    store: TaskTapeStore,
    *,
    retry_task_id: str,
    actor: str = "SandboxPatchReplanTemplate",
    reason: str | None = None,
) -> dict[str, Any]:
    retry_plan = _approved_retry_plan(store, retry_task_id)
    if retry_plan is None:
        return {"ok": False, "error": "approved_sandbox_retry_required", "retry_task_id": retry_task_id, "execute_automatically": False}

    failure_kind = retry_plan.get("failure_kind")
    failed_command = retry_plan.get("failed_command") or {}
    suggested_focus = {
        "patch_apply": ["regenerate_diff_against_current_base", "verify_changed_file_paths", "rerun_git_apply_check_in_sandbox"],
        "validation_command": ["inspect_failed_test_metadata", "create_new_diff_review", "preserve_or_reduce_validation_command_scope"],
        "sandbox_unavailable": ["verify_sandbox_backend", "check_docker_or_runner_health", "rerun_after_environment_fix"],
        "policy_rejected": ["review_policy_rejection_metadata", "adjust_validation_command_or_runner_mode", "resubmit_through_review_chain"],
    }.get(str(failure_kind), ["review_failure_metadata", "create_new_diff_review"] )
    template = {
        "schema": "cpos.sandbox_patch_replan_template.v1",
        "retry_task_id": retry_task_id,
        "source_execution_task_id": retry_plan.get("source_execution_task_id"),
        "failure_kind": failure_kind,
        "source_execution_status": retry_plan.get("source_execution_status"),
        "patch_apply_stage": retry_plan.get("patch_apply_stage"),
        "patch_apply_exit_code": retry_plan.get("patch_apply_exit_code"),
        "failed_command": failed_command,
        "validation_command_hashes": retry_plan.get("validation_command_hashes") or [],
        "validation_command_count": retry_plan.get("validation_command_count", 0),
        "suggested_focus": suggested_focus,
        "next_review_chain": [
            "github_diff_review",
            "sandbox_patch_plan",
            "sandbox_patch_execution_review",
            "sandbox_patch_execution_run",
        ],
        "raw_outputs_stored": False,
        "raw_patch_stored": False,
        "workspace_reused": False,
        "diff_text_included": False,
        "execute_automatically": False,
        "commit_created": False,
        "pushed": False,
        "pr_created": False,
        "requires_human_approval": True,
        "reason": reason,
        "guardrails": [
            "template contains metadata only; no raw stdout/stderr",
            "new diff text must be supplied through the normal diff review path",
            "do not reuse failed ephemeral workspace",
            "no commit/push/PR from replan template",
        ],
    }
    template["replan_template_sha256"] = _digest(template)
    target = f"sandbox://replan-template/{retry_task_id}"
    task_id = store.create_task(
        target=target,
        action="sandbox_patch_replan_template_request",
        payload={
            "review_type": REPLAN_REVIEW_TYPE,
            "retry_task_id": retry_task_id,
            "source_execution_task_id": retry_plan.get("source_execution_task_id"),
            "replan_template_sha256": template["replan_template_sha256"],
            "actor": actor,
        },
    )
    event = store.append_event(
        task_id=task_id,
        event="sandbox_patch_replan_template_created",
        target=target,
        status="template_created",
        payload={"review_type": REPLAN_REVIEW_TYPE, "template": template, "actor": actor},
    )
    return {"ok": True, "task_id": task_id, "status": "template_created", "event": event.to_dict(), "template": template, "execute_automatically": False}


def _replan_template_for_task(store: TaskTapeStore, task_id: str) -> dict[str, Any] | None:
    events = store.events_for_task(task_id)
    created = next((event for event in events if event.event == "sandbox_patch_replan_template_created" and event.payload.get("review_type") == REPLAN_REVIEW_TYPE), None)
    if created is None:
        return None
    return (created.payload or {}).get("template") or {}


def sandbox_replan_diff_intakes(store: TaskTapeStore) -> list[dict[str, Any]]:
    return [event.to_dict() for event in store.events() if event.event == "sandbox_replan_diff_intake_created"]


def create_sandbox_replan_diff_intake(
    store: TaskTapeStore,
    *,
    replan_task_id: str,
    actor: str = "SandboxReplanDiffIntake",
    reason: str | None = None,
) -> dict[str, Any]:
    template = _replan_template_for_task(store, replan_task_id)
    if template is None:
        return {"ok": False, "error": "replan_template_required", "replan_task_id": replan_task_id, "execute_automatically": False}

    intake = {
        "schema": "cpos.sandbox_replan_diff_intake.v1",
        "replan_task_id": replan_task_id,
        "retry_task_id": template.get("retry_task_id"),
        "source_execution_task_id": template.get("source_execution_task_id"),
        "failure_kind": template.get("failure_kind"),
        "suggested_focus": template.get("suggested_focus") or [],
        "next_review_chain": template.get("next_review_chain") or [],
        "required_human_inputs": [
            "diff_text",
            "changed_files",
            "validation_commands",
            "repo",
            "base_branch",
            "proposed_branch",
        ],
        "target_api": "POST /github/pr-dry-runs/<source_task_id>/create-diff-review",
        "raw_diff_stored": False,
        "raw_outputs_stored": False,
        "diff_text_included": False,
        "execute_automatically": False,
        "commit_created": False,
        "pushed": False,
        "pr_created": False,
        "requires_human_approval": True,
        "reason": reason,
        "guardrails": [
            "this intake is a checklist only; it never stores diff_text",
            "human must supply raw diff through normal diff review API",
            "all downstream sandbox gates still apply",
            "no commit/push/PR from intake",
        ],
    }
    intake["diff_intake_sha256"] = _digest(intake)
    target = f"sandbox://diff-intake/{replan_task_id}"
    task_id = store.create_task(
        target=target,
        action="sandbox_replan_diff_intake_request",
        payload={
            "review_type": DIFF_INTAKE_REVIEW_TYPE,
            "replan_task_id": replan_task_id,
            "source_execution_task_id": template.get("source_execution_task_id"),
            "diff_intake_sha256": intake["diff_intake_sha256"],
            "actor": actor,
        },
    )
    event = store.append_event(
        task_id=task_id,
        event="sandbox_replan_diff_intake_created",
        target=target,
        status="intake_created",
        payload={"review_type": DIFF_INTAKE_REVIEW_TYPE, "intake": intake, "actor": actor},
    )
    return {"ok": True, "task_id": task_id, "status": "intake_created", "event": event.to_dict(), "intake": intake, "execute_automatically": False}

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
    human_escalation = review_escalation_decision(
        review_type=REVIEW_TYPE,
        summary=f"Sandbox patch execution review for {patch_plan.get('repo')}",
        confidence=0.84,
        risk="medium",
        user_confirmation_required=True,
    )
    target = f"sandbox://execution/{patch_task_id}"
    task_id = store.create_task(
        target=target,
        action="sandbox_patch_execution_request",
        payload={
            "review_type": REVIEW_TYPE,
            "patch_task_id": patch_task_id,
            "repo": patch_plan.get("repo"),
            "sandbox_execution_sha256": execution_plan["sandbox_execution_sha256"],
            "human_escalation": human_escalation,
            "actor": actor,
        },
    )
    event = store.append_event(
        task_id=task_id,
        event="review_required",
        target=target,
        status="pending_review",
        payload={"review_type": REVIEW_TYPE, "plan": execution_plan, "human_escalation": human_escalation, "actor": actor},
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

    command_validation = validate_validation_commands(validation_commands)
    if not command_validation.get("ok"):
        return {**command_validation, "ok": False, "failure_kind": "policy_rejected", "policy_rejected": True, "task_id": task_id, "execute_automatically": False}

    runner_mode_result = resolve_runner_mode(runner_mode)
    if not runner_mode_result.get("ok"):
        return {**runner_mode_result, "ok": False, "failure_kind": "policy_rejected", "policy_rejected": True, "task_id": task_id, "execute_automatically": False}
    effective_runner_mode = runner_mode_result["runner_mode"]

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
                    "failure_kind": "patch_apply",
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
            return {"ok": False, "task_id": task_id, "status": "failed_patch_apply", "failure_kind": "patch_apply", "event": event.to_dict(), "workspace_copied": True, "patch_applied": False, "commands_executed": False, "execute_automatically": False}

        runner = SandboxRunner(str(_project_root() / "sandbox" / "Dockerfile.python"), mode=effective_runner_mode)
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
        failure_kind = None if success else classify_sandbox_execution_failure({"patch_applied": patch_result.get("ok"), "command_results": command_results}, status)
        event = store.append_event(
            task_id=task_id,
            event="sandbox_patch_execution_completed",
            target=f"sandbox://execution/{task_id}",
            status=status,
            payload={
                "review_type": REVIEW_TYPE,
                "actor": actor,
                "failure_kind": failure_kind,
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
            "failure_kind": failure_kind,
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
