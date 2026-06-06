from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from .goals import goal_summary
from .world_model import build_world_model_snapshot

EVALUATION_SCHEMA = "kagioneko.reflection_evaluation.v1"
ALLOWED_RECOMMENDATIONS = {"proceed", "ask", "defer", "block"}
RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
SAFETY_FLAGS = {
    "metadata_only": True,
    "raw_request_stored": False,
    "raw_diff_stored": False,
    "raw_outputs_stored": False,
    "secret_values_stored": False,
    "execute_automatically": False,
}
HIGH_STAKES_ACTIONS = {"push", "release", "publish", "tag", "port", "systemd", "user_management", "secret", "destructive"}
BLOCKED_ACTIONS = {"authorized_keys", "raw_db_rows", "android_raw_data", "phone_control"}
DOC_ACTIONS = {"doc", "reflection", "plan", "diagram"}
OVERCLAIM_RE = re.compile(r"(agi\s*(is|completed|done)|completed\s*agi|agi完成|agiできた|完全なagi)", re.IGNORECASE)
PRIVATE_LEAK_RE = re.compile(r"(/home/|raw db|db dump|diary text|phone data|private log|oauth|token|credential|\.env)", re.IGNORECASE)


def _risk_max(*risks: str) -> str:
    values = [risk for risk in risks if risk]
    if not values:
        return "low"
    return max(values, key=lambda risk: RISK_ORDER.get(risk, 1))


def _load_json_text(path: str | None) -> dict[str, Any]:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    try:
        has_stdin = not sys.stdin.isatty()
    except OSError:
        has_stdin = False
    if has_stdin:
        try:
            text = sys.stdin.read().strip()
        except OSError:
            text = ""
        if text:
            return json.loads(text)
    return {}


def _normalize_action(action: dict[str, Any] | None) -> dict[str, Any]:
    source = action or {}
    action_type = str(source.get("action_type") or "doc")
    summary = str(source.get("summary") or "Evaluate proposed action")
    return {
        "action_id": str(source.get("action_id") or "proposed_action"),
        "action_type": action_type,
        "summary": summary,
        "target_repo": str(source.get("target_repo") or "unknown"),
        "touches_public_surface": bool(source.get("touches_public_surface", action_type in {"release", "publish", "tag"})),
        "touches_private_context": bool(source.get("touches_private_context", False)),
        "requires_execution": bool(source.get("requires_execution", action_type not in DOC_ACTIONS)),
        "reads_raw_db_rows": bool(source.get("reads_raw_db_rows", False)),
        "reads_android_raw_data": bool(source.get("reads_android_raw_data", False)),
        "reads_phone_data": bool(source.get("reads_phone_data", False)),
        "changes_authorized_keys": bool(source.get("changes_authorized_keys", False)),
        "destructive": bool(source.get("destructive", action_type == "destructive")),
        "opens_port": bool(source.get("opens_port", action_type == "port")),
        "touches_secrets": bool(source.get("touches_secrets", action_type == "secret")),
        "claims": str(source.get("claims") or summary),
        "explicit_confirmation": bool(source.get("explicit_confirmation", False)),
        "published_true": bool(source.get("published_true", False)),
    }


def _goal_requires_confirmation(action: dict[str, Any], goals: dict[str, Any]) -> bool:
    goal_ids = set(goals.get("confirmation_required_goal_ids") or [])
    action_id = action.get("action_id") or ""
    if action_id in goal_ids:
        return True
    if action.get("action_type") in {"release", "publish", "tag"}:
        return True
    return False


