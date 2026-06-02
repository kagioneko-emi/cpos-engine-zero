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


def create_approved_diff(client, validation_commands=None):
    commands = validation_commands or ["pytest -q tests/test_report.py", "pytest -q tests/test_task_tape.py"]
    pr = client.post("/github/pr-dry-runs", json={"repo": "kagioneko/cpos-engine-zero", "title": "Fix sandbox", "files": ["README.md"], "summary": "ctx"})
    pr_task_id = pr.get_json()["task_id"]
    approved_pr = client.post(f"/github/pr-dry-runs/{pr_task_id}/approve", json={"confirm": True})
    assert approved_pr.status_code == 200

    diff = client.post(f"/github/pr-dry-runs/{pr_task_id}/create-diff-review", json={
        "diff_text": "+hello\n-old\n",
        "changed_files": ["README.md"],
        "validation_commands": commands,
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


def create_approved_execution(client, validation_commands=None):
    diff_task_id = create_approved_diff(client, validation_commands=validation_commands)
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
    return exec_task_id


def test_sandbox_patch_execution_rejects_shell_metacharacters(tmp_path):
    configure(tmp_path)
    client = server.app.test_client()
    command = "pytest -q tests/test_report.py; cat /etc/passwd"
    exec_task_id = create_approved_execution(client, validation_commands=[command])

    res = client.post(f"/sandbox/executions/{exec_task_id}/run", json={
        "diff_text": "diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n@@\n-old\n+new\n",
        "validation_commands": [command],
        "runner_mode": "strict",
    })
    assert res.status_code == 400
    payload = res.get_json()
    assert payload["error"] == "validation_command_disallowed_shell_syntax"
    assert payload["failure_kind"] == "policy_rejected"
    assert payload["policy_rejected"] is True
    assert payload["execute_automatically"] is False


def test_sandbox_patch_execution_rejects_local_dev_without_opt_in(tmp_path, monkeypatch):
    configure(tmp_path)
    client = server.app.test_client()
    monkeypatch.delenv("CPOS_ALLOW_LOCAL_DEV_RUN", raising=False)
    exec_task_id = create_approved_execution(client, validation_commands=["pytest -q tests/test_report.py"])

    res = client.post(f"/sandbox/executions/{exec_task_id}/run", json={
        "diff_text": "diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n@@\n-old\n+new\n",
        "validation_commands": ["pytest -q tests/test_report.py"],
        "runner_mode": "local-dev",
    })
    assert res.status_code == 400
    payload = res.get_json()
    assert payload["error"] == "local_dev_runner_mode_requires_explicit_opt_in"
    assert payload["failure_kind"] == "policy_rejected"
    assert payload["runner_mode"] == "local-dev"


def test_sandbox_patch_execution_retry_review_flow(tmp_path, monkeypatch):
    configure(tmp_path)
    client = server.app.test_client()
    exec_task_id = create_approved_execution(client, validation_commands=["pytest -q tests/test_report.py"])

    src_root = tmp_path / "src-fail"
    src_root.mkdir()
    (src_root / "README.md").write_text("old\n", encoding="utf-8")
    monkeypatch.setattr("cpos.sandbox_patch_runner._project_root", lambda: src_root)
    monkeypatch.setattr("cpos.sandbox_patch_runner._apply_patch", lambda workspace, diff_text: {"ok": True, "stage": "apply", "exit_code": 0, "stdout_sha256": "ok", "stderr_sha256": ""})

    class FailingSandboxRunner:
        def __init__(self, *args, **kwargs):
            self.mode = kwargs.get("mode")
        def run_command(self, target_dir, command):
            return {"stdout": "", "stderr": "failed", "exit_code": 2, "sandbox": {"backend": "fake", "mode": self.mode, "isolated": True, "fallback_used": False}}

    monkeypatch.setattr("cpos.sandbox_patch_runner.SandboxRunner", FailingSandboxRunner)

    run_res = client.post(f"/sandbox/executions/{exec_task_id}/run", json={
        "diff_text": "diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n@@\n-old\n+new\n",
        "validation_commands": ["pytest -q tests/test_report.py"],
        "runner_mode": "strict",
    })
    assert run_res.status_code == 200
    assert run_res.get_json()["ok"] is False
    assert run_res.get_json()["status"] == "completed_with_failures"
    assert run_res.get_json()["failure_kind"] == "validation_command"

    created = client.post(f"/sandbox/executions/{exec_task_id}/create-retry-review", json={"reason": "test_retry"})
    assert created.status_code == 200
    payload = created.get_json()
    retry_task_id = payload["task_id"]
    assert payload["plan"]["failure_kind"] == "validation_command"
    assert payload["plan"]["failed_command"]["exit_code"] == 2
    assert payload["plan"]["raw_outputs_stored"] is False
    assert payload["execute_automatically"] is False

    listed = client.get("/sandbox/execution-retries")
    assert listed.status_code == 200
    assert listed.get_json()["count"] == 1

    missing_confirm = client.post(f"/sandbox/execution-retries/{retry_task_id}/approve", json={})
    assert missing_confirm.status_code == 400
    assert missing_confirm.get_json()["error"] == "confirm_required"

    before_approve_template = client.post(f"/sandbox/execution-retries/{retry_task_id}/create-replan-template", json={})
    assert before_approve_template.status_code == 404
    assert before_approve_template.get_json()["error"] == "approved_sandbox_retry_required"

    approved = client.post(f"/sandbox/execution-retries/{retry_task_id}/approve", json={"confirm": True})
    assert approved.status_code == 200
    assert approved.get_json()["status"] == "approved_retry_plan_only"
    assert client.get("/sandbox/execution-retries").get_json()["count"] == 0

    template = client.post(f"/sandbox/execution-retries/{retry_task_id}/create-replan-template", json={"reason": "make_new_plan"})
    assert template.status_code == 200
    template_payload = template.get_json()
    assert template_payload["status"] == "template_created"
    assert template_payload["template"]["failure_kind"] == "validation_command"
    assert template_payload["template"]["raw_outputs_stored"] is False
    assert template_payload["template"]["raw_patch_stored"] is False
    assert template_payload["template"]["workspace_reused"] is False
    assert template_payload["template"]["diff_text_included"] is False
    assert template_payload["template"]["execute_automatically"] is False
    assert "github_diff_review" in template_payload["template"]["next_review_chain"]

    templates = client.get("/sandbox/replan-templates")
    assert templates.status_code == 200
    assert templates.get_json()["count"] == 1

    intake = client.post(f"/sandbox/replan-templates/{template_payload['task_id']}/create-diff-intake", json={"reason": "next_diff"})
    assert intake.status_code == 200
    intake_payload = intake.get_json()
    assert intake_payload["status"] == "intake_created"
    assert intake_payload["intake"]["diff_text_included"] is False
    assert intake_payload["intake"]["raw_diff_stored"] is False
    assert intake_payload["intake"]["execute_automatically"] is False
    assert "diff_text" in intake_payload["intake"]["required_human_inputs"]
    assert intake_payload["intake"]["target_api"].startswith("POST /github/pr-dry-runs")

    intakes = client.get("/sandbox/diff-intakes")
    assert intakes.status_code == 200
    assert intakes.get_json()["count"] == 1


def test_sandbox_patch_execution_retry_requires_failed_completed_run(tmp_path):
    configure(tmp_path)
    client = server.app.test_client()
    missing = client.post("/sandbox/executions/task_missing/create-retry-review", json={})
    assert missing.status_code == 404
    assert missing.get_json()["error"] == "completed_sandbox_execution_required"


def test_sandbox_patch_execution_retry_classifies_sandbox_unavailable(tmp_path, monkeypatch):
    configure(tmp_path)
    client = server.app.test_client()
    exec_task_id = create_approved_execution(client, validation_commands=["pytest -q tests/test_report.py"])

    src_root = tmp_path / "src-sandbox-missing"
    src_root.mkdir()
    (src_root / "README.md").write_text("old\n", encoding="utf-8")
    monkeypatch.setattr("cpos.sandbox_patch_runner._project_root", lambda: src_root)
    monkeypatch.setattr("cpos.sandbox_patch_runner._apply_patch", lambda workspace, diff_text: {"ok": True, "stage": "apply", "exit_code": 0, "stdout_sha256": "ok", "stderr_sha256": ""})

    class MissingSandboxRunner:
        def __init__(self, *args, **kwargs):
            self.mode = kwargs.get("mode")
        def run_command(self, target_dir, command):
            return {"stdout": "", "stderr": "docker missing", "exit_code": 125, "sandbox": {"backend": "none", "mode": self.mode, "isolated": False, "fallback_used": False}}

    monkeypatch.setattr("cpos.sandbox_patch_runner.SandboxRunner", MissingSandboxRunner)

    run_res = client.post(f"/sandbox/executions/{exec_task_id}/run", json={
        "diff_text": "diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n@@\n-old\n+new\n",
        "validation_commands": ["pytest -q tests/test_report.py"],
        "runner_mode": "strict",
    })
    assert run_res.status_code == 200
    assert run_res.get_json()["failure_kind"] == "sandbox_unavailable"

    created = client.post(f"/sandbox/executions/{exec_task_id}/create-retry-review", json={})
    assert created.status_code == 200
    assert created.get_json()["plan"]["failure_kind"] == "sandbox_unavailable"


def test_sandbox_patch_execution_retry_classifies_patch_apply(tmp_path, monkeypatch):
    configure(tmp_path)
    client = server.app.test_client()
    exec_task_id = create_approved_execution(client, validation_commands=["pytest -q tests/test_report.py"])

    src_root = tmp_path / "src-patch-fail"
    src_root.mkdir()
    (src_root / "README.md").write_text("old\n", encoding="utf-8")
    monkeypatch.setattr("cpos.sandbox_patch_runner._project_root", lambda: src_root)
    monkeypatch.setattr("cpos.sandbox_patch_runner._apply_patch", lambda workspace, diff_text: {"ok": False, "stage": "check", "exit_code": 1, "stdout_sha256": "", "stderr_sha256": "bad"})

    run_res = client.post(f"/sandbox/executions/{exec_task_id}/run", json={
        "diff_text": "bad diff",
        "validation_commands": ["pytest -q tests/test_report.py"],
        "runner_mode": "strict",
    })
    assert run_res.status_code == 200
    assert run_res.get_json()["failure_kind"] == "patch_apply"

    created = client.post(f"/sandbox/executions/{exec_task_id}/create-retry-review", json={})
    assert created.status_code == 200
    assert created.get_json()["plan"]["failure_kind"] == "patch_apply"


def test_sandbox_replan_diff_intake_requires_template(tmp_path):
    configure(tmp_path)
    client = server.app.test_client()
    missing = client.post("/sandbox/replan-templates/task_missing/create-diff-intake", json={})
    assert missing.status_code == 404
    assert missing.get_json()["error"] == "replan_template_required"


def test_sandbox_execution_driver_api_advances_to_ready(tmp_path):
    configure(tmp_path)
    client = server.app.test_client()
    diff_task_id = create_approved_diff(client)

    res = client.post("/sandbox/execution-driver/advance", json={
        "diff_task_id": diff_task_id,
        "approve_plan": True,
        "approve_execution": True,
        "reason": "api_test",
    })

    assert res.status_code == 200
    payload = res.get_json()
    assert payload["ok"] is True
    assert payload["status"] == "approved_sandbox_execution_ready"
    assert payload["metadata_only"] is True
    assert payload["raw_diff_stored"] is False
    assert payload["raw_outputs_stored"] is False
    assert payload["commit_created"] is False
    assert payload["pushed"] is False
    assert payload["pr_created"] is False
    assert payload["step_count"] == 4


def test_sandbox_execution_driver_api_scope_mapping():
    with server.app.test_request_context("/sandbox/execution-driver/advance", method="POST"):
        assert server.required_scope_for_request() == "write:sandbox"


def test_sandbox_execution_driver_replan_failure_api(tmp_path):
    configure(tmp_path)
    client = server.app.test_client()
    server.agent.task_tape.append_event(
        task_id="task_failed_exec_api",
        event="sandbox_patch_execution_completed",
        target="sandbox://execution/task_failed_exec_api",
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
            "command_results": [{"command_sha256": "abc", "exit_code": 1, "stdout_sha256": "out", "stderr_sha256": "err"}],
            "success": False,
            "execute_automatically": False,
        },
    )

    res = client.post("/sandbox/execution-driver/replan-failure", json={
        "source_execution_task_id": "task_failed_exec_api",
        "approve_retry": True,
        "create_replan_template": True,
        "create_diff_intake": True,
    })

    assert res.status_code == 200
    payload = res.get_json()
    assert payload["ok"] is True
    assert payload["status"] == "sandbox_diff_intake_created"
    assert payload["raw_outputs_stored"] is False
    assert payload["raw_diff_stored"] is False
    assert payload["workspace_reused"] is False


def test_sandbox_execution_driver_replan_failure_scope_mapping():
    with server.app.test_request_context("/sandbox/execution-driver/replan-failure", method="POST"):
        assert server.required_scope_for_request() == "write:sandbox"


def test_sandbox_execution_scoreboard_api(tmp_path):
    configure(tmp_path)
    client = server.app.test_client()
    server.agent.task_tape.append_event(
        task_id="task_score_ok",
        event="sandbox_patch_execution_completed",
        target="sandbox://execution/task_score_ok",
        status="completed_success",
        payload={"review_type": "sandbox_patch_execution", "success": True, "patch_applied": True, "workspace_copied": True, "commands_executed": True, "tests_run": True, "failure_kind": None, "execute_automatically": False},
    )
    server.agent.task_tape.append_event(
        task_id="task_score_fail",
        event="sandbox_patch_execution_completed",
        target="sandbox://execution/task_score_fail",
        status="completed_with_failures",
        payload={"review_type": "sandbox_patch_execution", "success": False, "patch_applied": True, "workspace_copied": True, "commands_executed": True, "tests_run": True, "failure_kind": "validation_command", "execute_automatically": False},
    )

    res = client.get("/sandbox/scoreboard")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["completed_runs"] == 2
    assert payload["success_runs"] == 1
    assert payload["failure_runs"] == 1
    assert payload["success_rate"] == 50.0
    assert payload["failure_kind_counts"]["validation_command"] == 1


def test_sandbox_scoreboard_scope_mapping():
    with server.app.test_request_context("/sandbox/scoreboard", method="GET"):
        assert server.required_scope_for_request() == "read:sandbox"


def test_sandbox_flow_graph_api(tmp_path):
    configure(tmp_path)
    client = server.app.test_client()
    server.agent.task_tape.append_event(
        task_id="task_exec_api",
        event="sandbox_patch_execution_completed",
        target="sandbox://execution/task_exec_api",
        status="completed_with_failures",
        payload={"review_type": "sandbox_patch_execution", "success": False, "failure_kind": "validation_command"},
    )
    server.agent.task_tape.append_event(
        task_id="task_retry_api",
        event="review_required",
        target="sandbox://execution/task_exec_api/retry",
        status="pending",
        payload={"review_type": "sandbox_patch_execution_retry", "plan": {"source_execution_task_id": "task_exec_api", "failure_kind": "validation_command"}},
    )

    res = client.get("/sandbox/flow-graph?source_execution_task_id=task_exec_api")

    assert res.status_code == 200
    payload = res.get_json()
    assert payload["ok"] is True
    assert payload["metadata_only"] is True
    assert payload["source_execution_task_id"] == "task_exec_api"
    assert payload["counts"]["nodes"] == 2
    assert payload["counts"]["edges"] == 1
    assert payload["raw_diff_stored"] is False
    assert payload["raw_outputs_stored"] is False
    assert payload["execute_automatically"] is False


def test_sandbox_flow_graph_scope_mapping():
    with server.app.test_request_context("/sandbox/flow-graph", method="GET"):
        assert server.required_scope_for_request() == "read:sandbox"



def test_sandbox_auto_fix_candidate_api(tmp_path):
    configure(tmp_path)
    client = server.app.test_client()
    replan_task_id = "task_replan_api"
    server.agent.task_tape.append_event(
        task_id=replan_task_id,
        event="sandbox_patch_replan_template_created",
        target="sandbox://replan-template/task_retry",
        status="template_created",
        payload={
            "review_type": "sandbox_patch_replan_template",
            "template": {
                "retry_task_id": "task_retry",
                "source_execution_task_id": "task_exec",
                "failure_kind": "patch_apply",
                "source_execution_status": "failed_patch_apply",
                "patch_apply_stage": "check",
                "patch_apply_exit_code": 1,
                "failed_command": {},
                "suggested_focus": ["regenerate_diff_against_current_base"],
                "execute_automatically": False,
            },
        },
    )

    created = client.post(f"/sandbox/replan-templates/{replan_task_id}/create-fix-candidate", json={"reason": "api"})
    assert created.status_code == 200
    payload = created.get_json()
    assert payload["ok"] is True
    assert payload["candidate"]["failure_kind"] == "patch_apply"
    assert payload["candidate"]["raw_diff_stored"] is False
    assert payload["candidate"]["raw_outputs_stored"] is False
    assert payload["candidate"]["execute_automatically"] is False

    listed = client.get("/sandbox/fix-candidates")
    assert listed.status_code == 200
    assert listed.get_json()["count"] == 1


def test_sandbox_auto_fix_candidate_scope_mapping():
    with server.app.test_request_context("/sandbox/fix-candidates", method="GET"):
        assert server.required_scope_for_request() == "read:sandbox"
    with server.app.test_request_context("/sandbox/replan-templates/task/create-fix-candidate", method="POST"):
        assert server.required_scope_for_request() == "write:sandbox"


def test_sandbox_diff_review_draft_api(tmp_path):
    configure(tmp_path)
    client = server.app.test_client()
    candidate_task_id = "task_candidate_api"
    server.agent.task_tape.append_event(
        task_id=candidate_task_id,
        event="sandbox_auto_fix_candidate_created",
        target="sandbox://auto-fix-candidate/task_replan",
        status="candidate_created",
        payload={
            "review_type": "sandbox_auto_fix_candidate",
            "candidate": {
                "replan_task_id": "task_replan",
                "retry_task_id": "task_retry",
                "source_execution_task_id": "task_exec",
                "failure_kind": "policy_rejected",
                "candidate_strategy": "adjust_policy_inputs_not_code",
                "confidence": 0.64,
                "suggested_focus": ["review_policy_rejection_metadata"],
                "candidate_steps": ["replace disallowed validation command"],
                "execute_automatically": False,
            },
        },
    )

    created = client.post(f"/sandbox/fix-candidates/{candidate_task_id}/create-diff-draft", json={"reason": "api"})
    assert created.status_code == 200
    payload = created.get_json()
    assert payload["ok"] is True
    assert payload["draft"]["failure_kind"] == "policy_rejected"
    assert payload["draft"]["raw_diff_stored"] is False
    assert payload["draft"]["diff_text_included"] is False
    assert payload["draft"]["execute_automatically"] is False

    listed = client.get("/sandbox/diff-drafts")
    assert listed.status_code == 200
    assert listed.get_json()["count"] == 1


def test_sandbox_diff_review_draft_scope_mapping():
    with server.app.test_request_context("/sandbox/diff-drafts", method="GET"):
        assert server.required_scope_for_request() == "read:sandbox"
    with server.app.test_request_context("/sandbox/fix-candidates/task/create-diff-draft", method="POST"):
        assert server.required_scope_for_request() == "write:sandbox"
