#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_task(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding='utf-8')
    suffix = path.suffix.lower()
    if suffix == '.json':
        data = json.loads(text)
    elif suffix in {'.yml', '.yaml'}:
        data = yaml.safe_load(text)
    else:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError('task file must decode to a mapping/object')
    return data


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def validate_task(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = ['task_id', 'title', 'owner', 'scope', 'repos', 'ai_roles', 'constraints', 'status', 'next_action']
    for key in required:
        if key not in data:
            issues.append(f'missing required field: {key}')

    scope = data.get('scope', {})
    if not isinstance(scope, dict):
        issues.append('scope must be a mapping/object')
    else:
        if scope.get('status') not in {'confirmed', 'uncertain', 'blocked'}:
            issues.append("scope.status should be one of: confirmed, uncertain, blocked")

    repos = data.get('repos', [])
    if not isinstance(repos, list):
        issues.append('repos must be a list')
    else:
        valid_repo_roles = {'allowed', 'reference_only', 'test_only', 'blocked', 'scope_unknown'}
        for i, repo in enumerate(repos):
            if not isinstance(repo, dict):
                issues.append(f'repos[{i}] must be an object')
                continue
            if 'name' not in repo:
                issues.append(f'repos[{i}] missing name')
            if repo.get('role') not in valid_repo_roles:
                issues.append(f"repos[{i}].role should be one of: {', '.join(sorted(valid_repo_roles))}")

    ai_roles = data.get('ai_roles', {})
    if not isinstance(ai_roles, dict):
        issues.append('ai_roles must be a mapping/object')
    else:
        if 'coordinator' not in ai_roles:
            issues.append('ai_roles missing coordinator')

    constraints = data.get('constraints', {})
    if not isinstance(constraints, dict):
        issues.append('constraints must be a mapping/object')

    if data.get('human_review_required') not in {True, False, None}:
        issues.append('human_review_required should be true/false')

    return issues


def summarize_task(data: dict[str, Any], path: Path) -> str:
    repos = _as_list(data.get('repos'))
    repo_lines = []
    for repo in repos:
        if isinstance(repo, dict):
            repo_lines.append(f"- {repo.get('name', '<missing>')} [{repo.get('role', '<missing>')}]")
        else:
            repo_lines.append(f'- {repo!r}')

    ai_roles = data.get('ai_roles') if isinstance(data.get('ai_roles'), dict) else {}
    constraints = data.get('constraints') if isinstance(data.get('constraints'), dict) else {}
    scope = data.get('scope') if isinstance(data.get('scope'), dict) else {}
    hypothesis = _as_list(data.get('hypothesis'))
    evidence = data.get('evidence') if isinstance(data.get('evidence'), dict) else {}

    lines = [
        f'File: {path}',
        f"Task ID: {data.get('task_id', '<missing>')}",
        f"Title: {data.get('title', '<missing>')}",
        f"Date: {data.get('date', '<missing>')}",
        f"Owner: {data.get('owner', '<missing>')}",
        f"Target program: {data.get('target_program', '<missing>')}",
        f"Status: {data.get('status', '<missing>')}",
        f"Next action: {data.get('next_action', '<missing>')}",
        f"Human review required: {data.get('human_review_required', '<missing>')}",
        '',
        'Scope:',
        f"- status: {scope.get('status', '<missing>')}",
        f"- notes: {scope.get('notes', '')}",
        '',
        'Repos:',
    ]
    if repo_lines:
        lines.extend(repo_lines)
    else:
        lines.append('- <none>')
    lines.extend([
        '',
        'AI roles:',
        f"- coordinator: {ai_roles.get('coordinator', '<missing>')}",
        f"- broad_survey: {ai_roles.get('broad_survey', '<missing>')}",
        f"- deep_review: {ai_roles.get('deep_review', '<missing>')}",
        f"- local_validation: {ai_roles.get('local_validation', '<missing>')}",
        f"- report_polish: {ai_roles.get('report_polish', '<missing>')}",
        '',
        'Hypotheses:',
    ])
    if hypothesis:
        lines.extend(f'- {item}' for item in hypothesis)
    else:
        lines.append('- <none>')
    lines.extend([
        '',
        'Constraints:',
        f"- no_secrets: {constraints.get('no_secrets', '<missing>')}",
        f"- no_production_data: {constraints.get('no_production_data', '<missing>')}",
        f"- no_destructive_actions: {constraints.get('no_destructive_actions', '<missing>')}",
        f"- minimal_reproduction: {constraints.get('minimal_reproduction', '<missing>')}",
        '',
        'Evidence:',
        f"- logs: {len(_as_list(evidence.get('logs')))}",
        f"- screenshots: {len(_as_list(evidence.get('screenshots')))}",
        f"- paths: {len(_as_list(evidence.get('paths')))}",
        f"- commits: {len(_as_list(evidence.get('commits')))}",
    ])
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description='Inspect and validate AI White-Hatter task files')
    parser.add_argument('file', help='Path to a YAML or JSON task file')
    parser.add_argument('--json', action='store_true', help='Emit machine-readable output')
    args = parser.parse_args()

    path = Path(args.file)
    if not path.is_file():
        candidate = ROOT / args.file
        if candidate.is_file():
            path = candidate
        else:
            raise SystemExit(f'task file not found: {args.file}')

    data = load_task(path)
    issues = validate_task(data)

    if args.json:
        payload = {
            'file': str(path),
            'task_id': data.get('task_id'),
            'title': data.get('title'),
            'status': data.get('status'),
            'next_action': data.get('next_action'),
            'human_review_required': data.get('human_review_required'),
            'issues': issues,
            'task': data,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(summarize_task(data, path))
        print()
        if issues:
            print('Validation issues:')
            for issue in issues:
                print(f'- {issue}')
        else:
            print('Validation issues: none')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
