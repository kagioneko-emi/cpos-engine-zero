from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import os
import time
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback, tests run on Linux.
    fcntl = None


@dataclass
class InMemoryRateLimiter:
    buckets: dict[str, list[float]] = field(default_factory=dict)

    def allow(self, key: str, *, limit: int, window_seconds: int, now: float | None = None) -> tuple[bool, int, float]:
        now = time.time() if now is None else now
        cutoff = now - window_seconds
        events = [ts for ts in self.buckets.get(key, []) if ts > cutoff]
        allowed = len(events) < limit
        if allowed:
            events.append(now)
        self.buckets[key] = events
        remaining = max(0, limit - len(events))
        reset_after = max(0.0, window_seconds - (now - events[0])) if events else float(window_seconds)
        return allowed, remaining, reset_after

    def clear(self) -> None:
        self.buckets.clear()


class FileBackedRateLimiter:
    """Small persistent sliding-window limiter using a locked JSON file.

    This is intended for single-host multi-process deployments. It avoids adding
    Redis/Valkey as a hard dependency while letting Gunicorn workers share rate
    limit state. The store contains timestamps only; no tokens, headers, or
    request bodies are recorded.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def allow(self, key: str, *, limit: int, window_seconds: int, now: float | None = None) -> tuple[bool, int, float]:
        now = time.time() if now is None else now
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8") as fh:
            if fcntl is not None:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                fh.seek(0)
                state = self._read_state(fh.read())
                cutoff = now - window_seconds
                buckets = state.setdefault("buckets", {})
                events = [float(ts) for ts in buckets.get(key, []) if float(ts) > cutoff]
                allowed = len(events) < limit
                if allowed:
                    events.append(now)
                buckets[key] = events
                self._prune(buckets, cutoff)
                remaining = max(0, limit - len(events))
                reset_after = max(0.0, window_seconds - (now - events[0])) if events else float(window_seconds)
                self._atomic_write_locked(fh, state)
                return allowed, remaining, reset_after
            finally:
                if fcntl is not None:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    def clear(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"version": 1, "buckets": {}}, ensure_ascii=False) + "\n", encoding="utf-8")

    @staticmethod
    def _read_state(raw: str) -> dict[str, Any]:
        if not raw.strip():
            return {"version": 1, "buckets": {}}
        try:
            state = json.loads(raw)
        except json.JSONDecodeError:
            return {"version": 1, "buckets": {}}
        if not isinstance(state, dict):
            return {"version": 1, "buckets": {}}
        if not isinstance(state.get("buckets"), dict):
            state["buckets"] = {}
        return state

    @staticmethod
    def _prune(buckets: dict[str, list[float]], cutoff: float) -> None:
        empty = []
        for bucket_key, events in buckets.items():
            buckets[bucket_key] = [float(ts) for ts in events if float(ts) > cutoff]
            if not buckets[bucket_key]:
                empty.append(bucket_key)
        for bucket_key in empty:
            buckets.pop(bucket_key, None)

    def _atomic_write_locked(self, fh, state: dict[str, Any]) -> None:
        # Keep the advisory lock on the same inode while updating. This favors
        # inter-process correctness over rename-based replacement.
        payload = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        fh.seek(0)
        fh.truncate(0)
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())


class RedisRateLimiter:
    """Optional Redis/Valkey sliding-window limiter.

    Requires the optional `redis` Python package at runtime. Connection URLs that
    include credentials should be provided via a Vault-rendered file, not a .env
    or command line.
    """

    def __init__(self, url: str, *, key_prefix: str = "cpos:rate_limit"):
        try:
            import redis  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency path
            raise RuntimeError("redis_dependency_missing") from exc
        self.client = redis.Redis.from_url(url, decode_responses=True)
        self.key_prefix = key_prefix.rstrip(":")

    def allow(self, key: str, *, limit: int, window_seconds: int, now: float | None = None) -> tuple[bool, int, float]:
        now = time.time() if now is None else now
        redis_key = f"{self.key_prefix}:{key}"
        cutoff = now - window_seconds
        member = f"{now:.6f}:{os.getpid()}:{id(self)}"
        pipe = self.client.pipeline()
        pipe.zremrangebyscore(redis_key, 0, cutoff)
        pipe.zcard(redis_key)
        removed, count = pipe.execute()
        allowed = int(count) < limit
        if allowed:
            pipe = self.client.pipeline()
            pipe.zadd(redis_key, {member: now})
            pipe.expire(redis_key, max(1, int(window_seconds * 2)))
            pipe.zcard(redis_key)
            _, _, count_after = pipe.execute()
            count = int(count_after)
        oldest = self.client.zrange(redis_key, 0, 0, withscores=True)
        remaining = max(0, limit - int(count))
        reset_after = float(window_seconds)
        if oldest:
            reset_after = max(0.0, window_seconds - (now - float(oldest[0][1])))
        return allowed, remaining, reset_after

    def clear(self) -> None:
        # Intentionally no global scan/delete; use Redis TTLs or admin tooling.
        return None
