from cpos.sandbox_flow_graph import build_sandbox_flow_graph
from cpos.task_tape import TaskTapeStore


def _append_flow_events(store):
    store.append_event(
        task_id="task_exec",
        event="sandbox_patch_execution_completed",
        target="sandbox://execution/task_exec",
        status="completed_with_failures",
        payload={
            "review_type": "sandbox_patch_execution",
            "success": False,
            "failure_kind": "validation_command",
            "patch_applied": True,
            "workspace_copied": True,
        },
    )
    store.append_event(
        task_id="task_retry",
        event="review_required",
        target="sandbox://execution/task_exec/retry",
        status="pending",
        payload={
            "review_type": "sandbox_patch_execution_retry",
            "plan": {
                "source_execution_task_id": "task_exec",
                "failure_kind": "validation_command",
                "raw_outputs_stored": False,
            },
        },
    )
    store.append_event(
        task_id="task_replan",
        event="sandbox_patch_replan_template_created",
        target="sandbox://replan-template/task_retry",
        status="template_created",
        payload={
            "review_type": "sandbox_patch_replan_template",
            "template": {
                "retry_task_id": "task_retry",
                "source_execution_task_id": "task_exec",
                "failure_kind": "validation_command",
                "diff_text_included": False,
            },
        },
    )
    store.append_event(
        task_id="task_intake",
        event="sandbox_replan_diff_intake_created",
        target="sandbox://diff-intake/task_replan",
        status="intake_created",
        payload={
            "review_type": "sandbox_replan_diff_intake",
            "intake": {
                "replan_task_id": "task_replan",
                "source_execution_task_id": "task_exec",
                "failure_kind": "validation_command",
                "execute_automatically": False,
            },
        },
    )
    store.append_event(
        task_id="task_candidate",
        event="sandbox_auto_fix_candidate_created",
        target="sandbox://auto-fix-candidate/task_replan",
        status="candidate_created",
        payload={
            "review_type": "sandbox_auto_fix_candidate",
            "candidate": {
                "replan_task_id": "task_replan",
                "source_execution_task_id": "task_exec",
                "failure_kind": "validation_command",
                "candidate_strategy": "target_failed_validation_metadata",
                "confidence": 0.68,
                "raw_diff_stored": False,
            },
        },
    )
    store.append_event(
        task_id="task_patch_generation",
        event="review_required",
        target="sandbox://patch-generation/task_candidate",
        status="pending_review",
        payload={
            "review_type": "sandbox_patch_generation",
            "plan": {
                "candidate_task_id": "task_candidate",
                "source_execution_task_id": "task_exec",
                "failure_kind": "validation_command",
                "candidate_strategy": "target_failed_validation_metadata",
                "confidence": 0.68,
                "raw_diff_stored": False,
                "execute_automatically": False,
            },
        },
    )
    store.append_event(
        task_id="task_patch_generation",
        event="sandbox_patch_generation_output_validated",
        target="sandbox://patch-generation/task_patch_generation/validation",
        status="validated",
        payload={
            "review_type": "sandbox_patch_generation_validation",
            "patch_generation_task_id": "task_patch_generation",
            "candidate_task_id": "task_candidate",
            "source_execution_task_id": "task_exec",
            "failure_kind": None,
            "diff_size_bytes": 43,
            "changed_file_count": 1,
            "workspace_copied": True,
            "patch_applied": False,
            "commands_executed": False,
            "raw_diff_stored": False,
            "raw_outputs_stored": False,
            "execute_automatically": False,
        },
    )
    store.append_event(
        task_id="task_patch_generation",
        event="sandbox_patch_generation_advanced_to_execution_review",
        target="sandbox://patch-generation/task_patch_generation/execution-review/task_execution_review_from_patch",
        status="execution_review_ready",
        payload={
            "review_type": "sandbox_patch_generation_safe_advance",
            "patch_generation_task_id": "task_patch_generation",
            "source_execution_task_id": "task_exec",
            "candidate_task_id": "task_candidate",
            "github_diff_review_task_id": "task_github_diff_from_patch_generation",
            "patch_task_id": "task_patch_plan_from_patch_generation",
            "execution_task_id": "task_execution_review_from_patch",
            "step_count": 6,
            "raw_diff_stored": False,
            "raw_outputs_stored": False,
            "patch_applied": False,
            "commands_executed": False,
            "execute_automatically": False,
        },
    )
    store.append_event(
        task_id="task_github_diff_from_patch_generation",
        event="sandbox_patch_generation_linked_to_github_diff_review",
        target="sandbox://patch-generation/task_patch_generation/github-diff-review/task_github_diff_from_patch_generation",
        status="linked_metadata_only",
        payload={
            "review_type": "sandbox_patch_generation_to_github_diff_review",
            "patch_generation_task_id": "task_patch_generation",
            "github_diff_review_task_id": "task_github_diff_from_patch_generation",
            "source_task_id": "task_pr",
            "source_execution_task_id": "task_exec",
            "failure_kind": "validation_command",
            "diff_size_bytes": 43,
            "changed_file_count": 1,
            "raw_diff_stored": False,
            "execute_automatically": False,
        },
    )
    store.append_event(
        task_id="task_draft",
        event="sandbox_diff_review_draft_created",
        target="sandbox://diff-review-draft/task_candidate",
        status="draft_created",
        payload={
            "review_type": "sandbox_diff_review_draft",
            "draft": {
                "candidate_task_id": "task_candidate",
                "source_execution_task_id": "task_exec",
                "failure_kind": "validation_command",
                "target_api": "POST /github/pr-dry-runs",
                "execute_automatically": False,
            },
        },
    )
    store.append_event(
        task_id="task_github_diff",
        event="sandbox_diff_review_draft_linked_to_github_diff_review",
        target="sandbox://diff-review-draft/task_draft/github-diff-review/task_github_diff",
        status="linked_metadata_only",
        payload={
            "review_type": "sandbox_diff_review_draft_to_github_diff_review",
            "draft_task_id": "task_draft",
            "github_diff_review_task_id": "task_github_diff",
            "source_task_id": "task_pr",
            "source_execution_task_id": "task_exec",
            "failure_kind": "validation_command",
            "diff_size_bytes": 42,
            "changed_file_count": 1,
            "raw_diff_stored": False,
            "execute_automatically": False,
        },
    )


