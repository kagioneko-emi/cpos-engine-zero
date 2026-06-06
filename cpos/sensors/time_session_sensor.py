from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .base import sensor_event


def classify_hour(hour: int) -> tuple[str, str, bool, str]:
    if 0 <= hour < 5:
        return "late_night_session", "medium", True, "handoff_then_rest_recommended"
    if 5 <= hour < 8:
        return "early_morning_session", "low", False, "continue_observing"
    if 22 <= hour <= 23:
        return "late_evening_session", "low", False, "avoid_high_stakes_if_tired"
    return "normal_session_time", "low", False, "continue_observing"


def observe_time_session(target: str | Path = ".", tz_name: str = "Asia/Tokyo", now: datetime | None = None) -> dict[str, object]:
    tz = ZoneInfo(tz_name)
    current = now.astimezone(tz) if now else datetime.now(tz)
    event_type, risk, review, suggested = classify_hour(current.hour)
    summary = f"local session time is {current.strftime('%H:%M')} ({tz_name})"
    if event_type == "late_night_session":
        summary += "; prefer handoff/rest before high-stakes actions"
    return sensor_event(
        source="time",
        event_type=event_type,
        target=target,
        summary=summary,
        risk=risk,
        confidence=0.9,
        source_of_truth=["local clock"],
        requires_human_review=review,
        suggested_next_action=suggested,
        observed_at=current.isoformat(timespec="seconds"),
        metadata={
            "timezone": tz_name,
            "local_hour": current.hour,
            "weekday": current.strftime("%A"),
            "wellbeing_advisory": event_type == "late_night_session",
            "blocks_ordinary_work": False,
            "extra_confirmation_for_high_stakes": event_type == "late_night_session",
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only metadata-only time/session sensor.")
    parser.add_argument("--target", default=".", help="Target workspace path for the observation.")
    parser.add_argument("--timezone", default="Asia/Tokyo", help="IANA timezone name.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    event = observe_time_session(args.target, tz_name=args.timezone)
    if args.json:
        print(json.dumps(event, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{event['event_type']}: {event['summary']}")


if __name__ == "__main__":
    main()
