from __future__ import annotations

import argparse
import json
from typing import Any

from .handoff_promotion import PROMOTION_RULE
from .pointer_os import PointerManager
from .task_tape import TaskTapeStore

REVIEW_TYPE = "handoff_promotion_execution"


def _safe_plan_from_pointer(pointer) -> dict[str, Any]:
    plan = pointer.metadata.get("plan") if isinstance(pointer.metadata, dict) else None
    if not isinstance(plan, dict):
        raise ValueError("promotion_plan_missing")
    return {
        "schema": plan.get("schema"),
        "plan_sha256": plan.get("plan_sha256"),
        "source_pointer_id": plan.get("source_pointer_id"),
        "source_bundle_sha256": plan.get("source_bundle_sha256"),
        "signature_ok": bool(plan.get("signature_ok")),
        "integrity_ok": bool(plan.get("integrity_ok")),
        "counts": plan.get("counts") if isinstance(plan.get("counts"), dict) else {},
        "retrieval_steps": plan.get("retrieval_steps") if isinstance(plan.get("retrieval_steps"), list) else [],
        "task_candidates": plan.get("task_candidates") if isinstance(plan.get("task_candidates"), list) else [],
        "blocked_inputs": plan.get("blocked_inputs") if isinstance(plan.get("blocked_inputs"), list) else [],
        "guardrails": plan.get("guardrails") if isinstance(plan.get("guardrails"), list) else [],
        "warnings": plan.get("warnings") if isinstance(plan.get("warnings"), list) else [],
    }


def create_execution_review(
    pointer_manager: PointerManager,
    task_store: TaskTapeStore,
    promotion_pointer_id: str,
    *,
    requester: str = "PromotionExecutor",
    reason: str | None = None,
) -> dict[str, Any]:
    pointer = next((p for p in pointer_manager.load() if p.pointer_id == promotion_pointer_id), None)
    if pointer is None:
        return {"ok": False, "error": "promotion_pointer_not_found", "pointer_id": promotion_pointer_id}
    if pointer.context_type != "handoff_promotion_plan":
        return {"ok": False, "error": "not_promotion_pointer", "pointer_id": promotion_pointer_id}
    if pointer.retrieval_rule != PROMOTION_RULE:
        return {"ok": False, "error": "promotion_pointer_not_review_gated", "pointer_id": promotion_pointer_id}

    plan = _safe_plan_from_pointer(pointer)
    task_id = task_store.create_task(
        target=promotion_pointer_id,
        action="handoff_promotion_execution_review",
        payload={
            "review_type": REVIEW_TYPE,
            "promotion_pointer_id": promotion_pointer_id,
            "source_pointer_id": plan.get("source_pointer_id"),
            "plan_sha256": plan.get("plan_sha256"),
            "requester": requester,
        },
    )
    review_event = task_store.append_event(
        task_id=task_id,
        event="review_required",
        target=promotion_pointer_id,
        status="pending_review",
        payload={
            "review_type": REVIEW_TYPE,
            "promotion_pointer_id": promotion_pointer_id,
            "plan": plan,
            "requester": requester,
            "reason": reason,
            "requires_human_approval": True,
            "execution_mode": "metadata_only_resume_plan",
            "blocked_inputs": plan.get("blocked_inputs", []),
        },
    )
    pointer_manager._audit("handoff_promotion_execution_review_created", promotion_pointer_id, {"task_id": task_id, "requester": requester, "reason": reason})
    return {"ok": True, "task_id": task_id, "review": review_event.to_dict()}


def pending_execution_reviews(task_store: TaskTapeStore) -> list[dict[str, Any]]:
    terminal_task_ids = {
        event.task_id
        for event in task_store.events()
        if event.event in {"review_approved", "review_rejected"}
        and event.payload.get("review_type") == REVIEW_TYPE
    }
    rows = []
    for event in task_store.events():
        if event.event != "review_required" or event.task_id in terminal_task_ids:
            continue
        if event.payload.get("review_type") != REVIEW_TYPE:
            continue
        row = event.to_dict()
        payload = dict(row.get("payload", {}))
        # Keep safe plan metadata only. There is no proposed_code/checkpoint content here.
        row["payload"] = payload
        rows.append(row)
    return rows


