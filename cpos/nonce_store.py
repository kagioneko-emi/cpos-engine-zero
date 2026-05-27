from __future__ import annotations

from pathlib import Path
import json


class NonceStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def seen(self, nonce: str, *, now: int, ttl_seconds: int) -> bool:
        cutoff = now - ttl_seconds
        if not self.path.exists():
            return False
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("nonce") == nonce and int(row.get("timestamp", 0)) >= cutoff:
                    return True
        return False

    def remember(self, nonce: str, *, timestamp: int) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"nonce": nonce, "timestamp": timestamp}, ensure_ascii=False) + "\n")
