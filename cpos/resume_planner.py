from __future__ import annotations

import argparse
import hashlib
import json
from typing import Any

from .promotion_executor import REVIEW_TYPE as EXECUTION_REVIEW_TYPE
from .task_tape import TaskTapeStore

RESUME_REVIEW_TYPE = "execution_resume_action"


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _events_for_task(store: TaskTapeStore, task_id: str) -> list[dict[str, Any]]:
    return [event.to_dict() for event in store.events_for_task(task_id)]


def _execution_ready_event(store: TaskTapeStore, task_id: str) -> dict[str, Any] | None:
    for event in reversed(_events_for_task(store, task_id)):
        if event.get("event") == "handoff_promotion_execution_ready" and event.get("payload", {}).get("review_type") == EXECUTION_REVIEW_TYPE:
            return event
    return None


def _source_execution_review(store: TaskTapeStore, task_id: str) -> dict[str, Any] | None:
    for event in _events_for_task(store, task_id):
        if event.get("event") == "review_required" and event.get("payload", {}).get("review_type") == EXECUTION_REVIEW_TYPE:
            return event
    return None


def _already_has_resume_proposal(store: TaskTapeStore, task_id: str) -> bool:
    return any(
        event.get("event") == "review_required" and event.get("payload", {}).get("review_type") == RESUME_REVIEW_TYPE
        for event in _events_for_task(store, task_id)
    )


def build_next_action_proposals(store: TaskTapeStore, task_id: str) -> dict[str, Any]:
    ready = _execution_ready_event(store, task_id)
    if ready is None:
        return {"ok": False, "error": "execution_review_not_ready", "task_id": task_id}
    source_review = _source_execution_review(store, task_id)
    if source_review is None:
        return {"ok": False, "error": "source_execution_review_not_found", "task_id": task_id}
    plan = source_review.get("payload", {}).get("plan") or {}
    if not isinstance(plan, dict):
        return {"ok": False, "error": "source_plan_missing", "task_id": task_id}

    proposals: list[dict[str, Any]] = [
        {
            "action_id": "inspect_promotion_plan",
            "title": "Inspect approved promotion plan metadata",
            "purpose": "Confirm source handoff, warnings, counts, and guardrails before any context retrieval.",
            "risk": "low",
            "requires_human_approval": True,
            "inputs_allowed": ["promotion_pointer_id", "plan_sha256", "counts", "warnings", "guardrails"],
            "inputs_blocked": plan.get("blocked_inputs", []),
        }
    ]
    if any(step.get("step") == "request_specific_pointer_references" and step.get("allowed") for step in plan.get("retrieval_steps", [])):
        proposals.append({
            "action_id": "request_scoped_pointer_references",
            "title": "Request scoped pointer references from source context",
            "purpose": "Ask for explicit pointer references only; do not import raw logs or checkpoint content.",
            "risk": "medium",
            "requires_human_approval": True,
            "max_references": next((step.get("max_references") for step in plan.get("retrieval_steps", []) if step.get("step") == "request_specific_pointer_references"), 0),
            "inputs_allowed": ["pointer_id", "summary", "source", "location", "trust_score", "sensitivity_level"],
            "inputs_blocked": plan.get("blocked_inputs", []),
        })
    if plan.get("task_candidates"):
        proposals.append({
            "action_id": "open_fresh_scoped_task",
            "title": "Open a fresh scoped Task Tape task for resumed work",
            "purpose": "Continue work in a new local task history instead of mutating imported/source history.",
            "risk": "medium",
            "requires_human_approval": True,
            "inputs_allowed": ["task_summary", "safe_next_step", "status", "target_hint"],
            "inputs_blocked": plan.get("blocked_inputs", []),
        })

    proposal = {
        "schema": "cpos.execution_resume_proposal.v1",
        "source_task_id": task_id,
        "promotion_pointer_id": ready.get("payload", {}).get("promotion_pointer_id"),
        "plan_sha256": plan.get("plan_sha256"),
        "signature_ok": bool(plan.get("signature_ok")),
        "integrity_ok": bool(plan.get("integrity_ok")),
        "warnings": plan.get("warnings", []),
        "guardrails": plan.get("guardrails", []),
        "blocked_inputs": plan.get("blocked_inputs", []),
        "proposals": proposals,
        "execute_automatically": False,
    }
    proposal["proposal_sha256"] = _digest(proposal)
    return {"ok": True, "proposal": proposal}


