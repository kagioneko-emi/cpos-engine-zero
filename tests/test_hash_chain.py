import json

from cpos.hash_chain import append_chained_jsonl, verify_hash_chain
from cpos.pointer_os import PointerManager
from cpos.security_audit import SecurityAuditLog
from cpos.task_tape import TaskTapeStore


def test_append_chained_jsonl_verifies_and_detects_tamper(tmp_path):
    path = tmp_path / "ledger.jsonl"
    append_chained_jsonl(path, {"event": "one", "value": 1})
    append_chained_jsonl(path, {"event": "two", "value": 2})

    ok = verify_hash_chain(path)
    assert ok["ok"] is True
    assert ok["verified_count"] == 2
    assert ok["legacy_prefix_count"] == 0

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows[0]["value"] = 999
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")

    broken = verify_hash_chain(path)
    assert broken["ok"] is False
    assert broken["error"] == "row_hash_mismatch"
    assert broken["line"] == 1


def test_hash_chain_allows_legacy_prefix_then_verifies_new_rows(tmp_path):
    path = tmp_path / "ledger.jsonl"
    path.write_text(json.dumps({"event": "legacy"}) + "\n", encoding="utf-8")
    append_chained_jsonl(path, {"event": "new"})

    result = verify_hash_chain(path)

    assert result["ok"] is True
    assert result["legacy_prefix_count"] == 1
    assert result["verified_count"] == 1


def test_task_tape_security_audit_and_pointer_audit_are_chained(tmp_path):
    tape = TaskTapeStore(tmp_path / "tapes" / "task_runs.jsonl", tmp_path / "tapes" / "task_checkpoints.jsonl")
    task_id = tape.create_task(target="workspace/app.py", action="unit_test")
    tape.create_checkpoint(task_id=task_id, target="workspace/app.py", content="old\n")
    task_integrity = tape.verify_integrity()
    assert task_integrity["events"]["ok"] is True
    assert task_integrity["checkpoints"]["ok"] is True
    assert task_integrity["events"]["verified_count"] == 2

    security = SecurityAuditLog(tmp_path / "cpos" / "security_audit.jsonl")
    security.append(event="auth_decision", actor="Tester", method="GET", path="/tasks", decision="allowed")
    assert security.verify_integrity()["ok"] is True

    pointer_manager = PointerManager(tmp_path / "cpos" / "pointers.jsonl", tmp_path / "cpos" / "audit_log.jsonl")
    pointer_manager.create_pointer(context_type="spec", summary="spec", source="unit", location="docs/spec.md")
    assert pointer_manager.verify_audit_integrity()["ok"] is True
