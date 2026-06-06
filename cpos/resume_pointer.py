from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .world_model import build_world_model_snapshot

HANDOFF_SCHEMA = "kagioneko.safe_handoff_digest.v1"

POINTER_SCHEMA = "kagioneko.tape_memory_bridge_pointer.v1"
SAFETY_FLAGS = {
    "metadata_only": True,
    "raw_request_stored": False,
    "raw_diff_stored": False,
    "raw_outputs_stored": False,
    "secret_values_stored": False,
    "execute_automatically": False,
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
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command != "build":
        raise SystemExit(2)
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


if __name__ == "__main__":
    main()
