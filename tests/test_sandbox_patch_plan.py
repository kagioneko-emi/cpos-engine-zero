from cpos.github_diff_review import approve_github_diff_review, create_github_diff_review
from cpos.github_pr_flow import approve_github_pr_dry_run, create_github_pr_dry_run
from cpos.sandbox_patch_plan import (
    approve_sandbox_patch_plan,
    create_sandbox_patch_plan,
    pending_sandbox_patch_plans,
    reject_sandbox_patch_plan,
)
from cpos.sandbox_patch_runner import (
    approve_sandbox_patch_execution,
    create_sandbox_patch_execution,
    execute_sandbox_patch_run,
    pending_sandbox_patch_executions,
    reject_sandbox_patch_execution,
)
from cpos.task_tape import TaskTapeStore


class _FakeRunResult:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def approved_diff_task(store):
    pr = create_github_pr_dry_run(
        store,
        repo="kagioneko/cpos-engine-zero",
        title="Fix sandbox flow",
        files=["README.md"],
        summary="issue context",
    )
    approve_github_pr_dry_run(store, pr["task_id"], confirm=True)
    diff = create_github_diff_review(
        store,
        source_task_id=pr["task_id"],
        diff_text="diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n@@\n-old\n+new\n",
        changed_files=["README.md"],
        validation_commands=["pytest -q tests/test_report.py", "pytest -q tests/test_task_tape.py"],
    )
    approve_github_diff_review(store, diff["task_id"], confirm=True)
    return diff["task_id"]


