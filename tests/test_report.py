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


def test_generate_report_renders_security_profile_validation(tmp_path, monkeypatch):
    audit_path = tmp_path / "cpos" / "audit_log.jsonl"
    pointer_path = tmp_path / "cpos" / "pointers.jsonl"
    output_path = tmp_path / "report.html"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("", encoding="utf-8")
    pointer_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("CPOS_SECURITY_PROFILE", "hardened")
    monkeypatch.setenv("CPOS_ENFORCE_HTTPS", "true")
    monkeypatch.setenv("CPOS_REQUIRE_API_AUTH", "true")
    monkeypatch.setenv("CPOS_REQUIRE_HMAC_AUTH", "true")
    monkeypatch.setenv("CPOS_REQUIRE_CLIENT_CERT", "true")
    monkeypatch.setenv("CPOS_SANDBOX_MODE", "strict")
    monkeypatch.setenv("CPOS_RATE_LIMIT_ENABLED", "true")
    monkeypatch.delenv("CPOS_API_HMAC_SECRET_FILE", raising=False)
    monkeypatch.delenv("CPOS_API_HMAC_KEY_REGISTRY_FILE", raising=False)
    monkeypatch.delenv("CPOS_CLIENT_CERT_FINGERPRINTS_FILE", raising=False)

    generate_hackathon_report(str(audit_path), output_path=str(output_path), pointer_path=str(pointer_path))

    html = output_path.read_text(encoding="utf-8")
    assert "Security Profile Validation" in html
    assert "Posture: hardened" in html
    assert "hmac_secret_or_registry_configured" in html
    assert "client_cert_fingerprints_configured" in html


def test_generate_report_renders_secret_inventory_summary(tmp_path):
    audit_path = tmp_path / "cpos" / "audit_log.jsonl"
    pointer_path = tmp_path / "cpos" / "pointers.jsonl"
    inventory_path = tmp_path / "cpos" / "secret_inventory.jsonl"
    output_path = tmp_path / "report.html"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("", encoding="utf-8")
    pointer_path.write_text("", encoding="utf-8")
    from cpos.secret_inventory import add_artifact, mark_status
    add_artifact(inventory_path, artifact_path="certs/key.pem", artifact_type="tls_private_key", vault_path="secret/cpos/tls", field="private_key")
    mark_status(inventory_path, artifact_path="certs/key.pem", status="stored_in_vault")

    generate_hackathon_report(str(audit_path), output_path=str(output_path), pointer_path=str(pointer_path), secret_inventory_path=str(inventory_path))

    html = output_path.read_text(encoding="utf-8")
    assert "Secret Inventory" in html
    assert "Vault Migration Metadata" in html
    assert "certs/key.pem" in html
    assert "stored_in_vault" in html


