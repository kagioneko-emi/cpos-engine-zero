from agents.main_agent import MainAgent
from cpos.mcp_registry import MCPRegistry
from cpos.task_tape import TaskTapeStore
import server


def configure(tmp_path):
    agent = MainAgent()
    agent.project_root = str(tmp_path)
    agent.task_tape = TaskTapeStore(tmp_path / "tapes" / "tasks.jsonl", tmp_path / "tapes" / "checkpoints.jsonl")
    server.agent = agent
    registry = MCPRegistry(tmp_path / "cpos" / "mcp_connectors.json", tmp_path / "cpos" / "mcp_audit.jsonl", tmp_path / "cpos" / "mcp_reviews.jsonl")
    assert registry.register({
        "connector_id": "mcp://docs/search",
        "name": "Docs MCP",
        "transport": "https",
        "url": "https://mcp.example.test/docs",
        "allowed_tools": ["docs.search"],
        "requires_human_approval": True,
        "env_secret_files": {"DOCS_TOKEN_FILE": str(tmp_path / "token_file")},
    }, confirm=True)["ok"] is True


def test_mcp_probe_api_flow(tmp_path):
    configure(tmp_path)
    client = server.app.test_client()
    res = client.post("/mcp/probes/dry-run", json={"connector_id": "mcp://docs/search"})
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["server_started"] is False
    task_id = payload["task_id"]
    assert client.get("/mcp/probes").get_json()["count"] == 1
    missing = client.post(f"/mcp/probes/{task_id}/approve", json={})
    assert missing.status_code == 400
    approved = client.post(f"/mcp/probes/{task_id}/approve", json={"confirm": True})
    assert approved.status_code == 200
    assert approved.get_json()["network_requested"] is False


def test_mcp_probe_api_rejects_real_probe(tmp_path):
    configure(tmp_path)
    client = server.app.test_client()
    res = client.post("/mcp/probes/dry-run", json={"connector_id": "mcp://docs/search", "dry_run": False})
    assert res.status_code == 400
    assert res.get_json()["error"] == "real_probe_disabled"


def test_mcp_probe_api_scope_mapping():
    with server.app.test_request_context("/mcp/probes", method="GET"):
        assert server.required_scope_for_request() == "read:mcp"
    with server.app.test_request_context("/mcp/probes/dry-run", method="POST"):
        assert server.required_scope_for_request() == "write:mcp"
