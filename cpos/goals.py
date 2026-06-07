from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GOAL_SCHEMA = "kagioneko.goal.v1"
GOAL_SET_SCHEMA = "kagioneko.goal_set.v1"
ALLOWED_STATES = {"active", "paused", "blocked", "observing", "ready_for_review", "done", "archived", "planned"}
SAFETY_FLAGS = {
    "metadata_only": True,
    "raw_request_stored": False,
    "raw_diff_stored": False,
    "raw_outputs_stored": False,
    "secret_values_stored": False,
    "execute_automatically": False,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _goal(
    *,
    goal_id: str,
    title: str,
    scope: str,
    state: str,
    priority: str,
    success_criteria: list[str],
    safety_constraints: list[str],
    source_of_truth: list[str],
    requires_human_confirmation: bool,
    revisit_after: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    normalized_state = state if state in ALLOWED_STATES else "blocked"
    return {
        "schema": GOAL_SCHEMA,
        "goal_id": goal_id,
        "title": title,
        "scope": scope,
        "state": normalized_state,
        "priority": priority,
        "created_at": "2026-06-06",
        "updated_at": updated_at or _now_iso(),
        "revisit_after": revisit_after,
        "success_criteria": success_criteria,
        "safety_constraints": safety_constraints,
        "source_of_truth": source_of_truth,
        "requires_human_confirmation": bool(requires_human_confirmation),
        **SAFETY_FLAGS,
    }


def default_goals() -> list[dict[str, Any]]:
    """Return read-only default goals for the current Cognitive Agent OS work."""
    return [
        _goal(
            goal_id="cpos_v0_1_1_final",
            title="Decide final v0.1.1 release",
            scope="release",
            state="paused",
            priority="medium",
            revisit_after="after RC observation and explicit user confirmation",
            success_criteria=["no RC issues", "tests pass", "prepublish ok", "release_check ok", "explicit user confirmation"],
            safety_constraints=["no final tag without explicit confirmation", "no GitHub Release publish without explicit confirmation"],
            source_of_truth=["GITHUB_RELEASE_DRAFT_v0.1.1.md", "RELEASE_NOTES_v0.1.1.md", "NEXT_HANDOFF.md"],
            requires_human_confirmation=True,
        ),
        _goal(
            goal_id="zenn_cognitive_agent_os_article",
            title="Review/publish Cognitive Agent OS Zenn article",
            scope="article",
            state="ready_for_review",
            priority="medium",
            success_criteria=["published=false draft reviewed", "public-safe wording", "explicit user confirmation before publish"],
            safety_constraints=["do not publish without explicit confirmation", "avoid AGI completion claims", "do not expose private repo/log/DB details"],
            source_of_truth=["zenn/articles/cognitive-agent-os-safety-kernel.md"],
            requires_human_confirmation=True,
        ),
        _goal(
            goal_id="cognitive_agent_os_lab",
            title="Grow private Cognitive Agent OS lab materials",
            scope="system",
            state="active",
            priority="medium",
            success_criteria=["private/public boundary preserved", "research notes organized", "no secrets or raw logs committed"],
            safety_constraints=["private lab is not a secrets store", "sanitize before moving to public CPOS"],
            source_of_truth=["kagioneko/cognitive-agent-os-lab", "REPO_BOUNDARY.md"],
            requires_human_confirmation=False,
        ),
        _goal(
            goal_id="world_model_mvp",
            title="Build read-only World Model snapshot MVP",
            scope="project",
            state="done",
            priority="medium",
            success_criteria=["snapshot command exists", "tests pass", "prepublish ok", "pushed to public CPOS"],
            safety_constraints=["read-only", "metadata-only", "no raw logs/diffs/secrets"],
            source_of_truth=["cpos/world_model.py", "tests/test_world_model.py"],
            requires_human_confirmation=False,
        ),
        _goal(
            goal_id="goal_manager_mvp",
            title="Build read-only Goal Manager MVP",
            scope="project",
            state="done",
            priority="high",
            success_criteria=["default goals list as JSON", "world model includes goal summary", "tests pass", "prepublish ok"],
            safety_constraints=["read-only first", "no autonomous goal updates", "no self-preservation goals"],
            source_of_truth=["docs/SENSOR_AND_GOAL_MANAGER_SPEC.md"],
            requires_human_confirmation=False,
        ),
        _goal(
            goal_id="db_inventory_sensor",
            title="Build path-only DB inventory sensor",
            scope="project",
            state="done",
            priority="medium",
            success_criteria=["path-only inventory command exists", "denylist credential/token/session DBs", "no row contents", "tests pass"],
            safety_constraints=["do not open sensitive credential DBs", "no raw private prompts/diary/log rows"],
            source_of_truth=["docs/DB_REFLECTION_SOURCE_INVENTORY.md", "cpos/sensors/db_inventory_sensor.py"],
            requires_human_confirmation=False,
        ),
        _goal(
            goal_id="android_emilia_bridge_sensor",
            title="Build observe-only Android Emilia bridge inventory sensor",
            scope="project",
            state="done",
            priority="medium",
            success_criteria=["bridge/reference availability only", "privacy review before ingestion", "no raw phone data", "tests pass"],
            safety_constraints=["observe-only", "no microphone/camera/location/diary ingestion by default", "no upload/publish triggers"],
            source_of_truth=["docs/ANDROID_EMILIA_SENSOR_BRIDGE.md", "cpos/sensors/android_emilia_sensor.py"],
            requires_human_confirmation=False,
        ),

        _goal(
            goal_id="reflection_evaluator_mvp",
            title="Build read-only Reflection Evaluator MVP",
            scope="project",
            state="done",
            priority="high",
            success_criteria=["evaluate command exists", "proceed/ask/defer/block recommendations", "tests pass", "no execution"],
            safety_constraints=["read-only", "metadata-only", "does not bypass Human Escalation", "does not read raw DB/Android/private data"],
            source_of_truth=["cpos/reflection_evaluator.py", "tests/test_reflection_evaluator.py"],
            requires_human_confirmation=False,
        ),

        _goal(
            goal_id="goal_store_phase1",
            title="Build read-only Goal Store schema validator",
            scope="project",
            state="done",
            priority="high",
            success_criteria=["validator command exists", "example goal set exists", "tests pass", "no writes"],
            safety_constraints=["read-only", "rejects secrets/raw logs/raw DB/Android data", "rejects self-preservation goals", "rejects autonomous goal updates"],
            source_of_truth=["cpos/goal_store.py", "goals/goals.example.json", "tests/test_goal_store.py"],
            requires_human_confirmation=False,
        ),

        _goal(
            goal_id="reflection_goal_store_gate",
            title="Connect Goal Store validation to Reflection Evaluator",
            scope="project",
            state="done",
            priority="high",
            success_criteria=["evaluator accepts optional goal store", "invalid goal store blocks reliance on persisted goals", "tests pass", "no writes"],
            safety_constraints=["read-only", "metadata-only validation summary", "no autonomous goal updates", "no raw goal bodies duplicated in evaluation output"],
            source_of_truth=["cpos/reflection_evaluator.py", "cpos/world_model.py", "tests/test_reflection_evaluator.py"],
            requires_human_confirmation=False,
        ),

        _goal(
            goal_id="goal_store_summary_export",
            title="Add metadata-only Goal Store summary export",
            scope="project",
            state="done",
            priority="medium",
            success_criteria=["summary command exists", "merged counts and IDs only", "tests pass", "no files written"],
            safety_constraints=["read-only", "metadata-only", "no raw goal bodies", "no secrets/raw logs/raw DB/Android data"],
            source_of_truth=["cpos/goal_store.py", "tests/test_goal_store.py"],
            requires_human_confirmation=False,
        ),

        _goal(
            goal_id="tape_memory_bridge_design",
            title="Document metadata-only tape-memory bridge design",
            scope="system",
            state="done",
            priority="medium",
            success_criteria=["pointer schema documented", "write/read safety policy documented", "tests pass"],
            safety_constraints=["design-only", "no runtime writes", "no raw handoff/private content", "human confirmation before future write path"],
            source_of_truth=["docs/TAPE_MEMORY_BRIDGE_DESIGN.md"],
            requires_human_confirmation=False,
        ),

        _goal(
            goal_id="resume_pointer_cli",
            title="Build read-only resume pointer CLI",
            scope="project",
            state="done",
            priority="high",
            success_criteria=["resume pointer command exists", "World Model can include pointer", "tests pass", "no tape-memory writes"],
            safety_constraints=["stdout-only", "metadata-only", "no raw handoff/private paths", "future tape-memory writes require explicit confirmation"],
            source_of_truth=["cpos/resume_pointer.py", "cpos/world_model.py", "tests/test_resume_pointer.py"],
            requires_human_confirmation=False,
        ),

        _goal(
            goal_id="resume_pointer_reflection_handoff",
            title="Connect Reflection metadata and safe handoff digest to resume pointer",
            scope="project",
            state="done",
            priority="high",
            success_criteria=["reflection JSON metadata can be included", "heading-only handoff digest can be included", "tests pass", "no tape-memory writes"],
            safety_constraints=["stdout-only", "metadata-only", "no raw handoff body", "no raw outputs/diffs/request bodies/secrets"],
            source_of_truth=["cpos/resume_pointer.py", "tests/test_resume_pointer.py"],
            requires_human_confirmation=False,
        ),

        _goal(
            goal_id="resume_pointer_validator_dry_run",
            title="Add resume pointer validator and tape-memory write dry-run plan",
            scope="project",
            state="done",
            priority="high",
            success_criteria=["pointer validator exists", "dry-run write plan exists", "tests pass", "no tape-memory writes"],
            safety_constraints=["dry-run only", "would_write=false", "write_enabled=false", "human confirmation and secret scan required before any future write"],
            source_of_truth=["cpos/resume_pointer.py", "docs/TAPE_MEMORY_BRIDGE_DESIGN.md", "tests/test_resume_pointer.py"],
            requires_human_confirmation=False,
        ),

        _goal(
            goal_id="resume_pipeline_bundle",
            title="Build integrated read-only resume pipeline bundle",
            scope="project",
            state="done",
            priority="high",
            success_criteria=["one command runs reflection, pointer build, validation, and dry-run write plan", "tests pass", "no writes or execution"],
            safety_constraints=["read-only", "metadata-only", "dry-run write plan only", "no raw outputs/diffs/request bodies/handoff bodies/secrets"],
            source_of_truth=["cpos/resume_pipeline.py", "tests/test_resume_pipeline.py"],
            requires_human_confirmation=False,
        ),

        _goal(
            goal_id="resume_pipeline_compact",
            title="Add compact resume pipeline output",
            scope="project",
            state="done",
            priority="medium",
            success_criteria=["compact option exists", "verbose handoff heading list omitted", "tests pass", "no writes"],
            safety_constraints=["metadata-only", "no raw handoff body", "no raw outputs/diffs/request bodies/secrets", "dry-run write plan only"],
            source_of_truth=["cpos/resume_pipeline.py", "tests/test_resume_pipeline.py", "docs/backlog/V0_1_2_BACKLOG.md"],
            requires_human_confirmation=False,
        ),

        _goal(
            goal_id="resume_pipeline_secret_scan_summary",
            title="Add compact resume pipeline secret scan and v0.1.2 summary",
            scope="project",
            state="done",
            priority="high",
            success_criteria=["compact payload scan exists", "summary doc exists", "tests pass", "no writes"],
            safety_constraints=["pattern/count output only", "no secret values printed", "metadata-only", "dry-run write plan only"],
            source_of_truth=["cpos/resume_pipeline.py", "docs/V0_1_2_RESUME_PIPELINE_SUMMARY.md", "tests/test_resume_pipeline.py"],
            requires_human_confirmation=False,
        ),

        _goal(
            goal_id="vault_backed_notion_helper",
            title="Add Vault-backed Notion helper dry-run path",
            scope="project",
            state="done",
            priority="high",
            success_criteria=["dry-run helper exists", "Vault-only execute path exists", "tests pass", "no hardcoded credentials"],
            safety_constraints=["dry-run by default", "--execute required for network write", "no tokens/database IDs printed", "Vault secret/notion only"],
            source_of_truth=["cpos/notion_vault_client.py", "docs/VAULT_BACKED_NOTION_HELPER.md", "tests/test_notion_vault_client.py"],
            requires_human_confirmation=False,
        ),
    ]


def list_goals(*, state: str | None = None, scope: str | None = None) -> dict[str, Any]:
    goals = default_goals()
    if state:
        goals = [goal for goal in goals if goal.get("state") == state]
    if scope:
        goals = [goal for goal in goals if goal.get("scope") == scope]
    counts_by_state: dict[str, int] = {}
    for goal in goals:
        counts_by_state[goal["state"]] = counts_by_state.get(goal["state"], 0) + 1
    return {
        "schema": GOAL_SET_SCHEMA,
        "count": len(goals),
        "counts_by_state": counts_by_state,
        "goals": goals,
        "source": "default_read_only_goals",
        "write_enabled": False,
        "autonomous_goal_updates": False,
        "self_preservation_goals": False,
        **SAFETY_FLAGS,
    }


def goal_summary() -> dict[str, Any]:
    payload = list_goals()
    active_or_review = [goal for goal in payload["goals"] if goal["state"] in {"active", "ready_for_review"}]
    confirmation_required = [goal["goal_id"] for goal in payload["goals"] if goal["requires_human_confirmation"]]
    return {
        "schema": "kagioneko.goal_summary.v1",
        "count": payload["count"],
        "counts_by_state": payload["counts_by_state"],
        "active_or_review_goal_ids": [goal["goal_id"] for goal in active_or_review],
        "confirmation_required_goal_ids": confirmation_required,
        "write_enabled": False,
        "autonomous_goal_updates": False,
        "self_preservation_goals": False,
        **SAFETY_FLAGS,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only metadata-only CPOS Goal Manager MVP.")
    sub = parser.add_subparsers(dest="command", required=True)
    list_cmd = sub.add_parser("list", help="List default goals.")
    list_cmd.add_argument("--state", help="Filter by state.")
    list_cmd.add_argument("--scope", help="Filter by scope.")
    list_cmd.add_argument("--json", action="store_true", help="Print JSON output.")
    summary_cmd = sub.add_parser("summary", help="Show goal summary.")
    summary_cmd.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def _print_text(payload: dict[str, Any]) -> None:
    if "goals" in payload:
        for goal in payload["goals"]:
            print(f"{goal['goal_id']} state={goal['state']} scope={goal['scope']} title={goal['title']}")
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "list":
        payload = list_goals(state=args.state, scope=args.scope)
    elif args.command == "summary":
        payload = goal_summary()
    else:
        raise SystemExit(2)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_text(payload)


if __name__ == "__main__":
    main()
