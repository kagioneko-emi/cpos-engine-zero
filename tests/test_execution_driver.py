import json
from cpos.execution_driver import advance_sandbox_patch_pipeline, build_execution_scoreboard
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


def _failed_execution(store):
    store.append_event(
        task_id="task_failed_exec",
        event="sandbox_patch_execution_completed",
        target="sandbox://execution/task_failed_exec",
        status="completed_with_failures",
        payload={
            "review_type": "sandbox_patch_execution",
            "failure_kind": "validation_command",
            "patch_applied": True,
            "commands_executed": True,
            "tests_run": True,
            "workspace_copied": True,
            "validation_command_hashes": [{"sha256": "abc", "size_bytes": 12}],
            "validation_command_count": 1,
            "command_results": [{
                "command_sha256": "abc",
                "exit_code": 1,
                "stdout_sha256": "out",
                "stderr_sha256": "err",
                "stdout_size_bytes": 10,
                "stderr_size_bytes": 5,
                "sandbox_backend": "fake",
                "sandbox_mode": "strict",
                "isolated": True,
                "fallback_used": False,
            }],
            "success": False,
            "execute_automatically": False,
        },
    )
    return "task_failed_exec"


def test_execution_driver_replan_failure_creates_retry_review_only_by_default(tmp_path):
    from cpos.execution_driver import advance_failed_sandbox_replan
    from cpos.sandbox_patch_runner import pending_sandbox_patch_execution_retries

    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    source_task_id = _failed_execution(store)

    result = advance_failed_sandbox_replan(store, source_execution_task_id=source_task_id)

    assert result["ok"] is True
    assert result["status"] == "pending_sandbox_retry_review"
    assert result["metadata_only"] is True
    assert result["raw_outputs_stored"] is False
    assert result["workspace_reused"] is False
    assert result["commit_created"] is False
    assert len(pending_sandbox_patch_execution_retries(store)) == 1


def test_execution_driver_replan_failure_advances_to_diff_intake(tmp_path):
    from cpos.execution_driver import advance_failed_sandbox_replan
    from cpos.sandbox_patch_runner import sandbox_patch_replan_templates, sandbox_replan_diff_intakes

    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    source_task_id = _failed_execution(store)

    result = advance_failed_sandbox_replan(
        store,
        source_execution_task_id=source_task_id,
        approve_retry=True,
        create_replan_template=True,
        create_diff_intake=True,
    )

    assert result["ok"] is True
    assert result["status"] == "sandbox_diff_intake_created"
    assert result["retry_task_id"]
    assert result["replan_task_id"]
    assert result["diff_intake_task_id"]
    assert result["step_count"] == 4
    assert result["raw_outputs_stored"] is False
    assert result["raw_diff_stored"] is False
    assert result["workspace_reused"] is False
    assert result["execute_automatically"] is False
    assert len(sandbox_patch_replan_templates(store)) == 1
    assert len(sandbox_replan_diff_intakes(store)) == 1


def test_execution_driver_scoreboard_counts_and_failure_kinds(tmp_path, monkeypatch):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    diff_task_id = approved_diff_task(store)

    # Mock the sandbox execution to avoid real git apply/docker issues in this unit test
    monkeypatch.setattr("cpos.sandbox_patch_runner._apply_patch", lambda workspace, diff_text: {"ok": True, "stage": "apply", "exit_code": 0, "stdout_sha256": "ok", "stderr_sha256": ""})
    class FakeSandboxRunner:
        def __init__(self, *args, **kwargs): pass
        def run_command(self, target_dir, command):
            return {"stdout": "ok", "stderr": "", "exit_code": 0, "sandbox": {"backend": "fake", "mode": "strict", "isolated": True}}
    monkeypatch.setattr("cpos.sandbox_patch_runner.SandboxRunner", FakeSandboxRunner)

    result = advance_sandbox_patch_pipeline(
        store,
        diff_task_id=diff_task_id,
        diff_text="diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n@@\n-old\n+new\n",
        validation_commands=["pytest -q tests/test_report.py", "pytest -q tests/test_task_tape.py"],
        approve_plan=True,
        approve_execution=True,
        run=True,
        runner_mode="strict",
    )
    assert result["ok"] is True

    scoreboard = build_execution_scoreboard(store)
    assert scoreboard["ok"] is True
    assert scoreboard["completed_runs"] == 1
    assert scoreboard["success_runs"] == 1
    assert scoreboard["failure_runs"] == 0
    assert scoreboard["success_rate"] == 100.0
    assert scoreboard["pending_retry_reviews"] == 0
    assert scoreboard["replan_templates"] == 0
    assert scoreboard["diff_intakes"] == 0

