import json
import subprocess
import sys
from pathlib import Path

from cpos.handoff_inbox import approve_handoff, handoff_inbox, reject_handoff
from cpos.pointer_os import PointerManager


def create_handoff(manager, pointer_id="ptr://handoff/test"):
    return manager.create_pointer(
        pointer_id=pointer_id,
        context_type="handoff_summary",
        summary="Imported CPOS handoff",
        source="handoff:AgentA",
        location="handoff://abc123",
        priority=0.55,
        trust_score=0.35,
        retrieval_rule="handoff_review_required",
        metadata={"bundle_sha256": "abc123", "counts": {"tasks": 1}, "signature": {"ok": True}},
    )


def test_handoff_inbox_lists_approves_and_rejects(tmp_path):
    manager = PointerManager(tmp_path / "pointers.jsonl", tmp_path / "audit.jsonl")
    pointer = create_handoff(manager)

    pending = handoff_inbox(manager)
    assert len(pending) == 1
    assert pending[0]["pointer_id"] == pointer.pointer_id
    assert pending[0]["review_status"] == "pending"
    assert "counts" in pending[0]["metadata"]

    approved = approve_handoff(manager, pointer.pointer_id, reviewer="Tester", reason="looks_good")
    assert approved is not None
    assert approved.retrieval_rule == "handoff_approved"
    assert approved.metadata["handoff_review"]["status"] == "approved"
    assert approved.trust_score >= 0.75
    assert handoff_inbox(manager, status="pending") == []
    assert handoff_inbox(manager, status="approved")[0]["pointer_id"] == pointer.pointer_id

    second = create_handoff(manager, "ptr://handoff/test2")
    rejected = reject_handoff(manager, second.pointer_id, reviewer="Tester", reason="stale")
    assert rejected is not None
    assert rejected.status == "invalidated"
    assert rejected.retrieval_rule == "handoff_rejected"
    assert rejected.invalidated_reason == "user_request"
    assert handoff_inbox(manager, status="rejected")[0]["pointer_id"] == second.pointer_id


def test_handoff_inbox_cli(tmp_path):
    manager = PointerManager(tmp_path / "pointers.jsonl", tmp_path / "audit.jsonl")
    pointer = create_handoff(manager)
    root = Path(__file__).resolve().parents[1]
    common = ["--pointer-path", str(tmp_path / "pointers.jsonl"), "--pointer-audit-path", str(tmp_path / "audit.jsonl")]

    listed = subprocess.run([sys.executable, "-m", "cpos.handoff_inbox", *common, "list"], cwd=str(root), check=True, capture_output=True, text=True)
    assert json.loads(listed.stdout)["count"] if "count" in json.loads(listed.stdout) else len(json.loads(listed.stdout)["handoffs"]) == 1

    approved = subprocess.run([sys.executable, "-m", "cpos.handoff_inbox", *common, "approve", pointer.pointer_id, "--reviewer", "CLI"], cwd=str(root), check=True, capture_output=True, text=True)
    assert json.loads(approved.stdout)["ok"] is True
    assert PointerManager(tmp_path / "pointers.jsonl", tmp_path / "audit.jsonl").load()[0].retrieval_rule == "handoff_approved"
