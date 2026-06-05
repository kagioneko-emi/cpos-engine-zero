# Local Runtime File Inventory

This document is a doc-only inventory for local/runtime artifacts that may appear in a CPOS Engine-Zero working tree after demos, tests, local servers, or release checks.

It does not instruct the agent to delete anything. Cleanup is a separate human-confirmed operation.

## Ground rules

- Do not delete files automatically.
- Do not run `rm -rf` without explicit confirmation from the user.
- Do not overwrite local runtime files without checking purpose and ownership first.
- Do not print secrets, private keys, token values, `.env` contents, cert/key material, raw stdout/stderr, or raw request bodies.
- If a file appears to contain credentials, move the secret-handling plan to Vault instead of copying values into code, docs, chat, logs, or commits.
- Keep runtime/local artifacts out of commits unless they are intentionally sanitized fixtures or docs.

## Common ignored local artifacts

| Path / pattern | Typical source | Commit? | Notes |
|---|---|---:|---|
| `.venv/` | local Python virtualenv | no | Required for local development; recreate from dependencies when needed. Do not vendor it. |
| `cpos/*.jsonl` | Task Tape, audit logs, runtime checkpoints | no | May contain local execution metadata. Do not publish raw runtime history by accident. |
| `certs/` | local TLS/cert/key material | no | Treat private keys and cert material as sensitive. Do not print contents. |
| `hackathon_report.html` | local generated report/demo output | no | Generated local artifact. Review before sharing; do not assume it is sanitized. |
| `__pycache__/` | Python bytecode cache | no | Recreated automatically. |
| `.pytest_cache/` | pytest cache | no | Recreated automatically. |
| `.mypy_cache/`, `.ruff_cache/` | local tooling cache | no | Recreated automatically if tools are used. |
| `*.log` | local command/server logs | no | Logs may contain paths or sensitive snippets. Inspect carefully. |
| local screenshots/captures outside `docs/assets/demo/` | manual demo capture | usually no | Only commit sanitized, intentionally selected demo assets. |

## Known examples in this workspace

These examples have appeared during local development or release/demo work:

- `hackathon_report.html`
- `cpos/audit_log.jsonl`
- `cpos/*.jsonl`
- `certs/`
- `.venv/`
- Python `__pycache__/` directories

Do not display the contents of cert/key files, token files, `.env` files, private logs, or runtime histories in chat. Use metadata-only descriptions such as path, tracked/ignored status, and file type.

## Why this matters

CPOS intentionally separates repo source from runtime evidence. Runtime files can be useful locally, but publishing them can undermine the safety posture by leaking:

- local execution history
- raw outputs or request fragments
- private paths or operator names
- cert/key material
- accidental secret values

The default posture is: source and sanitized fixtures are commit candidates; local runtime state is not.

## Safe inspection commands

Use these to inspect status without printing sensitive file contents:

```bash
git status --short --ignored
git check-ignore -v .venv cpos/audit_log.jsonl certs/key.pem hackathon_report.html
find . -maxdepth 2 -type f -name '*.jsonl' -print
find . -maxdepth 2 -type d \( -name '__pycache__' -o -name '.pytest_cache' -o -name '.ruff_cache' \) -print
```

Avoid commands that dump file bodies, especially for:

- `certs/*`
- `.env*`
- token files
- private keys
- raw logs
- runtime JSONL histories

## Cleanup policy

Cleanup is allowed only as a separate, explicit, human-confirmed task.

Before cleanup:

1. Confirm the exact paths.
2. Confirm whether each path is tracked or ignored.
3. Confirm whether the file may contain secrets or useful local evidence.
4. Ask the user before deleting or overwriting.
5. Never modify `authorized_keys`.

For destructive cleanup, ask first and do not bundle it into unrelated implementation work.

## Commit safety checklist

Before any commit/push/publish:

```bash
git status --short --branch
PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
```

Expected safety posture:

- working tree only contains intended source/docs/test changes
- `prepublish_check ok=true`
- secret scan `count=0`
- no local runtime artifacts staged
- no raw diff/output/request/secret values added to tracked files
