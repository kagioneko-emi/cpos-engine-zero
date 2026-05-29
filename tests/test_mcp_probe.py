from cpos.mcp_probe import request_mcp_capability_probe, pending_mcp_probe_reviews, approve_mcp_probe_review, reject_mcp_probe_review
from cpos.mcp_registry import MCPRegistry
from cpos.task_tape import TaskTapeStore


def setup(tmp_path, *, transport="https"):
    registry = MCPRegistry(tmp_path / "connectors.json", tmp_path / "audit.jsonl", tmp_path / "reviews.jsonl")
    data = {
        "connector_id": f"mcp://docs/{transport}",
        "name": "Docs MCP",
        "transport": transport,
        "allowed_tools": ["docs.search"],
        "requires_human_approval": True,
        "env_secret_files": {"DOCS_TOKEN_FILE": str(tmp_path / "token_file")},
    }
    if transport == "stdio":
        data["command"] = ["python", "-m", "safe_mcp"]
    else:
        data["url"] = "https://mcp.example.test/docs"
    assert registry.register(data, confirm=True)["ok"] is True
    tape = TaskTapeStore(tmp_path / "tasks.jsonl", tmp_path / "checkpoints.jsonl")
    return registry, tape, data["connector_id"]


def test_mcp_capability_probe_creates_metadata_only_review(tmp_path):
    registry, tape, connector_id = setup(tmp_path)
    result = request_mcp_capability_probe(registry, tape, connector_id=connector_id)
    assert result["ok"] is True
    assert result["server_started"] is False
    assert result["network_requested"] is False
    assert result["tool_called"] is False
    assert result["secret_files_read"] is False
    review = pending_mcp_probe_reviews(tape)[0]
    payload = review["payload"]
    assert payload["review_type"] == "mcp_capability_probe"
    assert payload["probe_mode"] == "dry_run_metadata_only"
    assert payload["url_host_only"] == "mcp.example.test"
    assert "list_tools request only after approval" in payload["probe_plan"]


def test_mcp_stdio_probe_stores_command_shape_not_full_execution(tmp_path):
    registry, tape, connector_id = setup(tmp_path, transport="stdio")
    result = request_mcp_capability_probe(registry, tape, connector_id=connector_id)
    assert result["ok"] is True
    payload = pending_mcp_probe_reviews(tape)[0]["payload"]
    assert payload["transport"] == "stdio"
    assert payload["command_shape"]["argv0"] == "python"
    assert payload["command_shape"]["argv_values_stored"] is False
    assert payload["server_started"] is False


def test_mcp_probe_approve_reject_are_dry_run_only(tmp_path):
    registry, tape, connector_id = setup(tmp_path)
    first = request_mcp_capability_probe(registry, tape, connector_id=connector_id)
    missing = approve_mcp_probe_review(tape, first["task_id"], confirm=False)
    assert missing["error"] == "confirm_required"
    approved = approve_mcp_probe_review(tape, first["task_id"], confirm=True)
    assert approved["ok"] is True
    assert approved["server_started"] is False
    assert pending_mcp_probe_reviews(tape) == []

    second = request_mcp_capability_probe(registry, tape, connector_id=connector_id)
    rejected = reject_mcp_probe_review(tape, second["task_id"], reason="no")
    assert rejected["ok"] is True
    assert rejected["tool_called"] is False


def test_mcp_probe_rejects_real_probe(tmp_path):
    registry, tape, connector_id = setup(tmp_path)
    result = request_mcp_capability_probe(registry, tape, connector_id=connector_id, dry_run=False)
    assert result["ok"] is False
    assert result["error"] == "real_probe_disabled"
