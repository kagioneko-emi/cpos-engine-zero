from __future__ import annotations

from typing import Any

from .sandbox_patch_plan import _digest
from .task_tape import TaskTapeStore

REVIEW_TYPE = "sandbox_diff_review_draft"


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


def _validation_hint(candidate: dict[str, Any]) -> list[str]:
    failure_kind = str(candidate.get("failure_kind") or "")
    if failure_kind == "policy_rejected":
        return ["replace disallowed validation command with pytest-style allowlisted command"]
    if failure_kind == "sandbox_unavailable":
        return ["verify sandbox backend before changing product code"]
    if failure_kind == "patch_apply":
        return ["include git apply --check compatible unified diff"]
    return ["reuse prior validation command scope when possible"]


def pending_diff_review_drafts(store: TaskTapeStore) -> list[dict[str, Any]]:
    return [event.to_dict() for event in store.events() if event.event == "sandbox_diff_review_draft_created"]


def create_diff_review_draft(
    store: TaskTapeStore,
    *,
    candidate_task_id: str,
    actor: str = "DiffReviewDraftBuilder",
    reason: str | None = None,
) -> dict[str, Any]:
    candidate = _auto_fix_candidate_for_task(store, candidate_task_id)
    if candidate is None:
        return {"ok": False, "error": "auto_fix_candidate_required", "candidate_task_id": candidate_task_id, "execute_automatically": False}

    draft = {
        "schema": "cpos.sandbox_diff_review_draft.v1",
        "candidate_task_id": candidate_task_id,
        "replan_task_id": candidate.get("replan_task_id"),
        "retry_task_id": candidate.get("retry_task_id"),
        "source_execution_task_id": candidate.get("source_execution_task_id"),
        "failure_kind": candidate.get("failure_kind"),
        "candidate_strategy": candidate.get("candidate_strategy"),
        "confidence": candidate.get("confidence"),
        "suggested_focus": candidate.get("suggested_focus") or [],
        "candidate_steps": candidate.get("candidate_steps") or [],
        "validation_hints": _validation_hint(candidate),
        "target_api": "POST /github/pr-dry-runs/<source_task_id>/create-diff-review",
        "draft_payload_shape": {
            "diff_text": "<required: human_or_agent_supplied_raw_diff_not_stored_here>",
            "changed_files": "<required: list_of_paths>",
            "validation_commands": "<required: allowlisted_pytest_style_commands>",
            "reason": reason or "auto_fix_candidate_diff_draft",
        },
        "required_human_inputs": [
            "diff_text",
            "changed_files",
            "validation_commands",
            "review_reason",
        ],
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
        "guardrails": [
            "draft contains only payload shape and metadata; no raw diff text",
            "human or agent must supply diff_text at the GitHub diff review endpoint",
            "downstream GitHub diff review and sandbox gates still apply",
            "no automatic patch apply, command execution, commit, push, or PR creation",
        ],
    }
    draft["draft_sha256"] = _digest(draft)
    target = f"sandbox://diff-review-draft/{candidate_task_id}"
    task_id = store.create_task(
        target=target,
        action="sandbox_diff_review_draft_request",
        payload={
            "review_type": REVIEW_TYPE,
            "candidate_task_id": candidate_task_id,
            "replan_task_id": candidate.get("replan_task_id"),
            "source_execution_task_id": candidate.get("source_execution_task_id"),
            "draft_sha256": draft["draft_sha256"],
            "actor": actor,
        },
    )
    event = store.append_event(
        task_id=task_id,
        event="sandbox_diff_review_draft_created",
        target=target,
        status="draft_created",
        payload={"review_type": REVIEW_TYPE, "draft": draft, "actor": actor},
    )
    return {"ok": True, "task_id": task_id, "status": "draft_created", "event": event.to_dict(), "draft": draft, "execute_automatically": False}
