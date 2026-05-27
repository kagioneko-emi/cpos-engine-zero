from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import uuid

from .hash_chain import append_chained_jsonl, verify_hash_chain
from .pointer_os import utc_now


@dataclass(frozen=True)
class SecurityAuditEvent:
    event_id: str
    event: str
    timestamp: str
    actor: str
    method: str
    path: str
    decision: str
    status_code: int | None = None
    required_scope: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event": self.event,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "method": self.method,
            "path": self.path,
            "decision": self.decision,
            "status_code": self.status_code,
            "required_scope": self.required_scope,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SecurityAuditEvent":
        return cls(
            event_id=str(data["event_id"]),
            event=str(data["event"]),
            timestamp=str(data.get("timestamp") or utc_now()),
            actor=str(data.get("actor") or "unknown"),
            method=str(data.get("method") or ""),
            path=str(data.get("path") or ""),
            decision=str(data.get("decision") or "unknown"),
            status_code=data.get("status_code"),
            required_scope=data.get("required_scope"),
            metadata=dict(data.get("metadata", {})),
        )


class SecurityAuditLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def append(
        self,
        *,
        event: str,
        actor: str,
        method: str,
        path: str,
        decision: str,
        status_code: int | None = None,
        required_scope: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityAuditEvent:
        item = SecurityAuditEvent(
            event_id=f"sec_{uuid.uuid4().hex[:12]}",
            event=event,
            timestamp=utc_now(),
            actor=actor,
            method=method,
            path=path,
            decision=decision,
            status_code=status_code,
            required_scope=required_scope,
            metadata=metadata or {},
        )
        append_chained_jsonl(self.path, item.to_dict())
        return item

    def events(self) -> list[SecurityAuditEvent]:
        if not self.path.exists():
            return []
        rows = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(SecurityAuditEvent.from_dict(json.loads(line)))
        return rows

    def verify_integrity(self) -> dict[str, Any]:
        return verify_hash_chain(self.path)
