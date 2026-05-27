from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .pointer_os import PointerManager, RetrievalPolicy


def _manager(args: argparse.Namespace) -> PointerManager:
    return PointerManager(args.pointer_path, args.audit_path)


def _print_payload(payload: Any, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                print(_format_pointer_line(item))
            else:
                print(item)
        return
    if isinstance(payload, dict) and "pointer_id" in payload:
        print(_format_pointer_line(payload))
        return
    print(payload)


def _format_pointer_line(pointer: dict[str, Any]) -> str:
    return (
        f"{pointer.get('pointer_id')} "
        f"type={pointer.get('context_type')} "
        f"status={pointer.get('status')} "
        f"trust={pointer.get('trust_score')} "
        f"priority={pointer.get('priority')} "
        f"location={pointer.get('location')}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect and manage Context Pointer OS pointers.")
    parser.add_argument("--pointer-path", default="cpos/pointers.jsonl")
    parser.add_argument("--audit-path", default="cpos/audit_log.jsonl")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_cmd = subparsers.add_parser("list", help="List retrievable pointers.")
    list_cmd.add_argument("--context-type")
    list_cmd.add_argument("--query")
    list_cmd.add_argument("--limit", type=int)
    list_cmd.add_argument("--minimum-trust-score", type=float, default=0.0)
    list_cmd.add_argument("--include-restricted", action="store_true")
    list_cmd.add_argument("--json", action="store_true")

    retrieve_cmd = subparsers.add_parser("retrieve", help="Retrieve context through governance.")
    retrieve_cmd.add_argument("pointer_id")
    retrieve_cmd.add_argument("--agent-id", default="PointerCLI")
    retrieve_cmd.add_argument("--purpose", default="manual_retrieval")
    retrieve_cmd.add_argument("--allowed-context-type", action="append", default=[])
    retrieve_cmd.add_argument("--minimum-trust-score", type=float, default=0.0)
    retrieve_cmd.add_argument("--include-restricted", action="store_true")
    retrieve_cmd.add_argument("--json", action="store_true")

    invalidate_cmd = subparsers.add_parser("invalidate", help="Invalidate a pointer.")
    invalidate_cmd.add_argument("pointer_id")
    invalidate_cmd.add_argument("--reason", required=True)
    invalidate_cmd.add_argument("--replacement-pointer")
    invalidate_cmd.add_argument("--json", action="store_true")

    trust_cmd = subparsers.add_parser("trust-update", help="Update a pointer trust score.")
    trust_cmd.add_argument("pointer_id")
    trust_cmd.add_argument("--score", type=float, required=True)
    trust_cmd.add_argument("--reason", required=True)
    trust_cmd.add_argument("--json", action="store_true")

    exchange_cmd = subparsers.add_parser("exchange", help="Record a multi-agent pointer exchange event.")
    exchange_cmd.add_argument("pointer_id")
    exchange_cmd.add_argument("--from-agent", required=True)
    exchange_cmd.add_argument("--to-agent", required=True)
    exchange_cmd.add_argument("--purpose", required=True)
    exchange_cmd.add_argument("--access-level", default="internal")
    exchange_cmd.add_argument("--json", action="store_true")

    return parser


def _policy_from_args(args: argparse.Namespace) -> RetrievalPolicy:
    levels = ["public", "internal", "private", "restricted"] if args.include_restricted else ["public", "internal"]
    return RetrievalPolicy(
        allowed_context_types=getattr(args, "allowed_context_type", []) or [],
        minimum_trust_score=args.minimum_trust_score,
        allowed_sensitivity_levels=levels,
    )


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    manager = _manager(args)

    if args.command == "list":
        policy = _policy_from_args(args)
        pointers = manager.search(
            context_type=args.context_type,
            query=args.query,
            policy=policy,
            limit=args.limit,
        )
        _print_payload([pointer.to_dict() for pointer in pointers], as_json=args.json)
        return

    if args.command == "retrieve":
        policy = _policy_from_args(args)
        result = manager.retrieve_context(
            args.pointer_id,
            agent_id=args.agent_id,
            purpose=args.purpose,
            policy=policy,
        )
        if result is None:
            if args.json:
                print(json.dumps({"ok": False, "pointer_id": args.pointer_id, "error": "not_found_or_denied"}, ensure_ascii=False, indent=2))
            else:
                print(f"not_found_or_denied: {args.pointer_id}")
            raise SystemExit(1)
        if args.json:
            print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
        else:
            pointer = result["pointer"]
            print(_format_pointer_line(pointer))
            context = result.get("snippet") or result.get("context")
            if context is not None:
                reconstruction = result.get("reconstruction") or {}
                if reconstruction.get("mode") == "line_window":
                    print(f"--- snippet lines {reconstruction.get('line_start')}-{reconstruction.get('line_end')} target={reconstruction.get('target_line')} ---")
                else:
                    print("--- context ---")
                print(context, end="" if context.endswith("\n") else "\n")
        return

    if args.command == "invalidate":
        try:
            pointer = manager.invalidate_pointer(
                args.pointer_id,
                reason=args.reason,
                replacement_pointer=args.replacement_pointer,
            )
        except ValueError as exc:
            print(str(exc))
            raise SystemExit(2)
        if pointer is None:
            if args.json:
                print(json.dumps({"ok": False, "pointer_id": args.pointer_id, "error": "not_found"}, ensure_ascii=False, indent=2))
            else:
                print(f"not_found: {args.pointer_id}")
            raise SystemExit(1)
        payload = {"ok": True, "pointer": pointer.to_dict()}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(_format_pointer_line(payload["pointer"]))
        return

    if args.command == "trust-update":
        pointer = manager.update_trust_score(args.pointer_id, args.score, reason=args.reason)
        if pointer is None:
            if args.json:
                print(json.dumps({"ok": False, "pointer_id": args.pointer_id, "error": "not_found"}, ensure_ascii=False, indent=2))
            else:
                print(f"not_found: {args.pointer_id}")
            raise SystemExit(1)
        payload = {"ok": True, "pointer": pointer.to_dict()}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(_format_pointer_line(payload["pointer"]))
        return

    if args.command == "exchange":
        event = manager.exchange_pointer(
            from_agent=args.from_agent,
            to_agent=args.to_agent,
            pointer_id=args.pointer_id,
            purpose=args.purpose,
            access_level=args.access_level,
        )
        if args.json:
            print(json.dumps({"ok": True, "exchange": event}, ensure_ascii=False, indent=2))
        else:
            print(f"exchange: {event['from_agent']} -> {event['to_agent']} pointer={event['pointer']} purpose={event['purpose']}")
        return


if __name__ == "__main__":
    main()
