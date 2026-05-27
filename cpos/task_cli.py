from __future__ import annotations

import argparse
import json

from .task_tape import TaskTapeStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect and operate CPOS task tape.")
    parser.add_argument("--tape-path", default="tapes/task_runs.jsonl")
    parser.add_argument("--checkpoint-path", default="tapes/task_checkpoints.jsonl")
    subparsers = parser.add_subparsers(dest="command", required=True)

    summary = subparsers.add_parser("summary", help="Show task tape summary.")
    summary.add_argument("--json", action="store_true")

    events = subparsers.add_parser("events", help="List task tape events.")
    events.add_argument("--task-id")
    events.add_argument("--target")
    events.add_argument("--json", action="store_true")

    checkpoints = subparsers.add_parser("checkpoints", help="List checkpoints.")
    checkpoints.add_argument("--task-id")
    checkpoints.add_argument("--target")
    checkpoints.add_argument("--json", action="store_true")

    rollback = subparsers.add_parser("rollback-latest", help="Restore latest checkpoint for a task or target.")
    rollback.add_argument("--task-id")
    rollback.add_argument("--target")
    rollback.add_argument("--json", action="store_true")

    return parser


def _store(args: argparse.Namespace) -> TaskTapeStore:
    return TaskTapeStore(args.tape_path, args.checkpoint_path)


def _print(payload, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if isinstance(payload, list):
        for row in payload:
            print(_compact_row(row))
        return
    if isinstance(payload, dict):
        for key, value in payload.items():
            print(f"{key}: {value}")
        return
    print(payload)


def _compact_row(row: dict) -> str:
    if "event" in row:
        return f"{row.get('timestamp')} {row.get('task_id')} {row.get('event')} status={row.get('status')} target={row.get('target')} checkpoint={row.get('checkpoint_id') or '-'}"
    if "checkpoint_id" in row:
        return f"{row.get('created_at')} {row.get('checkpoint_id')} task={row.get('task_id')} target={row.get('target')} sha={row.get('content_sha256')}"
    return str(row)


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    store = _store(args)

    if args.command == "summary":
        _print(store.summary(), as_json=args.json)
        return

    if args.command == "events":
        rows = [event.to_dict() for event in store.events()]
        if args.task_id:
            rows = [row for row in rows if row["task_id"] == args.task_id]
        if args.target:
            rows = [row for row in rows if row.get("target") == args.target]
        _print(rows, as_json=args.json)
        return

    if args.command == "checkpoints":
        rows = [checkpoint.to_dict() for checkpoint in store.checkpoints()]
        if args.task_id:
            rows = [row for row in rows if row["task_id"] == args.task_id]
        if args.target:
            rows = [row for row in rows if row.get("target") == args.target]
        _print(rows, as_json=args.json)
        return

    if args.command == "rollback-latest":
        if not args.task_id and not args.target:
            payload = {"ok": False, "error": "task_id_or_target_required"}
            _print(payload, as_json=args.json)
            raise SystemExit(2)
        result = store.rollback_latest(target=args.target, task_id=args.task_id)
        _print(result, as_json=args.json)
        if not result.get("ok"):
            raise SystemExit(1)
        return


if __name__ == "__main__":
    main()
