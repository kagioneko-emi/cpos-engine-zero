import json

import server
from cpos.demo_readiness import build_competitive_demo_readiness
from cpos.task_tape import TaskTapeStore


class _FakeMCPRegistry:
    def reviews(self, status=None):
        return [
            {
                "review_id": "mcp_review_demo",
                "connector_id": "mcp://tape-memory/cpos-resume",
                "status": status or "pending",
            }
        ]


def test_competitive_demo_readiness_uses_tape_cache_and_safety_flags(tmp_path):
    tape_root = tmp_path / "tape-memory"
    tape_root.mkdir()
    (tape_root / "tapes.json").write_text(json.dumps({
        "cpos_resume_latest": "s0c9",
        "cpos_safety_invariants": "s1c9",
        "cpos_next_action": "m2r8",
        "cpos_mcp_tape_memory": "m3r8",
    }), encoding="utf-8")
    store = TaskTapeStore(tmp_path / "tasks.jsonl", tmp_path / "checkpoints.jsonl")

    result = build_competitive_demo_readiness(store, mcp_registry=_FakeMCPRegistry(), tape_store_path=tape_root)

    assert result["ok"] is True
    assert result["schema"] == "cpos.competitive_demo_readiness.v1"
    assert result["ready"] is True
    assert result["counts"]["fast_resume_keys"] == 4
    assert result["counts"]["pending_tape_memory_reviews"] == 1
    assert result["competitive_posture"]["external_agent_adapter_available"] is True
    assert result["competitive_posture"]["external_agent_result_scoreboard_available"] is True
    assert result["competitive_posture"]["human_escalation_first_class"] is True
    assert result["competitive_posture"]["approval_separated_from_execution"] is True
    assert result["safety_flags"]["metadata_only"] is True
    assert result["safety_flags"]["raw_diff_stored"] is False
    assert result["safety_flags"]["raw_outputs_stored"] is False
    assert result["safety_flags"]["execute_automatically"] is False
    assert "External Agent Adapter" in result["next_demo_path"]
    assert "External Agent Result Scoreboard" in result["next_demo_path"]
    assert "Ready-to-Run Gate" in result["next_demo_path"]


def test_demo_readiness_api_is_metadata_only(tmp_path):
    from agents.main_agent import MainAgent

    agent = MainAgent()
    agent.project_root = str(tmp_path)
    agent.task_tape = TaskTapeStore(tmp_path / "tapes" / "tasks.jsonl", tmp_path / "tapes" / "checkpoints.jsonl")
    server.agent = agent
    client = server.app.test_client()

    res = client.get("/demo/readiness")

    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True
    assert data["schema"] == "cpos.competitive_demo_readiness.v1"
    assert data["safety_flags"]["metadata_only"] is True
    assert data["safety_flags"]["secret_values_stored"] is False
    assert data["safety_flags"]["raw_diff_stored"] is False
    assert data["safety_flags"]["raw_outputs_stored"] is False


def test_competitive_demo_fixture_creates_metadata_only_readiness_chain(tmp_path):
    from cpos.competitive_demo_fixture import create_competitive_demo_fixture

    tape_root = tmp_path / "tape-memory"
    tape_root.mkdir()
    (tape_root / "tapes.json").write_text(json.dumps({
        "cpos_resume_latest": "s0c9",
        "cpos_safety_invariants": "s1c9",
        "cpos_next_action": "m2r8",
        "cpos_mcp_tape_memory": "m3r8",
    }), encoding="utf-8")
    store = TaskTapeStore(tmp_path / "tasks.jsonl", tmp_path / "checkpoints.jsonl")

    missing = create_competitive_demo_fixture(store, confirm=False)
    assert missing["ok"] is False
    assert missing["error"] == "confirm_required"

    result = create_competitive_demo_fixture(store, confirm=True, mcp_registry=_FakeMCPRegistry())

    assert result["ok"] is True
    assert result["metadata_only"] is True
    assert result["raw_diff_stored"] is False
    assert result["raw_outputs_stored"] is False
    assert result["execute_automatically"] is False
    assert result["commit_created"] is False
    assert result["pushed"] is False
    assert result["pr_created"] is False
    assert result["step_count"] >= 12
    step_names = {step["name"] for step in result["steps"]}
    assert "create_external_agent_adapter_review" in step_names
    assert "record_external_agent_execution_result" in step_names
    assert "create_ready_to_run_execution_review" in step_names
    assert "create_patch_generation_review" in step_names
    assert "create_diff_review_draft" in step_names
    readiness = build_competitive_demo_readiness(store, mcp_registry=_FakeMCPRegistry(), tape_store_path=tape_root)
    assert readiness["counts"]["external_agent_actions"] >= 1
    assert readiness["counts"]["external_agent_results"] >= 1
    assert readiness["counts"]["ready_to_run_reviews"] >= 1
    assert readiness["counts"]["patch_generation_reviews"] >= 1
    assert readiness["counts"]["diff_drafts"] >= 1
    assert readiness["counts"]["flow_nodes"] >= 1
    assert "demo readiness placeholder" not in str(result)


def test_demo_fixture_api_creates_readiness_chain(tmp_path):
    from agents.main_agent import MainAgent

    agent = MainAgent()
    agent.project_root = str(tmp_path)
    agent.task_tape = TaskTapeStore(tmp_path / "tapes" / "tasks.jsonl", tmp_path / "tapes" / "checkpoints.jsonl")
    server.agent = agent
    client = server.app.test_client()

    missing = client.post("/demo/fixture", json={})
    assert missing.status_code == 400
    assert missing.get_json()["error"] == "confirm_required"

    created = client.post("/demo/fixture", json={"confirm": True, "reason": "unit_demo_fixture"})
    assert created.status_code == 200
    payload = created.get_json()
    assert payload["ok"] is True
    assert payload["metadata_only"] is True
    assert payload["raw_diff_stored"] is False
    assert payload["raw_outputs_stored"] is False
    assert payload["readiness"]["counts"]["external_agent_actions"] >= 1
    assert payload["readiness"]["counts"]["external_agent_results"] >= 1
    assert payload["readiness"]["counts"]["ready_to_run_reviews"] >= 1
    assert payload["readiness"]["counts"]["patch_generation_reviews"] >= 1
    assert payload["readiness"]["safety_flags"]["execute_automatically"] is False

    readiness = client.get("/demo/readiness").get_json()
    assert readiness["counts"]["ready_to_run_reviews"] >= 1
    assert readiness["counts"]["patch_generation_reviews"] >= 1
    assert readiness["counts"]["flow_nodes"] >= 1
