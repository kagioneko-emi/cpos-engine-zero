from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

SENSOR_SCHEMA = "kagioneko.sensor_event.v1"
SAFETY_FLAGS = {
    "metadata_only": True,
    "raw_request_stored": False,
    "raw_diff_stored": False,
    "raw_outputs_stored": False,
    "secret_values_stored": False,
    "execute_automatically": False,
}
ALLOWED_RISKS = {"low", "medium", "high", "critical"}


def now_iso(tz_name: str = "Asia/Tokyo") -> str:
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
    return datetime.now(tz).isoformat(timespec="seconds")


def stable_event_id(*parts: Any) -> str:
    text = "\x1f".join(str(part) for part in parts)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]
    return f"sensor_evt_{digest}"


def sensor_event(
    *,
    source: str,
    event_type: str,
    target: str | Path,
    summary: str,
    risk: str = "low",
    confidence: float = 0.9,
    source_of_truth: list[str] | None = None,
    requires_human_review: bool = False,
    suggested_next_action: str = "continue_observing",
    observed_at: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_risk = risk if risk in ALLOWED_RISKS else "medium"
    ts = observed_at or now_iso()
    target_text = str(Path(target).resolve()) if str(target) else ""
    return {
        "schema": SENSOR_SCHEMA,
        "event_id": stable_event_id(source, event_type, target_text, summary, ts),
        "source": source,
        "event_type": event_type,
        "observed_at": ts,
        "target": target_text,
        "summary": summary,
        "risk": normalized_risk,
        "confidence": float(confidence),
        "source_of_truth": source_of_truth or [],
        "requires_human_review": bool(requires_human_review),
        "suggested_next_action": suggested_next_action,
        **SAFETY_FLAGS,
        "metadata": metadata or {},
    }
