from agents.main_agent import MainAgent
from cpos.task_tape import TaskTapeStore
import server


def configure(tmp_path):
    agent = MainAgent()
    agent.project_root = str(tmp_path)
    agent.task_tape = TaskTapeStore(tmp_path / "tapes" / "tasks.jsonl", tmp_path / "tapes" / "checkpoints.jsonl")
    server.agent = agent


def test_github_pr_dry_run_api_flow(tmp_path):
    configure(tmp_path)
    client = server.app.test_client()

    created = client.post("/github/pr-dry-runs", json={
        "repo": "kagioneko/cpos-engine-zero",
        "title": "Fix dashboard docs",
        "issue_number": 7,
        "summary": "raw summary not in payload",
        "files": ["README.md"],
    })
    assert created.status_code == 200
    payload = created.get_json()
    task_id = payload["task_id"]
    assert payload["plan"]["pr_created"] is False

    listed = client.get("/github/pr-dry-runs")
    assert listed.status_code == 200
    assert listed.get_json()["count"] == 1

    missing = client.post(f"/github/pr-dry-runs/{task_id}/approve", json={})
    assert missing.status_code == 400
    assert missing.get_json()["error"] == "confirm_required"

    approved = client.post(f"/github/pr-dry-runs/{task_id}/approve", json={"confirm": True, "reason": "ok"})
    assert approved.status_code == 200
    assert approved.get_json()["pr_created"] is False
    assert client.get("/github/pr-dry-runs").get_json()["count"] == 0


def test_github_pr_dry_run_api_rejects_real_creation(tmp_path):
    configure(tmp_path)
    client = server.app.test_client()
    res = client.post("/github/pr-dry-runs", json={"repo": "kagioneko/cpos-engine-zero", "title": "x", "dry_run": False})
    assert res.status_code == 400
    assert res.get_json()["error"] == "real_github_pr_creation_disabled"


def test_github_pr_scope_mapping():
    with server.app.test_request_context("/github/pr-dry-runs", method="GET"):
        assert server.required_scope_for_request() == "read:github"
    with server.app.test_request_context("/github/pr-dry-runs", method="POST"):
        assert server.required_scope_for_request() == "write:github"


def test_github_pr_dry_run_api_rejects_secret_metadata(tmp_path):
    configure(tmp_path)
    client = server.app.test_client()
    res = client.post("/github/pr-dry-runs", json={
        "repo": "kagioneko/cpos-engine-zero",
        "title": "x",
        "metadata": {"token": "do-not-store"},
    })
    assert res.status_code == 400
    assert res.get_json()["error"] == "secret_like_request_blocked"
