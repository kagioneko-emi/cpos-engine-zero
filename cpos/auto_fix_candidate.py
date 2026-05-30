from __future__ import annotations

from typing import Any

from .sandbox_patch_plan import _digest
from .task_tape import TaskTapeStore

REVIEW_TYPE = "sandbox_auto_fix_candidate"


def _replan_template_for_task(store: TaskTapeStore, task_id: str) -> dict[str, Any] | None:
    events = store.events_for_task(task_id)
    created = next(
        (
            event
            for event in events
            if event.event == "sandbox_patch_replan_template_created"
            and event.payload.get("review_type") == "sandbox_patch_replan_template"
        ),
        None,
    )
    if created is None:
        return None
    return (created.payload or {}).get("template") or {}


def _strategy_for_failure(failure_kind: str | None) -> dict[str, Any]:
    strategies = {
        "patch_apply": {
            "strategy": "regenerate_patch_against_current_base",
            "confidence": 0.72,
            "candidate_steps": [
                "verify changed file paths and base branch",
                "regenerate diff against current repository state",
                "rerun git apply check in ephemeral sandbox",
            ],
        },
        "validation_command": {
            "strategy": "target_failed_validation_metadata",
            "confidence": 0.68,
            "candidate_steps": [
                "inspect failed command hash and affected test scope",
                "modify the smallest related code path",
                "preserve validation command list for rerun comparison",
            ],
        },
        "sandbox_unavailable": {
            "strategy": "repair_execution_environment_before_code_change",
            "confidence": 0.61,
            "candidate_steps": [
                "check sandbox backend health",
                "verify Docker/local runner policy",
                "do not change product code until environment is healthy",
            ],
        },
        "policy_rejected": {
            "strategy": "adjust_policy_inputs_not_code",
            "confidence": 0.64,
            "candidate_steps": [
                "review rejected command or runner mode metadata",
                "replace disallowed validation command with allowed pytest-style command",
                "resubmit through review chain",
            ],
        },
    }
    return strategies.get(str(failure_kind), {
        "strategy": "review_failure_metadata_before_patch",
        "confidence": 0.55,
        "candidate_steps": [
            "review failure metadata",
            "identify minimal changed files",
            "submit a new diff review",
        ],
    })


def pending_auto_fix_candidates(store: TaskTapeStore) -> list[dict[str, Any]]:
    return [event.to_dict() for event in store.events() if event.event == "sandbox_auto_fix_candidate_created"]


def create_auto_fix_candidate(
    store: TaskTapeStore,
    *,
    replan_task_id: str,
    actor: str = "AutoFixCandidateBuilder",
    reason: str | None = None,
) -> dict[str, Any]:
    template = _replan_template_for_task(store, replan_task_id)
    if template is None:
        return {"ok": False, "error": "replan_template_required", "replan_task_id": replan_task_id, "execute_automatically": False}

    failure_kind = template.get("failure_kind")
    strategy = _strategy_for_failure(failure_kind)
    failed_command = template.get("failed_command") or {}
    candidate = {
        "schema": "cpos.sandbox_auto_fix_candidate.v1",
        "replan_task_id": replan_task_id,
        "retry_task_id": template.get("retry_task_id"),
        "source_execution_task_id": template.get("source_execution_task_id"),
        "failure_kind": failure_kind,
        "source_execution_status": template.get("source_execution_status"),
        "patch_apply_stage": template.get("patch_apply_stage"),
        "patch_apply_exit_code": template.get("patch_apply_exit_code"),
        "failed_command": {
            "command_index": failed_command.get("command_index"),
            "command_sha256": failed_command.get("command_sha256"),
            "exit_code": failed_command.get("exit_code"),
            "stdout_sha256": failed_command.get("stdout_sha256"),
            "stderr_sha256": failed_command.get("stderr_sha256"),
            "stdout_size_bytes": failed_command.get("stdout_size_bytes"),
            "stderr_size_bytes": failed_command.get("stderr_size_bytes"),
        },
        "suggested_focus": template.get("suggested_focus") or [],
        "candidate_strategy": strategy["strategy"],
        "candidate_steps": strategy["candidate_steps"],
        "confidence": strategy["confidence"],
        "required_human_inputs": [
            "new_diff_text",
            "changed_files",
            "validation_commands",
            "review_reason",
        ],
        "next_api": "POST /github/pr-dry-runs/<source_task_id>/create-diff-review",
        "raw_outputs_stored": False,
        "raw_patch_stored": False,
        "raw_diff_stored": False,
        "diff_text_included": False,
        "workspace_reused": False,
        "execute_automatically": False,
        "commit_created": False,
        "pushed": False,
        "pr_created": False,
        "requires_human_approval": True,
        "reason": reason,
        "guardrails": [
            "candidate is metadata-only; it does not include patch text",
            "raw stdout/stderr remain excluded",
            "human or agent must submit a new diff through the normal review chain",
            "no automatic patch apply, commit, push, or PR creation",
        ],
    }
    candidate["candidate_sha256"] = _digest(candidate)
    target = f"sandbox://auto-fix-candidate/{replan_task_id}"
    task_id = store.create_task(
        target=target,
        action="sandbox_auto_fix_candidate_request",
        payload={
            "review_type": REVIEW_TYPE,
            "replan_task_id": replan_task_id,
            "source_execution_task_id": template.get("source_execution_task_id"),
            "candidate_sha256": candidate["candidate_sha256"],
            "actor": actor,
        },
    )
    event = store.append_event(
        task_id=task_id,
        event="sandbox_auto_fix_candidate_created",
        target=target,
        status="candidate_created",
        payload={"review_type": REVIEW_TYPE, "candidate": candidate, "actor": actor},
    )
    return {"ok": True, "task_id": task_id, "status": "candidate_created", "event": event.to_dict(), "candidate": candidate, "execute_automatically": False}
