from urllib.parse import quote

from agents.main_agent import MainAgent
import server


def configure_test_agent(tmp_path):
    test_agent = MainAgent()
    test_agent.project_root = str(tmp_path)
    server.agent = test_agent
    return test_agent


def valid_definition(tmp_path):
    return {
        "connector_id": "mcp://docs/search",
        "name": "Docs Search MCP",
        "transport": "https",
        "url": "https://mcp.example.test/docs",
        "allowed_tools": ["docs.search"],
        "blocked_tools": ["docs.write"],
        "sensitivity_level": "internal",
        "requires_human_approval": True,
        "env_secret_files": {"DOCS_TOKEN_FILE": str(tmp_path / "docs_token_file")},
    }


def test_mcp_api_check_register_list_and_tool_governance(tmp_path):
    configure_test_agent(tmp_path)
    client = server.app.test_client()
    definition = valid_definition(tmp_path)

    checked = client.post("/mcp/connectors/check", json=definition)
    assert checked.status_code == 200
    assert checked.get_json()["ok"] is True

    dry = client.post("/mcp/connectors", json=definition)
    assert dry.status_code == 400
    assert dry.get_json()["error"] == "confirm_required_after_security_check"

    registered = client.post("/mcp/connectors", json={**definition, "confirm": True})
    assert registered.status_code == 200
    assert registered.get_json()["ok"] is True

    listed = client.get("/mcp/connectors")
    assert listed.status_code == 200
    assert listed.get_json()["count"] == 1

    connector_id = quote("mcp://docs/search", safe="")
    evaluated = client.post(f"/mcp/connectors/{connector_id}/check-tool", json={"tool_name": "docs.search", "purpose": "unit"})
    assert evaluated.status_code == 200
    payload = evaluated.get_json()
    assert payload["decision"] == "approval_required"
    assert payload["requires_human_approval"] is True


def test_mcp_api_rejects_http_definition_before_registration(tmp_path):
    configure_test_agent(tmp_path)
    client = server.app.test_client()
    definition = valid_definition(tmp_path)
    definition["url"] = "http://mcp.example.test/docs"

    res = client.post("/mcp/connectors/check", json=definition)

    assert res.status_code == 400
    payload = res.get_json()
    assert payload["ok"] is False
    assert "https_required" in {finding["code"] for finding in payload["findings"]}


def test_mcp_api_scope_mapping(monkeypatch):
    with server.app.test_request_context("/mcp/connectors", method="GET"):
        assert server.required_scope_for_request() == "read:mcp"
    with server.app.test_request_context("/mcp/connectors", method="POST"):
        assert server.required_scope_for_request() == "write:mcp"


def test_mcp_review_api_submit_approve_and_reject(tmp_path):
    configure_test_agent(tmp_path)
    client = server.app.test_client()
    definition = valid_definition(tmp_path)

    submitted = client.post("/mcp/reviews", json=definition)
    assert submitted.status_code == 200
    review_id = submitted.get_json()["review"]["review_id"]

    pending = client.get("/mcp/reviews?status=pending")
    assert pending.status_code == 200
    assert pending.get_json()["count"] == 1

    approve_missing_confirm = client.post(f"/mcp/reviews/{review_id}/approve", json={"reason": "safe"})
    assert approve_missing_confirm.status_code == 400
    assert approve_missing_confirm.get_json()["error"] == "confirm_required"

    approved = client.post(f"/mcp/reviews/{review_id}/approve", json={"confirm": True, "reason": "safe"})
    assert approved.status_code == 200
    assert approved.get_json()["ok"] is True
    assert client.get("/mcp/connectors").get_json()["count"] == 1

    second = valid_definition(tmp_path)
    second["connector_id"] = "mcp://docs/other"
    second["name"] = "Other Docs MCP"
    second_submitted = client.post("/mcp/reviews", json=second)
    second_review_id = second_submitted.get_json()["review"]["review_id"]
    rejected = client.post(f"/mcp/reviews/{second_review_id}/reject", json={"reason": "duplicate"})
    assert rejected.status_code == 200
    assert rejected.get_json()["review"]["status"] == "rejected"


def test_mcp_review_api_does_not_store_failed_security_check(tmp_path):
    configure_test_agent(tmp_path)
    client = server.app.test_client()
    definition = valid_definition(tmp_path)
    definition["url"] = "http://mcp.example.test/docs"

    failed = client.post("/mcp/reviews", json=definition)
    assert failed.status_code == 400
    assert failed.get_json()["error"] == "security_check_failed_not_stored"
    assert client.get("/mcp/reviews").get_json()["count"] == 0
