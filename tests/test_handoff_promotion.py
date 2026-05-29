import json
import subprocess
import sys
from pathlib import Path

import pytest

from cpos.handoff_inbox import approve_handoff
from cpos.handoff_promotion import build_promotion_plan, create_promotion_pointer
from cpos.pointer_os import PointerManager
from tests.test_handoff_inbox import create_handoff


def test_promotion_requires_approved_handoff(tmp_path):
    manager = PointerManager(tmp_path / "pointers.jsonl", tmp_path / "audit.jsonl")
    pointer = create_handoff(manager)
    with pytest.raises(ValueError, match="handoff_not_approved"):
        build_promotion_plan(pointer)

    approved = approve_handoff(manager, pointer.pointer_id, reviewer="Tester")
    plan = build_promotion_plan(approved)
    assert plan["schema"] == "cpos.handoff_promotion_plan.v1"
    assert plan["source_pointer_id"] == pointer.pointer_id
    assert "raw_handoff_body" in plan["blocked_inputs"]
    assert "checkpoint_contents" in plan["blocked_inputs"]
    assert plan["task_candidates"][0]["requires_human_approval"] is True
    raw = json.dumps(plan, ensure_ascii=False)
    assert "secret_value" in raw  # blocked name only
    assert "SECRET" not in raw


def test_create_promotion_pointer_is_review_gated(tmp_path):
    manager = PointerManager(tmp_path / "pointers.jsonl", tmp_path / "audit.jsonl")
    pointer = create_handoff(manager)
    approve_handoff(manager, pointer.pointer_id, reviewer="Tester")

    promoted = create_promotion_pointer(manager, pointer.pointer_id, reviewer="Promoter", reason="continue")
    assert promoted is not None
    assert promoted.context_type == "handoff_promotion_plan"
    assert promoted.retrieval_rule == "handoff_promotion_review_required"
    assert promoted.dependencies == [pointer.pointer_id]
    assert promoted.metadata["plan"]["source_pointer_id"] == pointer.pointer_id


def test_handoff_promotion_cli(tmp_path):
    manager = PointerManager(tmp_path / "pointers.jsonl", tmp_path / "audit.jsonl")
    pointer = create_handoff(manager)
    approve_handoff(manager, pointer.pointer_id, reviewer="Tester")
    root = Path(__file__).resolve().parents[1]
    common = ["--pointer-path", str(tmp_path / "pointers.jsonl"), "--pointer-audit-path", str(tmp_path / "audit.jsonl")]

    planned = subprocess.run([sys.executable, "-m", "cpos.handoff_promotion", *common, "plan", pointer.pointer_id], cwd=str(root), check=True, capture_output=True, text=True)
    assert json.loads(planned.stdout)["plan"]["source_pointer_id"] == pointer.pointer_id

    promoted = subprocess.run([sys.executable, "-m", "cpos.handoff_promotion", *common, "promote", pointer.pointer_id, "--reviewer", "CLI"], cwd=str(root), check=True, capture_output=True, text=True)
    assert json.loads(promoted.stdout)["pointer"]["context_type"] == "handoff_promotion_plan"