def create_resume_proposal_review(store: TaskTapeStore, task_id: str, *, proposer: str = "ExecutionResumePlanner", reason: str | None = None) -> dict[str, Any]:
    if _already_has_resume_proposal(store, task_id):
        return {"ok": False, "error": "resume_proposal_already_exists", "task_id": task_id}
    built = build_next_action_proposals(store, task_id)
    if not built.get("ok"):
        return built
    proposal = built["proposal"]
    event = store.append_event(
        task_id=task_id,
        event="review_required",
        target=proposal.get("promotion_pointer_id"),
        status="pending_review",
        payload={
            "review_type": RESUME_REVIEW_TYPE,
            "proposal": proposal,
            "proposer": proposer,
            "reason": reason,
            "requires_human_approval": True,
        },
    )
    return {"ok": True, "task_id": task_id, "review": event.to_dict(), "proposal": proposal}


def pending_resume_reviews(store: TaskTapeStore) -> list[dict[str, Any]]:
    terminal = {
        event.task_id
        for event in store.events()
        if event.event in {"resume_action_approved", "resume_action_rejected"}
        and event.payload.get("review_type") == RESUME_REVIEW_TYPE
    }
    rows = []
    for event in store.events():
        if event.event == "review_required" and event.payload.get("review_type") == RESUME_REVIEW_TYPE and event.task_id not in terminal:
            rows.append(event.to_dict())
    return rows


def approve_resume_review(store: TaskTapeStore, task_id: str, *, approver: str = "ExecutionResumePlanner", action_id: str | None = None, reason: str | None = None) -> dict[str, Any]:
    review = next((row for row in pending_resume_reviews(store) if row.get("task_id") == task_id), None)
    if review is None:
        return {"ok": False, "error": "pending_resume_review_not_found", "task_id": task_id}
    proposal = review.get("payload", {}).get("proposal") or {}
    proposal_actions = {item.get("action_id") for item in proposal.get("proposals", []) if isinstance(item, dict)}
    if action_id and action_id not in proposal_actions:
        return {"ok": False, "error": "unknown_action_id", "task_id": task_id, "action_id": action_id}
    chosen = action_id or (proposal.get("proposals", [{}])[0].get("action_id") if proposal.get("proposals") else None)
    event = store.append_event(
        task_id=task_id,
        event="resume_action_approved",
        target=review.get("target"),
        status="approved",
        payload={
            "review_type": RESUME_REVIEW_TYPE,
            "approved_by": approver,
            "reason": reason,
            "proposal_sha256": proposal.get("proposal_sha256"),
            "approved_action_id": chosen,
            "execute_automatically": False,
        },
    )
    store.append_event(
        task_id=task_id,
        event="resume_action_ready",
        target=review.get("target"),
        status="ready",
        payload={
            "review_type": RESUME_REVIEW_TYPE,
            "approved_action_id": chosen,
            "safe_resume": True,
            "execute_automatically": False,
        },
    )
    return {"ok": True, "task_id": task_id, "status": "approved", "approved_action_id": chosen, "event": event.to_dict()}


def reject_resume_review(store: TaskTapeStore, task_id: str, *, reason: str = "manual_reject") -> dict[str, Any]:
    review = next((row for row in pending_resume_reviews(store) if row.get("task_id") == task_id), None)
    if review is None:
        return {"ok": False, "error": "pending_resume_review_not_found", "task_id": task_id}
    event = store.append_event(
        task_id=task_id,
        event="resume_action_rejected",
        target=review.get("target"),
        status="rejected",
        payload={"review_type": RESUME_REVIEW_TYPE, "reason": reason},
    )
    return {"ok": True, "task_id": task_id, "status": "rejected", "event": event.to_dict()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create review-gated next-action proposals from approved handoff execution reviews.")
    parser.add_argument("--task-tape-path", default="tapes/task_runs.jsonl")
    parser.add_argument("--task-checkpoint-path", default="tapes/task_checkpoints.jsonl")
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("task_id")
    create = sub.add_parser("create-review")
    create.add_argument("task_id")
    create.add_argument("--proposer", default="CLIResumePlanner")
    create.add_argument("--reason")
    sub.add_parser("list")
    approve = sub.add_parser("approve")
    approve.add_argument("task_id")
    approve.add_argument("--action-id")
    approve.add_argument("--approver", default="CLIResumePlanner")
    approve.add_argument("--reason")
    reject = sub.add_parser("reject")
    reject.add_argument("task_id")
    reject.add_argument("--reason", default="manual_reject")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    store = TaskTapeStore(args.task_tape_path, args.task_checkpoint_path)
    if args.command == "plan":
        result = build_next_action_proposals(store, args.task_id)
    elif args.command == "create-review":
        result = create_resume_proposal_review(store, args.task_id, proposer=args.proposer, reason=args.reason)
    elif args.command == "list":
        result = {"ok": True, "count": len(pending_resume_reviews(store)), "reviews": pending_resume_reviews(store)}
    elif args.command == "approve":
        result = approve_resume_review(store, args.task_id, approver=args.approver, action_id=args.action_id, reason=args.reason)
    else:
        result = reject_resume_review(store, args.task_id, reason=args.reason)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
