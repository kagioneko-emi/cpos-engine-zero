from cpos.github_pr_flow import (
    approve_github_pr_dry_run,
    create_github_pr_dry_run,
    pending_github_pr_reviews,
    reject_github_pr_dry_run,
)
from cpos.task_tape import TaskTapeStore


def test_github_pr_dry_run_creates_review_without_git_side_effects(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl", tmp_path / "checkpoints.jsonl")

    result = create_github_pr_dry_run(
        store,
        repo="kagioneko/cpos-engine-zero",
        issue_number=42,
        issue_url="https://github.com/kagioneko/cpos-engine-zero/issues/42",
        title="Fix failing sandbox policy",
        summary="Sensitive details should not be stored raw",
        files=["sandbox/runner.py", "tests/test_sandbox_runner.py"],
    )

    assert result["ok"] is True
    assert result["execute_automatically"] is False
    plan = result["plan"]
    assert plan["proposed_branch"].startswith("agent/issue-42-fix-failing-sandbox-policy")
    assert plan["summary_values_stored"] is False
    assert plan["branch_created"] is False
    assert plan["commit_created"] is False
    assert plan["pushed"] is False
    assert plan["pr_created"] is False
    assert "Sensitive details" not in str(result["review"]["payload"])
    assert len(pending_github_pr_reviews(store)) == 1


def test_github_pr_dry_run_rejects_secret_like_request(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")

    result = create_github_pr_dry_run(
        store,
        repo="kagioneko/cpos-engine-zero",
        title="Do not leak",
        summary="x",
        files=["app.py"],
        actor="Tester",
        metadata={"labels": ["docs"]},
    )
    assert result["ok"] is True
    assert result["plan"]["metadata_values_stored"] is False
    assert result["plan"]["metadata_keys"] == ["labels"]

    bad = create_github_pr_dry_run(
        store,
        repo="kagioneko/cpos-engine-zero",
        title="Secret request",
        summary="x",
        metadata={"api_key": "do-not-store"},
    )
    assert bad["ok"] is False
    assert bad["error"] == "secret_like_request_blocked"
    assert bad["blocked_paths"] == ["request.metadata.api_key"]

    direct_bad = create_github_pr_dry_run(store, repo="bad", title="x")
    assert direct_bad["ok"] is False
    assert direct_bad["error"] == "repo_owner_name_required"


def test_github_pr_dry_run_approve_and_reject_are_dry_run_only(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    result = create_github_pr_dry_run(store, repo="kagioneko/cpos-engine-zero", title="Fix docs")
    task_id = result["task_id"]

    missing = approve_github_pr_dry_run(store, task_id, confirm=False)
    assert missing["error"] == "confirm_required"

    approved = approve_github_pr_dry_run(store, task_id, confirm=True, reason="ok")
    assert approved["ok"] is True
    assert approved["pr_created"] is False
    assert approved["execute_automatically"] is False
    assert pending_github_pr_reviews(store) == []

    second = create_github_pr_dry_run(store, repo="kagioneko/cpos-engine-zero", title="Fix readme")
    rejected = reject_github_pr_dry_run(store, second["task_id"], reason="no")
    assert rejected["ok"] is True
    assert rejected["pr_created"] is False


def test_github_pr_real_creation_disabled(tmp_path):
    store = TaskTapeStore(tmp_path / "tasks.jsonl")
    result = create_github_pr_dry_run(store, repo="kagioneko/cpos-engine-zero", title="x", dry_run=False)
    assert result["ok"] is False
    assert result["error"] == "real_github_pr_creation_disabled"
