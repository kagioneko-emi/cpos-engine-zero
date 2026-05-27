from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
import hashlib
import json
import uuid

from .hash_chain import append_chained_jsonl, verify_hash_chain
from .pointer_os import utc_now


@dataclass(frozen=True)
class TaskTapeEvent:
    event_id: str
    task_id: str
    event: str
    timestamp: str
    target: str | None = None
    checkpoint_id: str | None = None
    status: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "task_id": self.task_id,
            "event": self.event,
            "timestamp": self.timestamp,
            "target": self.target,
            "checkpoint_id": self.checkpoint_id,
            "status": self.status,
            "payload": dict(self.payload),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskTapeEvent":
        return cls(
            event_id=str(data["event_id"]),
            task_id=str(data["task_id"]),
            event=str(data["event"]),
            timestamp=str(data.get("timestamp") or utc_now()),
            target=data.get("target"),
            checkpoint_id=data.get("checkpoint_id"),
            status=data.get("status"),
            payload=dict(data.get("payload", {})),
        )


@dataclass(frozen=True)
class TaskCheckpoint:
    checkpoint_id: str
    task_id: str
    target: str
    content_sha256: str
    content: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "task_id": self.task_id,
            "target": self.target,
            "content_sha256": self.content_sha256,
            "content": self.content,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskCheckpoint":
        return cls(
            checkpoint_id=str(data["checkpoint_id"]),
            task_id=str(data["task_id"]),
            target=str(data["target"]),
            content_sha256=str(data["content_sha256"]),
            content=str(data.get("content", "")),
            created_at=str(data.get("created_at") or utc_now()),
        )


class TaskTapeStore:
    def __init__(self, tape_path: str | Path, checkpoint_path: str | Path | None = None):
        self.tape_path = Path(tape_path)
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path is not None else self.tape_path.with_name("task_checkpoints.jsonl")

    def events(self) -> list[TaskTapeEvent]:
        return [TaskTapeEvent.from_dict(row) for row in self._read_jsonl(self.tape_path)]

    def checkpoints(self) -> list[TaskCheckpoint]:
        return [TaskCheckpoint.from_dict(row) for row in self._read_jsonl(self.checkpoint_path)]

    def append_event(
        self,
        *,
        task_id: str,
        event: str,
        target: str | None = None,
        checkpoint_id: str | None = None,
        status: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> TaskTapeEvent:
        item = TaskTapeEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            task_id=task_id,
            event=event,
            timestamp=utc_now(),
            target=target,
            checkpoint_id=checkpoint_id,
            status=status,
            payload=payload or {},
        )
        append_chained_jsonl(self.tape_path, item.to_dict())
        return item

    def create_task(self, *, target: str, action: str, payload: dict[str, Any] | None = None) -> str:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        self.append_event(task_id=task_id, event="task_started", target=target, status="running", payload={"action": action, **(payload or {})})
        return task_id

    def create_checkpoint(self, *, task_id: str, target: str, content: str) -> TaskCheckpoint:
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        checkpoint = TaskCheckpoint(
            checkpoint_id=f"chk_{uuid.uuid4().hex[:12]}",
            task_id=task_id,
            target=str(target),
            content_sha256=digest,
            content=content,
            created_at=utc_now(),
        )
        append_chained_jsonl(self.checkpoint_path, checkpoint.to_dict())
        self.append_event(
            task_id=task_id,
            event="checkpoint_created",
            target=str(target),
            checkpoint_id=checkpoint.checkpoint_id,
            status="checkpointed",
            payload={"content_sha256": digest},
        )
        return checkpoint


    def events_for_task(self, task_id: str) -> list[TaskTapeEvent]:
        return [event for event in self.events() if event.task_id == task_id]

    def pending_reviews(self) -> list[dict[str, Any]]:
        terminal_events = {"review_approved", "review_rejected", "fix_written", "rollback_applied"}
        terminal_task_ids = {event.task_id for event in self.events() if event.event in terminal_events}
        reviews = []
        for event in self.events():
            if event.event == "review_required" and event.task_id not in terminal_task_ids:
                reviews.append(event.to_dict())
        return reviews

    def latest_pending_review(self, task_id: str) -> TaskTapeEvent | None:
        reviews = [event for event in self.events_for_task(task_id) if event.event == "review_required"]
        if not reviews:
            return None
        if any(event.event in {"review_approved", "review_rejected", "fix_written"} for event in self.events_for_task(task_id)):
            return None
        return reviews[-1]

    def latest_checkpoint(self, *, target: str | None = None, task_id: str | None = None) -> TaskCheckpoint | None:
        checkpoints = self.checkpoints()
        if target is not None:
            checkpoints = [checkpoint for checkpoint in checkpoints if checkpoint.target == str(target)]
        if task_id is not None:
            checkpoints = [checkpoint for checkpoint in checkpoints if checkpoint.task_id == task_id]
        return checkpoints[-1] if checkpoints else None

    def rollback_latest(self, *, target: str | None = None, task_id: str | None = None) -> dict[str, Any]:
        checkpoint = self.latest_checkpoint(target=target, task_id=task_id)
        if checkpoint is None:
            return {"ok": False, "error": "checkpoint_not_found", "target": target, "task_id": task_id}
        Path(checkpoint.target).write_text(checkpoint.content, encoding="utf-8")
        self.append_event(
            task_id=checkpoint.task_id,
            event="rollback_applied",
            target=checkpoint.target,
            checkpoint_id=checkpoint.checkpoint_id,
            status="rolled_back",
            payload={"content_sha256": checkpoint.content_sha256},
        )
        return {"ok": True, "checkpoint": checkpoint.to_dict()}

    def verify_integrity(self) -> dict[str, Any]:
        return {
            "events": verify_hash_chain(self.tape_path),
            "checkpoints": verify_hash_chain(self.checkpoint_path),
        }

    def summary(self) -> dict[str, Any]:
        events = self.events()
        checkpoints = self.checkpoints()
        integrity = self.verify_integrity()
        return {
            "event_count": len(events),
            "checkpoint_count": len(checkpoints),
            "task_count": len({event.task_id for event in events}),
            "latest_event": events[-1].to_dict() if events else None,
            "integrity": integrity,
        }

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))
        return rows

