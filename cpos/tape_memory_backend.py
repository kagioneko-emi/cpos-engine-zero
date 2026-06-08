from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import MutableSequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .resume_pointer import POINTER_SCHEMA, VALIDATION_SCHEMA

FAKE_BACKEND_SCHEMA = "kagioneko.tape_memory_backend_fake.v1"
CONFIRMATION_PHRASE = "WRITE TAPE MEMORY RESUME POINTER"


def _error(code: str, field: str, message: str) -> dict[str, str]:
    return {"code": code, "field": field, "message": message}


def _canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _payload_hash(pointer: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(pointer).encode("utf-8")).hexdigest()


@runtime_checkable
class TapeMemoryBackendProtocol(Protocol):
    def write_resume_pointer(
        self,
        *,
        pointer: dict[str, Any],
        validation: dict[str, Any],
        secret_scan: dict[str, Any],
        target: dict[str, Any],
        confirmation: dict[str, Any],
        audit: dict[str, Any],
    ) -> dict[str, Any]:
        ...


def validate_backend_write_request(
    *,
    pointer: dict[str, Any] | None,
    validation: dict[str, Any] | None,
    secret_scan: dict[str, Any] | None,
    target: dict[str, Any] | None,
    confirmation: dict[str, Any] | None,
    audit: dict[str, Any] | None,
) -> dict[str, Any]:
    pointer = pointer or {}
    validation = validation or {}
    secret_scan = secret_scan or {}
    target = target or {}
    confirmation = confirmation or {}
    audit = audit or {}

    errors: list[dict[str, str]] = []

    if pointer.get("schema") != POINTER_SCHEMA:
        errors.append(_error("invalid_pointer_schema", "pointer.schema", f"pointer schema must be {POINTER_SCHEMA}"))
    if pointer.get("pointer_type") != "cpos_resume":
        errors.append(_error("invalid_pointer_type", "pointer.pointer_type", "pointer_type must be cpos_resume"))

    if validation.get("schema") != VALIDATION_SCHEMA:
        errors.append(_error("invalid_validation_schema", "validation.schema", f"validation schema must be {VALIDATION_SCHEMA}"))
    if validation.get("ok") is not True:
        errors.append(_error("validation_failed", "validation.ok", "pointer validation must pass"))

    if secret_scan.get("ok") is not True:
        errors.append(_error("secret_scan_failed", "secret_scan.ok", "secret scan must pass"))
    if secret_scan.get("count") != 0:
        errors.append(_error("secret_scan_nonzero", "secret_scan.count", "secret scan count must be zero"))

    if target.get("backend") != "in_memory_fake":
        errors.append(_error("invalid_backend", "target.backend", "backend must be in_memory_fake for the fake adapter"))
    if target.get("system") != "tape-memory":
        errors.append(_error("invalid_system", "target.system", "target.system must be tape-memory"))
    if target.get("record_type") != "cpos_resume_pointer":
        errors.append(_error("invalid_record_type", "target.record_type", "record_type must be cpos_resume_pointer"))
    if not target.get("path_or_key"):
        errors.append(_error("missing_target", "target.path_or_key", "target.path_or_key must be explicit"))

    if confirmation.get("accepted") is not True:
        errors.append(_error("confirmation_missing", "confirmation.accepted", "exact confirmation must be accepted"))
    if confirmation.get("phrase") != CONFIRMATION_PHRASE:
        errors.append(_error("confirmation_mismatch", "confirmation.phrase", "confirmation phrase must match exactly"))

    if audit.get("metadata_only") is not True:
        errors.append(_error("audit_not_metadata_only", "audit.metadata_only", "audit must be metadata-only"))
    if audit.get("raw_payload_echoed") is True:
        errors.append(_error("audit_echoes_raw_payload", "audit.raw_payload_echoed", "audit must not echo raw payloads"))

    return {
        "schema": FAKE_BACKEND_SCHEMA,
        "ok": not errors,
        "error_count": len(errors),
        "error_codes": sorted({error["code"] for error in errors}),
        "errors": errors,
        "real_tape_memory_write": False,
        "backend": "in_memory_fake",
        "metadata_only": True,
    }


@dataclass
class InMemoryTapeMemoryBackend:
    """Test-only fake backend that records metadata-only envelopes in memory."""

    writes: list[dict[str, Any]] = field(default_factory=list)

    def write_resume_pointer(
        self,
        *,
        pointer: dict[str, Any],
        validation: dict[str, Any],
        secret_scan: dict[str, Any],
        target: dict[str, Any],
        confirmation: dict[str, Any],
        audit: dict[str, Any],
    ) -> dict[str, Any]:
        result = validate_backend_write_request(
            pointer=pointer,
            validation=validation,
            secret_scan=secret_scan,
            target=target,
            confirmation=confirmation,
            audit=audit,
        )
        envelope = {
            "schema": FAKE_BACKEND_SCHEMA,
            "ok": result["ok"],
            "backend": result["backend"],
            "real_tape_memory_write": False,
            "metadata_only": True,
            "payload_hash": _payload_hash(pointer),
            "validation_ok": bool(validation.get("ok")),
            "secret_scan_ok": bool(secret_scan.get("ok")) and secret_scan.get("count") == 0,
            "target": {
                "system": target.get("system"),
                "record_type": target.get("record_type"),
                "path_or_key": target.get("path_or_key"),
                "backend": target.get("backend"),
            },
            "audit": {
                "metadata_only": audit.get("metadata_only") is True,
                "confirmation_accepted": confirmation.get("accepted") is True,
                "confirmation_phrase_stored": False,
                "raw_payload_echoed": False,
            },
            "error_codes": result["error_codes"],
        }
        if result["ok"]:
            self.writes.append(envelope)
        return envelope


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect the test-only tape-memory backend foundation.")
    sub = parser.add_subparsers(dest="command", required=True)
    inspect_parser = sub.add_parser("inspect", help="Print the backend protocol / fake backend metadata.")
    inspect_parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "inspect":
        result = {
            "schema": FAKE_BACKEND_SCHEMA,
            "backend": "in_memory_fake",
            "protocol": "TapeMemoryBackendProtocol",
            "real_tape_memory_write": False,
            "metadata_only": True,
            "confirmation_phrase": CONFIRMATION_PHRASE,
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print("tape_memory_backend: in_memory_fake metadata-only foundation")
        return
    raise SystemExit(2)


if __name__ == "__main__":
    main()
