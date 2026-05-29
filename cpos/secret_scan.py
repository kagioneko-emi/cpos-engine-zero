from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

DEFAULT_EXCLUDES = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
}

PATTERNS = [
    ("private_key_pem", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)?PRIVATE KEY-----")),
    ("github_token", re.compile(r"ghp_[A-Za-z0-9_]{20,}")),
    ("openai_like_key", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("vault_token", re.compile(r"\bs\.[A-Za-z0-9]{20,}")),
]


def should_skip(path: Path, root: Path, excludes: set[str]) -> bool:
    relative_parts = set(path.relative_to(root).parts)
    return path.name in excludes or bool(relative_parts & excludes)


def scan_paths(paths: Iterable[str | Path], *, excludes: set[str] | None = None) -> list[dict[str, object]]:
    excludes = set(DEFAULT_EXCLUDES if excludes is None else excludes)
    findings: list[dict[str, object]] = []
    for raw in paths:
        root = Path(raw)
        if not root.exists():
            continue
        files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
        base = root if root.is_dir() else root.parent
        for path in files:
            if should_skip(path, base, excludes):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                for name, pattern in PATTERNS:
                    if pattern.search(line):
                        findings.append({
                            "path": str(path),
                            "line": lineno,
                            "pattern": name,
                        })
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan files for high-risk secret patterns without printing secret values.")
    parser.add_argument("paths", nargs="*", default=["."], help="Paths to scan.")
    parser.add_argument("--exclude", action="append", default=[], help="Directory name to exclude. Can be repeated.")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    excludes = DEFAULT_EXCLUDES | set(args.exclude)
    findings = scan_paths(args.paths, excludes=excludes)
    payload = {"ok": not findings, "count": len(findings), "findings": findings}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"secret scan: {'OK' if payload['ok'] else 'CHECK'} findings={len(findings)}")
        for finding in findings:
            print(f"- {finding['path']}:{finding['line']} pattern={finding['pattern']}")
    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
