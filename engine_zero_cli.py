#!/usr/bin/env python3
"""Small command-line entrypoint for CPOS Engine-Zero.

This is intentionally thin: it exposes the same safe DevOps cycle used by the
webhook server, while keeping credentials out of CLI arguments and files.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
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


WELCOME_TEXT = r"""
[36m
  /\_/\   CPOS ENGINE-ZERO CLI
 ( o.o )  Zero-Trust Autonomous DevOps Runtime
  > ^ <   AIT Firewall -> Workspace -> Docker Sandbox -> Atomic Deploy
[0m
Quick start:
  python3 engine_zero_cli.py demo

Run against your own target app:
  python3 engine_zero_cli.py run \
    --instruction 'Feature Request: Handle division by zero by returning float("inf")' \
    --web-context 'safe check'

Useful commands:
  python3 engine_zero_cli.py --help
  python3 engine_zero_cli.py demo --help
  python3 engine_zero_cli.py run --help

Safety notes:
  - Do not pass secrets in --instruction or --instruction-file.
  - Docker validation fails closed by default.
  - Use --allow-local-fallback only for reduced-isolation local demos.
"""


def print_welcome() -> None:
    print(WELCOME_TEXT)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run CPOS Engine-Zero from the CLI without starting the webhook server."
    )
    sub = parser.add_subparsers(dest="command", required=False)

    sub.add_parser("welcome", help="Show the Engine-Zero welcome screen.")

    demo = sub.add_parser("demo", help="Create a fresh buggy sample app and run one visible Engine-Zero fix cycle.")
    demo.add_argument(
        "--workdir",
        help="Directory for the generated demo app. Defaults to a new /tmp/engine-zero-demo-* directory.",
    )
    demo.add_argument(
        "--allow-local-fallback",
        action="store_true",
        help="Allow reduced-isolation local pytest fallback when Docker is unavailable.",
    )

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


def create_demo_app(workdir: str | None = None) -> Path:
    """Create a fresh intentionally-buggy target app for repeatable demos."""
    root = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="engine-zero-demo-"))
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "src" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "calc.py").write_text(
        "def divide(a, b):\n"
        "    return a / b\n\n"
        "def add(a, b):\n"
        "    return a + b\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_calc.py").write_text(
        "import pytest\n"
        "from src.calc import divide, add\n\n"
        "def test_add():\n"
        "    assert add(2, 3) == 5\n\n"
        "def test_divide():\n"
        "    assert divide(10, 2) == 5\n\n"
        "def test_divide_by_zero():\n"
        "    with pytest.raises(ZeroDivisionError):\n"
        "        divide(10, 0)\n",
        encoding="utf-8",
    )
    return root


def demo_command(args: argparse.Namespace) -> int:
    if args.allow_local_fallback:
        os.environ["ENGINE_ZERO_ALLOW_LOCAL_FALLBACK"] = "1"

    demo_root = create_demo_app(args.workdir)
    print(f"[*] Fresh demo target created: {demo_root}")
    print("[*] Initial bug: divide(10, 0) raises ZeroDivisionError.")
    instruction = 'Feature Request: Handle division by zero by returning float("inf")'

    firewall = AITFirewallRuntime()
    protected_instruction = "\n\n".join([
        firewall.process_input(instruction, "USER"),
        firewall.process_input("repeatable CLI demo fixture", "WEB"),
    ])
    agent = EngineZeroAgent(str(demo_root))
    agent.run_devops_cycle(protected_instruction)

    fixed_code = (demo_root / "src" / "calc.py").read_text(encoding="utf-8")
    print("[*] Final demo calc.py:")
    print(fixed_code.rstrip())
    print(f"[*] Demo target kept for inspection: {demo_root}")
    return 0


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
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        print_welcome()
        return 0

    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "welcome":
        print_welcome()
        return 0
    if args.command == "demo":
        return demo_command(args)
    if args.command == "run":
        return run_command(args)
    print_welcome()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
