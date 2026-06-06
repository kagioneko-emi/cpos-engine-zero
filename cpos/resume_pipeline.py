from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .reflection_evaluator import evaluate_proposed_action
from .resume_pointer import build_resume_pointer, build_tape_memory_write_plan, validate_resume_pointer
from .world_model import build_world_model_snapshot

PIPELINE_SCHEMA = "kagioneko.resume_pipeline_bundle.v1"
COMPACT_PIPELINE_SCHEMA = "kagioneko.resume_pipeline_compact.v1"
SAFETY_FLAGS = {
    "metadata_only": True,
    "raw_request_stored": False,
    "raw_diff_stored": False,
    "raw_outputs_stored": False,
    "secret_values_stored": False,
    "execute_automatically": False,
}


def _action_from_options(
    *,
    action_type: str,
    summary: str,
    target_repo: str,
    touches_public_surface: bool,
    touches_private_context: bool,
    requires_execution: bool,
    explicit_confirmation: bool,
) -> dict[str, Any]:
    return {
        "action_id": "resume_pipeline_action",
        "action_type": action_type,
        "summary": summary,
        "target_repo": target_repo,
        "touches_public_surface": touches_public_surface,
        "touches_private_context": touches_private_context,
        "requires_execution": requires_execution,
        "explicit_confirmation": explicit_confirmation,
    }


def _compact_reflection(evaluation: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": evaluation.get("schema"),
        "action_id": evaluation.get("action_id"),
        "action_type": evaluation.get("action_type"),
        "recommendation": evaluation.get("recommendation"),
        "risk": evaluation.get("risk"),
        "required_confirmation_count": len(evaluation.get("required_confirmations") or []),
        "blocking_issue_count": len(evaluation.get("blocking_issues") or []),
        "goal_store_validation_used": bool(evaluation.get("goal_store_validation_used")),
        "goal_store_error_codes": evaluation.get("goal_store_error_codes", []),
        **SAFETY_FLAGS,
    }


def compact_resume_pipeline_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    pointer = bundle.get("resume_pointer") or {}
    handoff = pointer.get("handoff") or {}
    validation = bundle.get("resume_pointer_validation") or {}
    write_plan = bundle.get("tape_memory_write_plan") or {}
    return {
        "schema": COMPACT_PIPELINE_SCHEMA,
        "pipeline_type": bundle.get("pipeline_type"),
        "steps": bundle.get("steps", []),
        "overall": bundle.get("overall", {}),
        "reflection": bundle.get("reflection", {}),
        "resume_pointer": {
            "schema": pointer.get("schema"),
            "pointer_type": pointer.get("pointer_type"),
            "repo": pointer.get("repo"),
            "commit": pointer.get("commit"),
            "world_model": pointer.get("world_model", {}),
            "goal_store": pointer.get("goal_store", {}),
            "reflection": pointer.get("reflection", {}),
            "handoff": {
                "schema": handoff.get("schema"),
                "file": handoff.get("file"),
                "latest_heading": handoff.get("latest_heading"),
                "heading_count": handoff.get("heading_count"),
                "recent_heading_count": len(handoff.get("recent_headings") or []),
                "body_included": False,
                "full_handoff_stored": False,
            },
            "write_policy": pointer.get("write_policy", {}),
            **SAFETY_FLAGS,
        },
        "resume_pointer_validation": {
            "schema": validation.get("schema"),
            "ok": bool(validation.get("ok")),
            "error_count": validation.get("error_count", 0),
            "error_codes": validation.get("error_codes", []),
            **SAFETY_FLAGS,
        },
        "tape_memory_write_plan": {
            "schema": write_plan.get("schema"),
            "dry_run": True,
            "would_write": False,
            "write_enabled": False,
            "validation_ok": bool(write_plan.get("validation_ok")),
            "validation_error_codes": write_plan.get("validation_error_codes", []),
            "secret_scan_required_before_write": True,
            "human_confirmation_required_before_write": True,
            **SAFETY_FLAGS,
        },
        **SAFETY_FLAGS,
    }


