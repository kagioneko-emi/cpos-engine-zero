from __future__ import annotations

from typing import Any

from .handoff_inbox import handoff_review_status, is_handoff_pointer
from .task_tape import TaskTapeStore


def _event_dicts(store: TaskTapeStore) -> list[dict[str, Any]]:
    return [event.to_dict() for event in store.events()]


def build_handoff_graph(pointer_manager, task_store: TaskTapeStore, *, source_pointer_id: str | None = None, review_status: str | None = None, limit: int = 50) -> dict[str, Any]:
    pointers = pointer_manager.load()
    handoffs = [p for p in pointers if is_handoff_pointer(p) and p.context_type == "handoff_summary"]
    promotions = [p for p in pointers if p.context_type == "handoff_promotion_plan"]
    if source_pointer_id:
        handoffs = [p for p in handoffs if p.pointer_id == source_pointer_id]
        promotions = [p for p in promotions if source_pointer_id in p.dependencies]
    if review_status:
        handoffs = [p for p in handoffs if handoff_review_status(p) == review_status]
        allowed_sources = {p.pointer_id for p in handoffs}
        promotions = [p for p in promotions if any(dep in allowed_sources for dep in p.dependencies)]

    events = _event_dicts(task_store)
    promotion_by_source: dict[str, list[dict[str, Any]]] = {}
    for promotion in promotions:
        src = promotion.dependencies[0] if promotion.dependencies else None
        if not src:
            continue
        plan = (promotion.metadata.get("plan") or {}) if isinstance(promotion.metadata, dict) else {}
        promotion_by_source.setdefault(src, []).append({
            "pointer_id": promotion.pointer_id,
            "summary": promotion.summary,
            "retrieval_rule": promotion.retrieval_rule,
            "status": promotion.status,
            "trust_score": promotion.trust_score,
            "plan_sha256": plan.get("plan_sha256"),
            "plan_counts": plan.get("counts", {}),
            "warnings": plan.get("warnings", []),
            "guardrails": plan.get("guardrails", [])[:5],
            "blocked_inputs": plan.get("blocked_inputs", [])[:10],
        })

    execution_reviews = []
    resume_reviews = []
    ready_events = []
    for event in events:
        payload = event.get("payload") or {}
        review_type = payload.get("review_type")
        if review_type == "handoff_promotion_execution" and event.get("event") == "review_required":
            plan = payload.get("plan") or {}
            execution_reviews.append({
                "task_id": event.get("task_id"),
                "target": event.get("target"),
                "status": event.get("status"),
                "promotion_pointer_id": payload.get("promotion_pointer_id") or event.get("target"),
                "plan_sha256": plan.get("plan_sha256"),
                "blocked_inputs": plan.get("blocked_inputs", [])[:10],
                "warnings": plan.get("warnings", []),
                "execution_mode": payload.get("execution_mode"),
                "timestamp": event.get("timestamp"),
            })
        elif review_type == "execution_resume_action" and event.get("event") == "review_required":
            proposal = payload.get("proposal") or {}
            first = (proposal.get("proposals") or [{}])[0]
            resume_reviews.append({
                "task_id": event.get("task_id"),
                "target": event.get("target"),
                "status": event.get("status"),
                "proposal_sha256": proposal.get("proposal_sha256"),
                "first_action_id": first.get("action_id"),
                "first_action_title": first.get("title"),
                "blocked_inputs": proposal.get("blocked_inputs", [])[:10],
                "execute_automatically": bool(proposal.get("execute_automatically")),
                "timestamp": event.get("timestamp"),
            })
        elif event.get("event") in {"handoff_promotion_execution_ready", "resume_action_ready"}:
            ready_events.append({
                "task_id": event.get("task_id"),
                "target": event.get("target"),
                "event": event.get("event"),
                "status": event.get("status"),
                "timestamp": event.get("timestamp"),
            })

    if source_pointer_id:
        promotion_ids = {p["pointer_id"] for p in promotion_by_source.get(source_pointer_id, [])}
        execution_task_ids = {e["task_id"] for e in execution_reviews if e.get("promotion_pointer_id") in promotion_ids}
        execution_reviews = [e for e in execution_reviews if e.get("promotion_pointer_id") in promotion_ids]
        resume_reviews = [r for r in resume_reviews if r.get("task_id") in execution_task_ids]
        ready_events = [r for r in ready_events if r.get("target") in promotion_ids or r.get("task_id") in execution_task_ids]

    handoff_rows = []
    for handoff in handoffs:
        handoff_rows.append({
            "pointer_id": handoff.pointer_id,
            "summary": handoff.summary,
            "source": handoff.source,
            "review_status": handoff_review_status(handoff),
            "retrieval_rule": handoff.retrieval_rule,
            "status": handoff.status,
            "trust_score": handoff.trust_score,
            "counts": handoff.metadata.get("counts") if isinstance(handoff.metadata, dict) else {},
            "signature": handoff.metadata.get("signature") if isinstance(handoff.metadata, dict) else {},
            "promotions": promotion_by_source.get(handoff.pointer_id, []),
        })

    handoff_rows = handoff_rows[:max(1, limit)]
    allowed_promotion_ids = {p["pointer_id"] for row in handoff_rows for p in row.get("promotions", [])}
    if allowed_promotion_ids:
        execution_reviews = [e for e in execution_reviews if e.get("promotion_pointer_id") in allowed_promotion_ids]
        execution_task_ids = {e.get("task_id") for e in execution_reviews}
        resume_reviews = [r for r in resume_reviews if r.get("task_id") in execution_task_ids]
        ready_events = [r for r in ready_events if r.get("target") in allowed_promotion_ids or r.get("task_id") in execution_task_ids]

    return {
        "ok": True,
        "source_pointer_id": source_pointer_id,
        "review_status": review_status,
        "counts": {
            "handoffs": len(handoff_rows),
            "promotions": sum(len(row["promotions"]) for row in handoff_rows),
            "execution_reviews": len(execution_reviews),
            "resume_reviews": len(resume_reviews),
            "ready_events": len(ready_events),
        },
        "handoffs": handoff_rows,
        "execution_reviews": execution_reviews,
        "resume_reviews": resume_reviews,
        "ready_events": ready_events,
    }
