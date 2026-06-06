from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from .goals import ALLOWED_STATES, GOAL_SCHEMA, GOAL_SET_SCHEMA, SAFETY_FLAGS, default_goals

STORE_SCHEMA = "kagioneko.goal_store_validation.v1"
ALLOWED_SCOPES = {"project", "wellbeing", "release", "article", "system"}
ALLOWED_PRIORITIES = {"low", "medium", "high", "critical"}
FORBIDDEN_GOAL_KEYS = {
    "secret",
    "secrets",
    "token",
    "tokens",
    "api_key",
    "password",
    "private_key",
    "raw_log",
    "raw_logs",
    "raw_diff",
    "raw_output",
    "stdout",
    "stderr",
    "db_rows",
    "diary_text",
    "phone_data",
    "sensor_stream",
    "execution_authority",
    "autonomous_execution",
}
RISKY_TEXT_PATTERN = re.compile(
    r"(BEGIN (RSA|OPENSSH|PRIVATE) KEY|gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|x-access-token:|AKIA[0-9A-Z]{16}|\.env|raw db|db dump|diary text|phone data|private log)",
    re.IGNORECASE,
)
REQUIRED_GOAL_KEYS = {
    "schema",
    "goal_id",
    "title",
    "scope",
    "state",
    "priority",
    "success_criteria",
    "safety_constraints",
    "source_of_truth",
    "requires_human_confirmation",
    "metadata_only",
}


