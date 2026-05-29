from cpos.footprint import build_footprint
from cpos.pointer_os import PointerManager
from cpos.task_tape import TaskTapeStore
from agents.main_agent import MainAgent
import server


def test_build_footprint_reports_counts_and_no_secret_flags(tmp_path):
    pointer_path = tmp_path / "cpos" / "pointers.jsonl"
    pointer_audit = tmp_path / "cpos" / "audit_log.jsonl"
    task_path = tmp_path / "tapes" / "task_runs.jsonl"
    checkpoint_path = tmp_path / "tapes" / "task_checkpoints.jsonl"
    security_path = tmp_path / "cpos" / "security_audit.jsonl"
    inventory_path = tmp_path / "cpos" / "secret_inventory.jsonl"
    manager = PointerManager(pointer_path, pointer_audit)
    manager.create_pointer(context_type="handoff_summary", summary="handoff", source="test", location="handoff://x")
    store = TaskTapeStore(task_path, checkpoint_path)
    store.create_task(target="demo", action="unit")

    footprint = build_footprint(
        pointer_path=pointer_path,
        pointer_audit_path=pointer_audit,
        task_tape_path=task_path,
        task_checkpoint_path=checkpoint_path,
        security_audit_path=security_path,
        secret_inventory_path=inventory_path,
    )

    assert footprint["ok"] is True
    assert footprint["counts"]["pointers"] == 1
    assert footprint["counts"]["tasks"] == 1
    assert footprint["total_bytes"] > 0
    assert footprint["lightweight_properties"]["secrets_included"] is False
    assert footprint["lightweight_properties"]["handoff_imports_raw_body"] is False


def test_footprint_api_uses_agent_paths(tmp_path):
    test_agent = MainAgent()
    test_agent.project_root = str(tmp_path)
    test_agent.audit_log_path = str(tmp_path / "cpos" / "audit_log.jsonl")
    test_agent.pointers_path = str(tmp_path / "cpos" / "pointers.jsonl")
    test_agent.pointer_manager = PointerManager(test_agent.pointers_path, test_agent.audit_log_path)
    test_agent.task_tape_path = str(tmp_path / "tapes" / "task_runs.jsonl")
    test_agent.task_checkpoint_path = str(tmp_path / "tapes" / "task_checkpoints.jsonl")
    test_agent.task_tape = TaskTapeStore(test_agent.task_tape_path, test_agent.task_checkpoint_path)
    server.agent = test_agent
    test_agent.pointer_manager.create_pointer(context_type="spec", summary="demo", source="test", location="demo.md")

    res = server.app.test_client().get("/footprint")

    assert res.status_code == 200
    payload = res.get_json()
    assert payload["ok"] is True
    assert payload["counts"]["pointers"] == 1
    assert payload["lightweight_properties"]["checkpoint_contents_exposed_by_api"] is False
