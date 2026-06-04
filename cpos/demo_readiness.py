from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agent_adapter import build_external_agent_result_scoreboard, pending_external_agent_actions
from .auto_fix_candidate import pending_auto_fix_candidates
from .diff_review_draft import pending_diff_review_drafts
from .execution_driver import build_execution_scoreboard
from .github_diff_review import pending_github_diff_reviews
from .human_escalation import pending_human_escalations
from .patch_generation_review import pending_patch_generation_reviews
from .sandbox_flow_graph import build_sandbox_flow_graph
from .sandbox_patch_runner import completed_sandbox_patch_executions, ready_to_run_sandbox_patch_executions
from .task_tape import TaskTapeStore

REQUIRED_TAPE_KEYS = {
    "cpos_resume_latest",
    "cpos_safety_invariants",
    "cpos_next_action",
    "cpos_mcp_tape_memory",
}


def _tape_memory_snapshot(tape_store_path: str | Path | None = None) -> dict[str, Any]:
    root = Path(tape_store_path or "/home/mayutama/.tape-memory-mcp-cpos")
    tapes_path = root / "tapes.json"
    keys: list[str] = []
    ok = False
    if tapes_path.exists():
        try:
            data = json.loads(tapes_path.read_text(encoding="utf-8") or "{}")
            if isinstance(data, dict):
                keys = sorted(str(key) for key in data.keys())
                ok = REQUIRED_TAPE_KEYS.issubset(set(keys))
        except json.JSONDecodeError:
            ok = False
    return {
        "ok": ok,
        "store": str(root),
        "keys": keys,
        "required_keys": sorted(REQUIRED_TAPE_KEYS),
        "missing_keys": sorted(REQUIRED_TAPE_KEYS - set(keys)),
        "metadata_only": True,
        "raw_values_stored": False,
    }


def _pending_tape_memory_reviews(mcp_registry: Any | None) -> list[dict[str, Any]]:
    if mcp_registry is None:
        return []
    try:
        reviews = mcp_registry.reviews(status="pending")
    except Exception:
        return []
    return [
        row for row in reviews
        if row.get("connector_id") == "mcp://tape-memory/cpos-resume"
    ]


def build_competitive_demo_readiness(
    store: TaskTapeStore,
    *,
    mcp_registry: Any | None = None,
    tape_store_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build a metadata-only demo readiness snapshot.

    This is a presentation/readiness layer only. It never executes tools, applies
    patches, approves reviews, commits, pushes, creates PRs, or stores raw diff
    text/output/request/checkpoint/secret values.
    """
    tape = _tape_memory_snapshot(tape_store_path)
    tape_reviews = _pending_tape_memory_reviews(mcp_registry)
    external_agent_actions = pending_external_agent_actions(store)
    external_agent_scoreboard = build_external_agent_result_scoreboard(store)
    human_escalations = pending_human_escalations(store)
    patch_generations = pending_patch_generation_reviews(store)
    ready_runs = ready_to_run_sandbox_patch_executions(store)
    completed_runs = completed_sandbox_patch_executions(store)
    github_diffs = pending_github_diff_reviews(store)
    drafts = pending_diff_review_drafts(store)
    candidates = pending_auto_fix_candidates(store)
    scoreboard = build_execution_scoreboard(store)
    graph = build_sandbox_flow_graph(store, limit=50)
    graph_counts = graph.get("counts") or {}

    stages = [
        {
            "name": "Fast Resume Cache",
            "ready": bool(tape["ok"]),
            "count": len(tape["keys"]),
            "next_action": "Load tape-memory resume keys before long handoff reads",
            "evidence": tape,
        },
        {
            "name": "MCP Review-Gated Memory",
            "ready": True,
            "count": len(tape_reviews),
            "next_action": "Approve tape-memory MCP review only with explicit human approval",
            "endpoint": "/mcp/reviews?status=pending",
        },
        {
            "name": "External Agent Adapter",
            "ready": True,
            "count": len(external_agent_actions),
            "next_action": "Review external agent contracts before action execution",
            "endpoint": "/agent-adapter/actions",
        },
        {
            "name": "Human Escalation Queue",
            "ready": True,
            "count": len(human_escalations),
            "next_action": "Approve or reject through owning pipeline endpoints",
            "endpoint": "/human-escalations",
        },
        {
            "name": "Patch Generation Review",
            "ready": True,
            "count": len(patch_generations),
            "next_action": "Validate generated diff, then safe-advance to execution review",
            "endpoint": "/sandbox/patch-generations",
        },
        {
            "name": "Validation Harness",
            "ready": True,
            "count": len(patch_generations),
            "next_action": "Run git apply --check in an ephemeral workspace only",
            "endpoint": "/sandbox/patch-generations/<task_id>/validate-output",
        },
        {
            "name": "Ready-to-Run Gate",
            "ready": True,
            "count": len(ready_runs),
            "next_action": "Explicit approve + transient supplied-diff run",
            "endpoint": "/sandbox/executions/ready-to-run",
        },
        {
            "name": "Flow Graph",
            "ready": True,
            "count": int(graph_counts.get("nodes", 0) or 0),
            "next_action": "Show sandbox autonomy lineage",
            "endpoint": "/sandbox/flow-graph",
        },
        {
            "name": "Report Snapshot",
            "ready": True,
            "count": len(completed_runs),
            "next_action": "Generate report for demo evidence",
            "endpoint": "generate_report.py",
        },
    ]
    ready_count = sum(1 for stage in stages if stage.get("ready"))
    return {
        "ok": True,
        "schema": "cpos.competitive_demo_readiness.v1",
        "ready": ready_count == len(stages),
        "ready_count": ready_count,
        "stage_count": len(stages),
        "stages": stages,
        "counts": {
            "fast_resume_keys": len(tape["keys"]),
            "pending_tape_memory_reviews": len(tape_reviews),
            "external_agent_actions": len(external_agent_actions),
            "external_agent_results": external_agent_scoreboard.get("completed_results", 0),
            "human_escalations": len(human_escalations),
            "github_diff_reviews": len(github_diffs),
            "diff_drafts": len(drafts),
            "auto_fix_candidates": len(candidates),
            "patch_generation_reviews": len(patch_generations),
            "ready_to_run_reviews": len(ready_runs),
            "completed_runs": len(completed_runs),
            "flow_nodes": int(graph_counts.get("nodes", 0) or 0),
            "success_rate": scoreboard.get("success_rate", 0),
        },
        "competitive_posture": {
            "fast_resume_available": bool(tape["ok"]),
            "external_agent_adapter_available": True,
            "external_agent_result_scoreboard_available": True,
            "human_escalation_first_class": True,
            "patch_generation_review_gated": True,
            "validation_harness_available": True,
            "ready_to_run_gate_available": True,
            "flow_graph_available": True,
            "report_available": True,
            "approval_separated_from_execution": True,
        },
        "safety_flags": {
            "metadata_only": True,
            "raw_diff_stored": False,
            "raw_outputs_stored": False,
            "raw_request_stored": False,
            "checkpoint_contents_stored": False,
            "secret_values_stored": False,
            "live_repo_patch": False,
            "commit_created": False,
            "pushed": False,
            "pr_created": False,
            "execute_automatically": False,
            "destructive_actions_performed": False,
        },
        "next_demo_path": [
            "Fast Resume Cache",
            "External Agent Adapter",
            "Human Escalation Queue",
            "Patch Generation Review",
            "Validation Harness",
            "Safe Advance",
            "Ready-to-Run Gate",
            "Explicit Supplied-Diff Run",
            "Flow Graph",
            "Report Snapshot",
        ],
    }
