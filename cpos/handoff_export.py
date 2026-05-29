from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .hash_chain import verify_hash_chain
from .pointer_os import ContextPointer, PointerManager, utc_now
from .secret_inventory import latest_records
from .security_validation import validate_security_posture
from .task_tape import TaskTapeStore

SENSITIVE_PAYLOAD_KEYS = {
    "content",
    "checkpoint_content",
    "proposed_code",
    "request_body",
    "body",
    "token",
    "secret",
    "password",
    "private_key",
    "api_key",
    "authorization",
}


def default_paths(project_root: str | Path | None = None) -> dict[str, str]:
    root = Path(project_root or os.environ.get("CPOS_PROJECT_ROOT") or Path.cwd()).resolve()
    return {
        "project_root": str(root),
        "pointer_path": os.environ.get("CPOS_POINTER_STORE_PATH") or str(root / "cpos" / "pointers.jsonl"),
        "pointer_audit_path": os.environ.get("CPOS_POINTER_AUDIT_PATH") or str(root / "cpos" / "audit_log.jsonl"),
        "task_tape_path": os.environ.get("CPOS_TASK_TAPE_PATH") or str(root / "tapes" / "task_runs.jsonl"),
        "task_checkpoint_path": os.environ.get("CPOS_TASK_CHECKPOINT_PATH") or str(root / "tapes" / "task_checkpoints.jsonl"),
        "security_audit_path": os.environ.get("CPOS_SECURITY_AUDIT_PATH") or str(root / "cpos" / "security_audit.jsonl"),
        "secret_inventory_path": os.environ.get("CPOS_SECRET_INVENTORY_PATH") or str(root / "cpos" / "secret_inventory.jsonl"),
        "next_handoff_path": os.environ.get("CPOS_NEXT_HANDOFF_PATH") or str(root / "NEXT_HANDOFF.md"),
    }


def _redacted_payload_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    safe: dict[str, Any] = {}
    redacted_keys = []
    for key, value in payload.items():
        lower_key = str(key).lower()
        if lower_key in SENSITIVE_PAYLOAD_KEYS or any(marker in lower_key for marker in ("secret", "token", "password", "key")):
            redacted_keys.append(str(key))
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[str(key)] = value if not isinstance(value, str) or len(value) <= 180 else value[:177] + "..."
        elif isinstance(value, (list, tuple)):
            safe[str(key)] = {"type": "list", "count": len(value)}
        elif isinstance(value, dict):
            safe[str(key)] = {"type": "dict", "keys": sorted(str(k) for k in value.keys())[:20]}
        else:
            safe[str(key)] = {"type": type(value).__name__}
    if redacted_keys:
        safe["_redacted_keys"] = sorted(redacted_keys)
    return safe


def _pointer_summary(pointer_path: str, pointer_audit_path: str, *, limit: int) -> dict[str, Any]:
    manager = PointerManager(pointer_path, pointer_audit_path)
    pointers = manager.load()
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for pointer in pointers:
        by_status[pointer.status] = by_status.get(pointer.status, 0) + 1
        by_type[pointer.context_type] = by_type.get(pointer.context_type, 0) + 1
    top = sorted(pointers, key=lambda p: (p.priority * 0.6 + p.trust_score * 0.4, p.created_at), reverse=True)[:limit]
    return {
        "count": len(pointers),
        "by_status": by_status,
        "by_type": by_type,
        "avg_trust": round(sum(p.trust_score for p in pointers) / len(pointers), 4) if pointers else 0.0,
        "top": [
            {
                "pointer_id": p.pointer_id,
                "context_type": p.context_type,
                "summary": p.summary,
                "source": p.source,
                "location": p.location,
                "priority": p.priority,
                "trust_score": p.trust_score,
                "sensitivity_level": p.sensitivity_level,
                "status": p.status,
                "created_at": p.created_at,
            }
            for p in top
        ],
    }


def _task_summary(task_tape_path: str, task_checkpoint_path: str, *, limit: int) -> dict[str, Any]:
    store = TaskTapeStore(task_tape_path, task_checkpoint_path)
    summary = store.summary()
    recent_events = store.events()[-limit:]
    recent_events.reverse()
    return {
        "summary": {
            "task_count": summary["task_count"],
            "event_count": summary["event_count"],
            "checkpoint_count": summary["checkpoint_count"],
            "latest_event": _sanitize_event(summary.get("latest_event")),
        },
        "pending_review_count": len(store.pending_reviews()),
        "recent_events": [_sanitize_event(event.to_dict()) for event in recent_events],
    }


def _sanitize_event(event: dict[str, Any] | None) -> dict[str, Any] | None:
    if not event:
        return None
    return {
        "event_id": event.get("event_id"),
        "task_id": event.get("task_id"),
        "event": event.get("event"),
        "timestamp": event.get("timestamp"),
        "target": event.get("target"),
        "checkpoint_id": event.get("checkpoint_id"),
        "status": event.get("status"),
        "payload": _redacted_payload_summary(event.get("payload") if isinstance(event.get("payload"), dict) else {}),
    }


def _integrity_summary(paths: dict[str, str]) -> dict[str, Any]:
    targets = {
        "pointer_audit": paths["pointer_audit_path"],
        "task_events": paths["task_tape_path"],
        "task_checkpoints": paths["task_checkpoint_path"],
        "security_audit": paths["security_audit_path"],
        "secret_inventory": paths["secret_inventory_path"],
    }
    return {name: verify_hash_chain(path) for name, path in targets.items()}


