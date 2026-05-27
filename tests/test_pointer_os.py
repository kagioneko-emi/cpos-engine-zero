import json
from pathlib import Path

from agents.main_agent import MainAgent
from cpos.pointer_os import PointerManager, RetrievalPolicy


def test_pointer_manager_create_retrieve_and_invalidate(tmp_path):
    source = tmp_path / "app.py"
    source.write_text("print('ok')\n", encoding="utf-8")
    pointer_path = tmp_path / "pointers.jsonl"
    audit_path = tmp_path / "audit.jsonl"
    manager = PointerManager(pointer_path, audit_path)

    pointer = manager.create_pointer(
        context_type="code",
        summary="demo app source",
        source="unit_test",
        location=str(source),
        priority=0.8,
        trust_score=0.9,
    )

    retrieved = manager.retrieve_context(
        pointer.pointer_id,
        agent_id="TestAgent",
        purpose="verify_retrieval",
        policy=RetrievalPolicy(allowed_context_types=["code"], minimum_trust_score=0.7),
    )

    assert retrieved is not None
    assert retrieved["context"] == "print('ok')\n"
    stored = manager.load()[0]
    assert stored.access_count == 1
    assert stored.last_accessed is not None

    invalidated = manager.invalidate_pointer(pointer.pointer_id, reason="outdated")
    assert invalidated is not None
    assert invalidated.status == "invalidated"
    assert manager.retrieve_context(pointer.pointer_id, agent_id="TestAgent", purpose="after_invalidate") is None

    audit_events = [json.loads(line)["event"] for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert "pointer_created" in audit_events
    assert "context_retrieval" in audit_events
    assert "pointer_invalidated" in audit_events


def test_pointer_manager_governance_blocks_private_context(tmp_path):
    pointer_path = tmp_path / "pointers.jsonl"
    manager = PointerManager(pointer_path)
    pointer = manager.create_pointer(
        context_type="private_credentials",
        summary="credential reference",
        source="vault",
        location="secret/discord",
        trust_score=1.0,
        sensitivity_level="restricted",
    )

    assert manager.retrieve_context(pointer.pointer_id, agent_id="TestAgent", purpose="blocked") is None


def test_main_agent_writes_context_pointer_schema(tmp_path):
    agent = MainAgent()
    agent.project_root = str(tmp_path)
    agent.audit_log_path = str(tmp_path / "cpos" / "audit_log.jsonl")
    agent.pointers_path = str(tmp_path / "cpos" / "pointers.jsonl")
    agent.pointer_manager = PointerManager(agent.pointers_path, agent.audit_log_path)

    target = tmp_path / "workspace" / "risk.py"
    target.parent.mkdir()
    target.write_text("value = eval('1+1')\n", encoding="utf-8")

    agent.update_pointer(str(target), [
        {
            "rule_id": "PY-MISTAKE-0002",
            "title": "unsafe eval",
            "line": 1,
            "content": "value = eval('1+1')",
            "fix": "avoid eval",
            "severity": "high",
        }
    ])

    rows = [json.loads(line) for line in Path(agent.pointers_path).read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    row = rows[0]
    assert row["context_type"] == "finding"
    assert row["source"] == "python_subagent"
    assert row["status"] == "active"
    assert row["priority"] == 0.9
    assert row["metadata"]["rule_id"] == "PY-MISTAKE-0002"

    agent.update_pointer(str(target), [])
    assert Path(agent.pointers_path).read_text(encoding="utf-8") == ""

import subprocess
import sys


def run_pointer_cli(tmp_path, *args):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "cpos.pointer_cli",
            "--pointer-path",
            str(tmp_path / "pointers.jsonl"),
            "--audit-path",
            str(tmp_path / "audit.jsonl"),
            *args,
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )


def test_pointer_cli_list_retrieve_trust_invalidate_and_exchange(tmp_path):
    source = tmp_path / "app.py"
    source.write_text("VALUE = 42\n", encoding="utf-8")
    manager = PointerManager(tmp_path / "pointers.jsonl", tmp_path / "audit.jsonl")
    pointer = manager.create_pointer(
        context_type="code",
        summary="important app source",
        source="unit_test",
        location=str(source),
        priority=0.6,
        trust_score=0.8,
    )

    listed = run_pointer_cli(tmp_path, "list", "--json")
    assert listed.returncode == 0
    listed_payload = json.loads(listed.stdout)
    assert [row["pointer_id"] for row in listed_payload] == [pointer.pointer_id]

    retrieved = run_pointer_cli(tmp_path, "retrieve", pointer.pointer_id, "--json")
    assert retrieved.returncode == 0
    retrieved_payload = json.loads(retrieved.stdout)
    assert retrieved_payload["ok"] is True
    assert retrieved_payload["context"] == "VALUE = 42\n"
    assert retrieved_payload["pointer"]["access_count"] == 1

    trusted = run_pointer_cli(tmp_path, "trust-update", pointer.pointer_id, "--score", "0.95", "--reason", "user_confirmed", "--json")
    assert trusted.returncode == 0
    trusted_payload = json.loads(trusted.stdout)
    assert trusted_payload["pointer"]["trust_score"] == 0.95
    assert trusted_payload["pointer"]["metadata"]["trust_history"][-1]["reason"] == "user_confirmed"

    exchanged = run_pointer_cli(
        tmp_path,
        "exchange",
        pointer.pointer_id,
        "--from-agent",
        "CodingAgent",
        "--to-agent",
        "AuditAgent",
        "--purpose",
        "audit_required",
        "--json",
    )
    assert exchanged.returncode == 0
    assert json.loads(exchanged.stdout)["exchange"]["to_agent"] == "AuditAgent"

    invalidated = run_pointer_cli(tmp_path, "invalidate", pointer.pointer_id, "--reason", "outdated", "--json")
    assert invalidated.returncode == 0
    assert json.loads(invalidated.stdout)["pointer"]["status"] == "invalidated"

    denied = run_pointer_cli(tmp_path, "retrieve", pointer.pointer_id, "--json")
    assert denied.returncode == 1
    assert json.loads(denied.stdout)["error"] == "not_found_or_denied"


def test_pointer_cli_list_text_is_compact(tmp_path):
    manager = PointerManager(tmp_path / "pointers.jsonl")
    pointer = manager.create_pointer(
        context_type="spec",
        summary="Context Pointer OS spec",
        source="unit_test",
        location="docs/spec.md",
        priority=0.7,
        trust_score=0.9,
    )

    result = run_pointer_cli(tmp_path, "list", "--query", "pointer")

    assert result.returncode == 0
    assert pointer.pointer_id in result.stdout
    assert "type=spec" in result.stdout
    assert "status=active" in result.stdout


def test_retrieve_context_reconstructs_line_window_for_file_line_location(tmp_path):
    source = tmp_path / "app.py"
    source.write_text("one\ntwo\nthree\nfour\nfive\n", encoding="utf-8")
    manager = PointerManager(tmp_path / "pointers.jsonl", tmp_path / "audit.jsonl")
    pointer = manager.create_pointer(
        context_type="finding",
        summary="line three issue",
        source="unit_test",
        location=f"{source}:3",
        priority=0.9,
        trust_score=0.9,
    )

    retrieved = manager.retrieve_context(pointer.pointer_id, agent_id="TestAgent", purpose="line_window")

    assert retrieved is not None
    assert retrieved["context"] == "one\ntwo\nthree\nfour\nfive\n"
    assert retrieved["snippet"] == "one\ntwo\nthree\nfour\nfive\n"
    assert retrieved["target_line"] == 3
    assert retrieved["line_start"] == 1
    assert retrieved["line_end"] == 5
    assert retrieved["reconstruction"]["mode"] == "line_window"


def test_retrieve_context_line_window_clamps_edges(tmp_path):
    source = tmp_path / "app.py"
    source.write_text("one\ntwo\nthree\nfour\nfive\nsix\n", encoding="utf-8")
    manager = PointerManager(tmp_path / "pointers.jsonl")
    pointer = manager.create_pointer(
        context_type="finding",
        summary="last line issue",
        source="unit_test",
        location=f"{source}:6",
        priority=0.9,
        trust_score=0.9,
    )

    retrieved = manager.retrieve_context(pointer.pointer_id, agent_id="TestAgent", purpose="line_window")

    assert retrieved is not None
    assert retrieved["snippet"] == "four\nfive\nsix\n"
    assert retrieved["target_line"] == 6
    assert retrieved["line_start"] == 4
    assert retrieved["line_end"] == 6
