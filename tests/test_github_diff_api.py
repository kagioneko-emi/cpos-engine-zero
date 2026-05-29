from agents.main_agent import MainAgent
from cpos.task_tape import TaskTapeStore
import server


def configure(tmp_path):
    agent = MainAgent()
    agent.project_root = str(tmp_path)
    agent.task_tape = TaskTapeStore(tmp_path / "tapes" / "tasks.jsonl", tmp_path / "tapes" / "checkpoints.jsonl")
    server.agent = agent


def create_approved_pr(client):
    created = client.post("/github/pr-dry-runs", json={"repo": "kagioneko/cpos-engine-zero", "title": "Fix docs", "files": ["README.md"]})
    task_id = created.get_json()["task_id"]
    approved = client.post(f"/github/pr-dry-runs/{task_id}/approve", json={"confirm": True})
    assert approved.status_code == 200
    return task_id


def test_github_diff_review_api_flow(tmp_path):
    configure(tmp_path)
    client = server.app.test_client()
    source_task_id = create_approved_pr(client)

    created = client.post(f"/github/pr-dry-runs/{source_task_id}/create-diff-review", json={
        "diff_text": "+hello",
        "changed_files": ["README.md"],
        "validation_commands": ["pytest -q tests/test_report.py"],
    })
    assert created.status_code == 200
    payload = created.get_json()
    task_id = payload["task_id"]
    assert payload["plan"]["patch_applied"] is False

    listed = client.get("/github/diff-reviews")
    assert listed.status_code == 200
    assert listed.get_json()["count"] == 1

    missing = client.post(f"/github/diff-reviews/{task_id}/approve", json={})
    assert missing.status_code == 400
    assert missing.get_json()["error"] == "confirm_required"

    approved = client.post(f"/github/diff-reviews/{task_id}/approve", json={"confirm": True})
    assert approved.status_code == 200
    assert approved.get_json()["patch_applied"] is False
    assert client.get("/github/diff-reviews").get_json()["count"] == 0


def test_github_diff_review_api_requires_approved_plan(tmp_path):
    configure(tmp_path)
    client = server.app.test_client()
    res = client.post("/github/pr-dry-runs/task_missing/create-diff-review", json={"diff_text": "+x"})
    assert res.status_code == 400
    assert res.get_json()["error"] == "approved_pr_dry_run_required"
