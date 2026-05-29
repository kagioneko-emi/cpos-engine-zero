import json
import subprocess
import sys
from pathlib import Path

from cpos.handoff_export import build_handoff_bundle, render_markdown
from cpos.pointer_os import PointerManager
from cpos.secret_inventory import add_artifact
from cpos.task_tape import TaskTapeStore


def test_handoff_bundle_is_sanitized(tmp_path, monkeypatch):
    project = tmp_path
    (project / "cpos").mkdir()
    (project / "tapes").mkdir()
    (project / "NEXT_HANDOFF.md").write_text("# NEXT\ncontinue safely\n", encoding="utf-8")

    pointer_path = project / "cpos" / "pointers.jsonl"
    pointer_audit = project / "cpos" / "audit_log.jsonl"
    manager = PointerManager(pointer_path, pointer_audit)
    manager.create_pointer(
        context_type="project_memory",
        summary="Safe handoff summary",
        source="test",
        location="docs/spec.md",
        priority=0.9,
        trust_score=0.8,
    )

    store = TaskTapeStore(project / "tapes" / "task_runs.jsonl", project / "tapes" / "task_checkpoints.jsonl")
    task_id = store.create_task(target="server.py", action="patch", payload={"token": "SHOULD_NOT_LEAK", "note": "ok"})
    store.create_checkpoint(task_id=task_id, target=str(project / "server.py"), content="SECRET CHECKPOINT CONTENT")
    store.append_event(task_id=task_id, event="review_required", target="server.py", payload={"proposed_code": "SECRET PATCH", "safe": True})

    add_artifact(
        project / "cpos" / "secret_inventory.jsonl",
        artifact_path="certs/key.pem",
        artifact_type="private_key",
        vault_path="secret/ssh/example",
        field="private_key",
        status="review",
    )

    monkeypatch.chdir(project)
    bundle = build_handoff_bundle(project_root=project, limit=5, environ={"CPOS_SECURITY_PROFILE": "dev"})
    raw = json.dumps(bundle, ensure_ascii=False)

    assert bundle["schema"] == "cpos.multi_agent_handoff.v1"
    assert bundle["safety"]["secrets_included"] is False
    assert "SHOULD_NOT_LEAK" not in raw
    assert "SECRET CHECKPOINT CONTENT" not in raw
    assert "SECRET PATCH" not in raw
    assert bundle["pointers"]["count"] == 1
    assert bundle["tasks"]["summary"]["task_count"] == 1
    assert bundle["secret_inventory"]["count"] == 1
    assert bundle["integrity"]["task_events"]["ok"] is True
    assert "NEXT" in bundle["next_handoff"]["excerpt"]


def test_handoff_markdown_and_cli(tmp_path):
    (tmp_path / "cpos").mkdir()
    (tmp_path / "tapes").mkdir()
    (tmp_path / "NEXT_HANDOFF.md").write_text("handoff memo", encoding="utf-8")
    bundle = build_handoff_bundle(project_root=tmp_path, limit=2, environ={"CPOS_SECURITY_PROFILE": "dev"})
    markdown = render_markdown(bundle)
    assert "# CPOS Multi-Agent Handoff" in markdown
    assert "Secrets included: **no**" in markdown

    output = tmp_path / "handoff.md"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cpos.handoff_export",
            "--project-root",
            str(tmp_path),
            "--format",
            "markdown",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    assert json.loads(result.stdout)["ok"] is True
    assert output.exists()
    assert "CPOS Multi-Agent Handoff" in output.read_text(encoding="utf-8")
