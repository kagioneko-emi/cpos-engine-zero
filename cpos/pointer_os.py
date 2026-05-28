from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import json
import re
from .crypto import EncryptedStorageDriver

from .hash_chain import append_chained_jsonl, verify_hash_chain

VALID_STATUSES = {"active", "stale", "archived", "invalidated", "deleted"}
VALID_SENSITIVITY = {"public", "internal", "private", "restricted"}
INVALIDATION_REASONS = {
    "outdated",
    "contradicted",
    "security_risk",
    "revoked",
    "hallucinated",
    "corrupted",
    "user_request",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_token(value: str) -> str:
    token = re.sub(r"[^a-zA-Z0-9_.:-]+", "-", value.strip()).strip("-")
    return token or "unknown"


@dataclass(frozen=True)
class ContextPointer:
    pointer_id: str
    context_type: str
    summary: str
    source: str
    location: str
    priority: float = 0.5
    trust_score: float = 0.5
    sensitivity_level: str = "internal"
    retrieval_rule: str = "default"
    created_at: str = field(default_factory=utc_now)
    last_accessed: str | None = None
    access_count: int = 0
    decay_rate: float = 0.05
    expiration: str | None = None
    status: str = "active"
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    invalidated_reason: str | None = None
    invalidated_at: str | None = None
    replacement_pointer: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pointer_id": self.pointer_id,
            "context_type": self.context_type,
            "summary": self.summary,
            "source": self.source,
            "location": self.location,
            "priority": self.priority,
            "trust_score": self.trust_score,
            "sensitivity_level": self.sensitivity_level,
            "retrieval_rule": self.retrieval_rule,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "decay_rate": self.decay_rate,
            "expiration": self.expiration,
            "status": self.status,
            "dependencies": list(self.dependencies),
            "metadata": dict(self.metadata),
            "invalidated_reason": self.invalidated_reason,
            "invalidated_at": self.invalidated_at,
            "replacement_pointer": self.replacement_pointer,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContextPointer":
        # Backward compatibility for the previous finding-pointer shape.
        if "context_type" not in data and "file" in data:
            rule_id = data.get("rule_id", "unknown")
            line = data.get("line", 0)
            pointer_id = data.get("pointer_id") or f"ptr://python/{stable_token(rule_id)}/{stable_token(str(line))}"
            return cls(
                pointer_id=pointer_id,
                context_type="finding",
                summary=f"{rule_id} finding in {data.get('file')}:{line}",
                source="static_analyzer",
                location=f"{data.get('file')}:{line}",
                priority=0.8,
                trust_score=0.75,
                sensitivity_level="internal",
                status="active" if data.get("status") == "unresolved" else data.get("status", "active"),
                metadata=dict(data),
            )

        status = data.get("status", "active")
        if status not in VALID_STATUSES:
            status = "stale"
        sensitivity = data.get("sensitivity_level", "internal")
        if sensitivity not in VALID_SENSITIVITY:
            sensitivity = "internal"
        return cls(
            pointer_id=str(data["pointer_id"]),
            context_type=str(data.get("context_type", "unknown")),
            summary=str(data.get("summary", "")),
            source=str(data.get("source", "unknown")),
            location=str(data.get("location", "")),
            priority=float(data.get("priority", 0.5)),
            trust_score=float(data.get("trust_score", 0.5)),
            sensitivity_level=sensitivity,
            retrieval_rule=str(data.get("retrieval_rule", "default")),
            created_at=str(data.get("created_at") or utc_now()),
            last_accessed=data.get("last_accessed"),
            access_count=int(data.get("access_count", 0)),
            decay_rate=float(data.get("decay_rate", 0.05)),
            expiration=data.get("expiration"),
            status=status,
            dependencies=list(data.get("dependencies", [])),
            metadata=dict(data.get("metadata", {})),
            invalidated_reason=data.get("invalidated_reason"),
            invalidated_at=data.get("invalidated_at"),
            replacement_pointer=data.get("replacement_pointer"),
        )


@dataclass(frozen=True)
class RetrievalPolicy:
    allowed_context_types: list[str] = field(default_factory=list)
    blocked_context_types: list[str] = field(default_factory=lambda: ["private_credentials"])
    max_retrieval_depth: int = 2
    minimum_trust_score: float = 0.0
    requires_human_approval: bool = False
    audit_required: bool = True
    allowed_sensitivity_levels: list[str] = field(default_factory=lambda: ["public", "internal"])

    def allows(self, pointer: ContextPointer) -> tuple[bool, str]:
        if pointer.status not in {"active", "stale"}:
            return False, f"status_not_retrievable:{pointer.status}"
        if self.allowed_context_types and pointer.context_type not in self.allowed_context_types:
            return False, "context_type_not_allowed"
        if pointer.context_type in self.blocked_context_types:
            return False, "context_type_blocked"
        if pointer.trust_score < self.minimum_trust_score:
            return False, "trust_score_too_low"
        if pointer.sensitivity_level not in self.allowed_sensitivity_levels:
            return False, "sensitivity_not_allowed"
        return True, "allowed"


class PointerManager:
    def __init__(self, pointer_path: str | Path, audit_path: str | Path | None = None):
        self.pointer_path = Path(pointer_path)
        self.audit_path = Path(audit_path) if audit_path is not None else None
        self.crypto = EncryptedStorageDriver()

    def load(self) -> list[ContextPointer]:
        if not self.pointer_path.exists():
            return []
        pointers: list[ContextPointer] = []
        for line in self.crypto.wrap_file_reader(str(self.pointer_path)):
            if not line.strip():
                continue
            try:
                pointers.append(ContextPointer.from_dict(json.loads(line)))
            except json.JSONDecodeError:
                continue
        return pointers

    def save(self, pointers: Iterable[ContextPointer]) -> None:
        self.pointer_path.parent.mkdir(parents=True, exist_ok=True)
        with self.pointer_path.open("w", encoding="utf-8") as f:
            for pointer in pointers:
                plaintext = json.dumps(pointer.to_dict(), ensure_ascii=False)
                encrypted = self.crypto.encrypt_line(plaintext)
                f.write(encrypted + "\n")

    def create_pointer(
        self,
        *,
        context_type: str,
        summary: str,
        source: str,
        location: str,
        priority: float = 0.5,
        trust_score: float = 0.5,
        sensitivity_level: str = "internal",
        retrieval_rule: str = "default",
        dependencies: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        pointer_id: str | None = None,
    ) -> ContextPointer:
        pointer_id = pointer_id or f"ptr://{stable_token(context_type)}/{stable_token(source)}/{stable_token(location)}"
        pointer = ContextPointer(
            pointer_id=pointer_id,
            context_type=context_type,
            summary=summary,
            source=source,
            location=location,
            priority=max(0.0, min(1.0, priority)),
            trust_score=max(0.0, min(1.0, trust_score)),
            sensitivity_level=sensitivity_level if sensitivity_level in VALID_SENSITIVITY else "internal",
            retrieval_rule=retrieval_rule,
            dependencies=dependencies or [],
            metadata=metadata or {},
        )
        pointers = [p for p in self.load() if p.pointer_id != pointer.pointer_id]
        pointers.append(pointer)
        self.save(pointers)
        self._audit("pointer_created", pointer.pointer_id, {"context_type": context_type, "location": location})
        return pointer

    def replace_for_location(self, location_prefix: str, new_pointers: list[ContextPointer]) -> None:
        pointers = [p for p in self.load() if not p.location.startswith(location_prefix)]
        seen = {p.pointer_id for p in pointers}
        for pointer in new_pointers:
            if pointer.pointer_id not in seen:
                pointers.append(pointer)
                seen.add(pointer.pointer_id)
        self.save(pointers)
        self._audit("pointers_replaced_for_location", location_prefix, {"count": len(new_pointers)})

    def search(
        self,
        *,
        context_type: str | None = None,
        query: str | None = None,
        policy: RetrievalPolicy | None = None,
        limit: int | None = None,
    ) -> list[ContextPointer]:
        policy = policy or RetrievalPolicy()
        q = query.lower() if query else None
        results: list[ContextPointer] = []
        for pointer in self.load():
            allowed, _ = policy.allows(pointer)
            if not allowed:
                continue
            if context_type and pointer.context_type != context_type:
                continue
            if q and q not in pointer.summary.lower() and q not in pointer.location.lower():
                continue
            results.append(pointer)
        results.sort(key=lambda p: (p.priority * 0.6 + p.trust_score * 0.4, p.created_at), reverse=True)
        return results[:limit] if limit is not None else results

    def retrieve_context(self, pointer_id: str, *, agent_id: str, purpose: str, policy: RetrievalPolicy | None = None) -> dict[str, Any] | None:
        policy = policy or RetrievalPolicy()
        pointers = self.load()
        by_id = {p.pointer_id: p for p in pointers}
        pointer = by_id.get(pointer_id)
        if pointer is None:
            self._audit("context_retrieval_denied", pointer_id, {"agent": agent_id, "purpose": purpose, "reason": "not_found"})
            return None
        allowed, reason = policy.allows(pointer)
        if not allowed:
            self._audit("context_retrieval_denied", pointer_id, {"agent": agent_id, "purpose": purpose, "reason": reason})
            return None
        updated = ContextPointer.from_dict({**pointer.to_dict(), "last_accessed": utc_now(), "access_count": pointer.access_count + 1})
        self.save([updated if p.pointer_id == pointer_id else p for p in pointers])
        self._audit("context_retrieval", pointer_id, {"agent": agent_id, "purpose": purpose, "approved": True})
        reconstructed = self._reconstruct_location(updated.location)
        return {
            "pointer": updated.to_dict(),
            "context": reconstructed.get("context"),
            "snippet": reconstructed.get("snippet"),
            "line_start": reconstructed.get("line_start"),
            "line_end": reconstructed.get("line_end"),
            "target_line": reconstructed.get("target_line"),
            "reconstruction": reconstructed,
            "source": updated.source,
            "trust_score": updated.trust_score,
        }

    def invalidate_pointer(self, pointer_id: str, *, reason: str, replacement_pointer: str | None = None) -> ContextPointer | None:
        if reason not in INVALIDATION_REASONS:
            raise ValueError(f"invalid invalidation reason: {reason}")
        pointers = self.load()
        updated_pointer = None
        updated_pointers: list[ContextPointer] = []
        for pointer in pointers:
            if pointer.pointer_id == pointer_id:
                updated_pointer = ContextPointer.from_dict({
                    **pointer.to_dict(),
                    "status": "invalidated",
                    "invalidated_reason": reason,
                    "invalidated_at": utc_now(),
                    "replacement_pointer": replacement_pointer,
                })
                updated_pointers.append(updated_pointer)
            else:
                updated_pointers.append(pointer)
        if updated_pointer is not None:
            self.save(updated_pointers)
            self._audit("pointer_invalidated", pointer_id, {"reason": reason, "replacement_pointer": replacement_pointer})
        return updated_pointer

    def update_trust_score(self, pointer_id: str, score: float, *, reason: str) -> ContextPointer | None:
        score = max(0.0, min(1.0, score))
        pointers = self.load()
        updated_pointer = None
        updated_pointers: list[ContextPointer] = []
        for pointer in pointers:
            if pointer.pointer_id == pointer_id:
                metadata = dict(pointer.metadata)
                metadata.setdefault("trust_history", []).append({"score": score, "reason": reason, "timestamp": utc_now()})
                updated_pointer = ContextPointer.from_dict({**pointer.to_dict(), "trust_score": score, "metadata": metadata})
                updated_pointers.append(updated_pointer)
            else:
                updated_pointers.append(pointer)
        if updated_pointer is not None:
            self.save(updated_pointers)
            self._audit("trust_score_updated", pointer_id, {"score": score, "reason": reason})
        return updated_pointer

    def exchange_pointer(self, *, from_agent: str, to_agent: str, pointer_id: str, purpose: str, access_level: str = "internal") -> dict[str, Any]:
        event = {
            "from_agent": from_agent,
            "to_agent": to_agent,
            "pointer": pointer_id,
            "purpose": purpose,
            "access_level": access_level,
        }
        self._audit("pointer_exchanged", pointer_id, event)
        return event

    def _reconstruct_location(self, location: str, *, window: int = 2) -> dict[str, Any]:
        parsed = self._parse_line_location(location)
        if parsed is None:
            context = self._read_location(location)
            return {
                "mode": "full_file" if context is not None else "unavailable",
                "location": location,
                "context": context,
                "snippet": context,
                "line_start": None,
                "line_end": None,
                "target_line": None,
            }

        path, target_line = parsed
        try:
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError):
            return {
                "mode": "unavailable",
                "location": location,
                "context": None,
                "snippet": None,
                "line_start": None,
                "line_end": None,
                "target_line": target_line,
            }

        if target_line < 1 or target_line > len(lines):
            return {
                "mode": "line_out_of_range",
                "location": location,
                "context": None,
                "snippet": None,
                "line_start": None,
                "line_end": None,
                "target_line": target_line,
                "total_lines": len(lines),
            }

        line_start = max(1, target_line - window)
        line_end = min(len(lines), target_line + window)
        snippet = "".join(lines[line_start - 1:line_end])
        return {
            "mode": "line_window",
            "location": location,
            "context": snippet,
            "snippet": snippet,
            "line_start": line_start,
            "line_end": line_end,
            "target_line": target_line,
            "total_lines": len(lines),
            "window": window,
        }

    def _parse_line_location(self, location: str) -> tuple[Path, int] | None:
        match = re.match(r"^(.+):(\d+)$", location)
        if not match:
            return None
        path = Path(match.group(1))
        if not path.exists() or not path.is_file():
            return None
        return path, int(match.group(2))

    def _read_location(self, location: str) -> str | None:
        path = Path(location)
        if not path.exists() or not path.is_file():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return None

    def _audit(self, event: str, pointer_id: str, payload: dict[str, Any]) -> None:
        if self.audit_path is None:
            return
        entry = {"event": event, "pointer_id": pointer_id, "timestamp": utc_now(), **payload}
        append_chained_jsonl(self.audit_path, entry)

    def verify_audit_integrity(self) -> dict[str, Any]:
        if self.audit_path is None:
            return {"ok": True, "row_count": 0, "verified_count": 0, "legacy_prefix_count": 0, "head_hash": "0" * 64}
        return verify_hash_chain(self.audit_path)
