import server
from cpos.github_pr_flow import create_github_pr_dry_run
from cpos.human_escalation import pending_human_escalations
from cpos.task_tape import TaskTapeStore


def test_human_escalation_queue_collects_github_pr_metadata(tmp_path):
    store = TaskTapeStore(tmp_path / 'tasks.jsonl')
    created = create_github_pr_dry_run(store, repo='kagioneko/cpos-engine-zero', title='Safe release prep')
    assert created['ok'] is True
    rows = pending_human_escalations(store)
    assert len(rows) == 1
    assert rows[0]['review_type'] == 'github_pr_dry_run'
    assert rows[0]['decision']['requires_human'] is True
    assert rows[0]['decision']['secret_values_stored'] is False
    assert rows[0]['decision']['raw_diff_stored'] is False
    assert rows[0]['approval_endpoint_hint'].endswith('/approve')
    assert rows[0]['owning_pipeline'] == 'github_pr_dry_run'
    assert rows[0]['pipeline_stage'] == 'pr_dry_run_review'
    assert rows[0]['pipeline_node_id'].startswith('github_pr_dry_run:')


def test_human_escalation_api_and_dashboard_are_wired():
    client = server.app.test_client()
    res = client.get('/human-escalations')
    assert res.status_code == 200
    data = res.get_json()
    assert data['ok'] is True
    assert data['metadata_only'] is True

    html_res = client.get('/dashboard')
    html = html_res.get_data(as_text=True)
    assert 'human-escalation-card' in html
    assert 'human-escalation-section' in html
    assert '/human-escalations' in html
    assert 'renderHumanEscalations' in html
    assert 'approveHumanEscalation' in html
    assert 'rejectHumanEscalation' in html
    assert 'Approve via Pipeline' in html
    assert 'Show in Sandbox Flow' in html
    assert 'focusSandboxFlowFromEscalation' in html
    assert 'owning_pipeline=${row.owning_pipeline' in html
    assert 'flow_graph_endpoint=${row.flow_graph_endpoint_hint' in html
    assert 'Assisted autonomy gate across review pipelines' in html
    assert 'metadata-only: raw_request_stored' in html

from agents.main_agent import MainAgent
from cpos.mcp_execution import request_mcp_execution
from cpos.mcp_registry import MCPRegistry


def _mcp_definition(tmp_path):
    return {
        "connector_id": "mcp://docs/search",
        "name": "Docs Search MCP",
        "transport": "https",
        "url": "https://mcp.example.test/docs",
        "allowed_tools": ["docs.search"],
        "blocked_tools": [],
        "requires_human_approval": True,
        "env_secret_files": {"DOCS_TOKEN_FILE": str(tmp_path / "docs_token_file")},
    }


def test_human_escalation_queue_collects_mcp_execution_metadata(tmp_path):
    registry = MCPRegistry(tmp_path / "connectors.json", tmp_path / "mcp_audit.jsonl", tmp_path / "mcp_reviews.jsonl")
    assert registry.register(_mcp_definition(tmp_path), confirm=True)["ok"] is True
    store = TaskTapeStore(tmp_path / "tasks.jsonl")

    created = request_mcp_execution(
        registry,
        store,
        connector_id="mcp://docs/search",
        tool_name="docs.search",
        arguments={"query": "hello"},
    )

    assert created["ok"] is True
    rows = pending_human_escalations(store)
    assert len(rows) == 1
    assert rows[0]["review_type"] == "mcp_tool_execution"
    assert rows[0]["decision"]["requires_human"] is True
    assert rows[0]["decision"]["raw_request_stored"] is False
    assert "hello" not in str(rows[0])


def test_human_escalation_queue_collects_sandbox_pipeline_metadata(tmp_path):
    agent = MainAgent()
    agent.project_root = str(tmp_path)
    agent.task_tape = TaskTapeStore(tmp_path / "tapes" / "tasks.jsonl", tmp_path / "tapes" / "checkpoints.jsonl")
    server.agent = agent
    client = server.app.test_client()

    pr = client.post("/github/pr-dry-runs", json={"repo": "kagioneko/cpos-engine-zero", "title": "Fix sandbox", "files": ["README.md"], "summary": "ctx"})
    pr_task_id = pr.get_json()["task_id"]
    assert client.post(f"/github/pr-dry-runs/{pr_task_id}/approve", json={"confirm": True}).status_code == 200
    diff = client.post(f"/github/pr-dry-runs/{pr_task_id}/create-diff-review", json={"diff_text": "+hello\n", "changed_files": ["README.md"], "validation_commands": ["pytest -q tests/test_report.py"]})
    diff_task_id = diff.get_json()["task_id"]
    assert client.post(f"/github/diff-reviews/{diff_task_id}/approve", json={"confirm": True}).status_code == 200

    plan = client.post(f"/github/diff-reviews/{diff_task_id}/create-sandbox-plan", json={})
    assert plan.status_code == 200
    patch_task_id = plan.get_json()["task_id"]
    plan_rows = pending_human_escalations(agent.task_tape)
    assert "sandbox_patch_plan" in {row["review_type"] for row in plan_rows}
    assert client.post(f"/sandbox/patch-plans/{patch_task_id}/approve", json={"confirm": True}).status_code == 200
    execution = client.post(f"/sandbox/patch-plans/{patch_task_id}/create-execution-review", json={})
    assert execution.status_code == 200

    rows = pending_human_escalations(agent.task_tape)
    review_types = {row["review_type"] for row in rows}
    assert "sandbox_patch_execution" in review_types
    execution_row = next(row for row in rows if row["review_type"] == "sandbox_patch_execution")
    assert execution_row["owning_pipeline"] == "sandbox_patch_pipeline"
    assert execution_row["pipeline_stage"] == "sandbox_execution_gate"
    assert execution_row["flow_graph_endpoint_hint"].startswith("/sandbox/flow-graph?source_execution_task_id=")
    assert execution_row["sandbox_flow_source_execution_task_id"] == execution.get_json()["task_id"]
    assert all(row["decision"]["secret_values_stored"] is False for row in rows)
    assert "+hello" not in str(rows)