def test_generate_report_renders_handoff_queue_summary(tmp_path):
    audit_path = tmp_path / "cpos" / "audit_log.jsonl"
    pointer_path = tmp_path / "cpos" / "pointers.jsonl"
    tape_path = tmp_path / "tapes" / "task_runs.jsonl"
    checkpoint_path = tmp_path / "tapes" / "task_checkpoints.jsonl"
    output_path = tmp_path / "report.html"
    audit_path.parent.mkdir()
    audit_path.write_text("", encoding="utf-8")
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text(
        "\n".join(
            [
                json.dumps({
                    "pointer_id": "ptr://handoff/a",
                    "context_type": "handoff_summary",
                    "summary": "pending handoff",
                    "source": "handoff:AgentA",
                    "location": "handoff://a",
                    "priority": 0.5,
                    "trust_score": 0.4,
                    "retrieval_rule": "handoff_review_required",
                    "status": "active",
                    "metadata": {"counts": {"tasks": 1, "pointers": 2}, "signature": {"ok": True}},
                }),
                json.dumps({
                    "pointer_id": "ptr://handoff/p",
                    "context_type": "handoff_promotion_plan",
                    "summary": "promotion",
                    "source": "handoff_promotion_rules",
                    "location": "handoff-promotion://abc",
                    "priority": 0.6,
                    "trust_score": 0.6,
                    "retrieval_rule": "handoff_promotion_review_required",
                    "status": "active",
                    "metadata": {"plan": {"schema": "cpos.handoff_promotion_plan.v1"}},
                }),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    from cpos.task_tape import TaskTapeStore

    store = TaskTapeStore(tape_path, checkpoint_path)
    task_id = store.create_task(target="ptr://handoff/p", action="handoff_promotion_execution_review")
    store.append_event(task_id=task_id, event="review_required", target="ptr://handoff/p", status="pending_review", payload={"review_type": "handoff_promotion_execution", "promotion_pointer_id": "ptr://handoff/p"})
    store.append_event(task_id=task_id, event="handoff_promotion_execution_ready", target="ptr://handoff/p", status="ready", payload={"review_type": "handoff_promotion_execution", "promotion_pointer_id": "ptr://handoff/p"})
    resume_task_id = store.create_task(target="task_123", action="resume")
    store.append_event(task_id=resume_task_id, event="review_required", target="task_123", status="pending_review", payload={"review_type": "execution_resume_action", "proposal": {"schema": "cpos.execution_resume_proposal.v1", "proposals": [{"title": "Inspect"}]}})

    generate_hackathon_report(
        str(audit_path),
        output_path=str(output_path),
        pointer_path=str(pointer_path),
        task_tape_path=str(tape_path),
        task_checkpoint_path=str(checkpoint_path),
    )

    html = output_path.read_text(encoding="utf-8")
    assert "Handoff Queue Overview" in html
    assert "Pending Handoffs" in html
    assert "Execution Reviews" in html
    assert "Resume Reviews" in html
    assert "ptr://handoff/a" in html
    assert "task_123" in html


def test_generate_report_renders_footprint_summary(tmp_path):
    audit_path = tmp_path / "cpos" / "audit_log.jsonl"
    pointer_path = tmp_path / "cpos" / "pointers.jsonl"
    tape_path = tmp_path / "tapes" / "task_runs.jsonl"
    checkpoint_path = tmp_path / "tapes" / "task_checkpoints.jsonl"
    output_path = tmp_path / "report.html"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("", encoding="utf-8")
    manager = PointerManager(pointer_path)
    manager.create_pointer(context_type="spec", summary="demo", source="unit", location="demo.md")
    from cpos.task_tape import TaskTapeStore
    TaskTapeStore(tape_path, checkpoint_path).create_task(target="demo", action="unit")

    generate_hackathon_report(
        str(audit_path),
        output_path=str(output_path),
        pointer_path=str(pointer_path),
        task_tape_path=str(tape_path),
        task_checkpoint_path=str(checkpoint_path),
    )

    html = output_path.read_text(encoding="utf-8")
    assert "Lightweight Footprint" in html
    assert "Pointer/Tape Context Economy" in html
    assert "relationship_memory_full_logs_in_context" in html
    assert "secrets_included" in html


def test_generate_report_renders_rate_limit_backend_summary(tmp_path, monkeypatch):
    audit_path = tmp_path / "cpos" / "audit_log.jsonl"
    pointer_path = tmp_path / "cpos" / "pointers.jsonl"
    output_path = tmp_path / "report.html"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("", encoding="utf-8")
    pointer_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("CPOS_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("CPOS_RATE_LIMIT_BACKEND", "file")
    monkeypatch.setenv("CPOS_RATE_LIMIT_STORE_PATH", str(tmp_path / "rate_limit.json"))

    generate_hackathon_report(str(audit_path), output_path=str(output_path), pointer_path=str(pointer_path))

    html = output_path.read_text(encoding="utf-8")
    assert "Rate Limit Backend" in html
    assert "Request Throttling Posture" in html
    assert "file" in html
    assert "Authorization headers" in html


def test_generate_report_renders_handoff_flow_graph_widget(tmp_path):
    audit_path = tmp_path / "cpos" / "audit_log.jsonl"
    pointer_path = tmp_path / "cpos" / "pointers.jsonl"
    tape_path = tmp_path / "tapes" / "task_runs.jsonl"
    checkpoint_path = tmp_path / "tapes" / "task_checkpoints.jsonl"
    output_path = tmp_path / "report.html"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("", encoding="utf-8")

    from cpos.handoff_inbox import approve_handoff
    from cpos.handoff_promotion import create_promotion_pointer
    from cpos.promotion_executor import approve_execution_review, create_execution_review
    from cpos.resume_planner import create_resume_proposal_review
    from cpos.task_tape import TaskTapeStore

    manager = PointerManager(pointer_path)
    handoff = manager.create_pointer(
        pointer_id="ptr://handoff/report",
        context_type="handoff_summary",
        summary="report handoff",
        source="test",
        location="handoff://report",
        retrieval_rule="handoff_review_required",
        metadata={"counts": {"tasks": 1}, "signature": {"ok": True}},
    )
    approve_handoff(manager, handoff.pointer_id, reviewer="Tester")
    promotion = create_promotion_pointer(manager, handoff.pointer_id, reviewer="Promoter")
    store = TaskTapeStore(tape_path, checkpoint_path)
    execution = create_execution_review(manager, store, promotion.pointer_id)
    approve_execution_review(store, execution["task_id"])
    create_resume_proposal_review(store, execution["task_id"])

    generate_hackathon_report(
        str(audit_path),
        output_path=str(output_path),
        pointer_path=str(pointer_path),
        task_tape_path=str(tape_path),
        task_checkpoint_path=str(checkpoint_path),
    )

    html = output_path.read_text(encoding="utf-8")
    assert "Handoff Flow Graph" in html
    assert "Handoff → Promotion → Execution → Resume" in html
    assert "ptr://handoff/report" in html
    assert promotion.pointer_id in html
    assert execution["task_id"] in html
    assert "Raw handoff bodies" in html


def test_generate_report_renders_mcp_connector_registry_summary(tmp_path):
    audit_path = tmp_path / "cpos" / "audit_log.jsonl"
    pointer_path = tmp_path / "cpos" / "pointers.jsonl"
    mcp_registry_path = tmp_path / "cpos" / "mcp_connectors.json"
    mcp_audit_path = tmp_path / "cpos" / "mcp_audit.jsonl"
    mcp_review_path = tmp_path / "cpos" / "mcp_reviews.jsonl"
    output_path = tmp_path / "report.html"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("", encoding="utf-8")
    pointer_path.write_text("", encoding="utf-8")

    from cpos.mcp_registry import MCPRegistry

    registry = MCPRegistry(mcp_registry_path, mcp_audit_path, mcp_review_path)
    pending = registry.submit_review(
        {
            "connector_id": "mcp://docs/pending",
            "name": "Pending Docs MCP",
            "transport": "https",
            "url": "https://mcp.example.test/pending",
            "allowed_tools": ["docs.pending"],
            "requires_human_approval": True,
            "env_secret_files": {"DOCS_TOKEN_FILE": str(tmp_path / "pending_token_file")},
        },
        actor="Reporter",
    )
    assert pending["ok"] is True
    result = registry.register(
        {
            "connector_id": "mcp://docs/search",
            "name": "Docs Search MCP",
            "transport": "https",
            "url": "https://mcp.example.test/docs",
            "allowed_tools": ["docs.search"],
            "blocked_tools": ["docs.write"],
            "requires_human_approval": True,
            "env_secret_files": {"DOCS_TOKEN_FILE": str(tmp_path / "docs_token_file")},
        },
        confirm=True,
    )
    assert result["ok"] is True

    generate_hackathon_report(
        str(audit_path),
        output_path=str(output_path),
        pointer_path=str(pointer_path),
        mcp_registry_path=str(mcp_registry_path),
        mcp_audit_path=str(mcp_audit_path),
        mcp_review_path=str(mcp_review_path),
    )

    html = output_path.read_text(encoding="utf-8")
    assert "MCP Connector Registry" in html
    assert "Text-first Tool Governance" in html
    assert "mcp://docs/search" in html
    assert "docs.search" in html
    assert "Remote URLs must be HTTPS" in html
    assert "raw_values_hidden=true" in html
    assert "Pending MCP Reviews" in html
    assert "mcp://docs/pending" in html
    assert "docs.pending" in html


def test_generate_report_renders_mcp_execution_adapter_summary(tmp_path):
    audit_path = tmp_path / "cpos" / "audit_log.jsonl"
    pointer_path = tmp_path / "cpos" / "pointers.jsonl"
    mcp_registry_path = tmp_path / "cpos" / "mcp_connectors.json"
    mcp_audit_path = tmp_path / "cpos" / "mcp_audit.jsonl"
    mcp_review_path = tmp_path / "cpos" / "mcp_reviews.jsonl"
    tape_path = tmp_path / "tapes" / "task_runs.jsonl"
    checkpoint_path = tmp_path / "tapes" / "task_checkpoints.jsonl"
    output_path = tmp_path / "report.html"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("", encoding="utf-8")
    pointer_path.write_text("", encoding="utf-8")

    from cpos.mcp_execution import request_mcp_execution
    from cpos.mcp_registry import MCPRegistry
    from cpos.task_tape import TaskTapeStore

    registry = MCPRegistry(mcp_registry_path, mcp_audit_path, mcp_review_path)
    registry.register(
        {
            "connector_id": "mcp://docs/search",
            "name": "Docs Search MCP",
            "transport": "https",
            "url": "https://mcp.example.test/docs",
            "allowed_tools": ["docs.search"],
            "requires_human_approval": True,
            "env_secret_files": {"DOCS_TOKEN_FILE": str(tmp_path / "docs_token_file")},
        },
        confirm=True,
    )
    store = TaskTapeStore(tape_path, checkpoint_path)
    result = request_mcp_execution(registry, store, connector_id="mcp://docs/search", tool_name="docs.search", arguments={"query": "SENSITIVE_QUERY_VALUE_X"})
    assert result["ok"] is True

    generate_hackathon_report(
        str(audit_path),
        output_path=str(output_path),
        pointer_path=str(pointer_path),
        task_tape_path=str(tape_path),
        task_checkpoint_path=str(checkpoint_path),
        mcp_registry_path=str(mcp_registry_path),
        mcp_audit_path=str(mcp_audit_path),
        mcp_review_path=str(mcp_review_path),
    )

    html = output_path.read_text(encoding="utf-8")
    assert "MCP Execution Adapter" in html
    assert "Dry-run / Metadata-only Tool Gate" in html
    assert "mcp://docs/search" in html
    assert "docs.search" in html
    assert "Args Fingerprint" in html
    assert "SENSITIVE_QUERY_VALUE_X" not in html
    assert "It does not launch MCP servers or execute tools" in html


def test_generate_report_renders_github_pr_dry_run_summary(tmp_path):
    audit_path = tmp_path / "cpos" / "audit_log.jsonl"
    pointer_path = tmp_path / "cpos" / "pointers.jsonl"
    tape_path = tmp_path / "tapes" / "task_runs.jsonl"
    checkpoint_path = tmp_path / "tapes" / "task_checkpoints.jsonl"
    output_path = tmp_path / "report.html"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("", encoding="utf-8")
    pointer_path.write_text("", encoding="utf-8")

    from cpos.github_pr_flow import create_github_pr_dry_run
    from cpos.task_tape import TaskTapeStore

    store = TaskTapeStore(tape_path, checkpoint_path)
    result = create_github_pr_dry_run(
        store,
        repo="kagioneko/cpos-engine-zero",
        title="Fix docs",
        summary="RAW_SUMMARY_SHOULD_NOT_APPEAR",
        files=["README.md"],
    )
    assert result["ok"] is True

    generate_hackathon_report(
        str(audit_path),
        output_path=str(output_path),
        pointer_path=str(pointer_path),
        task_tape_path=str(tape_path),
        task_checkpoint_path=str(checkpoint_path),
    )

    html = output_path.read_text(encoding="utf-8")
    assert "GitHub PR Dry-run" in html
    assert "Review-gated PR Planning" in html
    assert "kagioneko/cpos-engine-zero" in html
    assert "README.md" in html
    assert "RAW_SUMMARY_SHOULD_NOT_APPEAR" not in html
    assert "PR Created" in html


def test_generate_report_renders_sandbox_patch_plan_summary(tmp_path):
    audit_path = tmp_path / "cpos" / "audit_log.jsonl"
    pointer_path = tmp_path / "cpos" / "pointers.jsonl"
    tape_path = tmp_path / "tapes" / "task_runs.jsonl"
    checkpoint_path = tmp_path / "tapes" / "task_checkpoints.jsonl"
    output_path = tmp_path / "report.html"
    audit_path.parent.mkdir()
    audit_path.write_text("", encoding="utf-8")
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text("", encoding="utf-8")

    from cpos.github_diff_review import approve_github_diff_review, create_github_diff_review
    from cpos.github_pr_flow import approve_github_pr_dry_run, create_github_pr_dry_run
    from cpos.sandbox_patch_plan import create_sandbox_patch_plan
    from cpos.task_tape import TaskTapeStore

    store = TaskTapeStore(tape_path, checkpoint_path)
    pr = create_github_pr_dry_run(store, repo="kagioneko/cpos-engine-zero", title="Fix sandbox", files=["README.md"], summary="ctx")
    approve_github_pr_dry_run(store, pr["task_id"], confirm=True)
    diff = create_github_diff_review(store, source_task_id=pr["task_id"], diff_text="+hello\n-old\n", changed_files=["README.md"], validation_commands=["pytest -q tests/test_report.py", "pytest -q tests/test_task_tape.py"])
    approve_github_diff_review(store, diff["task_id"], confirm=True)
    plan = create_sandbox_patch_plan(store, diff_task_id=diff["task_id"])

    generate_hackathon_report(
        str(audit_path),
        output_path=str(output_path),
        pointer_path=str(pointer_path),
        task_tape_path=str(tape_path),
        task_checkpoint_path=str(checkpoint_path),
    )

    html = output_path.read_text(encoding="utf-8")
    assert "Sandbox Patch Plan" in html
    assert "Ephemeral Workspace Validation Gate" in html
    assert plan["task_id"] in html
    assert "patch_applied" in html
    assert "commands_executed" in html


def test_generate_report_renders_sandbox_patch_execution_summary(tmp_path):
    audit_path = tmp_path / "cpos" / "audit_log.jsonl"
    pointer_path = tmp_path / "cpos" / "pointers.jsonl"
    tape_path = tmp_path / "tapes" / "task_runs.jsonl"
    checkpoint_path = tmp_path / "tapes" / "task_checkpoints.jsonl"
    output_path = tmp_path / "report.html"
    audit_path.parent.mkdir()
    audit_path.write_text("", encoding="utf-8")
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text("", encoding="utf-8")

    from cpos.github_diff_review import approve_github_diff_review, create_github_diff_review
    from cpos.github_pr_flow import approve_github_pr_dry_run, create_github_pr_dry_run
    from cpos.sandbox_patch_plan import approve_sandbox_patch_plan, create_sandbox_patch_plan
    from cpos.sandbox_patch_runner import create_sandbox_patch_execution
    from cpos.task_tape import TaskTapeStore

    store = TaskTapeStore(tape_path, checkpoint_path)
    pr = create_github_pr_dry_run(store, repo="kagioneko/cpos-engine-zero", title="Fix sandbox", files=["README.md"], summary="ctx")
    approve_github_pr_dry_run(store, pr["task_id"], confirm=True)
    diff = create_github_diff_review(store, source_task_id=pr["task_id"], diff_text="+hello\n-old\n", changed_files=["README.md"], validation_commands=["pytest -q tests/test_report.py", "pytest -q tests/test_task_tape.py"])
    approve_github_diff_review(store, diff["task_id"], confirm=True)
    patch_plan = create_sandbox_patch_plan(store, diff_task_id=diff["task_id"])
    approve_sandbox_patch_plan(store, patch_plan["task_id"], confirm=True)
    execution = create_sandbox_patch_execution(store, patch_task_id=patch_plan["task_id"])

    generate_hackathon_report(
        str(audit_path),
        output_path=str(output_path),
        pointer_path=str(pointer_path),
        task_tape_path=str(tape_path),
        task_checkpoint_path=str(checkpoint_path),
    )

    html = output_path.read_text(encoding="utf-8")
    assert "Sandbox Patch Execution" in html
    assert "Isolated Runner Readiness" in html
    assert execution["task_id"] in html
    assert "workspace_copied" in html
    assert "commands_executed" in html


def test_generate_report_renders_sandbox_patch_execution_results(tmp_path, monkeypatch):
    audit_path = tmp_path / "cpos" / "audit_log.jsonl"
    pointer_path = tmp_path / "cpos" / "pointers.jsonl"
    tape_path = tmp_path / "tapes" / "task_runs.jsonl"
    checkpoint_path = tmp_path / "tapes" / "task_checkpoints.jsonl"
    output_path = tmp_path / "report.html"
    audit_path.parent.mkdir()
    audit_path.write_text("", encoding="utf-8")
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text("", encoding="utf-8")

    from cpos.github_diff_review import approve_github_diff_review, create_github_diff_review
    from cpos.github_pr_flow import approve_github_pr_dry_run, create_github_pr_dry_run
    from cpos.sandbox_patch_plan import approve_sandbox_patch_plan, create_sandbox_patch_plan
    from cpos.sandbox_patch_runner import approve_sandbox_patch_execution, create_sandbox_patch_execution, execute_sandbox_patch_run
    from cpos.task_tape import TaskTapeStore

    store = TaskTapeStore(tape_path, checkpoint_path)
    pr = create_github_pr_dry_run(store, repo="kagioneko/cpos-engine-zero", title="Fix sandbox", files=["README.md"], summary="ctx")
    approve_github_pr_dry_run(store, pr["task_id"], confirm=True)
    diff = create_github_diff_review(store, source_task_id=pr["task_id"], diff_text="+hello\n-old\n", changed_files=["README.md"], validation_commands=["pytest -q tests/test_report.py", "pytest -q tests/test_task_tape.py"])
    approve_github_diff_review(store, diff["task_id"], confirm=True)
    patch_plan = create_sandbox_patch_plan(store, diff_task_id=diff["task_id"])
    approve_sandbox_patch_plan(store, patch_plan["task_id"], confirm=True)
    execution = create_sandbox_patch_execution(store, patch_task_id=patch_plan["task_id"])
    approve_sandbox_patch_execution(store, execution["task_id"], confirm=True)

    src_root = tmp_path / "src"
    src_root.mkdir()
    (src_root / "README.md").write_text("old\n", encoding="utf-8")
    monkeypatch.setattr("cpos.sandbox_patch_runner._project_root", lambda: src_root)
    monkeypatch.setattr("cpos.sandbox_patch_runner.subprocess.run", lambda *args, **kwargs: type('R', (), {'returncode': 0, 'stdout': 'ok\n', 'stderr': ''})())
    class FakeSandboxRunner:
        def __init__(self, *args, **kwargs):
            self.mode = kwargs.get("mode")
        def run_command(self, target_dir, command):
            return {"stdout": "validated\n", "stderr": "", "exit_code": 0, "sandbox": {"backend": "fake", "mode": self.mode, "isolated": True, "fallback_used": False}}
    monkeypatch.setattr("cpos.sandbox_patch_runner.SandboxRunner", FakeSandboxRunner)
    execute_sandbox_patch_run(store, task_id=execution["task_id"], diff_text="diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n@@\n-old\n+new\n", validation_commands=["pytest -q tests/test_report.py", "pytest -q tests/test_task_tape.py"], runner_mode="strict")

    generate_hackathon_report(
        str(audit_path),
        output_path=str(output_path),
        pointer_path=str(pointer_path),
        task_tape_path=str(tape_path),
        task_checkpoint_path=str(checkpoint_path),
    )

    html = output_path.read_text(encoding="utf-8")
    assert "Sandbox Patch Execution Results" in html
    assert "Completed Runs" in html
    assert "No raw outputs stored" in html or "Raw Outputs Stored" in html
    assert "command_results" not in html


def test_generate_report_renders_human_escalation_summary(tmp_path):
    audit_path = tmp_path / "cpos" / "audit_log.jsonl"
    pointer_path = tmp_path / "cpos" / "pointers.jsonl"
    tape_path = tmp_path / "tapes" / "task_runs.jsonl"
    checkpoint_path = tmp_path / "tapes" / "task_checkpoints.jsonl"
    output_path = tmp_path / "report.html"
    audit_path.parent.mkdir()
    audit_path.write_text("", encoding="utf-8")
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text("", encoding="utf-8")

    from cpos.github_pr_flow import create_github_pr_dry_run
    from cpos.task_tape import TaskTapeStore

    store = TaskTapeStore(tape_path, checkpoint_path)
    created = create_github_pr_dry_run(store, repo="kagioneko/cpos-engine-zero", title="Human gate", files=["README.md"], summary="ctx")

    generate_hackathon_report(
        str(audit_path),
        output_path=str(output_path),
        pointer_path=str(pointer_path),
        task_tape_path=str(tape_path),
        task_checkpoint_path=str(checkpoint_path),
    )

    html = output_path.read_text(encoding="utf-8")
    assert "Human Escalation Queue" in html
    assert "Assisted Autonomy Review Gate" in html
    assert created["task_id"] in html
    assert "github_pr_dry_run" in html
    assert "pr_dry_run_review" in html
    assert "/github/pr-dry-runs/" in html
    assert "Review / Flow Endpoint" in html
    assert "Secret Values Stored" in html
    assert "ctx" not in html


def test_generate_report_renders_execution_scoreboard(tmp_path):
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

    store = TaskTapeStore(tape_path, checkpoint_path)
    store.append_event(
        task_id="task_score_ok",
        event="sandbox_patch_execution_completed",
        target="sandbox://execution/task_score_ok",
        status="completed_success",
        payload={"review_type": "sandbox_patch_execution", "success": True, "patch_applied": True, "workspace_copied": True, "commands_executed": True, "tests_run": True, "failure_kind": None, "execute_automatically": False},
    )
    store.append_event(
        task_id="task_score_fail",
        event="sandbox_patch_execution_completed",
        target="sandbox://execution/task_score_fail",
        status="completed_with_failures",
        payload={"review_type": "sandbox_patch_execution", "success": False, "patch_applied": True, "workspace_copied": True, "commands_executed": True, "tests_run": True, "failure_kind": "validation_command", "execute_automatically": False},
    )

    generate_hackathon_report(
        str(audit_path),
        output_path=str(output_path),
        pointer_path=str(pointer_path),
        task_tape_path=str(tape_path),
        task_checkpoint_path=str(checkpoint_path),
    )

    html = output_path.read_text(encoding="utf-8")
    assert 'Execution Scoreboard' in html
    assert 'Safety & Throughput Snapshot' in html
    assert 'Completed' in html
    assert 'Success Rate' in html
    assert 'validation_command: 1' in html


def test_generate_report_renders_auto_fix_candidates(tmp_path):
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
    from cpos.auto_fix_candidate import create_auto_fix_candidate

    store = TaskTapeStore(tape_path, checkpoint_path)
    replan_task_id = "task_replan_report"
    store.append_event(
        task_id=replan_task_id,
        event="sandbox_patch_replan_template_created",
        target="sandbox://replan-template/task_retry",
        status="template_created",
        payload={
            "review_type": "sandbox_patch_replan_template",
            "template": {
                "retry_task_id": "task_retry",
                "source_execution_task_id": "task_exec",
                "failure_kind": "validation_command",
                "failed_command": {"command_sha256": "cmd", "exit_code": 1},
                "suggested_focus": ["inspect_failed_test_metadata"],
                "execute_automatically": False,
            },
        },
    )
    create_auto_fix_candidate(store, replan_task_id=replan_task_id)

    generate_hackathon_report(
        str(audit_path),
        output_path=str(output_path),
        pointer_path=str(pointer_path),
        task_tape_path=str(tape_path),
        task_checkpoint_path=str(checkpoint_path),
    )

    html = output_path.read_text(encoding="utf-8")
    assert 'Auto Fix Candidates' in html
    assert 'Metadata-only Repair Strategy' in html
    assert 'target_failed_validation_metadata' in html
    assert 'Raw Diff' in html


def test_generate_report_renders_diff_review_drafts(tmp_path):
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
    from cpos.diff_review_draft import create_diff_review_draft

    store = TaskTapeStore(tape_path, checkpoint_path)
    candidate_task_id = "task_candidate_report"
    store.append_event(
        task_id=candidate_task_id,
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
                "candidate_steps": ["modify smallest code path"],
                "execute_automatically": False,
            },
        },
    )
    create_diff_review_draft(store, candidate_task_id=candidate_task_id)

    generate_hackathon_report(
        str(audit_path),
        output_path=str(output_path),
        pointer_path=str(pointer_path),
        task_tape_path=str(tape_path),
        task_checkpoint_path=str(checkpoint_path),
    )

    html = output_path.read_text(encoding="utf-8")
    assert 'Diff Review Drafts' in html
    assert 'Next Diff Review Payload Shape' in html
    assert 'POST /github/pr-dry-runs' in html
    assert 'Raw Diff' in html


def test_generate_report_renders_patch_generation_reviews(tmp_path):
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
    from cpos.github_pr_flow import approve_github_pr_dry_run, create_github_pr_dry_run
    from cpos.patch_generation_review import (
        approve_patch_generation_review,
        create_github_diff_review_from_patch_generation,
        create_patch_generation_review,
    )

    store = TaskTapeStore(tape_path, checkpoint_path)
    candidate_task_id = "task_candidate_patch_report"
    store.append_event(
        task_id=candidate_task_id,
        event="sandbox_auto_fix_candidate_created",
        target="sandbox://auto-fix-candidate/task_replan_patch_report",
        status="candidate_created",
        payload={
            "review_type": "sandbox_auto_fix_candidate",
            "candidate": {
                "replan_task_id": "task_replan_patch_report",
                "source_execution_task_id": "task_exec_patch_report",
                "failure_kind": "validation_command",
                "candidate_strategy": "target_failed_validation_metadata",
                "confidence": 0.68,
                "candidate_steps": ["modify smallest code path"],
                "execute_automatically": False,
            },
        },
    )
    review = create_patch_generation_review(store, candidate_task_id=candidate_task_id)
    approve_patch_generation_review(store, review["task_id"], confirm=True)
    pr = create_github_pr_dry_run(
        store,
        repo="kagioneko/cpos-engine-zero",
        title="Patch generation report",
        files=["app.py"],
        summary="metadata-only report route",
    )
    approve_github_pr_dry_run(store, pr["task_id"], confirm=True)
    linked = create_github_diff_review_from_patch_generation(
        store,
        patch_generation_task_id=review["task_id"],
        source_task_id=pr["task_id"],
        diff_text="diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-old\n+new\n",
        changed_files=["app.py"],
        validation_commands=["pytest tests/test_app.py -q"],
    )

    generate_hackathon_report(
        str(audit_path),
        output_path=str(output_path),
        pointer_path=str(pointer_path),
        task_tape_path=str(tape_path),
        task_checkpoint_path=str(checkpoint_path),
    )

    html = output_path.read_text(encoding="utf-8")
    assert 'Patch Generation Reviews' in html
    assert 'Review-Gated Patch Generator' in html
    assert 'Pending Reviews' in html
    assert 'Diff Reviews Linked' in html
    assert 'Raw Diff' in html
    assert 'Auto Execute' in html
    assert review["task_id"] in html
    assert linked["task_id"] in html


def test_generate_report_renders_sandbox_flow_graph(tmp_path):
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

    store = TaskTapeStore(tape_path, checkpoint_path)
    store.append_event(
        task_id="task_exec_flow_report",
        event="sandbox_patch_execution_completed",
        target="sandbox://execution/task_exec_flow_report",
        status="completed_with_failures",
        payload={"review_type": "sandbox_patch_execution", "success": False, "failure_kind": "validation_command"},
    )
    store.append_event(
        task_id="task_retry_flow_report",
        event="review_required",
        target="sandbox://execution/task_exec_flow_report/retry",
        status="pending",
        payload={"review_type": "sandbox_patch_execution_retry", "plan": {"source_execution_task_id": "task_exec_flow_report", "failure_kind": "validation_command"}},
    )
    store.append_event(
        task_id="task_replan_flow_report",
        event="sandbox_patch_replan_template_created",
        target="sandbox://replan-template/task_retry_flow_report",
        status="template_created",
        payload={"review_type": "sandbox_patch_replan_template", "template": {"retry_task_id": "task_retry_flow_report", "source_execution_task_id": "task_exec_flow_report", "failure_kind": "validation_command"}},
    )
    store.append_event(
        task_id="task_candidate_flow_report",
        event="sandbox_auto_fix_candidate_created",
        target="sandbox://auto-fix-candidate/task_replan_flow_report",
        status="candidate_created",
        payload={"review_type": "sandbox_auto_fix_candidate", "candidate": {"replan_task_id": "task_replan_flow_report", "source_execution_task_id": "task_exec_flow_report", "failure_kind": "validation_command", "candidate_strategy": "target_failed_validation_metadata"}},
    )
    store.append_event(
        task_id="task_draft_flow_report",
        event="sandbox_diff_review_draft_created",
        target="sandbox://diff-review-draft/task_candidate_flow_report",
        status="draft_created",
        payload={"review_type": "sandbox_diff_review_draft", "draft": {"candidate_task_id": "task_candidate_flow_report", "source_execution_task_id": "task_exec_flow_report", "failure_kind": "validation_command", "target_api": "POST /github/pr-dry-runs"}},
    )

    generate_hackathon_report(
        str(audit_path),
        output_path=str(output_path),
        pointer_path=str(pointer_path),
        task_tape_path=str(tape_path),
        task_checkpoint_path=str(checkpoint_path),
    )

    html = output_path.read_text(encoding="utf-8")
    assert 'Sandbox Autonomy Flow Graph' in html
    assert 'Failure → Replan → Candidate → Diff Draft' in html
    assert 'sandbox_execution: 1' in html
    assert 'auto_fix_candidate: 1' in html
    assert 'task_draft_flow_report' in html
    assert 'Raw Diff' in html


def test_generate_report_renders_autonomy_loop_demo_snapshot(tmp_path):
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

    store = TaskTapeStore(tape_path, checkpoint_path)
    store.append_event(
        task_id="task_exec_demo_report",
        event="sandbox_patch_execution_completed",
        target="sandbox://execution/task_exec_demo_report",
        status="completed_with_failures",
        payload={"review_type": "sandbox_patch_execution", "success": False, "failure_kind": "validation_command", "execute_automatically": False},
    )
    store.append_event(
        task_id="task_draft_demo_report",
        event="sandbox_diff_review_draft_created",
        target="sandbox://diff-review-draft/task_candidate_demo_report",
        status="draft_created",
        payload={"review_type": "sandbox_diff_review_draft", "draft": {"candidate_task_id": "task_candidate_demo_report", "source_execution_task_id": "task_exec_demo_report", "failure_kind": "validation_command", "target_api": "POST /github/pr-dry-runs/<source_task_id>/create-diff-review", "raw_diff_stored": False, "execute_automatically": False}},
    )

    generate_hackathon_report(
        str(audit_path),
        output_path=str(output_path),
        pointer_path=str(pointer_path),
        task_tape_path=str(tape_path),
        task_checkpoint_path=str(checkpoint_path),
    )

    html = output_path.read_text(encoding="utf-8")
    assert 'Autonomy Loop Demo Snapshot' in html
    assert 'Safe Execution Loop on One Report' in html
    assert 'Diff Draft → GitHub Diff Review → Sandbox Execution Review' in html
    assert 'raw_diff_stored=false' in html
    assert 'raw_outputs_stored=false' in html
    assert 'live_repo_patch=false' in html
    assert 'auto_execute=false' in html
    assert 'Retry/Replan failed run' in html