def test_sandbox_patch_plan_requires_approved_diff_review(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    result = create_sandbox_patch_plan(store, diff_task_id="missing")
    assert result["ok"] is False
    assert result["error"] == "approved_diff_review_required"


def test_sandbox_patch_plan_is_metadata_only(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    diff_task_id = approved_diff_task(store)

    result = create_sandbox_patch_plan(store, diff_task_id=diff_task_id)
    assert result["ok"] is True
    plan = result["plan"]
    assert plan["validation_values_stored"] is False
    assert plan["patch_applied"] is False
    assert plan["commands_executed"] is False
    assert plan["tests_run"] is False
    assert plan["commit_created"] is False
    assert plan["pushed"] is False
    assert plan["pr_created"] is False
    assert plan["network_disabled_required"] is True
    assert plan["project_write_allowed"] is False
    assert plan["workspace_type"] == "ephemeral_copy"
    assert len(plan["validation_command_hashes"]) == 2
    assert len(pending_sandbox_patch_plans(store)) == 1


def test_sandbox_patch_plan_approve_and_reject_are_metadata_only(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    diff_task_id = approved_diff_task(store)
    result = create_sandbox_patch_plan(store, diff_task_id=diff_task_id)
    task_id = result["task_id"]

    missing = approve_sandbox_patch_plan(store, task_id, confirm=False)
    assert missing["error"] == "confirm_required"

    approved = approve_sandbox_patch_plan(store, task_id, confirm=True)
    assert approved["ok"] is True
    assert approved["patch_applied"] is False
    assert approved["commands_executed"] is False
    assert approved["pr_created"] is False
    assert pending_sandbox_patch_plans(store) == []

    second = create_sandbox_patch_plan(store, diff_task_id=diff_task_id)
    rejected = reject_sandbox_patch_plan(store, second["task_id"], reason="no")
    assert rejected["ok"] is True
    assert rejected["patch_applied"] is False
    assert rejected["commands_executed"] is False


def test_sandbox_patch_plan_real_execution_disabled(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    result = create_sandbox_patch_plan(store, diff_task_id="missing", dry_run=False)
    assert result["ok"] is False
    assert result["error"] == "real_sandbox_execution_disabled"


def test_sandbox_patch_execution_requires_approved_patch_plan(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    result = create_sandbox_patch_execution(store, patch_task_id="missing")
    assert result["ok"] is False
    assert result["error"] == "approved_sandbox_patch_plan_required"


def test_sandbox_patch_execution_is_metadata_only(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    diff_task_id = approved_diff_task(store)
    patch_plan = create_sandbox_patch_plan(store, diff_task_id=diff_task_id)
    approve_sandbox_patch_plan(store, patch_plan["task_id"], confirm=True)

    result = create_sandbox_patch_execution(store, patch_task_id=patch_plan["task_id"])
    assert result["ok"] is True
    plan = result["plan"]
    assert plan["workspace_copied"] is False
    assert plan["patch_applied"] is False
    assert plan["commands_executed"] is False
    assert plan["tests_run"] is False
    assert plan["command_outputs_stored"] is False
    assert plan["commit_created"] is False
    assert plan["pushed"] is False
    assert plan["pr_created"] is False
    assert plan["runner_mode"] == "strict"
    assert len(plan["validation_command_hashes"]) == 2


def test_sandbox_patch_execution_approve_and_reject_are_metadata_only(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    diff_task_id = approved_diff_task(store)
    patch_plan = create_sandbox_patch_plan(store, diff_task_id=diff_task_id)
    approve_sandbox_patch_plan(store, patch_plan["task_id"], confirm=True)
    execution = create_sandbox_patch_execution(store, patch_task_id=patch_plan["task_id"])
    task_id = execution["task_id"]

    missing = approve_sandbox_patch_execution(store, task_id, confirm=False)
    assert missing["error"] == "confirm_required"

    approved = approve_sandbox_patch_execution(store, task_id, confirm=True)
    assert approved["ok"] is True
    assert approved["workspace_copied"] is False
    assert approved["patch_applied"] is False
    assert approved["commands_executed"] is False

    second_patch_plan = create_sandbox_patch_plan(store, diff_task_id=diff_task_id)
    approve_sandbox_patch_plan(store, second_patch_plan["task_id"], confirm=True)
    second = create_sandbox_patch_execution(store, patch_task_id=second_patch_plan["task_id"])
    rejected = reject_sandbox_patch_execution(store, second["task_id"], reason="no")
    assert rejected["ok"] is True
    assert rejected["workspace_copied"] is False
    assert rejected["patch_applied"] is False


def test_sandbox_patch_execution_real_execution_disabled(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    result = create_sandbox_patch_execution(store, patch_task_id="missing", dry_run=False)
    assert result["ok"] is False
    assert result["error"] == "real_sandbox_patch_execution_disabled"


def test_sandbox_patch_execution_run_applies_patch_in_ephemeral_workspace(tmp_path, monkeypatch):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    diff_task_id = approved_diff_task(store)
    patch_plan = create_sandbox_patch_plan(store, diff_task_id=diff_task_id)
    approve_sandbox_patch_plan(store, patch_plan["task_id"], confirm=True)
    execution = create_sandbox_patch_execution(store, patch_task_id=patch_plan["task_id"])
    approve_sandbox_patch_execution(store, execution["task_id"], confirm=True)

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

    result = execute_sandbox_patch_run(
        store,
        task_id=execution["task_id"],
        diff_text="diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n@@\n-old\n+new\n",
        validation_commands=["pytest -q tests/test_report.py", "pytest -q tests/test_task_tape.py"],
        runner_mode="strict",
    )

    assert result["ok"] is True
    assert result["patch_applied"] is True
    assert result["commands_executed"] is True
    assert result["tests_run"] is True
    assert len(result["command_results"]) == 2
    assert result["command_results"][0]["exit_code"] == 0
    assert result["command_results"][0]["sandbox_backend"] == "fake"


def test_sandbox_patch_execution_run_rejects_validation_mismatch(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    diff_task_id = approved_diff_task(store)
    patch_plan = create_sandbox_patch_plan(store, diff_task_id=diff_task_id)
    approve_sandbox_patch_plan(store, patch_plan["task_id"], confirm=True)
    execution = create_sandbox_patch_execution(store, patch_task_id=patch_plan["task_id"])
    approve_sandbox_patch_execution(store, execution["task_id"], confirm=True)

    result = execute_sandbox_patch_run(
        store,
        task_id=execution["task_id"],
        diff_text="diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n@@\n-old\n+new\n",
        validation_commands=["pytest -q tests/test_task_tape.py"],
        runner_mode="strict",
    )

    assert result["ok"] is False
    assert result["error"] == "validation_commands_mismatch"
