from cpos.diff_review_draft import create_diff_review_draft, pending_diff_review_drafts
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
                "schema": "cpos.sandbox_auto_fix_candidate.v1",
                "replan_task_id": "task_replan",
                "retry_task_id": "task_retry",
                "source_execution_task_id": "task_exec",
                "failure_kind": "validation_command",
                "candidate_strategy": "target_failed_validation_metadata",
                "confidence": 0.68,
                "suggested_focus": ["inspect_failed_test_metadata"],
                "candidate_steps": ["modify smallest related code path"],
                "raw_diff_stored": False,
                "raw_outputs_stored": False,
                "execute_automatically": False,
            },
        },
    )
    return task_id


def test_diff_review_draft_requires_candidate(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    result = create_diff_review_draft(store, candidate_task_id="missing")
    assert result["ok"] is False
    assert result["error"] == "auto_fix_candidate_required"
    assert result["execute_automatically"] is False


def test_diff_review_draft_is_metadata_only(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    candidate_task_id = _candidate(store)

    result = create_diff_review_draft(store, candidate_task_id=candidate_task_id, reason="unit")

    assert result["ok"] is True
    draft = result["draft"]
    assert draft["schema"] == "cpos.sandbox_diff_review_draft.v1"
    assert draft["candidate_task_id"] == candidate_task_id
    assert draft["failure_kind"] == "validation_command"
    assert draft["target_api"].startswith("POST /github")
    assert draft["raw_diff_stored"] is False
    assert draft["raw_outputs_stored"] is False
    assert draft["raw_patch_stored"] is False
    assert draft["diff_text_included"] is False
    assert draft["execute_automatically"] is False
    assert draft["patch_applied"] is False
    assert draft["commands_executed"] is False
    assert draft["commit_created"] is False
    assert draft["pushed"] is False
    assert draft["pr_created"] is False
    assert "diff_text" in draft["required_human_inputs"]
    assert pending_diff_review_drafts(store)[0]["task_id"] == result["task_id"]
    assert "raw diff --git" not in str(store.events())
