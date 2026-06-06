from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .goals import goal_summary
from .release_check import run_release_check
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


def build_world_model_snapshot(repo: str | Path | None = None) -> dict[str, Any]:
    repo_path = Path(repo).resolve() if repo else _repo_root()
    git_event = observe_git_repo(repo_path)
    time_event = observe_time_session(repo_path)
    release_check = run_release_check() if repo_path == _repo_root() else {"ok": False, "git_status_lines": [], "tracked_bad_artifacts": [], "missing_files": [], "failures": [{"name": "repo", "error": "release_check_only_supported_for_cpos_root"}]}
    goal_state = goal_summary()
    risks = _known_risks(git_event, time_event, release_check)
    risk = _max_risk(git_event.get("risk", "low"), time_event.get("risk", "low"), *(item.get("risk", "low") for item in risks))

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
    snapshot.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "snapshot":
        parser.print_help()
        raise SystemExit(2)
    result = build_world_model_snapshot(args.repo)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"world_model_snapshot: risk={result['overall_risk']} repo={result['repo']['path']}")


if __name__ == "__main__":
    main()
