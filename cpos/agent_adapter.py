from __future__ import annotations

import hashlib
import json
from typing import Any

from .human_escalation import review_escalation_decision
from .task_tape import TaskTapeStore

REVIEW_TYPE = "external_agent_action"
TERMINAL_EVENTS = {"external_agent_action_approved", "external_agent_action_rejected"}
ALLOWED_EVENT_TYPES = {"agent_intent", "proposed_action", "proposed_diff", "command_request", "execution_result"}


def _stable_digest(value: Any) -> dict[str, Any]:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str) if not isinstance(value, str) else value
    encoded = text.encode("utf-8")
    return {"sha256": hashlib.sha256(encoded).hexdigest(), "size_bytes": len(encoded)}


def _string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value) for value in values[:100]]


def _result_summary(execution_result: Any, metadata: dict[str, Any]) -> dict[str, Any] | None:
    if execution_result is None and not any(key in metadata for key in {"success", "exit_code", "failure_kind", "duration_ms"}):
        return None
    exit_code = metadata.get("exit_code")
    try:
        exit_code = int(exit_code) if exit_code is not None else None
    except (TypeError, ValueError):
        exit_code = None
    duration_ms = metadata.get("duration_ms")
    try:
        duration_ms = int(duration_ms) if duration_ms is not None else None
    except (TypeError, ValueError):
        duration_ms = None
    return {
        "success": metadata.get("success") if isinstance(metadata.get("success"), bool) else None,
        "exit_code": exit_code,
        "failure_kind": str(metadata.get("failure_kind") or "")[:80] or None,
        "duration_ms": duration_ms,
        "result_digest": _stable_digest(execution_result) if execution_result is not None else None,
        "raw_outputs_stored": False,
        "secret_values_stored": False,
    }


def _risk_from_flags(*, event_type: str, flags: dict[str, bool], command_count: int, diff_size: int) -> str:
    if flags.get("touches_secrets") or flags.get("destructive") or flags.get("touches_production"):
        return "high"
    if event_type in {"proposed_diff", "command_request"}:
        return "medium"
    if command_count or diff_size:
        return "medium"
    return "low"


def _build_summary(event_type: str, agent_name: str, flags: dict[str, bool], metadata: dict[str, Any]) -> str:
    parts = [f"External agent {agent_name} submitted {event_type}"]
    if flags.get("touches_secrets"):
        parts.append("touches secrets/token/.env")
    if flags.get("touches_production"):
        parts.append("touches production/deploy")
    if flags.get("destructive"):
        parts.append("destructive/delete/overwrite")
    if metadata.get("requires_publish"):
        parts.append("push/publish requested")
    if metadata.get("opens_port"):
        parts.append("open port requested")
    return "; ".join(parts)


def pending_external_agent_actions(store: TaskTapeStore) -> list[dict[str, Any]]:
    terminal_task_ids = {
        event.task_id
        for event in store.events()
        if event.event in TERMINAL_EVENTS and event.payload.get("review_type") == REVIEW_TYPE
    }
    rows: list[dict[str, Any]] = []
    for event in store.events():
        payload = event.payload or {}
        if event.event != "review_required" or payload.get("review_type") != REVIEW_TYPE or event.task_id in terminal_task_ids:
            continue
        contract = payload.get("contract") or {}
        rows.append({
            "task_id": event.task_id,
            "event_id": event.event_id,
            "timestamp": event.timestamp,
            "target": event.target,
            "status": event.status,
            "contract": contract,
            "decision": payload.get("human_escalation") or {},
            "metadata_only": True,
            "approval_endpoint": f"/agent-adapter/actions/{event.task_id}/approve",
            "rejection_endpoint": f"/agent-adapter/actions/{event.task_id}/reject",
            "execute_automatically": False,
        })
    return rows


