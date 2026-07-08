#!/usr/bin/env python3
"""Small command-line entrypoint for CPOS Engine-Zero.

This is intentionally thin: it exposes the same safe DevOps cycle used by the
webhook server, while keeping credentials out of CLI arguments and files.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from ait_firewall.runtime import AITFirewallRuntime
from engine_zero_agent import EngineZeroAgent


def default_target_dir() -> str:
    return str(Path(__file__).resolve().parent / "target_app")


def read_instruction(args: argparse.Namespace) -> str:
    parts: list[str] = []
    if args.instruction:
        parts.append(args.instruction)
    if args.instruction_file:
        parts.append(Path(args.instruction_file).read_text(encoding="utf-8"))
    instruction = "\n".join(part.strip() for part in parts if part.strip())
    if not instruction:
        raise SystemExit("error: provide --instruction or --instruction-file")
    return instruction


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run CPOS Engine-Zero from the CLI without starting the webhook server."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run one Engine-Zero DevOps cycle.")
    run.add_argument(
        "--target",
        default=default_target_dir(),
        help="Target app directory. Defaults to ./target_app next to this CLI.",
    )
    run.add_argument(
        "--instruction",
        help="High-trust user instruction for the demo fixer. Do not pass secrets here.",
    )
    run.add_argument(
        "--instruction-file",
        help="Read instruction text from a UTF-8 file. Do not store secrets in the file.",
    )
    run.add_argument(
        "--web-context",
        default="",
        help="Optional untrusted WEB context to wrap as data through AIT Firewall.",
    )
    run.add_argument(
        "--allow-local-fallback",
        action="store_true",
        help="Allow reduced-isolation local pytest fallback when Docker is unavailable.",
    )
    run.add_argument(
        "--raw",
        action="store_true",
        help="Skip AIT wrapping and pass the instruction directly to the agent.",
    )

    return parser


def run_command(args: argparse.Namespace) -> int:
    if args.allow_local_fallback:
        os.environ["ENGINE_ZERO_ALLOW_LOCAL_FALLBACK"] = "1"

    instruction = read_instruction(args)
    if args.raw:
        protected_instruction = instruction
    else:
        firewall = AITFirewallRuntime()
        protected_title = firewall.process_input(instruction, "USER")
        protected_body = firewall.process_input(args.web_context, "WEB") if args.web_context else ""
        protected_instruction = "\n\n".join(part for part in [protected_title, protected_body] if part)

    agent = EngineZeroAgent(args.target)
    agent.run_devops_cycle(protected_instruction)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return run_command(args)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
