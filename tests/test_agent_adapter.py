import server
from agents.main_agent import MainAgent
from cpos.agent_adapter import intake_external_agent_action, pending_external_agent_actions, approve_external_agent_action
from cpos.human_escalation import pending_human_escalations
from cpos.task_tape import TaskTapeStore


def test_external_agent_adapter_stores_metadata_only_and_escalates_diff(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl", tmp_path / "checkpoints.jsonl")

    result = intake_external_agent_action(
        store,
        agent_name="codex-like-agent",
        event_type="proposed_diff",
        proposed_diff="diff --git a/app.py b/app.py\n+token = 'do-not-store'\n",
        commands=["pytest tests -q"],
        changed_files=["app.py"],
        metadata={"touches_secrets": True, "confidence": 0.9},
    )

    assert result["ok"] is True
    contract = result["contract"]
    assert contract["schema"] == "cpos.external_agent_action_contract.v1"
    assert contract["adapter_decision"] == "requires_review"
    assert contract["requires_human_approval"] is True
    assert contract["raw_request_stored"] is False
    assert contract["raw_diff_stored"] is False
    assert contract["raw_outputs_stored"] is False
    assert contract["secret_values_stored"] is False
    assert contract["input_digests"]["proposed_diff"]["size_bytes"] > 0
    assert "do-not-store" not in str(store.events())

    pending = pending_external_agent_actions(store)
    assert len(pending) == 1
    escalations = pending_human_escalations(store)
    assert len(escalations) == 1
    assert escalations[0]["owning_pipeline"] == "external_agent_adapter"
    assert escalations[0]["review_endpoint_hint"] == "/agent-adapter/actions"

    missing_confirm = approve_external_agent_action(store, result["task_id"])
    assert missing_confirm["ok"] is False
    assert missing_confirm["error"] == "confirm_required"

    approved = approve_external_agent_action(store, result["task_id"], confirm=True, reason="unit test")
    assert approved["ok"] is True
    assert pending_external_agent_actions(store) == []


def test_external_agent_adapter_api_roundtrip(tmp_path):
    agent = MainAgent()
    agent.project_root = str(tmp_path)
    agent.task_tape = TaskTapeStore(tmp_path / "tapes" / "tasks.jsonl", tmp_path / "tapes" / "checkpoints.jsonl")
    server.agent = agent
    client = server.app.test_client()

    created = client.post("/agent-adapter/intake", json={
        "agent_name": "hermes-test",
        "event_type": "command_request",
        "commands": ["python -m pytest tests -q"],
        "changed_files": ["cpos/agent_adapter.py"],
        "metadata": {"risk": "medium"},
    })
    assert created.status_code == 200
    payload = created.get_json()
    assert payload["ok"] is True
    assert payload["contract"]["execute_automatically"] is False
    assert payload["contract"]["raw_outputs_stored"] is False

    queue = client.get("/agent-adapter/actions")
    assert queue.status_code == 200
    q = queue.get_json()
    assert q["metadata_only"] is True
    assert q["count"] == 1
    task_id = q["reviews"][0]["task_id"]

    no_confirm = client.post(f"/agent-adapter/actions/{task_id}/approve", json={})
    assert no_confirm.status_code == 400
    assert no_confirm.get_json()["error"] == "confirm_required"

    approved = client.post(f"/agent-adapter/actions/{task_id}/approve", json={"confirm": True, "reason": "ok"})
    assert approved.status_code == 200
    assert approved.get_json()["execute_automatically"] is False
    assert client.get("/agent-adapter/actions").get_json()["count"] == 0