def build_resume_pipeline_bundle(
    *,
    goal_store_path: str | Path | None = None,
    action_type: str = "doc",
    summary: str = "Build safe resume pipeline bundle",
    target_repo: str = "cpos",
    touches_public_surface: bool = False,
    touches_private_context: bool = False,
    requires_execution: bool = False,
    explicit_confirmation: bool = False,
    include_handoff_digest: bool = True,
    handoff_path: str | Path = "NEXT_HANDOFF.md",
) -> dict[str, Any]:
    world = build_world_model_snapshot(goal_store_path=goal_store_path)
    action = _action_from_options(
        action_type=action_type,
        summary=summary,
        target_repo=target_repo,
        touches_public_surface=touches_public_surface,
        touches_private_context=touches_private_context,
        requires_execution=requires_execution,
        explicit_confirmation=explicit_confirmation,
    )
    evaluation = evaluate_proposed_action(action, world_model_snapshot=world)
    pointer = build_resume_pointer(
        world,
        reflection_evaluation=evaluation,
        include_handoff_digest=include_handoff_digest,
        handoff_path=handoff_path,
    )
    pointer_validation = validate_resume_pointer(pointer)
    write_plan = build_tape_memory_write_plan(pointer)
    return {
        "schema": PIPELINE_SCHEMA,
        "pipeline_type": "reflection_to_resume_pointer_dry_run",
        "steps": [
            "world_model_snapshot",
            "reflection_evaluation",
            "resume_pointer_build",
            "resume_pointer_validation",
            "tape_memory_write_plan_dry_run",
        ],
        "reflection": _compact_reflection(evaluation),
        "resume_pointer": pointer,
        "resume_pointer_validation": pointer_validation,
        "tape_memory_write_plan": write_plan,
        "overall": {
            "recommendation": evaluation.get("recommendation"),
            "risk": evaluation.get("risk"),
            "pointer_validation_ok": bool(pointer_validation.get("ok")),
            "would_write": False,
            "write_enabled": False,
            "requires_human_confirmation_before_write": True,
        },
        **SAFETY_FLAGS,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a read-only CPOS resume pipeline bundle.")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Evaluate action, build pointer, validate it, and build dry-run write plan.")
    run.add_argument("--goal-store", help="Optional goal store JSON to validate through World Model.")
    run.add_argument("--action-type", default="doc")
    run.add_argument("--summary", default="Build safe resume pipeline bundle")
    run.add_argument("--target-repo", default="cpos")
    run.add_argument("--touches-public-surface", action="store_true")
    run.add_argument("--touches-private-context", action="store_true")
    run.add_argument("--requires-execution", action="store_true")
    run.add_argument("--explicit-confirmation", action="store_true")
    run.add_argument("--include-handoff-digest", action="store_true", default=True)
    run.add_argument("--no-handoff-digest", action="store_false", dest="include_handoff_digest")
    run.add_argument("--handoff-path", default="NEXT_HANDOFF.md")
    run.add_argument("--compact", action="store_true", help="Print compact metadata-only pipeline summary.")
    run.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command != "run":
        raise SystemExit(2)
    result = build_resume_pipeline_bundle(
        goal_store_path=args.goal_store,
        action_type=args.action_type,
        summary=args.summary,
        target_repo=args.target_repo,
        touches_public_surface=args.touches_public_surface,
        touches_private_context=args.touches_private_context,
        requires_execution=args.requires_execution,
        explicit_confirmation=args.explicit_confirmation,
        include_handoff_digest=args.include_handoff_digest,
        handoff_path=args.handoff_path,
    )
    if args.compact:
        result = compact_resume_pipeline_bundle(result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            "resume_pipeline: "
            f"recommendation={result['overall']['recommendation']} "
            f"risk={result['overall']['risk']} "
            f"pointer_ok={result['overall']['pointer_validation_ok']} "
            "would_write=false"
        )


if __name__ == "__main__":
    main()