def _error(code: str, field: str, message: str) -> dict[str, str]:
    return {"code": code, "field": field, "message": message}


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _contains_risky_text(value: Any) -> bool:
    if isinstance(value, str):
        return bool(RISKY_TEXT_PATTERN.search(value))
    if isinstance(value, list):
        return any(_contains_risky_text(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_risky_text(item) for item in value.values())
    return False


def validate_goal(goal: dict[str, Any], *, index: int = 0) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    prefix = f"goals[{index}]"
    if not isinstance(goal, dict):
        return [_error("goal_must_be_object", prefix, "goal must be an object")]

    missing = sorted(REQUIRED_GOAL_KEYS - set(goal.keys()))
    for key in missing:
        errors.append(_error("required_key_missing", f"{prefix}.{key}", "required goal key is missing"))

    forbidden = sorted(key for key in goal.keys() if key in FORBIDDEN_GOAL_KEYS)
    for key in forbidden:
        errors.append(_error("forbidden_goal_key", f"{prefix}.{key}", "goal must not include raw secrets/logs/data or execution authority fields"))

    if goal.get("schema") != GOAL_SCHEMA:
        errors.append(_error("invalid_goal_schema", f"{prefix}.schema", f"schema must be {GOAL_SCHEMA}"))
    if not isinstance(goal.get("goal_id"), str) or not goal.get("goal_id"):
        errors.append(_error("invalid_goal_id", f"{prefix}.goal_id", "goal_id must be a non-empty string"))
    if "self_preservation" in str(goal.get("goal_id", "")).lower():
        errors.append(_error("self_preservation_goal_forbidden", f"{prefix}.goal_id", "self-preservation goals are forbidden"))
    if not isinstance(goal.get("title"), str) or not goal.get("title"):
        errors.append(_error("invalid_title", f"{prefix}.title", "title must be a non-empty string"))
    if goal.get("scope") not in ALLOWED_SCOPES:
        errors.append(_error("invalid_scope", f"{prefix}.scope", "scope is not allowed"))
    if goal.get("state") not in ALLOWED_STATES:
        errors.append(_error("invalid_state", f"{prefix}.state", "state is not allowed"))
    if goal.get("priority") not in ALLOWED_PRIORITIES:
        errors.append(_error("invalid_priority", f"{prefix}.priority", "priority is not allowed"))
    if not _is_string_list(goal.get("success_criteria")):
        errors.append(_error("invalid_success_criteria", f"{prefix}.success_criteria", "success_criteria must be a string array"))
    if not _is_string_list(goal.get("safety_constraints")):
        errors.append(_error("invalid_safety_constraints", f"{prefix}.safety_constraints", "safety_constraints must be a string array"))
    if not _is_string_list(goal.get("source_of_truth")):
        errors.append(_error("invalid_source_of_truth", f"{prefix}.source_of_truth", "source_of_truth must be a string array"))
    if not isinstance(goal.get("requires_human_confirmation"), bool):
        errors.append(_error("invalid_requires_human_confirmation", f"{prefix}.requires_human_confirmation", "requires_human_confirmation must be boolean"))
    if goal.get("metadata_only") is not True:
        errors.append(_error("metadata_only_required", f"{prefix}.metadata_only", "metadata_only must be true"))

    for key in ["raw_request_stored", "raw_diff_stored", "raw_outputs_stored", "secret_values_stored", "execute_automatically"]:
        if key in goal and goal.get(key) is not False:
            errors.append(_error("safety_flag_must_be_false", f"{prefix}.{key}", f"{key} must be false"))

    if _contains_risky_text(goal):
        errors.append(_error("risky_text_detected", prefix, "goal contains risky secret/raw/private text pattern"))

    return errors


def validate_goal_set(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    if not isinstance(payload, dict):
        errors.append(_error("goal_set_must_be_object", "root", "goal set must be an object"))
        payload = {}

    if payload.get("schema") != GOAL_SET_SCHEMA:
        errors.append(_error("invalid_goal_set_schema", "schema", f"schema must be {GOAL_SET_SCHEMA}"))
    if payload.get("write_enabled") is not False:
        errors.append(_error("write_enabled_forbidden", "write_enabled", "Phase 1 goal store must be read-only"))
    if payload.get("autonomous_goal_updates") is not False:
        errors.append(_error("autonomous_goal_updates_forbidden", "autonomous_goal_updates", "autonomous goal updates must be false"))
    if payload.get("self_preservation_goals") is not False:
        errors.append(_error("self_preservation_goals_forbidden", "self_preservation_goals", "self-preservation goals must be false"))
    if payload.get("metadata_only") is not True:
        errors.append(_error("metadata_only_required", "metadata_only", "metadata_only must be true"))

    goals = payload.get("goals")
    if not isinstance(goals, list):
        errors.append(_error("goals_must_be_array", "goals", "goals must be an array"))
        goals = []

    seen: set[str] = set()
    for index, goal in enumerate(goals):
        errors.extend(validate_goal(goal, index=index))
        goal_id = str(goal.get("goal_id", "")) if isinstance(goal, dict) else ""
        if goal_id:
            if goal_id in seen:
                errors.append(_error("duplicate_goal_id", f"goals[{index}].goal_id", "goal_id must be unique"))
            seen.add(goal_id)

    return {
        "schema": STORE_SCHEMA,
        "ok": not errors,
        "goal_count": len(goals),
        "errors": errors,
        "write_enabled": False,
        "autonomous_goal_updates": False,
        "self_preservation_goals": False,
        **SAFETY_FLAGS,
    }


def load_goal_set(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def merge_with_defaults(external_goals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = {goal["goal_id"]: goal for goal in default_goals()}
    for goal in external_goals:
        merged[goal["goal_id"]] = goal
    return list(merged.values())


def validate_file(path: str | Path, *, include_merged_summary: bool = False) -> dict[str, Any]:
    payload = load_goal_set(path)
    result = validate_goal_set(payload)
    if include_merged_summary and result["ok"]:
        merged = merge_with_defaults(payload.get("goals", []))
        result["merged_goal_count"] = len(merged)
        result["external_goal_ids"] = [goal["goal_id"] for goal in payload.get("goals", [])]
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate read-only CPOS goal store JSON.")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="Validate goal set JSON without writing.")
    validate.add_argument("--path", required=True, help="Path to goal set JSON.")
    validate.add_argument("--include-merged-summary", action="store_true", help="Include merged-with-defaults counts only.")
    validate.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command != "validate":
        raise SystemExit(2)
    result = validate_file(args.path, include_merged_summary=args.include_merged_summary)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"goal_store_validation: ok={result['ok']} goal_count={result['goal_count']}")
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