def intake_external_agent_action(
    store: TaskTapeStore,
    *,
    agent_name: str = "external-agent",
    event_type: str = "proposed_action",
    intent: Any = None,
    proposed_action: Any = None,
    proposed_diff: str | None = None,
    commands: Any = None,
    execution_result: Any = None,
    changed_files: Any = None,
    metadata: dict[str, Any] | None = None,
    actor: str = "ExternalAgentAdapter",
) -> dict[str, Any]:
    event_type = str(event_type or "proposed_action")
    if event_type not in ALLOWED_EVENT_TYPES:
        return {"ok": False, "error": "unsupported_event_type", "allowed_event_types": sorted(ALLOWED_EVENT_TYPES)}
    metadata = metadata if isinstance(metadata, dict) else {}
    commands_list = _string_list(commands)
    files = _string_list(changed_files)
    flags = {
        "touches_secrets": bool(metadata.get("touches_secrets")),
        "touches_production": bool(metadata.get("touches_production")),
        "destructive": bool(metadata.get("destructive")),
    }
    diff_digest = _stable_digest(proposed_diff or "") if proposed_diff is not None else None
    command_digests = [_stable_digest(command) for command in commands_list]
    input_digests = {
        "intent": _stable_digest(intent) if intent is not None else None,
        "proposed_action": _stable_digest(proposed_action) if proposed_action is not None else None,
        "proposed_diff": diff_digest,
        "commands": command_digests,
        "execution_result": _stable_digest(execution_result) if execution_result is not None else None,
    }
    risk = str(metadata.get("risk") or _risk_from_flags(
        event_type=event_type,
        flags=flags,
        command_count=len(commands_list),
        diff_size=(diff_digest or {}).get("size_bytes", 0),
    ))
    requires_human = event_type in {"proposed_diff", "command_request"} or bool(metadata.get("requires_human_approval", False))
    result_summary = _result_summary(execution_result, metadata) if event_type == "execution_result" else None
    summary = _build_summary(event_type, str(agent_name or "external-agent"), flags, metadata)
    human_escalation = review_escalation_decision(
        review_type=REVIEW_TYPE,
        summary=summary,
        confidence=float(metadata.get("confidence", 0.82)),
        risk=risk,
        touches_secrets=flags["touches_secrets"],
        touches_production=flags["touches_production"],
        destructive=flags["destructive"],
        user_confirmation_required=requires_human,
    )
    contract = {
        "schema": "cpos.external_agent_action_contract.v1",
        "agent_name": str(agent_name or "external-agent"),
        "event_type": event_type,
        "risk": risk,
        "changed_files": files,
        "changed_file_count": len(files),
        "command_count": len(commands_list),
        "input_digests": input_digests,
        "metadata_keys": sorted(str(key) for key in metadata.keys()),
        "result_summary": result_summary,
        "adapter_decision": "requires_review" if human_escalation["requires_human"] else "allow",
        "requires_human_approval": human_escalation["requires_human"],
        "execute_automatically": False,
        "raw_request_stored": False,
        "raw_diff_stored": False,
        "raw_outputs_stored": False,
        "secret_values_stored": False,
        "destructive_actions_performed": False,
        "next_step": "human_review" if human_escalation["requires_human"] else "safe_autonomy_metadata_recorded",
    }
    contract["contract_sha256"] = _stable_digest(contract)["sha256"]
    target = f"agent-adapter://{contract['agent_name']}/{event_type}"
    task_id = store.create_task(
        target=target,
        action="external_agent_action_intake",
        payload={"review_type": REVIEW_TYPE, "agent_name": contract["agent_name"], "event_type": event_type, "contract_sha256": contract["contract_sha256"], "actor": actor},
    )
    event = store.append_event(
        task_id=task_id,
        event="review_required",
        target=target,
        status="pending_review" if human_escalation["requires_human"] else "metadata_recorded",
        payload={"review_type": REVIEW_TYPE, "contract": contract, "human_escalation": human_escalation, "actor": actor},
    )
    return {"ok": True, "task_id": task_id, "status": event.status, "review": event.to_dict(), "contract": contract, "human_escalation": human_escalation, "execute_automatically": False}


def external_agent_execution_results(store: TaskTapeStore) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in store.events():
        payload = event.payload or {}
        contract = payload.get("contract") or {}
        if event.event != "review_required" or payload.get("review_type") != REVIEW_TYPE or contract.get("event_type") != "execution_result":
            continue
        result = contract.get("result_summary") or {}
        rows.append({
            "task_id": event.task_id,
            "event_id": event.event_id,
            "timestamp": event.timestamp,
            "target": event.target,
            "status": event.status,
            "agent_name": contract.get("agent_name"),
            "success": result.get("success"),
            "exit_code": result.get("exit_code"),
            "failure_kind": result.get("failure_kind"),
            "duration_ms": result.get("duration_ms"),
            "result_sha256": (result.get("result_digest") or {}).get("sha256"),
            "result_size_bytes": (result.get("result_digest") or {}).get("size_bytes"),
            "metadata_only": True,
            "raw_outputs_stored": False,
            "secret_values_stored": False,
            "execute_automatically": False,
        })
    return rows


def build_external_agent_result_scoreboard(store: TaskTapeStore) -> dict[str, Any]:
    results = external_agent_execution_results(store)
    successes = [row for row in results if row.get("success") is True]
    failures = [row for row in results if row.get("success") is not True]
    failure_kind_counts: dict[str, int] = {}
    for row in failures:
        kind = str(row.get("failure_kind") or "unknown")
        failure_kind_counts[kind] = failure_kind_counts.get(kind, 0) + 1
    return {
        "ok": True,
        "schema": "cpos.external_agent_result_scoreboard.v1",
        "completed_results": len(results),
        "success_results": len(successes),
        "failure_results": len(failures),
        "success_rate": round((len(successes) / len(results)) * 100, 1) if results else 0.0,
        "failure_kind_counts": failure_kind_counts,
        "recent_results": results[-10:],
        "metadata_only": True,
        "raw_outputs_stored": False,
        "secret_values_stored": False,
        "execute_automatically": False,
    }


def approve_external_agent_action(store: TaskTapeStore, task_id: str, *, approver: str = "ExternalAgentReviewer", reason: str | None = None, confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        return {"ok": False, "error": "confirm_required", "task_id": task_id}
    review = next((row for row in pending_external_agent_actions(store) if row.get("task_id") == task_id), None)
    if review is None:
        return {"ok": False, "error": "pending_external_agent_action_not_found", "task_id": task_id}
    contract = review.get("contract") or {}
    event = store.append_event(
        task_id=task_id,
        event="external_agent_action_approved",
        target=review.get("target"),
        status="approved_contract_only",
        payload={"review_type": REVIEW_TYPE, "approved_by": approver, "reason": reason, "contract_sha256": contract.get("contract_sha256"), "execute_automatically": False},
    )
    return {"ok": True, "task_id": task_id, "status": "approved_contract_only", "event": event.to_dict(), "execute_automatically": False}


def reject_external_agent_action(store: TaskTapeStore, task_id: str, *, reason: str = "manual_reject") -> dict[str, Any]:
    review = next((row for row in pending_external_agent_actions(store) if row.get("task_id") == task_id), None)
    if review is None:
        return {"ok": False, "error": "pending_external_agent_action_not_found", "task_id": task_id}
    event = store.append_event(
        task_id=task_id,
        event="external_agent_action_rejected",
        target=review.get("target"),
        status="rejected",
        payload={"review_type": REVIEW_TYPE, "reason": reason, "execute_automatically": False},
    )
    return {"ok": True, "task_id": task_id, "status": "rejected", "event": event.to_dict(), "execute_automatically": False}