def approve_execution_review(task_store: TaskTapeStore, task_id: str, *, approver: str = "PromotionExecutor", reason: str | None = None) -> dict[str, Any]:
    review = next((row for row in pending_execution_reviews(task_store) if row.get("task_id") == task_id), None)
    if review is None:
        return {"ok": False, "error": "pending_execution_review_not_found", "task_id": task_id}
    payload = review.get("payload", {})
    event = task_store.append_event(
        task_id=task_id,
        event="review_approved",
        target=review.get("target"),
        status="approved",
        payload={
            "review_type": REVIEW_TYPE,
            "approved_by": approver,
            "reason": reason,
            "promotion_pointer_id": payload.get("promotion_pointer_id"),
            "plan_sha256": (payload.get("plan") or {}).get("plan_sha256"),
            "next_step": "resume_work_with_fresh_task_tape_events_only",
        },
    )
    task_store.append_event(
        task_id=task_id,
        event="handoff_promotion_execution_ready",
        target=review.get("target"),
        status="ready",
        payload={
            "review_type": REVIEW_TYPE,
            "promotion_pointer_id": payload.get("promotion_pointer_id"),
            "safe_resume": True,
            "execute_automatically": False,
        },
    )
    return {"ok": True, "task_id": task_id, "status": "approved", "event": event.to_dict()}


def reject_execution_review(task_store: TaskTapeStore, task_id: str, *, reason: str = "manual_reject") -> dict[str, Any]:
    review = next((row for row in pending_execution_reviews(task_store) if row.get("task_id") == task_id), None)
    if review is None:
        return {"ok": False, "error": "pending_execution_review_not_found", "task_id": task_id}
    event = task_store.append_event(
        task_id=task_id,
        event="review_rejected",
        target=review.get("target"),
        status="rejected",
        payload={"review_type": REVIEW_TYPE, "reason": reason},
    )
    return {"ok": True, "task_id": task_id, "status": "rejected", "event": event.to_dict()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create and review Task Tape execution reviews from handoff promotion plans.")
    parser.add_argument("--pointer-path", default="cpos/pointers.jsonl")
    parser.add_argument("--pointer-audit-path", default="cpos/audit_log.jsonl")
    parser.add_argument("--task-tape-path", default="tapes/task_runs.jsonl")
    parser.add_argument("--task-checkpoint-path", default="tapes/task_checkpoints.jsonl")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-review")
    create.add_argument("promotion_pointer_id")
    create.add_argument("--requester", default="CLIPromotionExecutor")
    create.add_argument("--reason")
    sub.add_parser("list")
    approve = sub.add_parser("approve")
    approve.add_argument("task_id")
    approve.add_argument("--approver", default="CLIPromotionExecutor")
    approve.add_argument("--reason")
    reject = sub.add_parser("reject")
    reject.add_argument("task_id")
    reject.add_argument("--reason", default="manual_reject")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    manager = PointerManager(args.pointer_path, args.pointer_audit_path)
    store = TaskTapeStore(args.task_tape_path, args.task_checkpoint_path)
    if args.command == "create-review":
        result = create_execution_review(manager, store, args.promotion_pointer_id, requester=args.requester, reason=args.reason)
    elif args.command == "list":
        result = {"ok": True, "count": len(pending_execution_reviews(store)), "reviews": pending_execution_reviews(store)}
    elif args.command == "approve":
        result = approve_execution_review(store, args.task_id, approver=args.approver, reason=args.reason)
    else:
        result = reject_execution_review(store, args.task_id, reason=args.reason)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
