from cpos.github_diff_review import (
    approve_github_diff_review,
    create_github_diff_review,
    pending_github_diff_reviews,
    reject_github_diff_review,
)
from cpos.github_pr_flow import approve_github_pr_dry_run, create_github_pr_dry_run
from cpos.task_tape import TaskTapeStore


def approved_pr_plan(store):
    result = create_github_pr_dry_run(
        store,
        repo="kagioneko/cpos-engine-zero",
        title="Fix docs",
        issue_number=3,
        summary="raw issue context",
        files=["README.md"],
    )
    approve_github_pr_dry_run(store, result["task_id"], confirm=True)
    return result["task_id"]


def test_diff_review_requires_approved_pr_dry_run(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    result = create_github_diff_review(store, source_task_id="task_missing", diff_text="+hello")
    assert result["ok"] is False
    assert result["error"] == "approved_pr_dry_run_required"


def test_diff_review_is_metadata_only(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    source_task_id = approved_pr_plan(store)

    diff = """diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@
-old
+new secret-looking value is just text, not a key
"""
    result = create_github_diff_review(
        store,
        source_task_id=source_task_id,
        diff_text=diff,
        changed_files=["README.md"],
        validation_commands=["pytest -q tests/test_report.py"],
    )

    assert result["ok"] is True
    plan = result["plan"]
    assert plan["diff_values_stored"] is False
    assert plan["diff_size_bytes"] == len(diff.encode("utf-8"))
    assert plan["added_lines"] == 1
    assert plan["removed_lines"] == 1
    assert plan["files_written"] is False
    assert plan["patch_applied"] is False
    assert plan["commit_created"] is False
    assert plan["pr_created"] is False
    assert "old" not in str(result["review"]["payload"])
    assert "new secret-looking" not in str(result["review"]["payload"])
    assert len(pending_github_diff_reviews(store)) == 1


def test_diff_review_rejects_secret_like_validation_key(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    source_task_id = approved_pr_plan(store)
    result = create_github_diff_review(
        store,
        source_task_id=source_task_id,
        validation_commands=[{"api_key": "do-not-store"}],
    )
    assert result["ok"] is False
    assert result["error"] == "secret_like_request_blocked"


def test_diff_review_approve_and_reject_are_metadata_only(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    source_task_id = approved_pr_plan(store)
    result = create_github_diff_review(store, source_task_id=source_task_id, diff_text="+x")
    task_id = result["task_id"]

    missing = approve_github_diff_review(store, task_id, confirm=False)
    assert missing["error"] == "confirm_required"

    approved = approve_github_diff_review(store, task_id, confirm=True)
    assert approved["ok"] is True
    assert approved["patch_applied"] is False
    assert approved["pr_created"] is False
    assert pending_github_diff_reviews(store) == []

    second_source = approved_pr_plan(store)
    second = create_github_diff_review(store, source_task_id=second_source, diff_text="+y")
    rejected = reject_github_diff_review(store, second["task_id"], reason="no")
    assert rejected["ok"] is True
    assert rejected["patch_applied"] is False
