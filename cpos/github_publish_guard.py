from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

BAD_TRACKED_PATTERN = re.compile(
    r'(^|/)('
    r'__pycache__/|\.pytest_cache/|\.venv/|venv/|env/|'
    r'\.ruff_cache/|\.mypy_cache/|\.pyc$|\.pyo$|'
    r'pointers\.jsonl$|audit_log\.jsonl$|task_runs\.jsonl$|task_checkpoints\.jsonl$|'
    r'\.env$|\.env\.|\.pem$|\.key$|\.crt$|\.p12$|\.pfx$'
    r')'
)

RISKY_UNTRACKED_PATTERN = re.compile(
    r'(^|/)('
    r'\.env($|\.)|id_rsa$|id_ed25519$|.*_rsa$|.*_ed25519$|'
    r'.*secret.*|.*token.*|.*credential.*|.*password.*|'
    r'.*\.pem$|.*\.key$|.*\.p12$|.*\.pfx$|'
    r'.*\.jsonl$|\.venv/|__pycache__/|\.pytest_cache/'
    r')',
    re.IGNORECASE,
)

DEFAULT_REQUIRED_FILES = ['README.md', 'SECURITY.md']


def _run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(['git', *args], cwd=repo, capture_output=True, text=True, check=False)


def _remote_url(repo: Path, remote: str) -> str | None:
    result = _run_git(repo, ['remote', 'get-url', remote])
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _status_lines(repo: Path) -> list[str]:
    result = _run_git(repo, ['status', '--short'])
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def _tracked_files(repo: Path) -> list[str]:
    result = _run_git(repo, ['ls-files'])
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def _untracked_files(repo: Path) -> list[str]:
    result = _run_git(repo, ['ls-files', '--others', '--exclude-standard'])
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def run_guard(
    *,
    repo: str | Path = '.',
    expected_remote: str | None = None,
    remote: str = 'origin',
    require_clean: bool = True,
    required_files: list[str] | None = None,
    include_untracked_risky: bool = True,
) -> dict[str, Any]:
    repo_path = Path(repo).resolve()
    required = required_files if required_files is not None else list(DEFAULT_REQUIRED_FILES)
    remote_url = _remote_url(repo_path, remote)
    status_lines = _status_lines(repo_path)
    tracked_bad = [path for path in _tracked_files(repo_path) if BAD_TRACKED_PATTERN.search(path)]
    untracked = _untracked_files(repo_path) if include_untracked_risky else []
    untracked_risky = [path for path in untracked if RISKY_UNTRACKED_PATTERN.search(path)]
    missing = [path for path in required if not (repo_path / path).exists()]

    failures: list[dict[str, Any]] = []
    if expected_remote and remote_url != expected_remote:
        failures.append({'name': 'remote', 'error': 'unexpected_remote', 'expected': expected_remote, 'actual': remote_url})
    if require_clean and status_lines:
        failures.append({'name': 'git_status', 'error': 'working_tree_not_clean', 'lines': status_lines})
    if tracked_bad:
        failures.append({'name': 'tracked_bad_artifacts', 'error': 'tracked_forbidden_or_runtime_artifacts', 'paths': tracked_bad})
    if untracked_risky:
        failures.append({'name': 'untracked_risky_files', 'error': 'review_or_ignore_before_publish', 'paths': untracked_risky})
    if missing:
        failures.append({'name': 'required_files', 'error': 'required_file_missing', 'paths': missing})

    return {
        'ok': not failures,
        'repo': str(repo_path),
        'remote': remote,
        'remote_url': remote_url,
        'expected_remote': expected_remote,
        'git_status_lines': status_lines,
        'tracked_bad_artifacts': tracked_bad,
        'untracked_risky_files': untracked_risky,
        'missing_required_files': missing,
        'failures': failures,
        'destructive_actions_performed': False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Non-destructive GitHub publish safety guard.')
    parser.add_argument('--repo', default='.', help='Repository path to check.')
    parser.add_argument('--expected-remote', help='Expected remote URL.')
    parser.add_argument('--remote', default='origin', help='Remote name to verify.')
    parser.add_argument('--allow-dirty', action='store_true', help='Do not fail on non-clean git status.')
    parser.add_argument('--skip-untracked-risky', action='store_true', help='Do not report risky untracked files.')
    parser.add_argument('--required-file', action='append', dest='required_files', help='Required file path. Can be repeated.')
    parser.add_argument('--json', action='store_true', help='Print JSON output.')
    return parser


def print_text(result: dict[str, Any]) -> None:
    status = 'OK' if result['ok'] else 'CHECK'
    print(f"GitHub publish guard: {status}")
    print(f"repo: {result['repo']}")
    print(f"remote: {result.get('remote_url') or '-'}")
    print(f"dirty_lines: {len(result['git_status_lines'])}")
    print(f"tracked_bad_artifacts: {len(result['tracked_bad_artifacts'])}")
    print(f"untracked_risky_files: {len(result['untracked_risky_files'])}")
    print(f"missing_required_files: {len(result['missing_required_files'])}")
    for failure in result['failures']:
        print(f"- {failure.get('name')}: {failure.get('error')}")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = run_guard(
        repo=args.repo,
        expected_remote=args.expected_remote,
        remote=args.remote,
        require_clean=not args.allow_dirty,
        required_files=args.required_files,
        include_untracked_risky=not args.skip_untracked_risky,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_text(result)
    if not result['ok']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
