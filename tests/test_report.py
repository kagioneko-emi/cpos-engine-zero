import json

from cpos.pointer_os import PointerManager
from generate_report import generate_hackathon_report, pointer_governance_events, pointer_summary


def test_pointer_summary_counts_status_type_and_trust(tmp_path):
    manager = PointerManager(tmp_path / "pointers.jsonl")
    active = manager.create_pointer(
        context_type="finding",
        summary="unsafe eval finding",
        source="unit_test",
        location="workspace/app.py:1",
        priority=0.9,
        trust_score=0.8,
    )
    invalidated = manager.create_pointer(
        context_type="spec",
        summary="old spec",
        source="unit_test",
        location="docs/old.md",
        priority=0.4,
        trust_score=0.6,
    )
    manager.invalidate_pointer(invalidated.pointer_id, reason="outdated")

    summary = pointer_summary(manager.load())

    assert summary["total"] == 2
    assert summary["active"] == 1
    assert summary["invalidated"] == 1
    assert summary["finding_count"] == 1
    assert summary["by_type"] == {"finding": 1, "spec": 1}
    assert round(summary["avg_trust"], 2) == 0.70
    assert summary["top_findings"][0].pointer_id == active.pointer_id


def test_generate_report_renders_pointer_os_summary(tmp_path):
    audit_path = tmp_path / "cpos" / "audit_log.jsonl"
    pointer_path = tmp_path / "cpos" / "pointers.jsonl"
    output_path = tmp_path / "report.html"
    audit_path.parent.mkdir()
    audit_path.write_text(
        json.dumps(
            {
                "target": "workspace/app.py",
                "rule_findings": [
                    {
                        "severity": "high",
                        "title": "unsafe eval",
                        "line": 1,
                        "content": "eval(user_input)",
                    }
                ],
                "sandbox_lint": {"exit_code": 0, "stdout": "All checks passed!\n"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    manager = PointerManager(pointer_path)
    pointer = manager.create_pointer(
        context_type="finding",
        summary="unsafe eval in app.py:1",
        source="unit_test",
        location="workspace/app.py:1",
        priority=0.9,
        trust_score=0.82,
    )

    generate_hackathon_report(str(audit_path), output_path=str(output_path), pointer_path=str(pointer_path))

    html = output_path.read_text(encoding="utf-8")
    assert "Context Pointer OS" in html
    assert "Memory Operating Layer" in html
    assert "Total Pointers" in html
    assert "Avg Trust" in html
    assert pointer.pointer_id in html
    assert "unsafe eval in app.py:1" in html
    assert "VERIFIED STABLE" in html


def test_pointer_governance_events_filters_and_sorts():
    events = [
        {"event": "context_retrieval", "timestamp": "2026-05-27T00:00:00Z"},
        {"event": "trust_score_updated", "pointer_id": "ptr://a", "score": 0.8, "timestamp": "2026-05-27T00:01:00Z"},
        {"event": "pointer_exchanged", "pointer_id": "ptr://b", "timestamp": "2026-05-27T00:02:00Z"},
    ]

    result = pointer_governance_events(events)

    assert [event["event"] for event in result] == ["pointer_exchanged", "trust_score_updated"]


def test_generate_report_renders_pointer_governance_events(tmp_path):
    audit_path = tmp_path / "cpos" / "audit_log.jsonl"
    pointer_path = tmp_path / "cpos" / "pointers.jsonl"
    output_path = tmp_path / "report.html"
    audit_path.parent.mkdir()
    pointer_id = "ptr://finding/python/PY-MISTAKE-0002/workspace-app.py:1"
    audit_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event": "trust_score_updated",
                        "pointer_id": pointer_id,
                        "score": 0.95,
                        "reason": "user_confirmed",
                        "timestamp": "2026-05-27T00:01:00Z",
                    }
                ),
                json.dumps(
                    {
                        "event": "pointer_exchanged",
                        "pointer_id": pointer_id,
                        "from_agent": "CodingAgent",
                        "to_agent": "AuditAgent",
                        "purpose": "audit_required",
                        "access_level": "internal",
                        "timestamp": "2026-05-27T00:02:00Z",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    PointerManager(pointer_path).create_pointer(
        context_type="finding",
        summary="unsafe eval in app.py:1",
        source="unit_test",
        location="workspace/app.py:1",
        priority=0.9,
        trust_score=0.95,
        pointer_id=pointer_id,
    )

    generate_hackathon_report(str(audit_path), output_path=str(output_path), pointer_path=str(pointer_path))

    html = output_path.read_text(encoding="utf-8")
    assert "Pointer Governance Events" in html
    assert "Trust & Agent Exchange Audit" in html
    assert "trust_score_updated" in html
    assert "score=0.95 reason=user_confirmed" in html
    assert "pointer_exchanged" in html
    assert "CodingAgent → AuditAgent" in html
    assert "purpose=audit_required access=internal" in html


def test_generate_report_renders_task_tape_summary(tmp_path):
    audit_path = tmp_path / "cpos" / "audit_log.jsonl"
    pointer_path = tmp_path / "cpos" / "pointers.jsonl"
    tape_path = tmp_path / "tapes" / "task_runs.jsonl"
    checkpoint_path = tmp_path / "tapes" / "task_checkpoints.jsonl"
    output_path = tmp_path / "report.html"
    audit_path.parent.mkdir()
    audit_path.write_text("", encoding="utf-8")
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text("", encoding="utf-8")

    from cpos.task_tape import TaskTapeStore

    target = tmp_path / "workspace" / "app.py"
    target.parent.mkdir()
    target.write_text("old\n", encoding="utf-8")
    store = TaskTapeStore(tape_path, checkpoint_path)
    task_id = store.create_task(target=str(target), action="unit_test")
    checkpoint = store.create_checkpoint(task_id=task_id, target=str(target), content="old\n")
    store.append_event(task_id=task_id, event="verification_completed", target=str(target), checkpoint_id=checkpoint.checkpoint_id, status="success")

    generate_hackathon_report(
        str(audit_path),
        output_path=str(output_path),
        pointer_path=str(pointer_path),
        task_tape_path=str(tape_path),
        task_checkpoint_path=str(checkpoint_path),
    )

    html = output_path.read_text(encoding="utf-8")
    assert "Task Tape" in html
    assert "Append-only Execution & Rollback" in html
    assert "Recent Task Events" in html
    assert "verification_completed" in html
    assert task_id in html
    assert checkpoint.checkpoint_id in html


def test_generate_report_renders_security_audit_summary(tmp_path):
    audit_path = tmp_path / "cpos" / "audit_log.jsonl"
    pointer_path = tmp_path / "cpos" / "pointers.jsonl"
    security_audit_path = tmp_path / "cpos" / "security_audit.jsonl"
    output_path = tmp_path / "report.html"
    audit_path.parent.mkdir()
    audit_path.write_text("", encoding="utf-8")
    pointer_path.write_text("", encoding="utf-8")
    security_audit_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_id": "sec_1",
                        "event": "auth_decision",
                        "timestamp": "2026-05-27T00:00:00Z",
                        "actor": "AuditTester",
                        "method": "GET",
                        "path": "/tasks",
                        "decision": "allowed",
                        "status_code": 200,
                        "required_scope": "read:tasks",
                        "metadata": {},
                    }
                ),
                json.dumps(
                    {
                        "event_id": "sec_2",
                        "event": "security_mutation",
                        "timestamp": "2026-05-27T00:01:00Z",
                        "actor": "RollbackBot",
                        "method": "POST",
                        "path": "/tasks/rollback-latest",
                        "decision": "rollback_applied",
                        "status_code": 200,
                        "required_scope": "write:rollback",
                        "metadata": {"checkpoint_id": "chk_123"},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    generate_hackathon_report(
        str(audit_path),
        output_path=str(output_path),
        pointer_path=str(pointer_path),
        security_audit_path=str(security_audit_path),
    )

    html = output_path.read_text(encoding="utf-8")
    assert "Security Audit Trail" in html
    assert "Auth, Scope & Mutation Ledger" in html
    assert "AuditTester" in html
    assert "RollbackBot" in html
    assert "rollback_applied" in html
    assert "write:rollback" in html


def test_generate_report_renders_integrity_summary(tmp_path):
    audit_path = tmp_path / "cpos" / "audit_log.jsonl"
    pointer_path = tmp_path / "cpos" / "pointers.jsonl"
    security_audit_path = tmp_path / "cpos" / "security_audit.jsonl"
    tape_path = tmp_path / "tapes" / "task_runs.jsonl"
    checkpoint_path = tmp_path / "tapes" / "task_checkpoints.jsonl"
    output_path = tmp_path / "report.html"
    from cpos.hash_chain import append_chained_jsonl
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text("", encoding="utf-8")
    append_chained_jsonl(audit_path, {"event": "pointer_created", "pointer_id": "ptr://x", "timestamp": "2026-05-27T00:00:00Z"})
    append_chained_jsonl(security_audit_path, {"event": "auth_decision", "actor": "Tester", "method": "GET", "path": "/tasks", "decision": "allowed", "timestamp": "2026-05-27T00:00:00Z"})
    from cpos.task_tape import TaskTapeStore
    store = TaskTapeStore(tape_path, checkpoint_path)
    task_id = store.create_task(target="workspace/app.py", action="unit_test")
    store.create_checkpoint(task_id=task_id, target="workspace/app.py", content="old\n")

    generate_hackathon_report(
        str(audit_path),
        output_path=str(output_path),
        pointer_path=str(pointer_path),
        task_tape_path=str(tape_path),
        task_checkpoint_path=str(checkpoint_path),
        security_audit_path=str(security_audit_path),
    )

    html = output_path.read_text(encoding="utf-8")
    assert "Tamper-evident Integrity" in html
    assert "Hash-chained JSONL Ledgers" in html
    assert "pointer_audit" in html
    assert "security_audit" in html
    assert "task_events" in html
