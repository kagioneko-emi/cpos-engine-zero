from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .hash_chain import append_chained_jsonl, read_jsonl, verify_hash_chain
from .pointer_os import utc_now

VALID_STATUSES = {
    "review",
    "stored_in_vault",
    "render_verified",
    "preflight_passed",
    "cleanup_approved",
    "removed",
}


def load_inventory(path: str | Path) -> list[dict[str, Any]]:
    return read_jsonl(path)


def latest_records(path: str | Path) -> dict[str, dict[str, Any]]:
    records = {}
    for row in load_inventory(path):
        records[row["artifact_path"]] = row
    return records


def add_artifact(path: str | Path, *, artifact_path: str, artifact_type: str, vault_path: str, field: str, runtime_destination: str | None = None, owner: str | None = None, notes: str | None = None, status: str = "review") -> dict[str, Any]:
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid status: {status}")
    row = {
        "event": "artifact_added",
        "artifact_path": artifact_path,
        "artifact_type": artifact_type,
        "vault_path": vault_path,
        "field": field,
        "runtime_destination": runtime_destination,
        "owner": owner,
        "status": status,
        "notes": notes,
        "timestamp": utc_now(),
    }
    return append_chained_jsonl(path, row)


def mark_status(path: str | Path, *, artifact_path: str, status: str, notes: str | None = None) -> dict[str, Any]:
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid status: {status}")
    current = latest_records(path).get(artifact_path)
    if current is None:
        raise KeyError("artifact_not_found")
    row = {key: value for key, value in current.items() if key != "_chain"}
    row.update({"event": "status_marked", "status": status, "notes": notes, "timestamp": utc_now()})
    return append_chained_jsonl(path, row)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Track secret artifact Vault migration metadata without storing secret values.")
    parser.add_argument("--inventory-path", default="cpos/secret_inventory.jsonl")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add")
    add.add_argument("artifact_path")
    add.add_argument("--type", required=True, dest="artifact_type")
    add.add_argument("--vault-path", required=True)
    add.add_argument("--field", required=True)
    add.add_argument("--runtime-destination")
    add.add_argument("--owner")
    add.add_argument("--status", default="review", choices=sorted(VALID_STATUSES))
    add.add_argument("--notes")
    add.add_argument("--json", action="store_true")

    mark = sub.add_parser("mark")
    mark.add_argument("artifact_path")
    mark.add_argument("--status", required=True, choices=sorted(VALID_STATUSES))
    mark.add_argument("--notes")
    mark.add_argument("--json", action="store_true")

    list_cmd = sub.add_parser("list")
    list_cmd.add_argument("--json", action="store_true")

    verify = sub.add_parser("verify")
    verify.add_argument("--json", action="store_true")
    return parser


def _print(payload: Any, *, as_json: bool):
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if isinstance(payload, list):
        for row in payload:
            print(f"{row.get('artifact_path')} status={row.get('status')} vault={row.get('vault_path')} field={row.get('field')}")
    else:
        print(payload)


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "add":
            row = add_artifact(
                args.inventory_path,
                artifact_path=args.artifact_path,
                artifact_type=args.artifact_type,
                vault_path=args.vault_path,
                field=args.field,
                runtime_destination=args.runtime_destination,
                owner=args.owner,
                notes=args.notes,
                status=args.status,
            )
            _print({"ok": True, "record": row}, as_json=args.json)
            return
        if args.command == "mark":
            row = mark_status(args.inventory_path, artifact_path=args.artifact_path, status=args.status, notes=args.notes)
            _print({"ok": True, "record": row}, as_json=args.json)
            return
        if args.command == "list":
            _print(list(latest_records(args.inventory_path).values()), as_json=args.json)
            return
        if args.command == "verify":
            result = verify_hash_chain(args.inventory_path)
            _print(result, as_json=args.json)
            if not result.get("ok"):
                raise SystemExit(1)
            return
    except (ValueError, KeyError) as exc:
        _print({"ok": False, "error": str(exc)}, as_json=getattr(args, "json", False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
