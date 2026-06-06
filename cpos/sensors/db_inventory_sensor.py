from __future__ import annotations

import argparse
import fnmatch
import json
import re
from pathlib import Path
from typing import Any

from .base import sensor_event

DB_PATTERNS = ("*.db", "*.sqlite", "*.sqlite3")
DEFAULT_SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "target",
    "build",
    "dist",
}
SENSITIVE_PATH_PATTERN = re.compile(
    r"(credential|credentials|access[_-]?token|token|secret|oauth|cookie|session|browser|keyring|gcloud|\.config/gcloud)",
    re.IGNORECASE,
)
REFLECTION_CANDIDATE_PATTERN = re.compile(
    r"(gemini|antigravity|conversation|spirit|neuro|emilia|journal|memory|agent|discord|llm|prompt)",
    re.IGNORECASE,
)


def _matches_db(path: Path) -> bool:
    name = path.name.lower()
    return any(fnmatch.fnmatch(name, pattern) for pattern in DB_PATTERNS)


def _is_under_skipped_dir(path: Path, root: Path, skip_dir_names: set[str]) -> bool:
    try:
        relative_parts = path.relative_to(root).parts
    except ValueError:
        relative_parts = path.parts
    return any(part in skip_dir_names for part in relative_parts[:-1])


def classify_db_path(relative_path: str) -> dict[str, Any]:
    normalized = relative_path.replace("\\", "/")
    sensitive = bool(SENSITIVE_PATH_PATTERN.search(normalized))
    reflection_candidate = bool(REFLECTION_CANDIDATE_PATTERN.search(normalized)) and not sensitive
    if sensitive:
        category = "sensitive_skipped"
        risk = "high"
        suggested = "do_not_open_without_explicit_review"
    elif reflection_candidate:
        category = "reflection_candidate"
        risk = "medium"
        suggested = "schema_only_review_before_any_content_access"
    else:
        category = "db_candidate"
        risk = "medium"
        suggested = "inventory_only_continue_observing"
    return {
        "category": category,
        "risk": risk,
        "reflection_candidate": reflection_candidate,
        "sensitive_skipped": sensitive,
        "suggested_next_action": suggested,
    }


def _candidate_record(path: Path, root: Path) -> dict[str, Any]:
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        relative = path.as_posix()
    classification = classify_db_path(relative)
    try:
        stat = path.stat()
        size_bytes = stat.st_size
        modified_ns = stat.st_mtime_ns
        stat_ok = True
    except OSError:
        size_bytes = None
        modified_ns = None
        stat_ok = False
    return {
        "path": relative,
        "suffix": path.suffix.lower(),
        "size_bytes": size_bytes,
        "modified_ns": modified_ns,
        "stat_ok": stat_ok,
        "db_opened": False,
        "schema_read": False,
        "row_contents_read": False,
        "table_names_read": False,
        **classification,
    }


def inventory_db_paths(
    root: str | Path = ".",
    *,
    max_candidates: int = 200,
    skip_dir_names: set[str] | None = None,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    skips = set(DEFAULT_SKIP_DIR_NAMES if skip_dir_names is None else skip_dir_names)
    candidates: list[dict[str, Any]] = []
    skipped_dir_count = 0

    for path in root_path.rglob("*"):
        if _is_under_skipped_dir(path, root_path, skips):
            skipped_dir_count += 1
            continue
        if not path.is_file() or not _matches_db(path):
            continue
        candidates.append(_candidate_record(path, root_path))
        if len(candidates) >= max_candidates:
            break

    sensitive_count = sum(1 for item in candidates if item["sensitive_skipped"])
    reflection_count = sum(1 for item in candidates if item["reflection_candidate"])
    risk = "high" if sensitive_count else ("medium" if candidates else "low")
    event_type = "db_source_inventory_available" if candidates else "db_source_inventory_empty"
    summary = f"found {len(candidates)} database candidate(s); {sensitive_count} sensitive skipped; {reflection_count} reflection candidate(s)"

    return sensor_event(
        source="db_inventory",
        event_type=event_type,
        target=root_path,
        summary=summary,
        risk=risk,
        confidence=0.85,
        source_of_truth=["filesystem path inventory only"],
        requires_human_review=bool(sensitive_count),
        suggested_next_action="review_sensitive_skips_before_schema_or_content_access" if sensitive_count else "continue_observing",
        metadata={
            "root": str(root_path),
            "max_candidates": max_candidates,
            "candidate_count": len(candidates),
            "sensitive_skipped_count": sensitive_count,
            "reflection_candidate_count": reflection_count,
            "skipped_dir_count": skipped_dir_count,
            "skip_dir_names": sorted(skips),
            "db_patterns": list(DB_PATTERNS),
            "candidates": candidates,
            "db_files_opened": False,
            "table_names_read": False,
            "row_contents_read": False,
            "prompt_text_read": False,
            "diary_text_read": False,
            "token_values_read": False,
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only path-only DB inventory sensor.")
    parser.add_argument("--root", default=".", help="Root path to scan for DB file names.")
    parser.add_argument("--max-candidates", type=int, default=200, help="Maximum candidate DB paths to report.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    event = inventory_db_paths(args.root, max_candidates=args.max_candidates)
    if args.json:
        print(json.dumps(event, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{event['event_type']}: {event['summary']}")


if __name__ == "__main__":
    main()
