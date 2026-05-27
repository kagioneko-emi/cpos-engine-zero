import json

from agents.main_agent import MainAgent
from cpos.task_tape import TaskTapeStore


class FakeArchitect:
    def __init__(self, fixed_code):
        self.fixed_code = fixed_code

    def propose_fix(self, target_file, content, finding, sandbox_output=None):
        return self.fixed_code


class FakeSandbox:
    def __init__(self, exit_code=0):
        self.exit_code = exit_code

    def run_command(self, target_dir, command):
        return {"exit_code": self.exit_code, "stdout": "ok\n", "stderr": ""}


def test_task_tape_checkpoint_and_rollback_latest(tmp_path):
    target = tmp_path / "app.py"
    target.write_text("old\n", encoding="utf-8")
    store = TaskTapeStore(tmp_path / "task_runs.jsonl", tmp_path / "task_checkpoints.jsonl")
    task_id = store.create_task(target=str(target), action="unit_test")
    checkpoint = store.create_checkpoint(task_id=task_id, target=str(target), content=target.read_text(encoding="utf-8"))

    target.write_text("new\n", encoding="utf-8")
    result = store.rollback_latest(target=str(target))

    assert result["ok"] is True
    assert result["checkpoint"]["checkpoint_id"] == checkpoint.checkpoint_id
    assert target.read_text(encoding="utf-8") == "old\n"
    events = store.events()
    assert [event.event for event in events] == ["task_started", "checkpoint_created", "rollback_applied"]
    assert store.summary()["checkpoint_count"] == 1


def test_task_tape_rollback_reports_missing_checkpoint(tmp_path):
    store = TaskTapeStore(tmp_path / "task_runs.jsonl")

    result = store.rollback_latest(target=str(tmp_path / "missing.py"))

    assert result == {"ok": False, "error": "checkpoint_not_found", "target": str(tmp_path / "missing.py"), "task_id": None}