def test_sandbox_flow_graph_links_failure_to_draft(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    _append_flow_events(store)

    graph = build_sandbox_flow_graph(store, source_execution_task_id="task_exec")

    assert graph["ok"] is True
    assert graph["metadata_only"] is True
    assert graph["raw_diff_stored"] is False
    assert graph["raw_outputs_stored"] is False
    assert graph["execute_automatically"] is False
    assert graph["counts"]["nodes"] == 12
    assert graph["counts"]["edges"] == 11
    assert graph["counts"]["sandbox_execution"] == 1
    assert graph["counts"]["retry_review"] == 1
    assert graph["counts"]["replan_template"] == 1
    assert graph["counts"]["diff_intake"] == 1
    assert graph["counts"]["auto_fix_candidate"] == 1
    assert graph["counts"]["diff_review_draft"] == 1
    assert graph["counts"]["patch_generation_review"] == 1
    assert graph["counts"]["patch_generation_validation"] == 1
    assert graph["counts"]["patch_generation_safe_advance"] == 1
    assert graph["counts"]["sandbox_execution_review"] == 1
    assert graph["counts"]["github_diff_review"] == 2
    assert {node["kind"] for node in graph["nodes"]} == {
        "sandbox_execution",
        "retry_review",
        "replan_template",
        "diff_intake",
        "auto_fix_candidate",
        "patch_generation_review",
        "patch_generation_validation",
        "patch_generation_safe_advance",
        "sandbox_execution_review",
        "diff_review_draft",
        "github_diff_review",
    }
    assert ("task_exec", "task_retry", "creates_retry_review") in {
        (edge["source"], edge["target"], edge["relation"]) for edge in graph["edges"]
    }
    assert ("task_candidate", "task_draft", "creates_diff_review_draft") in {
        (edge["source"], edge["target"], edge["relation"]) for edge in graph["edges"]
    }
    assert ("task_candidate", "task_patch_generation", "creates_patch_generation_review") in {
        (edge["source"], edge["target"], edge["relation"]) for edge in graph["edges"]
    }
    assert ("task_patch_generation", "task_patch_generation:validation", "validates_generated_patch") in {
        (edge["source"], edge["target"], edge["relation"]) for edge in graph["edges"]
    }
    assert ("task_patch_generation", "task_patch_generation:safe-advance", "advances_to_execution_review") in {
        (edge["source"], edge["target"], edge["relation"]) for edge in graph["edges"]
    }
    assert ("task_patch_generation:safe-advance", "task_execution_review_from_patch", "creates_execution_review") in {
        (edge["source"], edge["target"], edge["relation"]) for edge in graph["edges"]
    }
    assert ("task_patch_generation", "task_github_diff_from_patch_generation", "creates_github_diff_review") in {
        (edge["source"], edge["target"], edge["relation"]) for edge in graph["edges"]
    }
    assert ("task_draft", "task_github_diff", "creates_github_diff_review") in {
        (edge["source"], edge["target"], edge["relation"]) for edge in graph["edges"]
    }


def test_sandbox_flow_graph_filters_by_source_execution(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    _append_flow_events(store)

    graph = build_sandbox_flow_graph(store, source_execution_task_id="missing")

    assert graph["counts"]["nodes"] == 0
    assert graph["counts"]["edges"] == 0
    assert graph["nodes"] == []
    assert graph["edges"] == []
