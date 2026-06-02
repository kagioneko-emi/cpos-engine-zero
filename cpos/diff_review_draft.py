from __future__ import annotations

from typing import Any

from .github_diff_review import create_github_diff_review
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


def _draft_for_task(store: TaskTapeStore, task_id: str) -> dict[str, Any] | None:
    events = store.events_for_task(task_id)
    created = next(
        (
            event
            for event in events
            if event.event == "sandbox_diff_review_draft_created"
            and event.payload.get("review_type") == REVIEW_TYPE
        ),
        None,
    )
    if created is None:
        return None
    return (created.payload or {}).get("draft") or {}


def create_github_diff_review_from_draft(
    store: TaskTapeStore,
    *,
    draft_task_id: str,
    source_task_id: str | None,
    diff_text: str | None = None,
    changed_files: list[str] | None = None,
    validation_commands: list[str] | None = None,
    actor: str = "DiffReviewDraftRouter",
    reason: str | None = None,
) -> dict[str, Any]:
    """Route a metadata-only draft into the normal GitHub diff review gate.

    The raw diff is accepted only as transient input to the downstream diff
    review creator, which stores hashes and counters only. This wrapper records
    lineage metadata so dashboard/report/flow graph can show draft -> review.
    """
    draft = _draft_for_task(store, draft_task_id)
    if draft is None:
        return {"ok": False, "error": "diff_review_draft_required", "draft_task_id": draft_task_id, "execute_automatically": False}
    if not source_task_id:
        return {"ok": False, "error": "approved_pr_dry_run_source_required", "draft_task_id": draft_task_id, "execute_automatically": False}
    if not diff_text:
        return {"ok": False, "error": "diff_text_required", "draft_task_id": draft_task_id, "raw_diff_stored": False, "execute_automatically": False}
    if not isinstance(changed_files, list) or not changed_files:
        return {"ok": False, "error": "changed_files_required", "draft_task_id": draft_task_id, "execute_automatically": False}
    if not isinstance(validation_commands, list) or not validation_commands:
        return {"ok": False, "error": "validation_commands_required", "draft_task_id": draft_task_id, "execute_automatically": False}

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
        result.setdefault("draft_task_id", draft_task_id)
        result.setdefault("raw_diff_stored", False)
        result.setdefault("execute_automatically", False)
        return result

    plan = result.get("plan") or {}
    link_payload = {
        "review_type": "sandbox_diff_review_draft_to_github_diff_review",
        "draft_task_id": draft_task_id,
        "github_diff_review_task_id": result.get("task_id"),
        "source_task_id": source_task_id,
        "candidate_task_id": draft.get("candidate_task_id"),
        "source_execution_task_id": draft.get("source_execution_task_id"),
        "failure_kind": draft.get("failure_kind"),
        "diff_plan_sha256": plan.get("diff_plan_sha256"),
        "diff_sha256": plan.get("diff_sha256"),
        "diff_size_bytes": plan.get("diff_size_bytes"),
        "changed_file_count": len(plan.get("changed_files") or []),
        "validation_command_count": len(plan.get("validation_commands") or []),
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
        event="sandbox_diff_review_draft_linked_to_github_diff_review",
        target=f"sandbox://diff-review-draft/{draft_task_id}/github-diff-review/{result['task_id']}",
        status="linked_metadata_only",
        payload=link_payload,
    )
    result["draft_task_id"] = draft_task_id
    result["draft_link"] = link_event.to_dict()
    result["raw_diff_stored"] = False
    result["diff_text_included"] = False
    return result
