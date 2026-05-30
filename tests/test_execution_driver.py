from cpos.execution_driver import advance_sandbox_patch_pipeline
from cpos.sandbox_patch_plan import pending_sandbox_patch_plans
from cpos.sandbox_patch_runner import pending_sandbox_patch_executions
from cpos.task_tape import TaskTapeStore
from tests.test_sandbox_patch_plan import approved_diff_task, _FakeRunResult


def test_execution_driver_creates_next_review_only_by_default(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    diff_task_id = approved_diff_task(store)

    result = advance_sandbox_patch_pipeline(store, diff_task_id=diff_task_id)

    assert result["ok"] is True
    assert result["status"] == "pending_sandbox_patch_plan_review"
    assert result["metadata_only"] is True
    assert result["raw_diff_stored"] is False
    assert result["raw_outputs_stored"] is False
    assert result["commit_created"] is False
    assert result["pushed"] is False
    assert result["pr_created"] is False
    assert len(pending_sandbox_patch_plans(store)) == 1
    assert pending_sandbox_patch_executions(store) == []


def test_execution_driver_advances_to_approved_execution_without_run(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    diff_task_id = approved_diff_task(store)

    result = advance_sandbox_patch_pipeline(
        store,
        diff_task_id=diff_task_id,
        approve_plan=True,
        approve_execution=True,
    )

    assert result["ok"] is True
    assert result["status"] == "approved_sandbox_execution_ready"
    assert result["patch_task_id"]
    assert result["execution_task_id"]
    assert result["step_count"] == 4
    assert result["execute_automatically"] is False


def test_execution_driver_run_uses_transient_inputs_and_metadata_only(tmp_path, monkeypatch):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    diff_text = "diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n@@\n-old\n+new\n"
    commands = ["pytest -q tests/test_report.py", "pytest -q tests/test_task_tape.py"]
    diff_task_id = approved_diff_task(store)

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
            return {
                "stdout": "validated\n",
                "stderr": "",
                "exit_code": 0,
                "sandbox": {"backend": "fake", "mode": self.mode, "isolated": True, "fallback_used": False},
            }

    monkeypatch.setattr("cpos.sandbox_patch_runner.SandboxRunner", FakeSandboxRunner)

    result = advance_sandbox_patch_pipeline(
        store,
        diff_task_id=diff_task_id,
        diff_text=diff_text,
        validation_commands=commands,
        approve_plan=True,
        approve_execution=True,
        run=True,
        runner_mode="strict",
    )

    assert result["ok"] is True
    assert result["status"] == "completed_success"
    assert result["run_status"] == "completed_success"
    assert result["raw_diff_stored"] is False
    assert result["raw_outputs_stored"] is False
    assert result["workspace_type"] == "ephemeral_copy"
    assert result["commit_created"] is False
    assert result["pushed"] is False
    assert result["pr_created"] is False
    assert "old" not in str(store.events())
    assert "validated" not in str(store.events())
