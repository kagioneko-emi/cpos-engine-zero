#!/usr/bin/env python3
"""Minimal CPOS External Agent Adapter client.

This example uses only the Python standard library and never prints token values.
For protected CPOS deployments, pass a Vault-rendered token file with
`--token-file`; do not hardcode tokens in code, shell history, or .env files.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _read_token(path: str | None) -> str | None:
    if not path:
        return None
    token = Path(path).read_text(encoding="utf-8").strip()
    return token or None


def _post_json(url: str, payload: dict[str, Any], token: str | None = None) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as res:  # nosec B310: caller supplies CPOS URL intentionally
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "status": exc.code, "error": "http_error", "detail": detail}


def build_command_request(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "agent_name": args.agent_name,
        "event_type": "command_request",
        "commands": args.command,
        "changed_files": args.changed_file,
        "metadata": {
            "risk": args.risk,
            "requires_human_approval": True,
            "client": "examples/agent_adapter_client.py",
        },
    }


def build_execution_result(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "agent_name": args.agent_name,
        "event_type": "execution_result",
        "execution_result": {
            "status": "success" if args.success else "failed",
            "output_redacted": True,
        },
        "commands": args.command,
        "changed_files": args.changed_file,
        "metadata": {
            "success": args.success,
            "exit_code": args.exit_code,
            "failure_kind": args.failure_kind,
            "duration_ms": args.duration_ms,
            "client": "examples/agent_adapter_client.py",
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Submit metadata-only events to CPOS External Agent Adapter.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080", help="CPOS base URL; prefer localhost or a protected HTTPS endpoint.")
    parser.add_argument("--token-file", help="Optional Vault-rendered bearer token file. Token value is never printed.")
    parser.add_argument("--agent-name", default="example-external-agent")
    parser.add_argument("--command", action="append", default=[], help="Command metadata to hash/store; repeatable. Do not include secrets.")
    parser.add_argument("--changed-file", action="append", default=[], help="Changed file path metadata; repeatable.")
    parser.add_argument("--risk", default="medium", choices=["low", "medium", "high", "critical"])
    parser.add_argument("--send", action="store_true", help="Actually POST to CPOS. Without this, print sanitized JSON payload only.")

    sub = parser.add_subparsers(dest="kind", required=True)
    sub.add_parser("command-request", help="Submit a command_request review contract.")
    result = sub.add_parser("execution-result", help="Submit a metadata-only execution_result scoreboard record.")
    result.add_argument("--success", action="store_true", help="Mark result as success. Default is failure.")
    result.add_argument("--exit-code", type=int, default=1)
    result.add_argument("--failure-kind", default="validation_command")
    result.add_argument("--duration-ms", type=int, default=0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_command_request(args) if args.kind == "command-request" else build_execution_result(args)
    if not args.send:
        print(json.dumps({"dry_run": True, "url": f"{args.base_url.rstrip('/')}/agent-adapter/intake", "payload": payload}, ensure_ascii=False, indent=2))
        return 0
    token = _read_token(args.token_file)
    result = _post_json(f"{args.base_url.rstrip('/')}/agent-adapter/intake", payload, token=token)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
