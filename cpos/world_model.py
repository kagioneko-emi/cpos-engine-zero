from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .goal_store import validate_file as validate_goal_store_file
from .goals import goal_summary
from .release_check import run_release_check
from .sensors.android_emilia_sensor import observe_android_emilia_bridge
from .sensors.db_inventory_sensor import inventory_db_paths
from .sensors.git_sensor import observe_git_repo
from .sensors.time_session_sensor import observe_time_session

SNAPSHOT_SCHEMA = "kagioneko.world_model_snapshot.v1"
EXPECTED_REMOTE = "https://github.com/kagioneko/cpos-engine-zero.git"
PUBLIC_REPO = "kagioneko/cpos-engine-zero"
PRIVATE_LAB_REPO = "kagioneko/cognitive-agent-os-lab"
PUBLIC_PRIVATE_BOUNDARY_DOCS = [
    "docs/COGNITIVE_AGENT_OS_ROADMAP.md",
    "NEXT_HANDOFF.md",
]

SAFETY_FLAGS = {
    "metadata_only": True,
    "raw_request_stored": False,
    "raw_diff_stored": False,
    "raw_outputs_stored": False,
    "secret_values_stored": False,
    "execute_automatically": False,
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _risk_rank(risk: str) -> int:
    return {"low": 0, "medium": 1, "high": 2, "critical": 3}.get(risk, 1)


def _max_risk(*risks: str) -> str:
    ordered = [risk for risk in risks if risk]
    if not ordered:
        return "low"
    return max(ordered, key=_risk_rank)




def _compact_sensor(event: dict[str, Any]) -> dict[str, Any]:
    metadata = event.get("metadata") or {}
    compact_keys = {
        "candidate_count",
        "sensitive_skipped_count",
        "reflection_candidate_count",
        "db_files_opened",
        "table_names_read",
        "row_contents_read",
        "content_read",
        "phone_data_read",
        "diary_text_read",
        "sensor_stream_read",
        "upload_triggered",
        "publish_triggered",
        "video_pipeline_triggered",
        "phone_control_enabled",
        "reference_count",
        "existing_count",
        "missing_count",
    }
    return {
        "schema": event.get("schema"),
        "source": event.get("source"),
        "event_type": event.get("event_type"),
        "summary": event.get("summary"),
        "risk": event.get("risk"),
        "requires_human_review": event.get("requires_human_review"),
        "suggested_next_action": event.get("suggested_next_action"),
        "metadata": {key: metadata.get(key) for key in sorted(compact_keys) if key in metadata},
        "metadata_only": event.get("metadata_only") is True,
        "raw_request_stored": False,
        "raw_diff_stored": False,
        "raw_outputs_stored": False,
        "secret_values_stored": False,
        "execute_automatically": False,
    }


def _optional_sensor_risks(optional_sensors: dict[str, Any]) -> list[dict[str, str]]:
    risks: list[dict[str, str]] = []
    db = optional_sensors.get("db_inventory")
    if db and db.get("metadata", {}).get("sensitive_skipped_count", 0):
        risks.append({"risk": "high", "name": "db_sensitive_paths_observed", "summary": "DB inventory found sensitive-skipped paths; do not open without review"})
    android = optional_sensors.get("android_emilia")
    if android and android.get("metadata", {}).get("existing_count", 0):
        risks.append({"risk": "medium", "name": "android_emilia_bridge_observed", "summary": "Android Emilia references detected; privacy review required before ingestion"})
    return risks



def _compact_goal_store_validation(result: dict[str, Any], path: str | Path) -> dict[str, Any]:
    errors = result.get("errors") or []
    return {
        "schema": result.get("schema"),
        "path": str(path),
        "ok": bool(result.get("ok")),
        "goal_count": result.get("goal_count", 0),
        "merged_goal_count": result.get("merged_goal_count"),
        "external_goal_ids": result.get("external_goal_ids", []),
        "error_count": len(errors),
        "error_codes": sorted({str(error.get("code")) for error in errors if isinstance(error, dict)}),
        "write_enabled": False,
        "autonomous_goal_updates": False,
        "self_preservation_goals": False,
        "metadata_only": True,
        "raw_request_stored": False,
        "raw_diff_stored": False,
        "raw_outputs_stored": False,
        "secret_values_stored": False,
        "execute_automatically": False,
    }


def _goal_store_risks(goal_store_validation: dict[str, Any] | None) -> list[dict[str, str]]:
    if not goal_store_validation:
        return []
    if goal_store_validation.get("ok"):
        return []
    return [{
        "risk": "medium",
        "name": "goal_store_validation_failed",
        "summary": "Goal store validation failed; use defaults or fix goal store before relying on persisted goals",
    }]

def _release_state(release_check: dict[str, Any]) -> dict[str, Any]:
    return {
        "repo": PUBLIC_REPO,
        "expected_remote": EXPECTED_REMOTE,
        "release_check_ok": bool(release_check.get("ok")),
        "working_tree_clean_for_release": not bool(release_check.get("git_status_lines")),
        "tracked_bad_artifacts_count": len(release_check.get("tracked_bad_artifacts") or []),
        "missing_files_count": len(release_check.get("missing_files") or []),
        "final_release_requires_explicit_confirmation": True,
        "known_rc": "v0.1.1-rc1",
        "final_v0_1_1_paused": True,
    }


def _known_risks(git_event: dict[str, Any], time_event: dict[str, Any], release_check: dict[str, Any]) -> list[dict[str, str]]:
    risks: list[dict[str, str]] = []
    if git_event.get("event_type") == "remote_secret_risk_detected":
        risks.append({"risk": "high", "name": "remote_secret_risk", "summary": "remote URL credential material was redacted"})
    if git_event.get("event_type") == "git_dirty":
        risks.append({"risk": "medium", "name": "dirty_working_tree", "summary": git_event.get("summary", "repo has changes")})
    if git_event.get("event_type") == "git_ahead":
        risks.append({"risk": "medium", "name": "unpushed_commits", "summary": git_event.get("summary", "branch is ahead")})
    if git_event.get("event_type") == "git_behind":
        risks.append({"risk": "medium", "name": "behind_upstream", "summary": git_event.get("summary", "branch is behind")})
    if time_event.get("event_type") == "late_night_session":
        risks.append({"risk": "medium", "name": "late_night_high_stakes_caution", "summary": "extra confirmation recommended for release/publish/destructive actions"})
    if not release_check.get("ok"):
        risks.append({"risk": "medium", "name": "release_check_not_ready", "summary": "release_check reports non-ready state"})
    risks.append({"risk": "medium", "name": "public_private_boundary", "summary": "Android/DB/private strategy should stay in private lab until sanitized"})
    return risks


def _suggested_next_actions(git_event: dict[str, Any], time_event: dict[str, Any], release_check: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    if git_event.get("event_type") == "git_dirty":
        actions.append("review_and_commit_or_revert_local_changes")
    elif git_event.get("event_type") == "git_ahead":
        actions.append("ask_before_push")
    elif git_event.get("event_type") == "remote_secret_risk_detected":
        actions.append("rotate_or_remove_credential_from_remote")
    else:
        actions.append("continue_world_model_or_goal_manager_work")

    if time_event.get("event_type") == "late_night_session":
        actions.append("prefer_handoff_before_high_stakes_actions")
    if release_check.get("ok"):
        actions.append("release_work_still_requires_explicit_confirmation")
    else:
        actions.append("fix_release_check_before_release_or_publish")
    actions.append("keep_private_lab_material_out_of_public_cpos_until_reviewed")
    return actions


def build_world_model_snapshot(
    repo: str | Path | None = None,
    *,
    include_db_inventory: bool = False,
    db_root: str | Path | None = None,
    include_android_emilia: bool = False,
    android_references: dict[str, str] | None = None,
    goal_store_path: str | Path | None = None,
) -> dict[str, Any]:
    repo_path = Path(repo).resolve() if repo else _repo_root()
    git_event = observe_git_repo(repo_path)
    time_event = observe_time_session(repo_path)
    release_check = run_release_check() if repo_path == _repo_root() else {"ok": False, "git_status_lines": [], "tracked_bad_artifacts": [], "missing_files": [], "failures": [{"name": "repo", "error": "release_check_only_supported_for_cpos_root"}]}
    goal_state = goal_summary()
    optional_sensors: dict[str, Any] = {}
    goal_store_validation = None
    if goal_store_path:
        goal_store_validation = _compact_goal_store_validation(
            validate_goal_store_file(goal_store_path, include_merged_summary=True),
            goal_store_path,
        )
    if include_db_inventory:
        optional_sensors["db_inventory"] = _compact_sensor(inventory_db_paths(db_root or repo_path))
    if include_android_emilia:
        optional_sensors["android_emilia"] = _compact_sensor(observe_android_emilia_bridge(android_references or {}))
    risks = _known_risks(git_event, time_event, release_check) + _optional_sensor_risks(optional_sensors) + _goal_store_risks(goal_store_validation)
    optional_risks = [sensor.get("risk", "low") for sensor in optional_sensors.values()]
    risk = _max_risk(git_event.get("risk", "low"), time_event.get("risk", "low"), *optional_risks, *(item.get("risk", "low") for item in risks))

    return {
        "schema": SNAPSHOT_SCHEMA,
        "snapshot_type": "cpos_current_state",
        "repo": {
            "path": str(repo_path),
            "public_repo": PUBLIC_REPO,
            "private_lab_repo": PRIVATE_LAB_REPO,
            "git": git_event,
        },
        "session": {
            "time": time_event,
            "late_night_extra_confirmation": bool(time_event.get("metadata", {}).get("extra_confirmation_for_high_stakes")),
        },
        "release": _release_state(release_check),
        "goals": goal_state,
        "goal_store_validation": goal_store_validation,
        "optional_sensors": optional_sensors,
        "public_private_boundary": {
            "public_repo": PUBLIC_REPO,
            "private_lab_repo": PRIVATE_LAB_REPO,
            "rule": "public CPOS keeps release-ready safety-kernel material; private lab keeps Cognitive Agent OS research until sanitized and reviewed",
            "source_of_truth": PUBLIC_PRIVATE_BOUNDARY_DOCS,
        },
        "known_risks": risks,
        "suggested_next_actions": _suggested_next_actions(git_event, time_event, release_check),
        "overall_risk": risk,
        **SAFETY_FLAGS,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only metadata-only CPOS world model snapshot.")
    sub = parser.add_subparsers(dest="command")
    snapshot = sub.add_parser("snapshot", help="Build current world model snapshot.")
    snapshot.add_argument("--repo", default=None, help="Repository path to observe. Defaults to CPOS root.")
    snapshot.add_argument("--goal-store", help="Optional goal store JSON to validate and summarize.")
    snapshot.add_argument("--include-db-inventory", action="store_true", help="Include compact path-only DB inventory summary.")
    snapshot.add_argument("--db-root", default=None, help="Root for DB inventory when included. Defaults to observed repo.")
    snapshot.add_argument("--include-android-emilia", action="store_true", help="Include compact Android Emilia bridge inventory summary.")
    snapshot.add_argument("--android-repo", help="Optional Android app repository path for Android Emilia inventory.")
    snapshot.add_argument("--receiver", help="Optional VPS receiver path for Android Emilia inventory.")
    snapshot.add_argument("--article", help="Optional article path for Android Emilia inventory.")
    snapshot.add_argument("--ref", action="append", help="Optional Android Emilia reference in NAME=PATH form. Can be repeated.")
    snapshot.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "snapshot":
        parser.print_help()
        raise SystemExit(2)
    android_refs: dict[str, str] = {}
    for value in args.ref or []:
        if "=" not in value:
            raise SystemExit("--ref must be NAME=PATH")
        name, ref_path = value.split("=", 1)
        if not name or not ref_path:
            raise SystemExit("--ref must be NAME=PATH")
        android_refs[name] = ref_path
    if args.android_repo:
        android_refs["android_app_repo"] = args.android_repo
    if args.receiver:
        android_refs["vps_receiver"] = args.receiver
    if args.article:
        android_refs["public_article"] = args.article
    result = build_world_model_snapshot(
        args.repo,
        include_db_inventory=args.include_db_inventory,
        db_root=args.db_root,
        include_android_emilia=args.include_android_emilia,
        android_references=android_refs,
        goal_store_path=args.goal_store,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"world_model_snapshot: risk={result['overall_risk']} repo={result['repo']['path']}")


if __name__ == "__main__":
    main()