def test_main_agent_autonomous_fix_records_task_tape_and_checkpoint(tmp_path):
    target = tmp_path / "app.py"
    target.write_text("bad = eval('1+1')\n", encoding="utf-8")
    agent = MainAgent()
    agent.project_root = str(tmp_path)
    agent.audit_log_path = str(tmp_path / "cpos" / "audit_log.jsonl")
    agent.pointers_path = str(tmp_path / "cpos" / "pointers.jsonl")
    agent.task_tape_path = str(tmp_path / "tapes" / "task_runs.jsonl")
    agent.task_checkpoint_path = str(tmp_path / "tapes" / "task_checkpoints.jsonl")
    agent.task_tape = TaskTapeStore(agent.task_tape_path, agent.task_checkpoint_path)
    agent.architect = FakeArchitect("good = 2\n")
    agent.sandbox = FakeSandbox(exit_code=0)

    result = agent.apply_autonomous_fix(
        str(target),
        "bad = eval('1+1')\n",
        [{"rule_id": "PY-MISTAKE-0002", "severity": "high"}],
        "",
        require_review=False,
    )

    assert result["exit_code"] == 0
    assert result["task_id"].startswith("task_")
    assert result["checkpoint_id"].startswith("chk_")
    assert target.read_text(encoding="utf-8") == "good = 2\n"

    events = [json.loads(line)["event"] for line in (tmp_path / "tapes" / "task_runs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert events == ["task_started", "checkpoint_created", "fix_requested", "fix_written", "verification_completed"]

    rollback = agent.task_tape.rollback_latest(target=str(target))
    assert rollback["ok"] is True
    assert target.read_text(encoding="utf-8") == "bad = eval('1+1')\n"

import subprocess
import sys
from pathlib import Path


def run_task_cli(tmp_path, *args):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "cpos.task_cli",
            "--tape-path",
            str(tmp_path / "task_runs.jsonl"),
            "--checkpoint-path",
            str(tmp_path / "task_checkpoints.jsonl"),
            *args,
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )


def test_task_cli_summary_events_checkpoints_and_rollback(tmp_path):
    target = tmp_path / "app.py"
    target.write_text("old\n", encoding="utf-8")
    store = TaskTapeStore(tmp_path / "task_runs.jsonl", tmp_path / "task_checkpoints.jsonl")
    task_id = store.create_task(target=str(target), action="unit_test")
    checkpoint = store.create_checkpoint(task_id=task_id, target=str(target), content="old\n")
    target.write_text("new\n", encoding="utf-8")

    summary = run_task_cli(tmp_path, "summary", "--json")
    assert summary.returncode == 0
    assert json.loads(summary.stdout)["checkpoint_count"] == 1

    events = run_task_cli(tmp_path, "events", "--task-id", task_id, "--json")
    assert events.returncode == 0
    assert [row["event"] for row in json.loads(events.stdout)] == ["task_started", "checkpoint_created"]

    checkpoints = run_task_cli(tmp_path, "checkpoints", "--target", str(target), "--json")
    assert checkpoints.returncode == 0
    assert json.loads(checkpoints.stdout)[0]["checkpoint_id"] == checkpoint.checkpoint_id

    rollback = run_task_cli(tmp_path, "rollback-latest", "--target", str(target), "--json")
    assert rollback.returncode == 0
    assert json.loads(rollback.stdout)["ok"] is True
    assert target.read_text(encoding="utf-8") == "old\n"


def test_task_cli_rollback_requires_task_or_target(tmp_path):
    result = run_task_cli(tmp_path, "rollback-latest", "--json")

    assert result.returncode == 2
    assert json.loads(result.stdout)["error"] == "task_id_or_target_required"



def test_main_agent_autonomous_fix_requires_review_before_writing(tmp_path):
    target = tmp_path / "app.py"
    original = "bad = eval('1+1')\n"
    target.write_text(original, encoding="utf-8")
    agent = MainAgent()
    agent.project_root = str(tmp_path)
    agent.task_tape_path = str(tmp_path / "tapes" / "task_runs.jsonl")
    agent.task_checkpoint_path = str(tmp_path / "tapes" / "task_checkpoints.jsonl")
    agent.task_tape = TaskTapeStore(agent.task_tape_path, agent.task_checkpoint_path)
    agent.architect = FakeArchitect("good = 2\n")
    agent.sandbox = FakeSandbox(exit_code=0)

    result = agent.apply_autonomous_fix(
        str(target),
        original,
        [{"rule_id": "PY-MISTAKE-0002", "severity": "high"}],
        "",
    )

    assert result["exit_code"] == 2
    assert result["status"] == "pending_review"
    assert target.read_text(encoding="utf-8") == original
    events = [event.event for event in agent.task_tape.events()]
    assert events == ["task_started", "checkpoint_created", "fix_requested", "review_required"]
    reviews = agent.pending_fix_reviews()
    assert len(reviews) == 1
    assert reviews[0]["task_id"] == result["task_id"]
    assert "proposed_code" not in reviews[0]["payload"]
    assert reviews[0]["payload"]["proposed_size"] == len("good = 2\n")


def test_main_agent_approve_pending_fix_writes_and_verifies(tmp_path):
    target = tmp_path / "app.py"
    original = "bad = eval('1+1')\n"
    target.write_text(original, encoding="utf-8")
    agent = MainAgent()
    agent.project_root = str(tmp_path)
    agent.task_tape_path = str(tmp_path / "tapes" / "task_runs.jsonl")
    agent.task_checkpoint_path = str(tmp_path / "tapes" / "task_checkpoints.jsonl")
    agent.task_tape = TaskTapeStore(agent.task_tape_path, agent.task_checkpoint_path)
    agent.architect = FakeArchitect("good = 2\n")
    agent.sandbox = FakeSandbox(exit_code=0)
    pending = agent.apply_autonomous_fix(str(target), original, [{"rule_id": "PY-MISTAKE-0002", "severity": "high"}], "")

    denied = agent.approve_pending_fix(pending["task_id"], confirm=False)
    assert denied["error"] == "confirm_required"
    assert target.read_text(encoding="utf-8") == original

    approved = agent.approve_pending_fix(pending["task_id"], confirm=True)

    assert approved["ok"] is True
    assert target.read_text(encoding="utf-8") == "good = 2\n"
    events = [event.event for event in agent.task_tape.events()]
    assert events == [
        "task_started",
        "checkpoint_created",
        "fix_requested",
        "review_required",
        "review_approved",
        "fix_written",
        "verification_completed",
    ]


def test_main_agent_reject_pending_fix_records_rejection_without_writing(tmp_path):
    target = tmp_path / "app.py"
    original = "bad = eval('1+1')\n"
    target.write_text(original, encoding="utf-8")
    agent = MainAgent()
    agent.project_root = str(tmp_path)
    agent.task_tape_path = str(tmp_path / "tapes" / "task_runs.jsonl")
    agent.task_checkpoint_path = str(tmp_path / "tapes" / "task_checkpoints.jsonl")
    agent.task_tape = TaskTapeStore(agent.task_tape_path, agent.task_checkpoint_path)
    agent.architect = FakeArchitect("good = 2\n")
    agent.sandbox = FakeSandbox(exit_code=0)
    pending = agent.apply_autonomous_fix(str(target), original, [{"rule_id": "PY-MISTAKE-0002", "severity": "high"}], "")

    rejected = agent.reject_pending_fix(pending["task_id"], reason="unsafe_change")

    assert rejected["ok"] is True
    assert target.read_text(encoding="utf-8") == original
    assert agent.pending_fix_reviews() == []
    assert [event.event for event in agent.task_tape.events()][-1] == "review_rejected"
