from cpos.auto_fix_candidate import create_auto_fix_candidate, pending_auto_fix_candidates
from cpos.task_tape import TaskTapeStore


def _replan_template(store):
    task_id = "task_replan"
    store.append_event(
        task_id=task_id,
        event="sandbox_patch_replan_template_created",
        target="sandbox://replan-template/task_retry",
        status="template_created",
        payload={
            "review_type": "sandbox_patch_replan_template",
            "template": {
                "schema": "cpos.sandbox_patch_replan_template.v1",
                "retry_task_id": "task_retry",
                "source_execution_task_id": "task_exec",
                "failure_kind": "validation_command",
                "source_execution_status": "completed_with_failures",
                "patch_apply_stage": "apply",
                "patch_apply_exit_code": 0,
                "failed_command": {
                    "command_index": 0,
                    "command_sha256": "cmdhash",
                    "exit_code": 1,
                    "stdout_sha256": "outhash",
                    "stderr_sha256": "errhash",
                    "stdout_size_bytes": 10,
                    "stderr_size_bytes": 5,
                },
                "suggested_focus": ["inspect_failed_test_metadata", "create_new_diff_review"],
                "raw_outputs_stored": False,
                "raw_patch_stored": False,
                "diff_text_included": False,
                "execute_automatically": False,
            },
        },
    )
    return task_id


def test_auto_fix_candidate_requires_replan_template(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    result = create_auto_fix_candidate(store, replan_task_id="missing")
    assert result["ok"] is False
    assert result["error"] == "replan_template_required"
    assert result["execute_automatically"] is False


def test_auto_fix_candidate_is_metadata_only(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    replan_task_id = _replan_template(store)

    result = create_auto_fix_candidate(store, replan_task_id=replan_task_id, reason="unit")

    assert result["ok"] is True
    candidate = result["candidate"]
    assert candidate["schema"] == "cpos.sandbox_auto_fix_candidate.v1"
    assert candidate["failure_kind"] == "validation_command"
    assert candidate["candidate_strategy"] == "target_failed_validation_metadata"
    assert candidate["confidence"] > 0
    assert candidate["raw_outputs_stored"] is False
    assert candidate["raw_patch_stored"] is False
    assert candidate["raw_diff_stored"] is False
    assert candidate["diff_text_included"] is False
    assert candidate["workspace_reused"] is False
    assert candidate["execute_automatically"] is False
    assert candidate["commit_created"] is False
    assert candidate["pushed"] is False
    assert candidate["pr_created"] is False
    assert "new_diff_text" in candidate["required_human_inputs"]
    assert pending_auto_fix_candidates(store)[0]["task_id"] == result["task_id"]
    assert "validated output" not in str(store.events())
