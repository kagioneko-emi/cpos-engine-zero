from __future__ import annotations

from pathlib import Path
from typing import Any

from .pointer_os import PointerManager
from .task_tape import TaskTapeStore


def file_size(path: str | Path) -> int:
    p = Path(path)
    try:
        return p.stat().st_size
    except OSError:
        return 0


def build_footprint(
    *,
    pointer_path: str | Path,
    pointer_audit_path: str | Path,
    task_tape_path: str | Path,
    task_checkpoint_path: str | Path,
    security_audit_path: str | Path,
    secret_inventory_path: str | Path,
) -> dict[str, Any]:
    pointer_manager = PointerManager(pointer_path, pointer_audit_path)
    task_store = TaskTapeStore(task_tape_path, task_checkpoint_path)
    pointers = pointer_manager.load()
    task_summary = task_store.summary()
    sizes = {
        "pointers_bytes": file_size(pointer_path),
        "pointer_audit_bytes": file_size(pointer_audit_path),
        "task_events_bytes": file_size(task_tape_path),
        "task_checkpoints_bytes": file_size(task_checkpoint_path),
        "security_audit_bytes": file_size(security_audit_path),
        "secret_inventory_bytes": file_size(secret_inventory_path),
    }
    total = sum(sizes.values())
    pointer_by_type: dict[str, int] = {}
    for pointer in pointers:
        pointer_by_type[pointer.context_type] = pointer_by_type.get(pointer.context_type, 0) + 1
    return {
        "ok": True,
        "mode": "metadata_pointer_tape",
        "total_bytes": total,
        "sizes": sizes,
        "counts": {
            "pointers": len(pointers),
            "pointer_types": pointer_by_type,
            "tasks": task_summary.get("task_count", 0),
            "task_events": task_summary.get("event_count", 0),
            "checkpoints": task_summary.get("checkpoint_count", 0),
        },
        "lightweight_properties": {
            "relationship_memory_full_logs_in_context": False,
            "task_tape_append_only": True,
            "handoff_imports_raw_body": False,
            "checkpoint_contents_exposed_by_api": False,
            "secrets_included": False,
        },
        "notes": [
            "LLM context stays light by passing summaries, pointers, counts, and hashes instead of raw logs.",
            "Persistence overhead is mostly small JSONL ledgers plus optional checkpoint files for rollback.",
            "Security/audit layers add control overhead but avoid stuffing long history into prompts.",
        ],
    }