def _secret_inventory_summary(path: str, *, limit: int) -> dict[str, Any]:
    records = list(latest_records(path).values())
    by_status: dict[str, int] = {}
    for record in records:
        status = str(record.get("status", "unknown"))
        by_status[status] = by_status.get(status, 0) + 1
    recent = sorted(records, key=lambda row: row.get("timestamp", ""), reverse=True)[:limit]
    return {
        "count": len(records),
        "by_status": by_status,
        "latest": [
            {
                "artifact_path": row.get("artifact_path"),
                "artifact_type": row.get("artifact_type"),
                "vault_path": row.get("vault_path"),
                "field": row.get("field"),
                "runtime_destination": row.get("runtime_destination"),
                "status": row.get("status"),
                "timestamp": row.get("timestamp"),
            }
            for row in recent
        ],
    }


def _next_handoff_excerpt(path: str, *, max_chars: int) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"exists": False, "path": path, "excerpt": ""}
    text = p.read_text(encoding="utf-8", errors="replace")
    excerpt = text[:max_chars]
    if len(text) > max_chars:
        excerpt += "\n... [truncated]"
    return {"exists": True, "path": path, "chars": len(text), "excerpt": excerpt}


def build_handoff_bundle(*, project_root: str | Path | None = None, limit: int = 8, include_next_chars: int = 6000, environ=None) -> dict[str, Any]:
    paths = default_paths(project_root)
    return {
        "schema": "cpos.multi_agent_handoff.v1",
        "generated_at": utc_now(),
        "safety": {
            "secrets_included": False,
            "checkpoint_contents_included": False,
            "request_bodies_included": False,
            "notes": "This bundle includes metadata and summaries only. Tokens, private keys, checkpoint content, and proposed_code payloads are redacted/excluded.",
        },
        "paths": paths,
        "security_profile": validate_security_posture(environ=environ),
        "integrity": _integrity_summary(paths),
        "pointers": _pointer_summary(paths["pointer_path"], paths["pointer_audit_path"], limit=limit),
        "tasks": _task_summary(paths["task_tape_path"], paths["task_checkpoint_path"], limit=limit),
        "secret_inventory": _secret_inventory_summary(paths["secret_inventory_path"], limit=limit),
        "next_handoff": _next_handoff_excerpt(paths["next_handoff_path"], max_chars=include_next_chars),
        "recommended_next_steps": [
            "Run hardened preflight before deployment: python3 -m cpos.preflight --profile hardened --json",
            "Keep runtime secrets in Vault-rendered 0600 files; do not place tokens in .env, code, logs, or crontab.",
            "Use this handoff bundle as the cross-agent context seed instead of passing raw logs/checkpoints.",
        ],
    }


def render_markdown(bundle: dict[str, Any]) -> str:
    def status_map(items: dict[str, int]) -> str:
        return ", ".join(f"{key}={value}" for key, value in sorted(items.items())) or "none"

    profile = bundle["security_profile"]
    pointers = bundle["pointers"]
    tasks = bundle["tasks"]["summary"]
    inventory = bundle["secret_inventory"]
    failed_integrity = [name for name, result in bundle["integrity"].items() if not result.get("ok")]

    lines = [
        "# CPOS Multi-Agent Handoff",
        "",
        f"Generated: `{bundle['generated_at']}`",
        f"Schema: `{bundle['schema']}`",
        "",
        "## Safety",
        "",
        "- Secrets included: **no**",
        "- Checkpoint contents included: **no**",
        "- Request bodies included: **no**",
        "",
        "## Security Profile",
        "",
        f"- Profile: `{profile.get('profile')}`",
        f"- Validation OK: `{profile.get('ok')}`",
        f"- Failures: `{len(profile.get('failures', []))}`",
        "",
        "## Integrity",
        "",
        f"- Failed ledgers: `{', '.join(failed_integrity) if failed_integrity else 'none'}`",
    ]
    for name, result in bundle["integrity"].items():
        lines.append(f"- `{name}`: ok={result.get('ok')} rows={result.get('row_count', 0)} head={str(result.get('head_hash', '-'))[:16]}")
    lines.extend([
        "",
        "## Pointer OS",
        "",
        f"- Pointers: `{pointers['count']}`",
        f"- By status: {status_map(pointers['by_status'])}",
        f"- By type: {status_map(pointers['by_type'])}",
        f"- Average trust: `{pointers['avg_trust']}`",
        "",
        "## Task Tape",
        "",
        f"- Tasks: `{tasks['task_count']}`",
        f"- Events: `{tasks['event_count']}`",
        f"- Checkpoints: `{tasks['checkpoint_count']}`",
        f"- Pending reviews: `{bundle['tasks']['pending_review_count']}`",
        "",
        "## Secret Inventory",
        "",
        f"- Artifacts tracked: `{inventory['count']}`",
        f"- By status: {status_map(inventory['by_status'])}",
        "",
        "## NEXT_HANDOFF excerpt",
        "",
        "```markdown",
        bundle["next_handoff"].get("excerpt", ""),
        "```",
        "",
        "## Recommended next steps",
        "",
    ])
    lines.extend(f"- {step}" for step in bundle["recommended_next_steps"])
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export a sanitized CPOS multi-agent handoff bundle.")
    parser.add_argument("--project-root", default=None)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--include-next-chars", type=int, default=6000)
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--output", help="Optional output file. Defaults to stdout.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    bundle = build_handoff_bundle(project_root=args.project_root, limit=max(1, args.limit), include_next_chars=max(0, args.include_next_chars))
    if args.format == "markdown":
        rendered = render_markdown(bundle)
    else:
        rendered = json.dumps(bundle, ensure_ascii=False, indent=2)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered + ("" if rendered.endswith("\n") else "\n"), encoding="utf-8")
        print(json.dumps({"ok": True, "output": str(path), "format": args.format}, ensure_ascii=False))
        return
    print(rendered)


if __name__ == "__main__":
    main()
