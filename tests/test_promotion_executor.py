import json
import subprocess
import sys
from pathlib import Path

from cpos.handoff_inbox import approve_handoff
from cpos.handoff_promotion import create_promotion_pointer
from cpos.pointer_os import PointerManager
from cpos.promotion_executor import (
    approve_execution_review,
    create_execution_review,
    pending_execution_reviews,
    reject_execution_review,
)
from cpos.task_tape import TaskTapeStore
from tests.test_handoff_inbox import create_handoff


def approved_promotion(tmp_path):
    manager = PointerManager(tmp_path / "pointers.jsonl", tmp_path / "audit.jsonl")
    handoff = create_handoff(manager)
    approve_handoff(manager, handoff.pointer_id, reviewer="Tester")
    promotion = create_promotion_pointer(manager, handoff.pointer_id, reviewer="Promoter")
    return manager, promotion


def test_create_and_approve_execution_review(tmp_path):
    manager, promotion = approved_promotion(tmp_path)
    store = TaskTapeStore(tmp_path / "tasks.jsonl", tmp_path / "checkpoints.jsonl")

    result = create_execution_review(manager, store, promotion.pointer_id, requester="Tester", reason="resume")
    assert result["ok"] is True
    assert result["review"]["event"] == "review_required"
    assert result["review"]["payload"]["review_type"] == "handoff_promotion_execution"
    raw = json.dumps(result, ensure_ascii=False)
    assert "proposed_code" in raw  # blocked input name only
    assert "checkpoint_content" in raw  # blocked input name only

    pending = pending_execution_reviews(store)
    assert len(pending) == 1
    assert pending[0]["task_id"] == result["task_id"]

    approved = approve_execution_review(store, result["task_id"], approver="Human")
    assert approved["ok"] is True
    assert pending_execution_reviews(store) == []
    assert any(event.event == "handoff_promotion_execution_ready" for event in store.events())


def test_reject_execution_review(tmp_path):
    manager, promotion = approved_promotion(tmp_path)
    store = TaskTapeStore(tmp_path / "tasks.jsonl", tmp_path / "checkpoints.jsonl")
    result = create_execution_review(manager, store, promotion.pointer_id)
    rejected = reject_execution_review(store, result["task_id"], reason="not_now")
    assert rejected["ok"] is True
    assert rejected["status"] == "rejected"
    assert pending_execution_reviews(store) == []


def test_promotion_executor_cli(tmp_path):
    manager, promotion = approved_promotion(tmp_path)
    root = Path(__file__).resolve().parents[1]
    common = [
        "--pointer-path", str(tmp_path / "pointers.jsonl"),
        "--pointer-audit-path", str(tmp_path / "audit.jsonl"),
        "--task-tape-path", str(tmp_path / "tasks.jsonl"),
        "--task-checkpoint-path", str(tmp_path / "checkpoints.jsonl"),
    ]
    created = subprocess.run([sys.executable, "-m", "cpos.promotion_executor", *common, "create-review", promotion.pointer_id], cwd=str(root), check=True, capture_output=True, text=True)
    task_id = json.loads(created.stdout)["task_id"]
    listed = subprocess.run([sys.executable, "-m", "cpos.promotion_executor", *common, "list"], cwd=str(root), check=True, capture_output=True, text=True)
    assert json.loads(listed.stdout)["count"] == 1
    approved = subprocess.run([sys.executable, "-m", "cpos.promotion_executor", *common, "approve", task_id], cwd=str(root), check=True, capture_output=True, text=True)
    assert json.loads(approved.stdout)["ok"] is True
