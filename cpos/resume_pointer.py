from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .world_model import build_world_model_snapshot

HANDOFF_SCHEMA = "kagioneko.safe_handoff_digest.v1"

POINTER_SCHEMA = "kagioneko.tape_memory_bridge_pointer.v1"
VALIDATION_SCHEMA = "kagioneko.resume_pointer_validation.v1"
WRITE_PLAN_SCHEMA = "kagioneko.tape_memory_write_plan.v1"
SAFETY_FLAGS = {
    "metadata_only": True,
    "raw_request_stored": False,
    "raw_diff_stored": False,
    "raw_outputs_stored": False,
    "secret_values_stored": False,
    "execute_automatically": False,
}


def _validation_error(code: str, field: str, message: str) -> dict[str, str]:
    return {"code": code, "field": field, "message": message}


def validate_resume_pointer(pointer: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    if not isinstance(pointer, dict):
        errors.append(_validation_error("pointer_must_be_object", "root", "resume pointer must be an object"))
        pointer = {}
    if pointer.get("schema") != POINTER_SCHEMA:
        errors.append(_validation_error("invalid_schema", "schema", f"schema must be {POINTER_SCHEMA}"))
    if pointer.get("pointer_type") != "cpos_resume":
        errors.append(_validation_error("invalid_pointer_type", "pointer_type", "pointer_type must be cpos_resume"))
    for key, expected in SAFETY_FLAGS.items():
        if pointer.get(key) is not expected:
            errors.append(_validation_error("safety_flag_violation", key, f"{key} must be {expected}"))
    write_policy = pointer.get("write_policy") or {}
    if write_policy.get("tape_memory_write_enabled") is not False:
        errors.append(_validation_error("write_enabled_forbidden", "write_policy.tape_memory_write_enabled", "tape-memory writes must be disabled in CPOS pointer MVP"))
    if write_policy.get("requires_human_confirmation_before_write") is not True:
        errors.append(_validation_error("human_confirmation_required", "write_policy.requires_human_confirmation_before_write", "future tape-memory writes require human confirmation"))
    if write_policy.get("stdout_only") is not True:
        errors.append(_validation_error("stdout_only_required", "write_policy.stdout_only", "pointer build must be stdout-only"))
    handoff = pointer.get("handoff") or {}
    if handoff.get("schema") == HANDOFF_SCHEMA:
        if handoff.get("body_included") is not False:
            errors.append(_validation_error("handoff_body_forbidden", "handoff.body_included", "handoff body must not be included"))
        if handoff.get("full_handoff_stored") is not False:
            errors.append(_validation_error("full_handoff_forbidden", "handoff.full_handoff_stored", "full handoff must not be stored"))
    return {
        "schema": VALIDATION_SCHEMA,
        "ok": not errors,
        "error_count": len(errors),
        "error_codes": sorted({error["code"] for error in errors}),
        "errors": errors,
        "write_enabled": False,
        "autonomous_goal_updates": False,
        "self_preservation_goals": False,
        **SAFETY_FLAGS,
    }


def build_tape_memory_write_plan(pointer: dict[str, Any]) -> dict[str, Any]:
    validation = validate_resume_pointer(pointer)
    return {
        "schema": WRITE_PLAN_SCHEMA,
        "dry_run": True,
        "would_write": False,
        "write_enabled": False,
        "requires_human_confirmation": True,
        "validation_ok": bool(validation.get("ok")),
        "validation_error_codes": validation.get("error_codes", []),
        "target": {
            "system": "tape-memory",
            "record_type": "cpos_resume_pointer",
            "path_or_key": "not_selected_in_dry_run",
        },
        "payload_schema": pointer.get("schema") if isinstance(pointer, dict) else None,
        "payload_pointer_type": pointer.get("pointer_type") if isinstance(pointer, dict) else None,
        "payload_body_included": False,
        "secret_scan_required_before_write": True,
        "human_confirmation_required_before_write": True,
        **SAFETY_FLAGS,
    }


def load_json_file(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_safe_handoff_digest(path: str | Path = "NEXT_HANDOFF.md", *, max_headings: int = 12) -> dict[str, Any]:
    handoff_path = Path(path)
    headings: list[str] = []
    if handoff_path.exists():
        for line in handoff_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                title = stripped.lstrip("#").strip()
                if title:
                    headings.append(title[:120])
    selected = headings[-max_headings:]
    return {
        "schema": HANDOFF_SCHEMA,
        "file": str(handoff_path.name),
        "exists": handoff_path.exists(),
        "heading_count": len(headings),
        "latest_heading": headings[-1] if headings else None,
        "recent_headings": selected,
        "body_included": False,
        "full_handoff_stored": False,
        **SAFETY_FLAGS,
    }


def _risk_names(world: dict[str, Any]) -> list[str]:
    return sorted(str(item.get("name")) for item in world.get("known_risks", []) if isinstance(item, dict) and item.get("name"))


def _git_commit(world: dict[str, Any]) -> str | None:
    metadata = world.get("repo", {}).get("git", {}).get("metadata", {})
    for key in ("head", "commit", "short_head", "head_short"):
        if metadata.get(key):
            return str(metadata[key])
    return None


def _goal_store_pointer(world: dict[str, Any]) -> dict[str, Any]:
    validation = world.get("goal_store_validation") or {}
    return {
        "validation_present": bool(validation),
        "validation_ok": bool(validation.get("ok")) if validation else None,
        "goal_count": validation.get("goal_count", 0) if validation else 0,
        "merged_goal_count": validation.get("merged_goal_count") if validation else None,
        "external_goal_ids": validation.get("external_goal_ids", []) if validation else [],
        "validation_error_count": validation.get("error_count", 0) if validation else 0,
        "validation_error_codes": validation.get("error_codes", []) if validation else [],
    }


def _reflection_pointer(reflection_evaluation: dict[str, Any] | None) -> dict[str, Any]:
    if not reflection_evaluation:
        return {
            "present": False,
            "last_recommendation": None,
            "last_risk": None,
            "goal_store_validation_used": False,
            "goal_store_error_codes": [],
        }
    return {
        "present": True,
        "last_recommendation": reflection_evaluation.get("recommendation"),
        "last_risk": reflection_evaluation.get("risk"),
        "goal_store_validation_used": bool(reflection_evaluation.get("goal_store_validation_used")),
        "goal_store_error_codes": reflection_evaluation.get("goal_store_error_codes", []),
    }


def build_resume_pointer(
    world_model_snapshot: dict[str, Any] | None = None,
    *,
    goal_store_path: str | Path | None = None,
    reflection_evaluation: dict[str, Any] | None = None,
    include_handoff_digest: bool = False,
    handoff_path: str | Path = "NEXT_HANDOFF.md",
) -> dict[str, Any]:
    world = world_model_snapshot or build_world_model_snapshot(goal_store_path=goal_store_path)
    repo = world.get("repo", {})
    return {
        "schema": POINTER_SCHEMA,
        "pointer_type": "cpos_resume",
        "repo": repo.get("public_repo", "kagioneko/cpos-engine-zero"),
        "repo_path_present": bool(repo.get("path")),
        "commit": _git_commit(world),
        "world_model": {
            "schema": world.get("schema"),
            "overall_risk": world.get("overall_risk"),
            "known_risk_names": _risk_names(world),
            "suggested_next_actions": world.get("suggested_next_actions", []),
        },
        "goal_store": _goal_store_pointer(world),
        "reflection": _reflection_pointer(reflection_evaluation),
        "handoff": build_safe_handoff_digest(handoff_path) if include_handoff_digest else {
            "file": "NEXT_HANDOFF.md",
            "section": "Latest Handoff",
            "digest_present": False,
        },
        "write_policy": {
            "tape_memory_write_enabled": False,
            "requires_human_confirmation_before_write": True,
            "stdout_only": True,
        },
        **SAFETY_FLAGS,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a read-only metadata-only CPOS resume pointer.")
    sub = parser.add_subparsers(dest="command", required=True)
    pointer = sub.add_parser("build", help="Build resume pointer JSON without writing to tape-memory.")
    pointer.add_argument("--goal-store", help="Optional goal store JSON to summarize through the World Model.")
    pointer.add_argument("--reflection-json", help="Optional Reflection Evaluator JSON to summarize in the pointer.")
    pointer.add_argument("--include-handoff-digest", action="store_true", help="Include safe heading-only NEXT_HANDOFF digest.")
    pointer.add_argument("--handoff-path", default="NEXT_HANDOFF.md", help="Handoff file to summarize by headings only.")
    pointer.add_argument("--json", action="store_true", help="Print JSON output.")
    validate = sub.add_parser("validate", help="Validate a resume pointer JSON file without writing.")
    validate.add_argument("--pointer-json", required=True, help="Resume pointer JSON file to validate.")
    validate.add_argument("--json", action="store_true", help="Print JSON output.")
    plan = sub.add_parser("write-plan", help="Build a dry-run tape-memory write plan without writing.")
    plan.add_argument("--pointer-json", required=True, help="Resume pointer JSON file to plan for.")
    plan.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "build":
        result = build_resume_pointer(
            goal_store_path=args.goal_store,
            reflection_evaluation=load_json_file(args.reflection_json),
            include_handoff_digest=args.include_handoff_digest,
            handoff_path=args.handoff_path,
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"resume_pointer: risk={result['world_model']['overall_risk']} write_enabled=false")
        return
    if args.command == "validate":
        result = validate_resume_pointer(load_json_file(args.pointer_json) or {})
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"resume_pointer_validation: ok={result['ok']} errors={result['error_count']}")
        if not result["ok"]:
            raise SystemExit(1)
        return
    if args.command == "write-plan":
        result = build_tape_memory_write_plan(load_json_file(args.pointer_json) or {})
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"tape_memory_write_plan: dry_run=true would_write=false validation_ok={result['validation_ok']}")
        return
    raise SystemExit(2)


if __name__ == "__main__":
    main()
