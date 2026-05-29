from agents.main_agent import MainAgent
from cpos.task_tape import TaskTapeStore
import server


def configure(tmp_path):
    agent = MainAgent()
    agent.project_root = str(tmp_path)
    agent.task_tape = TaskTapeStore(tmp_path / "tapes" / "tasks.jsonl", tmp_path / "tapes" / "checkpoints.jsonl")
    server.agent = agent


def create_approved_diff(client):
    pr = client.post("/github/pr-dry-runs", json={"repo": "kagioneko/cpos-engine-zero", "title": "Fix sandbox", "files": ["README.md"], "summary": "ctx"})
    pr_task_id = pr.get_json()["task_id"]
    approved_pr = client.post(f"/github/pr-dry-runs/{pr_task_id}/approve", json={"confirm": True})
    assert approved_pr.status_code == 200

    diff = client.post(f"/github/pr-dry-runs/{pr_task_id}/create-diff-review", json={
        "diff_text": "+hello\n-old\n",
        "changed_files": ["README.md"],
        "validation_commands": ["pytest -q tests/test_report.py"],
    })
    diff_task_id = diff.get_json()["task_id"]
    approved_diff = client.post(f"/github/diff-reviews/{diff_task_id}/approve", json={"confirm": True})
    assert approved_diff.status_code == 200
    return diff_task_id


def test_sandbox_patch_plan_api_flow(tmp_path):
    configure(tmp_path)
    client = server.app.test_client()
    diff_task_id = create_approved_diff(client)

    created = client.post(f"/github/diff-reviews/{diff_task_id}/create-sandbox-plan", json={})
    assert created.status_code == 200
    payload = created.get_json()
    task_id = payload["task_id"]
    assert payload["plan"]["patch_applied"] is False

    listed = client.get("/sandbox/patch-plans")
    assert listed.status_code == 200
    assert listed.get_json()["count"] == 1

    missing = client.post(f"/sandbox/patch-plans/{task_id}/approve", json={})
    assert missing.status_code == 400
    assert missing.get_json()["error"] == "confirm_required"

    approved = client.post(f"/sandbox/patch-plans/{task_id}/approve", json={"confirm": True})
    assert approved.status_code == 200
    assert approved.get_json()["patch_applied"] is False
    assert client.get("/sandbox/patch-plans").get_json()["count"] == 0


def test_sandbox_patch_plan_api_requires_approved_diff(tmp_path):
    configure(tmp_path)
    client = server.app.test_client()
    res = client.post("/github/diff-reviews/task_missing/create-sandbox-plan", json={})
    assert res.status_code == 400
    assert res.get_json()["error"] == "approved_diff_review_required"


def test_sandbox_scope_mapping():
    with server.app.test_request_context("/sandbox/patch-plans", method="GET"):
        assert server.required_scope_for_request() == "read:sandbox"
    with server.app.test_request_context("/sandbox/patch-plans", method="POST"):
        assert server.required_scope_for_request() == "write:sandbox"