def evaluate_proposed_action(
    proposed_action: dict[str, Any] | None = None,
    *,
    world_model_snapshot: dict[str, Any] | None = None,
    goal_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    action = _normalize_action(proposed_action)
    world = world_model_snapshot or build_world_model_snapshot()
    goals = goal_state or world.get("goals") or goal_summary()

    reasons: list[str] = []
    required_confirmations: list[str] = []
    blocking_issues: list[str] = []
    risks: list[str] = []

    action_type = action["action_type"]
    summary = action["summary"]
    claim_text = action.get("claims") or summary

    if action_type in DOC_ACTIONS and not action["requires_execution"]:
        reasons.append("documentation/planning action does not require execution")
        risks.append("low")

    if action_type in HIGH_STAKES_ACTIONS or action["touches_public_surface"]:
        risks.append("high")
        required_confirmations.append(f"explicit confirmation for {action_type}")
        reasons.append("high-stakes or public-surface action requires confirmation")

    if action["destructive"] or action["opens_port"] or action["touches_secrets"]:
        risks.append("critical" if action["destructive"] else "high")
        required_confirmations.append("explicit safety confirmation")
        reasons.append("action touches destructive/port/secret boundary")

    if action_type in BLOCKED_ACTIONS or action["changes_authorized_keys"]:
        risks.append("critical")
        blocking_issues.append("action violates hard safety boundary")

    if action["reads_raw_db_rows"]:
        risks.append("high")
        blocking_issues.append("raw DB row access is outside current path-only inventory boundary")
    if action["reads_android_raw_data"] or action["reads_phone_data"]:
        risks.append("high")
        blocking_issues.append("raw Android/phone data ingestion requires separate privacy review")

    if OVERCLAIM_RE.search(claim_text):
        risks.append("high")
        blocking_issues.append("public or action claim implies completed AGI")
    elif "agi" in claim_text.lower() and action.get("target_repo") != "private_lab":
        risks.append("medium")
        required_confirmations.append("review AGI wording for public-safe framing")

    if action["touches_public_surface"] and (action["touches_private_context"] or PRIVATE_LEAK_RE.search(summary)):
        risks.append("high")
        blocking_issues.append("public/private boundary leak risk")

    if _goal_requires_confirmation(action, goals) and not action["explicit_confirmation"]:
        risks.append("high")
        if "explicit confirmation for goal/action" not in required_confirmations:
            required_confirmations.append("explicit confirmation for goal/action")

    if world.get("session", {}).get("late_night_extra_confirmation") and action_type in HIGH_STAKES_ACTIONS:
        risks.append("medium")
        required_confirmations.append("late-night high-stakes extra confirmation")
        reasons.append("late-night high-stakes caution applies")

    if world.get("release", {}).get("final_v0_1_1_paused") and action_type == "release":
        risks.append("high")
        required_confirmations.append("final release pause override confirmation")
        reasons.append("final v0.1.1 release goal is paused")

    if not reasons:
        reasons.append("no high-risk rule matched")
        risks.append("medium" if action["requires_execution"] else "low")

    risk = _risk_max(*risks)
    recommendation = "proceed"
    suggested = "proceed_with_safe_action"
    if blocking_issues:
        recommendation = "block"
        suggested = "do_not_proceed_without_redesign"
    elif action_type in {"release", "publish", "tag"} and not action["explicit_confirmation"]:
        recommendation = "ask"
        suggested = "ask_for_explicit_confirmation"
    elif required_confirmations and not action["explicit_confirmation"]:
        recommendation = "ask"
        suggested = "ask_for_confirmation_or_clarification"
    elif world.get("session", {}).get("late_night_extra_confirmation") and action_type in HIGH_STAKES_ACTIONS:
        recommendation = "defer"
        suggested = "write_handoff_and_revisit_later"
    elif risk in {"high", "critical"}:
        recommendation = "ask"
        suggested = "route_to_human_escalation"

    return {
        "schema": EVALUATION_SCHEMA,
        "action_id": action["action_id"],
        "action_type": action_type,
        "recommendation": recommendation,
        "confidence": 0.86,
        "risk": risk,
        "reasons": reasons,
        "required_confirmations": sorted(set(required_confirmations)),
        "blocking_issues": blocking_issues,
        "suggested_next_action": suggested,
        "goal_summary_used": goals.get("schema") == "kagioneko.goal_summary.v1",
        "world_model_used": world.get("schema") == "kagioneko.world_model_snapshot.v1",
        **SAFETY_FLAGS,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only CPOS Reflection Evaluator MVP.")
    sub = parser.add_subparsers(dest="command", required=True)
    evaluate = sub.add_parser("evaluate", help="Evaluate a proposed action without executing it.")
    evaluate.add_argument("--action-json", help="Path to proposed action JSON. Reads stdin if omitted and stdin has data.")
    evaluate.add_argument("--action-type", help="Action type when not using JSON.")
    evaluate.add_argument("--summary", help="Action summary when not using JSON.")
    evaluate.add_argument("--target-repo", default="unknown", help="Target repo/category when not using JSON.")
    evaluate.add_argument("--touches-public-surface", action="store_true")
    evaluate.add_argument("--touches-private-context", action="store_true")
    evaluate.add_argument("--requires-execution", action="store_true")
    evaluate.add_argument("--reads-raw-db-rows", action="store_true")
    evaluate.add_argument("--reads-android-raw-data", action="store_true")
    evaluate.add_argument("--reads-phone-data", action="store_true")
    evaluate.add_argument("--changes-authorized-keys", action="store_true")
    evaluate.add_argument("--destructive", action="store_true")
    evaluate.add_argument("--opens-port", action="store_true")
    evaluate.add_argument("--touches-secrets", action="store_true")
    evaluate.add_argument("--explicit-confirmation", action="store_true")
    evaluate.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def _action_from_args(args: argparse.Namespace) -> dict[str, Any]:
    loaded = _load_json_text(args.action_json)
    if loaded:
        return loaded.get("proposed_action", loaded)
    return {
        "action_id": "cli_action",
        "action_type": args.action_type or "doc",
        "summary": args.summary or "Evaluate proposed action",
        "target_repo": args.target_repo,
        "touches_public_surface": args.touches_public_surface,
        "touches_private_context": args.touches_private_context,
        "requires_execution": args.requires_execution,
        "reads_raw_db_rows": args.reads_raw_db_rows,
        "reads_android_raw_data": args.reads_android_raw_data,
        "reads_phone_data": args.reads_phone_data,
        "changes_authorized_keys": args.changes_authorized_keys,
        "destructive": args.destructive,
        "opens_port": args.opens_port,
        "touches_secrets": args.touches_secrets,
        "explicit_confirmation": args.explicit_confirmation,
    }


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command != "evaluate":
        raise SystemExit(2)
    result = evaluate_proposed_action(_action_from_args(args))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"reflection_evaluation: recommendation={result['recommendation']} risk={result['risk']} action={result['action_id']}")


if __name__ == "__main__":
    main()
