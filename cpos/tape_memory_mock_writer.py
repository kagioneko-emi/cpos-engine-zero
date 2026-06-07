from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .resume_pointer import (
    SAFETY_FLAGS,
    build_tape_memory_write_plan,
    load_json_file,
    validate_resume_pointer,
)
from .secret_scan import PATTERNS

CONFIRMATION_PHRASE = "WRITE TAPE MEMORY RESUME POINTER"
MOCK_WRITE_SCHEMA = "kagioneko.tape_memory_mock_write.v1"
MOCK_BACKEND = "local_mock_file_for_tests_only"


def _error(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _safe_record_name(pointer: dict[str, Any], payload: str) -> str:
    commit = str(pointer.get("commit") or "unknown")
    commit = re.sub(r"[^A-Za-z0-9_.-]", "_", commit)[:40] or "unknown"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"cpos_resume_pointer_{commit}_{digest}.json"


def scan_payload_text(text: str) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for name, pattern in PATTERNS:
            if pattern.search(line):
                findings.append({"line": lineno, "pattern": name})
    return findings


def build_mock_write_result(
    pointer: dict[str, Any],
    *,
    output_dir: str | Path,
    confirm_write: str | None,
) -> dict[str, Any]:
    """Write a metadata-only pointer to a local mock file for tests.

    This is deliberately not a tape-memory backend adapter. It requires the same
    explicit confirmation phrase planned for a future real writer so fail-closed
    behavior can be tested before any real backend exists.
    """

    validation = validate_resume_pointer(pointer)
    plan = build_tape_memory_write_plan(pointer)
    payload = json.dumps(pointer, ensure_ascii=False, sort_keys=True, indent=2)
    secret_findings = scan_payload_text(payload)
    errors: list[dict[str, str]] = []

    if confirm_write != CONFIRMATION_PHRASE:
        errors.append(_error("confirmation_phrase_mismatch", "exact confirmation phrase is required for mock writes"))
    if not validation.get("ok"):
        errors.append(_error("resume_pointer_validation_failed", "resume pointer validation must pass before mock write"))
    if secret_findings:
        errors.append(_error("secret_scan_failed", "payload secret scan must pass before mock write"))
    if plan.get("write_enabled") is not False or plan.get("would_write") is not False:
        errors.append(_error("dry_run_plan_must_be_disabled", "write plan must remain disabled before mock write"))

    base = Path(output_dir)
    target_path: Path | None = None
    if not base.exists():
        errors.append(_error("output_dir_missing", "mock output_dir must already exist and be explicit"))
    elif not base.is_dir():
        errors.append(_error("output_dir_not_directory", "mock output_dir must be a directory"))
    else:
        target_path = base / _safe_record_name(pointer, payload)

    result: dict[str, Any] = {
        "schema": MOCK_WRITE_SCHEMA,
        "ok": not errors,
        "mock_backend": MOCK_BACKEND,
        "real_tape_memory_write": False,
        "wrote": False,
        "target_path": str(target_path) if target_path else None,
        "confirmation_phrase_accepted": confirm_write == CONFIRMATION_PHRASE,
        "confirmation_phrase_stored": False,
        "resume_pointer_validation_ok": bool(validation.get("ok")),
        "secret_scan": {
            "ok": not secret_findings,
            "count": len(secret_findings),
            "findings": secret_findings,
        },
        "dry_run_plan": {
            "schema": plan.get("schema"),
            "would_write": plan.get("would_write"),
            "write_enabled": plan.get("write_enabled"),
            "validation_ok": plan.get("validation_ok"),
        },
        "errors": errors,
        "error_codes": [error["code"] for error in errors],
        **SAFETY_FLAGS,
    }

    if errors:
        return result

    assert target_path is not None
    envelope = {
        "schema": MOCK_WRITE_SCHEMA,
        "mock_backend": MOCK_BACKEND,
        "real_tape_memory_write": False,
        "payload_schema": pointer.get("schema"),
        "payload_pointer_type": pointer.get("pointer_type"),
        "payload_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "payload": pointer,
        "audit": {
            "confirmation_phrase_accepted": True,
            "confirmation_phrase_stored": False,
            "secret_scan_ok": True,
            "secret_scan_count": 0,
            "resume_pointer_validation_ok": True,
        },
        **SAFETY_FLAGS,
    }
    target_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    result["wrote"] = True
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Test-only local mock writer for CPOS resume pointers.")
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write", help="Write a pointer to an explicit local mock file target only.")
    write.add_argument("--pointer-json", required=True, help="Resume pointer JSON file.")
    write.add_argument("--output-dir", required=True, help="Existing local directory for test-only mock output.")
    write.add_argument("--confirm-write", required=True, help="Must exactly match the real-write confirmation phrase.")
    write.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "write":
        result = build_mock_write_result(
            load_json_file(args.pointer_json) or {},
            output_dir=args.output_dir,
            confirm_write=args.confirm_write,
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"tape_memory_mock_writer: ok={result['ok']} wrote={result['wrote']}")
        if not result["ok"]:
            raise SystemExit(1)
        return
    raise SystemExit(2)


if __name__ == "__main__":
    main()
