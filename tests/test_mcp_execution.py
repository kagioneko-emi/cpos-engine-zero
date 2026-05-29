from cpos.mcp_execution import (
    approve_mcp_execution_review,
    pending_mcp_execution_reviews,
    reject_mcp_execution_review,
    request_mcp_execution,
)
from cpos.mcp_registry import MCPRegistry
from cpos.task_tape import TaskTapeStore


def definition(tmp_path, *, approval=True):
    return {
        "connector_id": "mcp://docs/search",
        "name": "Docs Search MCP",
        "transport": "https",
        "url": "https://mcp.example.test/docs",
        "allowed_tools": ["docs.search"],
        "blocked_tools": ["docs.write"],
        "requires_human_approval": approval,
        "env_secret_files": {"DOCS_TOKEN_FILE": str(tmp_path / "docs_token_file")},
    }


def setup_registry_and_tape(tmp_path, *, approval=True):
    registry = MCPRegistry(tmp_path / "connectors.json", tmp_path / "mcp_audit.jsonl", tmp_path / "mcp_reviews.jsonl")
    assert registry.register(definition(tmp_path, approval=approval), confirm=True)["ok"] is True
    tape = TaskTapeStore(tmp_path / "task_runs.jsonl", tmp_path / "task_checkpoints.jsonl")
    return registry, tape


def test_mcp_execution_dry_run_creates_review_and_stores_no_args_values(tmp_path):
    registry, tape = setup_registry_and_tape(tmp_path, approval=True)

    result = request_mcp_execution(
        registry,
        tape,
        connector_id="mcp://docs/search",
        tool_name="docs.search",
        arguments={"query": "hello", "limit": 5},
        actor="UnitTest",
        purpose="unit",
    )

    assert result["ok"] is True
    assert result["status"] == "pending_review"
    assert result["execute_automatically"] is False
    assert result["tool_executed"] is False
    assert result["arguments"]["args_values_stored"] is False
    reviews = pending_mcp_execution_reviews(tape)
    assert len(reviews) == 1
    payload = reviews[0]["payload"]
    assert payload["review_type"] == "mcp_tool_execution"
    assert payload["args_top_level_keys"] == ["limit", "query"]
    assert "hello" not in str(payload)


def test_mcp_execution_rejects_secret_like_arguments_and_blocked_tools(tmp_path):
    registry, tape = setup_registry_and_tape(tmp_path, approval=True)

    secret_arg = request_mcp_execution(
        registry,
        tape,
        connector_id="mcp://docs/search",
        tool_name="docs.search",
        arguments={"api_key": "nope"},
    )
    blocked_tool = request_mcp_execution(
        registry,
        tape,
        connector_id="mcp://docs/search",
        tool_name="docs.write",
        arguments={"title": "x"},
    )

    assert secret_arg["ok"] is False
    assert secret_arg["error"] == "secret_like_arguments_blocked"
    assert blocked_tool["ok"] is False
    assert blocked_tool["error"] == "tool_blocked"
    assert pending_mcp_execution_reviews(tape) == []


def test_mcp_execution_approve_and_reject_are_metadata_only(tmp_path):
    registry, tape = setup_registry_and_tape(tmp_path, approval=True)
    result = request_mcp_execution(registry, tape, connector_id="mcp://docs/search", tool_name="docs.search", arguments={"query": "x"})
    task_id = result["task_id"]

    missing_confirm = approve_mcp_execution_review(tape, task_id, confirm=False)
    assert missing_confirm["error"] == "confirm_required"

    approved = approve_mcp_execution_review(tape, task_id, approver="Reviewer", reason="ok", confirm=True)
    assert approved["ok"] is True
    assert approved["execute_automatically"] is False
    assert approved["tool_executed"] is False
    assert pending_mcp_execution_reviews(tape) == []

    second = request_mcp_execution(registry, tape, connector_id="mcp://docs/search", tool_name="docs.search", arguments={"query": "y"})
    rejected = reject_mcp_execution_review(tape, second["task_id"], reason="no")
    assert rejected["ok"] is True
    assert rejected["tool_executed"] is False


def test_mcp_execution_without_approval_still_dry_run_only(tmp_path):
    registry, tape = setup_registry_and_tape(tmp_path, approval=False)

    result = request_mcp_execution(registry, tape, connector_id="mcp://docs/search", tool_name="docs.search", arguments={"query": "x"})

    assert result["ok"] is True
    assert result["status"] == "dry_run_ready"
    assert result["execute_automatically"] is False
    assert result["tool_executed"] is False
    assert pending_mcp_execution_reviews(tape) == []


def test_mcp_real_execution_is_disabled(tmp_path):
    registry, tape = setup_registry_and_tape(tmp_path, approval=False)

    result = request_mcp_execution(registry, tape, connector_id="mcp://docs/search", tool_name="docs.search", dry_run=False)

    assert result["ok"] is False
    assert result["error"] == "real_execution_disabled"
    assert result["execute_automatically"] is False
