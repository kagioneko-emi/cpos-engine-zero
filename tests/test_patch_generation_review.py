from cpos.github_pr_flow import approve_github_pr_dry_run, create_github_pr_dry_run
from cpos.patch_generation_review import (
    advance_patch_generation_to_execution_review,
    approve_patch_generation_review,
    create_github_diff_review_from_patch_generation,
    create_patch_generation_review,
    pending_patch_generation_reviews,
)
from cpos.task_tape import TaskTapeStore


def _candidate(store):
    task_id = "task_candidate"
    store.append_event(
        task_id=task_id,
        event="sandbox_auto_fix_candidate_created",
        target="sandbox://auto-fix-candidate/task_replan",
        status="candidate_created",
        payload={
            "review_type": "sandbox_auto_fix_candidate",
            "candidate": {
                "replan_task_id": "task_replan",
                "retry_task_id": "task_retry",
                "source_execution_task_id": "task_exec",
                "failure_kind": "validation_command",
                "candidate_strategy": "target_failed_validation_metadata",
                "confidence": 0.68,
                "candidate_steps": ["modify smallest related code path"],
                "raw_diff_stored": False,
                "raw_outputs_stored": False,
                "execute_automatically": False,
            },
        },
    )
    return task_id


def _approved_pr(store):
    pr = create_github_pr_dry_run(store, repo="kagioneko/cpos-engine-zero", title="Patch gen route", files=["README.md"], summary="ctx")
    approve_github_pr_dry_run(store, pr["task_id"], confirm=True)
    return pr["task_id"]


