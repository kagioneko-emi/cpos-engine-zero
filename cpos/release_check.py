from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

BAD_ARTIFACT_PATTERN = re.compile(r'(^|/)(__pycache__/|\.pytest_cache/|\.venv/|venv/|env/|pointers\.jsonl$|audit_log\.jsonl$|task_runs\.jsonl$|task_checkpoints\.jsonl$|\.pyc$|\.pyo$|\.env$|\.pem$|\.key$|\.crt$|\.p12$|\.pfx$)')
REQUIRED_FILES = [
    Path('README.md'),
    Path('SECURITY.md'),
    Path('OSS_RELEASE_CHECKLIST.md'),
    Path('LICENSE'),
]


def _run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(['git', *args], capture_output=True, text=True, check=False)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _tracked_bad_artifacts() -> list[str]:
    result = _run_git(['ls-files'])
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if BAD_ARTIFACT_PATTERN.search(line)]


def _current_remote_url() -> str | None:
    result = _run_git(['remote', '-v'])
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if line.startswith('origin\t') and '(push)' in line:
            parts = line.split()
            if len(parts) >= 2:
                return parts[1]
    return None


def _git_status_lines() -> list[str]:
    result = _run_git(['status', '--short'])
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def run_release_check() -> dict[str, Any]:
    root = _repo_root()
    remote_url = _current_remote_url()
    status_lines = _git_status_lines()
    tracked_bad = _tracked_bad_artifacts()
    missing_files = [str(path) for path in REQUIRED_FILES if not (root / path).exists()]
    ok = (
        remote_url == 'https://github.com/kagioneko/cpos-engine-zero.git'
        and not status_lines
        and not tracked_bad
        and not missing_files
    )
    failures = []
    if remote_url != 'https://github.com/kagioneko/cpos-engine-zero.git':
        failures.append({'name': 'remote_url', 'error': 'unexpected_remote', 'value': remote_url})
    if status_lines:
        failures.append({'name': 'git_status', 'error': 'working_tree_not_clean', 'count': len(status_lines), 'lines': status_lines})
    if tracked_bad:
        failures.append({'name': 'tracked_bad_artifacts', 'error': 'bad_artifacts_tracked', 'paths': tracked_bad})
    if missing_files:
        failures.append({'name': 'required_files', 'error': 'missing_required_files', 'paths': missing_files})
    return {
        'ok': ok,
        'remote_url': remote_url,
        'git_status_lines': status_lines,
        'tracked_bad_artifacts': tracked_bad,
        'missing_files': missing_files,
        'failures': failures,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='CPOS release readiness check (non-destructive).')
    parser.add_argument('--json', action='store_true', help='Print JSON output.')
    return parser


def print_text(result: dict[str, Any]) -> None:
    status = 'OK' if result['ok'] else 'CHECK'
    print(f"CPOS release readiness: {status}")
    print(f"remote: {result['remote_url'] or '-'}")
    print(f"working_tree_clean: {not result['git_status_lines']}")
    print(f"tracked_bad_artifacts: {len(result['tracked_bad_artifacts'])}")
    print(f"missing_files: {', '.join(result['missing_files']) if result['missing_files'] else '-'}")
    for failure in result['failures']:
        print(f"- {failure.get('name')}: {failure.get('error')}")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = run_release_check()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_text(result)
    if not result['ok']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
