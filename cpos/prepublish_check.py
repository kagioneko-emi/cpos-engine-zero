from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cpos.github_publish_guard import run_guard
from cpos.release_check import run_release_check
from cpos.secret_scan import DEFAULT_EXCLUDES, scan_paths

DEFAULT_SECRET_EXCLUDES = DEFAULT_EXCLUDES | {
    'workspace',
    'certs',
    'hackathon_report.html',
    'audit_log.jsonl',
    'pointers.jsonl',
    'task_runs.jsonl',
    'task_checkpoints.jsonl',
}

EXPECTED_REMOTE = 'https://github.com/kagioneko/cpos-engine-zero.git'


def _secret_scan_result(paths: list[str], excludes: set[str]) -> dict[str, Any]:
    findings = scan_paths(paths, excludes=excludes)
    return {
        'ok': not findings,
        'count': len(findings),
        'findings': findings,
    }


def run_prepublish_check(
    *,
    repo: str | Path = '.',
    expected_remote: str = EXPECTED_REMOTE,
    secret_scan_paths: list[str] | None = None,
    secret_excludes: set[str] | None = None,
    require_clean: bool = True,
) -> dict[str, Any]:
    repo_path = Path(repo).resolve()
    scan_paths_arg = secret_scan_paths if secret_scan_paths is not None else [str(repo_path)]
    excludes = set(DEFAULT_SECRET_EXCLUDES if secret_excludes is None else secret_excludes)

    publish_guard = run_guard(
        repo=repo_path,
        expected_remote=expected_remote,
        require_clean=require_clean,
    )
    release = run_release_check()
    secrets = _secret_scan_result(scan_paths_arg, excludes)

    checks = {
        'github_publish_guard': publish_guard,
        'release_check': release,
        'secret_scan': secrets,
    }
    failures = [name for name, result in checks.items() if not result.get('ok')]
    return {
        'ok': not failures,
        'repo': str(repo_path),
        'expected_remote': expected_remote,
        'checks': checks,
        'failures': failures,
        'destructive_actions_performed': False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Non-destructive CPOS pre-publish safety gate.')
    parser.add_argument('--repo', default='.', help='Repository path to check.')
    parser.add_argument('--expected-remote', default=EXPECTED_REMOTE, help='Expected Git remote URL.')
    parser.add_argument('--secret-path', action='append', dest='secret_paths', help='Path to scan for secrets. Can be repeated; defaults to repo.')
    parser.add_argument('--exclude', action='append', default=[], help='Secret-scan exclude name. Can be repeated.')
    parser.add_argument('--allow-dirty', action='store_true', help='Do not fail the publish guard on dirty git status.')
    parser.add_argument('--json', action='store_true', help='Print JSON output.')
    return parser


def print_text(result: dict[str, Any]) -> None:
    status = 'OK' if result['ok'] else 'CHECK'
    print(f'CPOS pre-publish safety gate: {status}')
    print(f"repo: {result['repo']}")
    print(f"expected_remote: {result['expected_remote']}")
    for name, check in result['checks'].items():
        check_status = 'OK' if check.get('ok') else 'CHECK'
        print(f'- {name}: {check_status}')
    print(f"destructive_actions_performed: {result['destructive_actions_performed']}")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    secret_paths = args.secret_paths if args.secret_paths else None
    excludes = DEFAULT_SECRET_EXCLUDES | set(args.exclude)
    result = run_prepublish_check(
        repo=args.repo,
        expected_remote=args.expected_remote,
        secret_scan_paths=secret_paths,
        secret_excludes=excludes,
        require_clean=not args.allow_dirty,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_text(result)
    if not result['ok']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