def test_patch_generation_review_requires_candidate(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    result = create_patch_generation_review(store, candidate_task_id="missing")
    assert result["ok"] is False
    assert result["error"] == "auto_fix_candidate_required"
    assert result["execute_automatically"] is False


def test_patch_generation_review_is_metadata_only_and_approval_gated(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    candidate_task_id = _candidate(store)

    created = create_patch_generation_review(store, candidate_task_id=candidate_task_id, reason="unit")

    assert created["ok"] is True
    plan = created["plan"]
    assert plan["schema"] == "cpos.sandbox_patch_generation_review.v1"
    assert plan["candidate_task_id"] == candidate_task_id
    assert plan["raw_diff_stored"] is False
    assert plan["diff_text_included"] is False
    assert plan["execute_automatically"] is False
    assert plan["commit_created"] is False
    assert plan["pushed"] is False
    assert plan["pr_created"] is False
    assert pending_patch_generation_reviews(store)[0]["task_id"] == created["task_id"]

    missing_confirm = approve_patch_generation_review(store, created["task_id"], confirm=False)
    assert missing_confirm["error"] == "confirm_required"
    approved = approve_patch_generation_review(store, created["task_id"], confirm=True)
    assert approved["ok"] is True
    assert approved["execute_automatically"] is False
    assert pending_patch_generation_reviews(store) == []


def test_patch_generation_routes_transient_diff_to_github_diff_review(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    source_task_id = _approved_pr(store)
    candidate_task_id = _candidate(store)
    review = create_patch_generation_review(store, candidate_task_id=candidate_task_id)
    approve_patch_generation_review(store, review["task_id"], confirm=True)
    diff_text = "diff --git a/README.md b/README.md\n@@\n-old\n+new\n"

    result = create_github_diff_review_from_patch_generation(
        store,
        patch_generation_task_id=review["task_id"],
        source_task_id=source_task_id,
        diff_text=diff_text,
        changed_files=["README.md"],
        validation_commands=["pytest -q tests/test_report.py"],
        reason="unit",
    )

    assert result["ok"] is True
    assert result["raw_diff_stored"] is False
    assert result["diff_text_included"] is False
    assert result["plan"]["diff_values_stored"] is False
    assert result["plan"]["diff_size_bytes"] == len(diff_text.encode("utf-8"))
    link = result["patch_generation_link"]["payload"]
    assert link["patch_generation_task_id"] == review["task_id"]
    assert link["github_diff_review_task_id"] == result["task_id"]
    assert link["raw_diff_stored"] is False
    assert link["execute_automatically"] is False
    assert "diff --git" not in str(link)
    assert "new" not in str(link)
    assert "diff --git" not in str(store.events())

def test_patch_generation_validation_harness_is_metadata_only(tmp_path, monkeypatch):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    candidate_task_id = _candidate(store)
    review = create_patch_generation_review(store, candidate_task_id=candidate_task_id)
    approve_patch_generation_review(store, review["task_id"], confirm=True)
    diff_text = "diff --git a/README.md b/README.md\n@@\n-old\n+new\n"
    monkeypatch.setattr(
        "cpos.patch_generation_review._check_generated_patch",
        lambda diff_text: {
            "ok": True,
            "stage": "git_apply_check",
            "exit_code": 0,
            "stdout_sha256": "out",
            "stderr_sha256": "err",
            "stdout_size_bytes": 0,
            "stderr_size_bytes": 0,
            "workspace_copied": True,
            "patch_applied": False,
            "commands_executed": False,
        },
    )

    from cpos.patch_generation_review import validate_patch_generation_output

    result = validate_patch_generation_output(
        store,
        patch_generation_task_id=review["task_id"],
        diff_text=diff_text,
        changed_files=["README.md"],
        validation_commands=["pytest -q tests/test_report.py"],
        reason="unit",
    )

    assert result["ok"] is True
    validation = result["validation"]
    assert validation["patch_apply_stage"] == "git_apply_check"
    assert validation["raw_diff_stored"] is False
    assert validation["diff_text_included"] is False
    assert validation["raw_outputs_stored"] is False
    assert validation["patch_applied"] is False
    assert validation["commands_executed"] is False
    assert validation["diff_size_bytes"] == len(diff_text.encode("utf-8"))
    assert "diff --git" not in str(result["event"])
    assert "diff --git" not in str(store.events())


def test_patch_generation_validation_rejects_disallowed_command(tmp_path, monkeypatch):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    candidate_task_id = _candidate(store)
    review = create_patch_generation_review(store, candidate_task_id=candidate_task_id)
    approve_patch_generation_review(store, review["task_id"], confirm=True)
    called = {"check": False}

    def fake_check(diff_text):
        called["check"] = True
        return {"ok": True}

    monkeypatch.setattr("cpos.patch_generation_review._check_generated_patch", fake_check)

    from cpos.patch_generation_review import validate_patch_generation_output

    result = validate_patch_generation_output(
        store,
        patch_generation_task_id=review["task_id"],
        diff_text="diff --git a/README.md b/README.md\n@@\n-old\n+new\n",
        changed_files=["README.md"],
        validation_commands=["python -c 'print(1)'"]
    )

    assert result["ok"] is False
    assert result["failure_kind"] == "policy_rejected"
    assert result["validation"]["command_policy"]["ok"] is False
    assert result["validation"]["commands_executed"] is False
    assert called["check"] is False

def test_patch_generation_safe_advance_opens_execution_review(tmp_path, monkeypatch):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    source_task_id = _approved_pr(store)
    candidate_task_id = _candidate(store)
    review = create_patch_generation_review(store, candidate_task_id=candidate_task_id)
    approve_patch_generation_review(store, review["task_id"], confirm=True)
    diff_text = "diff --git a/README.md b/README.md\n@@\n-old\n+new\n"
    monkeypatch.setattr(
        "cpos.patch_generation_review._check_generated_patch",
        lambda diff_text: {
            "ok": True,
            "stage": "git_apply_check",
            "exit_code": 0,
            "stdout_sha256": "out",
            "stderr_sha256": "err",
            "stdout_size_bytes": 0,
            "stderr_size_bytes": 0,
            "workspace_copied": True,
            "patch_applied": False,
            "commands_executed": False,
        },
    )

    result = advance_patch_generation_to_execution_review(
        store,
        patch_generation_task_id=review["task_id"],
        source_task_id=source_task_id,
        diff_text=diff_text,
        changed_files=["README.md"],
        validation_commands=["pytest -q tests/test_report.py"],
        confirm=True,
        reason="unit",
    )

    assert result["ok"] is True
    assert result["status"] == "execution_review_ready"
    assert result["github_diff_review_task_id"]
    assert result["patch_task_id"]
    assert result["execution_task_id"]
    assert result["raw_diff_stored"] is False
    assert result["patch_applied"] is False
    assert result["commands_executed"] is False
    assert result["execute_automatically"] is False
    assert any(event.event == "github_diff_review_approved" for event in store.events())
    assert any(event.event == "sandbox_patch_plan_approved" for event in store.events())
    assert any(
        event.event == "review_required" and event.payload.get("review_type") == "sandbox_patch_execution"
        for event in store.events()
    )
    assert any(event.event == "sandbox_patch_generation_advanced_to_execution_review" for event in store.events())
    assert "diff --git" not in str(result["event"])
    assert "diff --git" not in str(store.events())


def test_patch_generation_safe_advance_requires_confirm(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    result = advance_patch_generation_to_execution_review(
        store,
        patch_generation_task_id="task_patch_generation",
        source_task_id="task_source",
        diff_text="diff --git a/README.md b/README.md\n@@\n-old\n+new\n",
        changed_files=["README.md"],
        validation_commands=["pytest -q tests/test_report.py"],
    )

    assert result["ok"] is False
    assert result["error"] == "confirm_required"
    assert result["execute_automatically"] is False

