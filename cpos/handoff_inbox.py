from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .pointer_os import ContextPointer, PointerManager, utc_now

PENDING_RULE = "handoff_review_required"
APPROVED_RULE = "handoff_approved"
REJECTED_RULE = "handoff_rejected"


def is_handoff_pointer(pointer: ContextPointer) -> bool:
    return pointer.context_type == "handoff_summary" or pointer.retrieval_rule in {PENDING_RULE, APPROVED_RULE, REJECTED_RULE}


def handoff_review_status(pointer: ContextPointer) -> str:
    review = pointer.metadata.get("handoff_review") if isinstance(pointer.metadata, dict) else None
    if isinstance(review, dict) and review.get("status"):
        return str(review["status"])
    if pointer.retrieval_rule == APPROVED_RULE:
        return "approved"
    if pointer.retrieval_rule == REJECTED_RULE or pointer.status == "invalidated":
        return "rejected"
    if pointer.retrieval_rule == PENDING_RULE:
        return "pending"
    return "unknown"


def handoff_inbox(manager: PointerManager, *, status: str = "pending", limit: int | None = None) -> list[dict[str, Any]]:
    allowed_status = {"pending", "approved", "rejected", "unknown", "all"}
    if status not in allowed_status:
        raise ValueError("invalid_status")
    rows = []
    for pointer in manager.load():
        if not is_handoff_pointer(pointer):
            continue
        review_status = handoff_review_status(pointer)
        if status != "all" and review_status != status:
            continue
        rows.append({
            "pointer_id": pointer.pointer_id,
            "summary": pointer.summary,
            "source": pointer.source,
            "location": pointer.location,
            "trust_score": pointer.trust_score,
            "priority": pointer.priority,
            "status": pointer.status,
            "review_status": review_status,
            "retrieval_rule": pointer.retrieval_rule,
            "created_at": pointer.created_at,
            "metadata": {
                "generated_at": pointer.metadata.get("generated_at"),
                "bundle_sha256": pointer.metadata.get("bundle_sha256"),
                "signature": pointer.metadata.get("signature"),
                "counts": pointer.metadata.get("counts"),
                "integrity_ok": pointer.metadata.get("integrity_ok"),
                "handoff_review": pointer.metadata.get("handoff_review"),
            },
        })
    rows.sort(key=lambda row: row.get("created_at", ""), reverse=True)
    return rows[:limit] if limit is not None else rows


def _update_handoff_pointer(manager: PointerManager, pointer_id: str, *, reviewer: str, decision: str, reason: str | None = None) -> ContextPointer | None:
    if decision not in {"approved", "rejected"}:
        raise ValueError("invalid_decision")
    pointers = manager.load()
    updated = None
    out = []
    for pointer in pointers:
        if pointer.pointer_id != pointer_id:
            out.append(pointer)
            continue
        if not is_handoff_pointer(pointer):
            raise ValueError("not_handoff_pointer")
        metadata = dict(pointer.metadata)
        metadata["handoff_review"] = {
            "status": decision,
            "reviewer": reviewer,
            "reason": reason,
            "decided_at": utc_now(),
        }
        if decision == "approved":
            updated = ContextPointer.from_dict({
                **pointer.to_dict(),
                "status": "active",
                "retrieval_rule": APPROVED_RULE,
                "trust_score": max(pointer.trust_score, 0.75),
                "metadata": metadata,
            })
        else:
            updated = ContextPointer.from_dict({
                **pointer.to_dict(),
                "status": "invalidated",
                "retrieval_rule": REJECTED_RULE,
                "trust_score": min(pointer.trust_score, 0.25),
                "metadata": metadata,
                "invalidated_reason": "user_request",
                "invalidated_at": utc_now(),
            })
        out.append(updated)
    if updated is None:
        return None
    manager.save(out)
    manager._audit(f"handoff_{decision}", pointer_id, {"reviewer": reviewer, "reason": reason})
    return updated


def approve_handoff(manager: PointerManager, pointer_id: str, *, reviewer: str, reason: str | None = None) -> ContextPointer | None:
    return _update_handoff_pointer(manager, pointer_id, reviewer=reviewer, decision="approved", reason=reason)


def reject_handoff(manager: PointerManager, pointer_id: str, *, reviewer: str, reason: str | None = None) -> ContextPointer | None:
    return _update_handoff_pointer(manager, pointer_id, reviewer=reviewer, decision="rejected", reason=reason)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review imported CPOS handoff_summary pointers.")
    parser.add_argument("--pointer-path", default="cpos/pointers.jsonl")
    parser.add_argument("--pointer-audit-path", default="cpos/audit_log.jsonl")
    sub = parser.add_subparsers(dest="command", required=True)
    list_cmd = sub.add_parser("list")
    list_cmd.add_argument("--status", default="pending", choices=["pending", "approved", "rejected", "unknown", "all"])
    list_cmd.add_argument("--limit", type=int)
    approve = sub.add_parser("approve")
    approve.add_argument("pointer_id")
    approve.add_argument("--reviewer", default="CLIReviewer")
    approve.add_argument("--reason")
    reject = sub.add_parser("reject")
    reject.add_argument("pointer_id")
    reject.add_argument("--reviewer", default="CLIReviewer")
    reject.add_argument("--reason")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    manager = PointerManager(args.pointer_path, args.pointer_audit_path)
    try:
        if args.command == "list":
            print(json.dumps({"ok": True, "handoffs": handoff_inbox(manager, status=args.status, limit=args.limit)}, ensure_ascii=False, indent=2))
            return
        if args.command == "approve":
            pointer = approve_handoff(manager, args.pointer_id, reviewer=args.reviewer, reason=args.reason)
        else:
            pointer = reject_handoff(manager, args.pointer_id, reviewer=args.reviewer, reason=args.reason)
        if pointer is None:
            print(json.dumps({"ok": False, "error": "not_found", "pointer_id": args.pointer_id}, ensure_ascii=False, indent=2))
            raise SystemExit(1)
        print(json.dumps({"ok": True, "pointer": pointer.to_dict()}, ensure_ascii=False, indent=2))
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
