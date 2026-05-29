from agents.main_agent import MainAgent
from cpos.task_tape import TaskTapeStore
import server


class _FakeRunResult:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


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
        "validation_commands": ["pytest -q tests/test_report.py", "pytest -q tests/test_task_tape.py"],
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


def test_sandbox_patch_execution_api_flow(tmp_path, monkeypatch):
    configure(tmp_path)
    client = server.app.test_client()
    diff_task_id = create_approved_diff(client)

    created_plan = client.post(f"/github/diff-reviews/{diff_task_id}/create-sandbox-plan", json={})
    assert created_plan.status_code == 200
    patch_task_id = created_plan.get_json()["task_id"]
    approved_plan = client.post(f"/sandbox/patch-plans/{patch_task_id}/approve", json={"confirm": True})
    assert approved_plan.status_code == 200

    created_exec = client.post(f"/sandbox/patch-plans/{patch_task_id}/create-execution-review", json={})
    assert created_exec.status_code == 200
    exec_task_id = created_exec.get_json()["task_id"]
    approved_exec = client.post(f"/sandbox/executions/{exec_task_id}/approve", json={"confirm": True})
    assert approved_exec.status_code == 200

    src_root = tmp_path / "src"
    src_root.mkdir()
    (src_root / "README.md").write_text("old\n", encoding="utf-8")
    monkeypatch.setattr("cpos.sandbox_patch_runner._project_root", lambda: src_root)
    monkeypatch.setattr("cpos.sandbox_patch_runner._apply_patch", lambda workspace, diff_text: {"ok": True, "stage": "apply", "exit_code": 0, "stdout_sha256": "ok", "stderr_sha256": ""})
    monkeypatch.setattr("cpos.sandbox_patch_runner.subprocess.run", lambda *args, **kwargs: _FakeRunResult(returncode=0, stdout="ok\n", stderr=""))

    class FakeSandboxRunner:
        def __init__(self, *args, **kwargs):
            self.mode = kwargs.get("mode")
        def run_command(self, target_dir, command):
            return {"stdout": "validated\n", "stderr": "", "exit_code": 0, "sandbox": {"backend": "fake", "mode": self.mode, "isolated": True, "fallback_used": False}}

    monkeypatch.setattr("cpos.sandbox_patch_runner.SandboxRunner", FakeSandboxRunner)

    run_res = client.post(f"/sandbox/executions/{exec_task_id}/run", json={
        "diff_text": "diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n@@\n-old\n+new\n",
        "validation_commands": ["pytest -q tests/test_report.py", "pytest -q tests/test_task_tape.py"],
        "runner_mode": "strict",
    })
    assert run_res.status_code == 200
    payload = run_res.get_json()
    assert payload["ok"] is True
    assert payload["patch_applied"] is True
    assert payload["commands_executed"] is True
    assert payload["command_results"][0]["sandbox_backend"] == "fake"

    completed = client.get("/sandbox/executions/completed")
    assert completed.status_code == 200
    completed_payload = completed.get_json()
    assert completed_payload["count"] == 1
    assert completed_payload["results"][0]["event"] == "sandbox_patch_execution_completed"
    assert completed_payload["results"][0]["payload"]["command_results"][0]["stdout_sha256"]


def test_sandbox_patch_execution_run_requires_approved_plan(tmp_path):
    configure(tmp_path)
    client = server.app.test_client()
    res = client.post("/sandbox/executions/task_missing/run", json={"diff_text": "x", "validation_commands": []})
    assert res.status_code == 404
    assert res.get_json()["error"] == "approved_sandbox_patch_execution_required"
