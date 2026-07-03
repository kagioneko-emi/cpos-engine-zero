from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from datetime import date as _date

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOAL_STORE = "goals/goals.example.json"
DEFAULT_TASK_FILE = "docs/AI_WHITE_HATTER_TASK.example.yaml"
DEFAULT_HOST = "127.0.0.1:8080"
TASK_GLOB_PATTERNS = ("docs/AI_WHITE_HATTER_TASK*.yml", "docs/AI_WHITE_HATTER_TASK*.yaml", "docs/AI_WHITE_HATTER_TASK*.json")


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def load_task(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(text)
    elif suffix in {".yml", ".yaml"}:
        data = yaml.safe_load(text)
    else:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("task file must decode to a mapping/object")
    return data


def validate_task(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = ["task_id", "title", "owner", "scope", "repos", "ai_roles", "constraints", "status", "next_action"]
    for key in required:
        if key not in data:
            issues.append(f"missing required field: {key}")

    scope = data.get("scope", {})
    if not isinstance(scope, dict):
        issues.append("scope must be a mapping/object")
    else:
        if scope.get("status") not in {"confirmed", "uncertain", "blocked"}:
            issues.append("scope.status should be one of: confirmed, uncertain, blocked")

    repos = data.get("repos", [])
    if not isinstance(repos, list):
        issues.append("repos must be a list")
    else:
        valid_repo_roles = {"allowed", "reference_only", "test_only", "blocked", "scope_unknown"}
        for i, repo in enumerate(repos):
            if not isinstance(repo, dict):
                issues.append(f"repos[{i}] must be an object")
                continue
            if "name" not in repo:
                issues.append(f"repos[{i}] missing name")
            if repo.get("role") not in valid_repo_roles:
                issues.append(f"repos[{i}].role should be one of: {', '.join(sorted(valid_repo_roles))}")

    ai_roles = data.get("ai_roles", {})
    if not isinstance(ai_roles, dict):
        issues.append("ai_roles must be a mapping/object")
    else:
        if "coordinator" not in ai_roles:
            issues.append("ai_roles missing coordinator")

    constraints = data.get("constraints", {})
    if not isinstance(constraints, dict):
        issues.append("constraints must be a mapping/object")

    if data.get("human_review_required") not in {True, False, None}:
        issues.append("human_review_required should be true/false")

    return issues


def compare_task_data(left: dict[str, Any], right: dict[str, Any], *, left_label: str, right_label: str) -> dict[str, Any]:
    def repo_map(task: dict[str, Any]) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for repo in _as_list(task.get("repos")):
            if isinstance(repo, dict) and repo.get("name"):
                mapping[str(repo["name"])] = str(repo.get("role", "unknown"))
        return mapping

    left_repos = repo_map(left)
    right_repos = repo_map(right)
    all_repo_names = sorted(set(left_repos) | set(right_repos))
    repo_diffs = []
    for name in all_repo_names:
        l = left_repos.get(name, "<missing>")
        r = right_repos.get(name, "<missing>")
        if l != r:
            repo_diffs.append({"repo": name, "left": l, "right": r})

    fields = ["title", "status", "next_action", "human_review_required", "target_program"]
    field_diffs = []
    for field in fields:
        lv = left.get(field)
        rv = right.get(field)
        if lv != rv:
            field_diffs.append({"field": field, "left": lv, "right": rv})

    left_scope = left.get("scope") if isinstance(left.get("scope"), dict) else {}
    right_scope = right.get("scope") if isinstance(right.get("scope"), dict) else {}
    scope_fields = ["status", "notes"]
    scope_diffs = []
    for field in scope_fields:
        lv = left_scope.get(field)
        rv = right_scope.get(field)
        if lv != rv:
            scope_diffs.append({"field": field, "left": lv, "right": rv})

    left_ai = left.get("ai_roles") if isinstance(left.get("ai_roles"), dict) else {}
    right_ai = right.get("ai_roles") if isinstance(right.get("ai_roles"), dict) else {}
    ai_fields = ["coordinator", "broad_survey", "deep_review", "local_validation", "report_polish"]
    ai_diffs = []
    for field in ai_fields:
        lv = left_ai.get(field)
        rv = right_ai.get(field)
        if lv != rv:
            ai_diffs.append({"field": field, "left": lv, "right": rv})

    left_issues = validate_task(left)
    right_issues = validate_task(right)
    return {
        "ok": True,
        "schema": "cpos.ai_white_hatter_task_compare.v1",
        "left_label": left_label,
        "right_label": right_label,
        "summary": {
            "left_task_id": left.get("task_id"),
            "right_task_id": right.get("task_id"),
            "left_title": left.get("title"),
            "right_title": right.get("title"),
            "repo_diff_count": len(repo_diffs),
            "field_diff_count": len(field_diffs),
            "scope_diff_count": len(scope_diffs),
            "ai_role_diff_count": len(ai_diffs),
        },
        "differences": {
            "repos": repo_diffs,
            "fields": field_diffs,
            "scope": scope_diffs,
            "ai_roles": ai_diffs,
        },
        "validation": {
            "left_issues": left_issues,
            "right_issues": right_issues,
        },
        "left": {
            "task_id": left.get("task_id"),
            "title": left.get("title"),
            "file": left_label,
            "status": left.get("status"),
            "next_action": left.get("next_action"),
        },
        "right": {
            "task_id": right.get("task_id"),
            "title": right.get("title"),
            "file": right_label,
            "status": right.get("status"),
            "next_action": right.get("next_action"),
        },
    }

def compare_task_against_many(base_path: Path, candidate_paths: list[Path], *, top_n: int | None = None) -> dict[str, Any]:
    base = load_task(base_path)
    rows = []
    for candidate_path in candidate_paths:
        candidate = load_task(candidate_path)
        compare = compare_task_data(base, candidate, left_label=display_task_path(base_path), right_label=display_task_path(candidate_path))
        summary = compare.get("summary", {}) if isinstance(compare, dict) else {}
        score = (
            int(summary.get("repo_diff_count", 0))
            + int(summary.get("field_diff_count", 0))
            + int(summary.get("scope_diff_count", 0))
            + int(summary.get("ai_role_diff_count", 0))
        )
        rows.append({
            "file": display_task_path(candidate_path),
            "task_id": candidate.get("task_id"),
            "title": candidate.get("title"),
            "status": candidate.get("status"),
            "next_action": candidate.get("next_action"),
            "score": score,
            "compare": compare,
        })
    rows.sort(key=lambda row: (-row["score"], row["file"]))
    if top_n is not None and top_n >= 0:
        rows = rows[:top_n]
    return {
        "ok": True,
        "schema": "cpos.ai_white_hatter_task_batch_compare.v1",
        "base": {
            "file": display_task_path(base_path),
            "task_id": base.get("task_id"),
            "title": base.get("title"),
        },
        "count": len(rows),
        "comparisons": rows,
    }





def summarize_task(data: dict[str, Any], path: Path) -> str:
    repos = _as_list(data.get("repos"))
    repo_lines = []
    for repo in repos:
        if isinstance(repo, dict):
            repo_lines.append(f"- {repo.get('name', '<missing>')} [{repo.get('role', '<missing>')}]")
        else:
            repo_lines.append(f"- {repo!r}")

    ai_roles = data.get("ai_roles") if isinstance(data.get("ai_roles"), dict) else {}
    constraints = data.get("constraints") if isinstance(data.get("constraints"), dict) else {}
    scope = data.get("scope") if isinstance(data.get("scope"), dict) else {}
    hypothesis = _as_list(data.get("hypothesis"))
    evidence = data.get("evidence") if isinstance(data.get("evidence"), dict) else {}
    derived_from = data.get("derived_from")
    clone_source = data.get("clone_source") if isinstance(data.get("clone_source"), dict) else {}

    lines = [
        f"File: {path}",
        f"Task ID: {data.get('task_id', '<missing>')}",
        f"Title: {data.get('title', '<missing>')}",
        f"Date: {data.get('date', '<missing>')}",
        f"Owner: {data.get('owner', '<missing>')}",
        f"Target program: {data.get('target_program', '<missing>')}",
        f"Status: {data.get('status', '<missing>')}",
        f"Next action: {data.get('next_action', '<missing>')}",
        f"Human review required: {data.get('human_review_required', '<missing>')}",
        "",
        "Scope:",
        f"- status: {scope.get('status', '<missing>')}",
        f"- notes: {scope.get('notes', '')}",
        "",
        "Repos:",
    ]
    if repo_lines:
        lines.extend(repo_lines)
    else:
        lines.append("- <none>")
    lines.extend([
        "",
        "AI roles:",
        f"- coordinator: {ai_roles.get('coordinator', '<missing>')}",
        f"- broad_survey: {ai_roles.get('broad_survey', '<missing>')}",
        f"- deep_review: {ai_roles.get('deep_review', '<missing>')}",
        f"- local_validation: {ai_roles.get('local_validation', '<missing>')}",
        f"- report_polish: {ai_roles.get('report_polish', '<missing>')}",
        "",
        "Hypotheses:",
    ])
    if hypothesis:
        lines.extend(f"- {item}" for item in hypothesis)
    else:
        lines.append("- <none>")
    lines.extend([
        "",
        "Constraints:",
        f"- no_secrets: {constraints.get('no_secrets', '<missing>')}",
        f"- no_production_data: {constraints.get('no_production_data', '<missing>')}",
        f"- no_destructive_actions: {constraints.get('no_destructive_actions', '<missing>')}",
        f"- minimal_reproduction: {constraints.get('minimal_reproduction', '<missing>')}",
        "",
        "Evidence:",
        f"- logs: {len(_as_list(evidence.get('logs')))}",
        f"- screenshots: {len(_as_list(evidence.get('screenshots')))}",
        f"- paths: {len(_as_list(evidence.get('paths')))}",
        f"- commits: {len(_as_list(evidence.get('commits')))}",
    ])
    if derived_from:
        lines.extend([
            "",
            "Clone source:",
            f"- derived_from: {derived_from}",
            f"- source_task_id: {clone_source.get('task_id', '<missing>')}",
            f"- source_title: {clone_source.get('title', '<missing>')}",
            f"- cloned_at: {clone_source.get('cloned_at', '<missing>')}",
        ])
    return "\n".join(lines)


def list_task_files() -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for pattern in TASK_GLOB_PATTERNS:
        for path in sorted(ROOT.glob(pattern)):
            if path.is_file() and path not in seen:
                seen.add(path)
                files.append(path)
    return files


def display_task_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        try:
            return str(path.resolve())
        except Exception:
            return str(path)


def build_task_scaffold(task_id: str, title: str, *, target_program: str = "local-lab", owner: str = "codex", scope_status: str = "uncertain", human_review_required: bool = True, next_action: str = "scope_gate") -> dict[str, Any]:
    today = _date.today().isoformat()
    return {
        "task_id": task_id,
        "title": title,
        "date": today,
        "owner": owner,
        "target_program": target_program,
        "scope": {
            "status": scope_status,
            "notes": "Fill in approved scope before execution.",
        },
        "repos": [],
        "ai_roles": {
            "coordinator": "codex",
            "broad_survey": "gemini",
            "deep_review": "claude",
            "local_validation": "codex",
            "report_polish": "codex",
        },
        "hypothesis": [],
        "constraints": {
            "no_secrets": True,
            "no_production_data": True,
            "no_destructive_actions": True,
            "minimal_reproduction": True,
        },
        "evidence": {
            "logs": [],
            "screenshots": [],
            "paths": [],
            "commits": [],
        },
        "status": "planned",
        "next_action": next_action,
        "human_review_required": human_review_required,
    }


def load_task_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_file():
        return path.resolve()
    candidate = ROOT / raw_path
    if candidate.is_file():
        return candidate.resolve()
    raise SystemExit(f"task file not found: {raw_path}")


def cmd_create_task(output_path: Path, *, task_id: str | None, title: str | None, target_program: str, owner: str, scope_status: str, human_review_required: bool, next_action: str, as_json: bool) -> int:
    output_path = output_path.expanduser()
    if output_path.exists():
        raise SystemExit(f"task file already exists: {display_task_path(output_path)}")
    if not task_id:
        task_id = output_path.stem.replace(" ", "-").replace("_", "-")
    if not title:
        title = task_id.replace("-", " ").title()
    scaffold = build_task_scaffold(
        task_id=task_id,
        title=title,
        target_program=target_program,
        owner=owner,
        scope_status=scope_status,
        human_review_required=human_review_required,
        next_action=next_action,
    )
    if as_json:
        print(json.dumps({"file": display_task_path(output_path), "task": scaffold}, ensure_ascii=False, indent=2))
        return 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.safe_dump(scaffold, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"created: {display_task_path(output_path)}")
    print(summarize_task(scaffold, output_path))
    return 0


def clone_task_scaffold(
    source_path: Path,
    output_path: Path,
    *,
    task_id: str | None,
    title: str | None,
    target_program: str | None,
    owner: str | None,
    scope_status: str | None,
    human_review_required: bool | None,
    next_action: str | None,
) -> tuple[dict[str, Any], list[str]]:
    source_path = load_task_path(str(source_path))
    output_path = output_path.expanduser()
    if output_path.exists():
        raise SystemExit(f"task file already exists: {display_task_path(output_path)}")
    base = load_task(source_path)
    cloned = json.loads(json.dumps(base, ensure_ascii=False))
    cloned["derived_from"] = display_task_path(source_path)
    cloned["clone_source"] = {
        "file": display_task_path(source_path),
        "task_id": base.get("task_id"),
        "title": base.get("title"),
        "cloned_at": _date.today().isoformat(),
    }
    if task_id:
        cloned["task_id"] = task_id
    if title:
        cloned["title"] = title
    elif not cloned.get("title"):
        cloned["title"] = f"Clone of {base.get('task_id', source_path.stem)}"
    if target_program:
        cloned["target_program"] = target_program
    if owner:
        cloned["owner"] = owner
    if scope_status:
        cloned.setdefault("scope", {})
        if isinstance(cloned["scope"], dict):
            cloned["scope"]["status"] = scope_status
    if human_review_required is not None:
        cloned["human_review_required"] = human_review_required
    if next_action:
        cloned["next_action"] = next_action
    cloned["status"] = "planned"
    cloned["date"] = _date.today().isoformat()
    cloned.setdefault("evidence", {})
    if isinstance(cloned["evidence"], dict):
        cloned["evidence"].update({"logs": [], "screenshots": [], "paths": [], "commits": []})
    issues = validate_task(cloned)
    return cloned, issues


def cmd_clone_task(source_path: Path, output_path: Path, *, task_id: str | None, title: str | None, target_program: str | None, owner: str | None, scope_status: str | None, human_review_required: bool | None, next_action: str | None, as_json: bool) -> int:
    source_path = load_task_path(str(source_path))
    output_path = output_path.expanduser()
    cloned, issues = clone_task_scaffold(
        source_path,
        output_path,
        task_id=task_id,
        title=title,
        target_program=target_program,
        owner=owner,
        scope_status=scope_status,
        human_review_required=human_review_required,
        next_action=next_action,
    )
    compare = compare_task_data(load_task(source_path), cloned, left_label=display_task_path(source_path), right_label=display_task_path(output_path))
    if as_json:
        print(json.dumps({"file": display_task_path(output_path), "source": display_task_path(source_path), "task": cloned, "issues": issues, "compare": compare}, ensure_ascii=False, indent=2))
        return 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.safe_dump(cloned, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"cloned: {display_task_path(source_path)} -> {display_task_path(output_path)}")
    print(summarize_task(cloned, output_path))
    print()
    if issues:
        print("Validation issues:")
        for issue in issues:
            print(f"- {issue}")
    else:
        print("Validation issues: none")
    print()
    print("Compare summary:")
    summary = compare.get("summary", {}) if isinstance(compare, dict) else {}
    print(f"- repo_diffs: {summary.get('repo_diff_count', 0)}")
    print(f"- field_diffs: {summary.get('field_diff_count', 0)}")
    print(f"- scope_diffs: {summary.get('scope_diff_count', 0)}")
    print(f"- ai_role_diffs: {summary.get('ai_role_diff_count', 0)}")
    return 0


def cmd_task(path: Path, *, as_json: bool) -> int:
    data = load_task(path)
    issues = validate_task(data)
    if as_json:
        payload = {
            "file": str(path),
            "task_id": data.get("task_id"),
            "title": data.get("title"),
            "status": data.get("status"),
            "next_action": data.get("next_action"),
            "human_review_required": data.get("human_review_required"),
            "issues": issues,
            "task": data,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    print(summarize_task(data, path))
    print()
    if issues:
        print("Validation issues:")
        for issue in issues:
            print(f"- {issue}")
    else:
        print("Validation issues: none")
    return 0


def cmd_compare_tasks(left_path: Path, right_path: Path, *, as_json: bool) -> int:
    left = load_task(left_path)
    right = load_task(right_path)
    payload = compare_task_data(left, right, left_label=display_task_path(left_path), right_label=display_task_path(right_path))
    _print(payload, as_json=as_json)
    return 0


def cmd_compare_many(base_path: Path, candidate_paths: list[Path] | None, *, top_n: int | None, as_json: bool) -> int:
    if candidate_paths:
        paths = [p.expanduser() for p in candidate_paths]
    else:
        paths = [p for p in list_task_files() if p.resolve() != base_path.resolve()]
    payload = compare_task_against_many(base_path, paths, top_n=top_n)
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    print(f"Base: {payload['base']['file']} ({payload['base']['task_id'] or '-'})")
    print(f"Comparisons: {payload['count']}")
    print()
    for row in payload.get('comparisons', []):
        compare = row.get('compare', {}) if isinstance(row.get('compare'), dict) else {}
        summary = compare.get('summary', {}) if isinstance(compare, dict) else {}
        print(
            f"- {row.get('file')} | score={row.get('score', 0)} | repo={summary.get('repo_diff_count', 0)} | field={summary.get('field_diff_count', 0)} | scope={summary.get('scope_diff_count', 0)} | ai={summary.get('ai_role_diff_count', 0)}"
        )
    return 0


def _print(payload: Any, *, as_json: bool) -> None:
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI White-Hatter operational CLI.")
    parser.add_argument("--goal-store", default=DEFAULT_GOAL_STORE)
    parser.add_argument("--host", default=DEFAULT_HOST)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Read current world model and goal state.")

    validate = subparsers.add_parser("validate", help="Validate the goal store and show summary.")
    validate.add_argument("--json", action="store_true")

    subparsers.add_parser("compare", help="Inspect docs and compare stored templates.")

    subparsers.add_parser("review", help="Read local review queues from the CPOS HTTP API.")

    subparsers.add_parser("pipeline", help="Run the read-only evaluation/pointer pipeline.")

    subparsers.add_parser("demo", help="Read demo readiness from the CPOS HTTP API.")

    task = subparsers.add_parser("task", help="Read, validate, and summarize a task file.")
    task.add_argument("file")

    task_json = subparsers.add_parser("task-json", help="Emit machine-readable task output.")
    task_json.add_argument("file")

    compare_task = subparsers.add_parser("compare-task", help="Compare two task files.")
    compare_task.add_argument("left")
    compare_task.add_argument("right")
    compare_task.add_argument("--json", action="store_true")

    compare_many = subparsers.add_parser("compare-many", help="Compare one task against many task files.")
    compare_many.add_argument("base")
    compare_many.add_argument("candidates", nargs="*")
    compare_many.add_argument("--top-n", type=int, default=5, help="Limit batch compare results to the top N rows. Use -1 for all rows.")
    compare_many.add_argument("--json", action="store_true")

    create_task = subparsers.add_parser("create-task", help="Create a new task scaffold.")
    create_task.add_argument("file")
    create_task.add_argument("--task-id")
    create_task.add_argument("--title")
    create_task.add_argument("--target-program", default="local-lab")
    create_task.add_argument("--owner", default="codex")
    create_task.add_argument("--scope-status", default="uncertain", choices=["confirmed", "uncertain", "blocked"])
    create_task.add_argument("--next-action", default="scope_gate")
    create_task.add_argument("--human-review-required", action=argparse.BooleanOptionalAction, default=True)
    create_task.add_argument("--json", action="store_true")

    clone_task = subparsers.add_parser("clone-task", help="Clone an existing task to a new file.")
    clone_task.add_argument("source")
    clone_task.add_argument("file")
    clone_task.add_argument("--task-id")
    clone_task.add_argument("--title")
    clone_task.add_argument("--target-program")
    clone_task.add_argument("--owner")
    clone_task.add_argument("--scope-status", choices=["confirmed", "uncertain", "blocked"])
    clone_task.add_argument("--next-action")
    clone_task.add_argument("--human-review-required", action=argparse.BooleanOptionalAction)
    clone_task.add_argument("--json", action="store_true")

    dashboard = subparsers.add_parser("dashboard", help="Show the dashboard-ready AI White-Hatter summary.")
    dashboard.add_argument("--task-file", default=DEFAULT_TASK_FILE)
    dashboard.add_argument("--json", action="store_true")

    subparsers.add_parser("tasks", help="List available AI White-Hatter task files.")

    subparsers.add_parser("all", help="Run the full read-only workflow.")
    return parser


def _run_status(goal_store: str) -> int:
    from . import world_model, goals

    world_model.main(["snapshot", "--json"])
    goals.main(["list", "--json"])
    return 0


def _run_validate(goal_store: str, *, as_json: bool) -> int:
    from . import goal_store as goal_store_module

    payload = goal_store_module.validate_file(goal_store, include_merged_summary=True)
    _print(payload, as_json=as_json)
    return 0


def _run_compare() -> int:
    import subprocess

    result = subprocess.run(
        ["bash", "-lc", "cd /home/mayutama/cpos_defensive_agent && rg -n 'red team|review|security|tape|scope|human escalation|adapter' ."],
        check=True,
        capture_output=True,
        text=True,
    )
    print(result.stdout, end="")
    print()
    for rel in ["docs/AI_WHITE_HATTER_SYSTEM_SPEC.md", "docs/AI_WHITE_HATTER_TASK_SCHEMA.md", "docs/AI_WHITE_HATTER_OPERATION_TEMPLATES.md"]:
        print(Path(ROOT / rel).read_text(encoding="utf-8"))
        print()
    return 0


def _run_review(host: str) -> int:
    import urllib.request

    for path in ["/agent-adapter/actions", "/agent-adapter/execution-results", "/human-escalations"]:
        with urllib.request.urlopen(f"http://{host}{path}") as response:
            print(response.read().decode("utf-8"))
            print()
    return 0


def _run_pipeline(goal_store: str) -> int:
    from . import reflection_evaluator, resume_pipeline, resume_pointer

    reflection_evaluator.main(["evaluate", "--json"])
    resume_pipeline.main(["run", "--goal-store", goal_store, "--json"])
    resume_pointer.main(["build", "--goal-store", goal_store, "--json"])
    return 0


def _run_demo(host: str) -> int:
    import urllib.request

    with urllib.request.urlopen(f"http://{host}/demo/readiness") as response:
        print(response.read().decode("utf-8"))
    return 0


def build_task_catalog() -> dict[str, Any]:
    rows = []
    for path in list_task_files():
        try:
            data = load_task(path)
            issues = validate_task(data)
        except Exception as exc:
            data = {}
            issues = [f"load_error: {exc}"]
        rows.append({
            "file": display_task_path(path),
            "task_id": data.get("task_id"),
            "title": data.get("title"),
            "status": data.get("status"),
            "next_action": data.get("next_action"),
            "human_review_required": data.get("human_review_required"),
            "issues": issues,
        })
    return {"ok": True, "schema": "cpos.ai_white_hatter_task_catalog.v1", "count": len(rows), "tasks": rows}


def build_dashboard_summary(goal_store: str = DEFAULT_GOAL_STORE, task_file: str = DEFAULT_TASK_FILE) -> dict[str, Any]:
    from .goal_store import build_goal_store_summary

    task_path = load_task_path(task_file)
    task_data = load_task(task_path)
    task_issues = validate_task(task_data)
    goal_summary = build_goal_store_summary(goal_store)
    checklist = [
        "Scope gate",
        "Existing repo comparison",
        "Task file validation",
        "Review queue inspection",
        "Read-only pipeline",
        "Demo readiness",
    ]
    task_options = []
    for path in list_task_files():
        try:
            candidate = load_task(path)
            issues = validate_task(candidate)
        except Exception as exc:
            candidate = {}
            issues = [f"load_error: {exc}"]
        task_options.append({
            "file": display_task_path(path),
            "task_id": candidate.get("task_id"),
            "title": candidate.get("title"),
            "status": candidate.get("status"),
            "next_action": candidate.get("next_action"),
            "human_review_required": candidate.get("human_review_required"),
            "issues": issues,
        })
    return {
        "ok": True,
        "schema": "cpos.ai_white_hatter_dashboard_summary.v1",
        "goal_store": goal_summary,
        "task": {
            "file": display_task_path(task_path),
            "task_id": task_data.get("task_id"),
            "title": task_data.get("title"),
            "status": task_data.get("status"),
            "next_action": task_data.get("next_action"),
            "human_review_required": task_data.get("human_review_required"),
            "issues": task_issues,
        },
        "task_options": task_options,
        "checklist": checklist,
        "commands": [
            "./scripts/ai_white_hatter.sh all",
            "./scripts/ai_white_hatter.sh task docs/AI_WHITE_HATTER_TASK.example.yaml",
            "./scripts/ai_white_hatter.sh task-json docs/AI_WHITE_HATTER_TASK.example.yaml",
            "./scripts/ai_white_hatter.sh compare-many docs/AI_WHITE_HATTER_TASK.example.yaml --top-n 5",
            "./scripts/ai_white_hatter.sh clone-task docs/AI_WHITE_HATTER_TASK.example.yaml /tmp/wh-clone-task.yaml",
            "PYTHONPATH=. .venv/bin/python -m cpos.ai_white_hatter dashboard",
        ],
        "docs": [
            "docs/AI_WHITE_HATTER_SYSTEM_SPEC.md",
            "docs/AI_WHITE_HATTER_OPERATION_TEMPLATES.md",
            "docs/AI_WHITE_HATTER_TASK_SCHEMA.md",
            "docs/AI_WHITE_HATTER_COMMANDS.md",
        ],
        "status": {
            "task_validation_ok": not task_issues,
            "goal_validation_ok": bool(goal_summary.get("validation_ok")),
            "task_review_required": bool(task_data.get("human_review_required")),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "status":
        return _run_status(args.goal_store)
    if args.command == "validate":
        return _run_validate(args.goal_store, as_json=args.json)
    if args.command == "compare":
        return _run_compare()
    if args.command == "review":
        return _run_review(args.host)
    if args.command == "pipeline":
        return _run_pipeline(args.goal_store)
    if args.command == "demo":
        return _run_demo(args.host)
    if args.command == "task":
        return cmd_task(load_task_path(args.file), as_json=False)
    if args.command == "task-json":
        return cmd_task(load_task_path(args.file), as_json=True)
    if args.command == "compare-task":
        return cmd_compare_tasks(load_task_path(args.left), load_task_path(args.right), as_json=args.json)
    if args.command == "compare-many":
        top_n = None if args.top_n is None or args.top_n < 0 else args.top_n
        return cmd_compare_many(load_task_path(args.base), [load_task_path(p) for p in args.candidates] if args.candidates else None, top_n=top_n, as_json=args.json)
    if args.command == "create-task":
        return cmd_create_task(Path(args.file), task_id=args.task_id, title=args.title, target_program=args.target_program, owner=args.owner, scope_status=args.scope_status, human_review_required=args.human_review_required, next_action=args.next_action, as_json=args.json)
    if args.command == "clone-task":
        return cmd_clone_task(Path(args.source), Path(args.file), task_id=args.task_id, title=args.title, target_program=args.target_program, owner=args.owner, scope_status=args.scope_status, human_review_required=args.human_review_required, next_action=args.next_action, as_json=args.json)
    if args.command == "dashboard":
        payload = build_dashboard_summary(args.goal_store, args.task_file)
        _print(payload, as_json=args.json)
        return 0
    if args.command == "tasks":
        _print(build_task_catalog(), as_json=False)
        return 0
    if args.command == "all":
        _run_status(args.goal_store)
        print()
        _run_validate(args.goal_store, as_json=False)
        print()
        _run_compare()
        print()
        cmd_task(load_task_path("docs/AI_WHITE_HATTER_TASK.example.yaml"), as_json=False)
        print()
        _run_review(args.host)
        print()
        _run_pipeline(args.goal_store)
        print()
        _run_demo(args.host)
        return 0
    raise SystemExit(1)


if __name__ == "__main__":
    raise SystemExit(main())
