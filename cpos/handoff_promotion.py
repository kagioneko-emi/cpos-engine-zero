from __future__ import annotations

import argparse
import hashlib
import json
from typing import Any

from .handoff_inbox import APPROVED_RULE, handoff_review_status, is_handoff_pointer
from .pointer_os import ContextPointer, PointerManager, utc_now

PROMOTION_RULE = "handoff_promotion_review_required"
PROMOTED_RULE = "handoff_promoted"


def _stable_digest(value: dict[str, Any]) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _counts(pointer: ContextPointer) -> dict[str, int]:
    raw = pointer.metadata.get("counts") if isinstance(pointer.metadata, dict) else {}
    if not isinstance(raw, dict):
        raw = {}
    return {str(k): int(v) for k, v in raw.items() if isinstance(v, int | float) or str(v).isdigit()}


def build_promotion_plan(pointer: ContextPointer) -> dict[str, Any]:
    if not is_handoff_pointer(pointer):
        raise ValueError("not_handoff_pointer")
    if handoff_review_status(pointer) != "approved" or pointer.retrieval_rule != APPROVED_RULE:
        raise ValueError("handoff_not_approved")

    counts = _counts(pointer)
    signature = pointer.metadata.get("signature") if isinstance(pointer.metadata, dict) else {}
    signature_ok = bool(isinstance(signature, dict) and signature.get("ok"))
    integrity_ok = bool(pointer.metadata.get("integrity_ok")) if isinstance(pointer.metadata, dict) else False

    retrieval_steps = [
        {
            "step": "review_handoff_summary_pointer",
            "pointer_id": pointer.pointer_id,
            "purpose": "human_or_agent_review_before_context_use",
            "allowed": True,
        }
    ]
    if counts.get("pointers", 0) > 0:
        retrieval_steps.append({
            "step": "request_specific_pointer_references",
            "purpose": "retrieve only explicitly approved pointers from source agent/session",
            "allowed": signature_ok,
            "max_references": min(counts.get("pointers", 0), 10),
        })

    task_candidates = []
    if counts.get("tasks", 0) > 0 or counts.get("task_events", 0) > 0:
        task_candidates.append({
            "candidate": "resume_prior_task_context",
            "source_pointer_id": pointer.pointer_id,
            "requires_human_approval": True,
            "max_task_summaries": min(max(counts.get("tasks", 0), 1), 5),
            "allowed_inputs": ["task_id", "summary", "status", "safe_next_step"],
            "blocked_inputs": ["checkpoint_content", "proposed_code", "request_body", "secret_value"],
        })

    blocked = ["raw_handoff_body", "checkpoint_contents", "request_bodies", "secret_values", "unreviewed_code_patches"]
    warnings = []
    if not signature_ok:
        warnings.append("signature_not_verified")
    if not integrity_ok:
        warnings.append("source_integrity_not_fully_ok")

    plan = {
        "schema": "cpos.handoff_promotion_plan.v1",
        "source_pointer_id": pointer.pointer_id,
        "source_bundle_sha256": pointer.metadata.get("bundle_sha256") if isinstance(pointer.metadata, dict) else None,
        "generated_at": utc_now(),
        "trust_score": pointer.trust_score,
        "signature_ok": signature_ok,
        "integrity_ok": integrity_ok,
        "counts": counts,
        "retrieval_steps": retrieval_steps,
        "task_candidates": task_candidates,
        "blocked_inputs": blocked,
        "guardrails": [
            "Do not import raw logs or checkpoint contents.",
            "Do not execute proposed code from handoff without a fresh review cycle.",
            "Use approved source pointers only and keep sensitivity restrictions intact.",
            "Create new Task Tape events for any resumed work instead of mutating source history.",
        ],
        "warnings": warnings,
    }
    plan["plan_sha256"] = _stable_digest(plan)
    return plan


def create_promotion_pointer(manager: PointerManager, pointer_id: str, *, reviewer: str, reason: str | None = None) -> ContextPointer | None:
    source = next((p for p in manager.load() if p.pointer_id == pointer_id), None)
    if source is None:
        return None
    plan = build_promotion_plan(source)
    promotion_id = f"ptr://handoff-promotion/{plan['plan_sha256'][:16]}"
    pointer = manager.create_pointer(
        pointer_id=promotion_id,
        context_type="handoff_promotion_plan",
        summary=f"Promotion plan for approved handoff {pointer_id}",
        source="handoff_promotion_rules",
        location=f"handoff-promotion://{plan['plan_sha256']}",
        priority=0.6,
        trust_score=min(max(source.trust_score, 0.5), 0.85),
        sensitivity_level="internal",
        retrieval_rule=PROMOTION_RULE,
        dependencies=[pointer_id],
        metadata={
            "plan": plan,
            "created_by": reviewer,
            "reason": reason,
            "created_at": utc_now(),
        },
    )
    manager._audit("handoff_promotion_planned", promotion_id, {"source_pointer_id": pointer_id, "reviewer": reviewer, "reason": reason})
    return pointer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create safe promotion plans from approved CPOS handoff summaries.")
    parser.add_argument("--pointer-path", default="cpos/pointers.jsonl")
    parser.add_argument("--pointer-audit-path", default="cpos/audit_log.jsonl")
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("pointer_id")
    promote = sub.add_parser("promote")
    promote.add_argument("pointer_id")
    promote.add_argument("--reviewer", default="CLIPromoter")
    promote.add_argument("--reason")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    manager = PointerManager(args.pointer_path, args.pointer_audit_path)
    try:
        if args.command == "plan":
            pointer = next((p for p in manager.load() if p.pointer_id == args.pointer_id), None)
            if pointer is None:
                print(json.dumps({"ok": False, "error": "not_found", "pointer_id": args.pointer_id}, ensure_ascii=False, indent=2))
                raise SystemExit(1)
            print(json.dumps({"ok": True, "plan": build_promotion_plan(pointer)}, ensure_ascii=False, indent=2))
            return
        pointer = create_promotion_pointer(manager, args.pointer_id, reviewer=args.reviewer, reason=args.reason)
        if pointer is None:
            print(json.dumps({"ok": False, "error": "not_found", "pointer_id": args.pointer_id}, ensure_ascii=False, indent=2))
            raise SystemExit(1)
        print(json.dumps({"ok": True, "pointer": pointer.to_dict()}, ensure_ascii=False, indent=2))
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
