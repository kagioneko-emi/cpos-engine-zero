from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import time


@dataclass(frozen=True)
class HMACKeyRecord:
    key_id: str
    secret_file: str
    status: str = "active"
    scopes: set[str] = field(default_factory=lambda: {"*"})
    not_before: int | None = None
    not_after: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, key_id: str, data: dict[str, Any]) -> "HMACKeyRecord":
        scopes_raw = data.get("scopes", ["*"])
        if isinstance(scopes_raw, str):
            scopes = {chunk.strip() for chunk in scopes_raw.replace("\n", ",").split(",") if chunk.strip()}
        else:
            scopes = {str(scope).strip() for scope in scopes_raw if str(scope).strip()}
        return cls(
            key_id=key_id,
            secret_file=str(data.get("secret_file") or ""),
            status=str(data.get("status", "active")),
            scopes=scopes or {"*"},
            not_before=int(data["not_before"]) if data.get("not_before") is not None else None,
            not_after=int(data["not_after"]) if data.get("not_after") is not None else None,
            metadata=dict(data.get("metadata", {})),
        )

    def is_usable(self, *, now: int | None = None) -> tuple[bool, str]:
        now = int(time.time()) if now is None else now
        if self.status not in {"active", "deprecated"}:
            return False, f"key_status_{self.status}"
        if self.not_before is not None and now < self.not_before:
            return False, "key_not_yet_valid"
        if self.not_after is not None and now > self.not_after:
            return False, "key_expired"
        return True, "allowed"

    def load_secret(self) -> str | None:
        if not self.secret_file:
            return None
        try:
            secret = Path(self.secret_file).read_text(encoding="utf-8").strip()
        except OSError:
            return None
        return secret or None


class HMACKeyRegistry:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> dict[str, HMACKeyRecord]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        keys = raw.get("keys", raw)
        if not isinstance(keys, dict):
            return {}
        return {str(key_id): HMACKeyRecord.from_dict(str(key_id), data) for key_id, data in keys.items() if isinstance(data, dict)}

    def get(self, key_id: str) -> HMACKeyRecord | None:
        return self.load().get(key_id)
