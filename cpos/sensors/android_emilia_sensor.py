from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .base import sensor_event

DEFAULT_REFERENCES: dict[str, str] = {}


def _reference_record(name: str, path_text: str) -> dict[str, Any]:
    path = Path(path_text).expanduser()
    exists = path.exists()
    is_file = path.is_file() if exists else False
    is_dir = path.is_dir() if exists else False
    try:
        stat = path.stat() if exists else None
        size_bytes = stat.st_size if stat and is_file else None
        modified_ns = stat.st_mtime_ns if stat else None
        stat_ok = exists
    except OSError:
        size_bytes = None
        modified_ns = None
        stat_ok = False
    return {
        "name": name,
        "path": str(path),
        "exists": exists,
        "is_file": is_file,
        "is_dir": is_dir,
        "size_bytes": size_bytes,
        "modified_ns": modified_ns,
        "stat_ok": stat_ok,
        "content_read": False,
        "phone_data_read": False,
        "diary_text_read": False,
        "sensor_stream_read": False,
        "secret_values_read": False,
        "action_triggered": False,
    }


def observe_android_emilia_bridge(references: dict[str, str] | None = None) -> dict[str, Any]:
    refs = DEFAULT_REFERENCES if references is None else references
    records = [_reference_record(name, path) for name, path in refs.items()]
    existing_count = sum(1 for record in records if record["exists"])
    missing_count = len(records) - existing_count
    receiver_exists = any(record["name"] == "vps_receiver" and record["exists"] for record in records)
    android_repo_exists = any(record["name"] == "android_app_repo" and record["exists"] for record in records)

    if existing_count:
        event_type = "android_emilia_bridge_detected"
        risk = "medium"
        summary = f"Android Emilia bridge references detected: {existing_count} present, {missing_count} missing"
    else:
        event_type = "android_emilia_bridge_not_detected"
        risk = "low"
        summary = "Android Emilia bridge references not detected"

    return sensor_event(
        source="android_emilia",
        event_type=event_type,
        target=records[0]["path"] if records else "",
        summary=summary,
        risk=risk,
        confidence=0.85,
        source_of_truth=["path existence/stat inventory only", "docs/ANDROID_EMILIA_SENSOR_BRIDGE.md"],
        requires_human_review=bool(existing_count),
        suggested_next_action="privacy_review_before_any_content_or_sensor_ingestion" if existing_count else "continue_observing",
        metadata={
            "reference_count": len(records),
            "existing_count": existing_count,
            "missing_count": missing_count,
            "android_repo_exists": android_repo_exists,
            "receiver_exists": receiver_exists,
            "references": records,
            "content_read": False,
            "phone_data_read": False,
            "microphone_content_read": False,
            "camera_content_read": False,
            "location_read": False,
            "diary_text_read": False,
            "sensor_stream_read": False,
            "secret_values_read": False,
            "upload_triggered": False,
            "publish_triggered": False,
            "video_pipeline_triggered": False,
            "notification_triggered": False,
            "phone_control_enabled": False,
        },
    )


def _parse_named_refs(values: list[str] | None) -> dict[str, str]:
    refs: dict[str, str] = {}
    for value in values or []:
        if "=" not in value:
            raise SystemExit("--ref must be NAME=PATH")
        name, path = value.split("=", 1)
        if not name or not path:
            raise SystemExit("--ref must be NAME=PATH")
        refs[name] = path
    return refs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Observe-only Android Emilia bridge inventory sensor.")
    parser.add_argument("--android-repo", help="Optional Android app repository path to check.")
    parser.add_argument("--receiver", help="Optional VPS receiver file path to check.")
    parser.add_argument("--article", help="Optional public article path to check.")
    parser.add_argument("--ref", action="append", help="Optional extra named reference in NAME=PATH form. Can be repeated.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    refs = _parse_named_refs(args.ref)
    if args.android_repo:
        refs["android_app_repo"] = args.android_repo
    if args.receiver:
        refs["vps_receiver"] = args.receiver
    if args.article:
        refs["public_article"] = args.article
    event = observe_android_emilia_bridge(refs)
    if args.json:
        print(json.dumps(event, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{event['event_type']}: {event['summary']}")


if __name__ == "__main__":
    main()
