# CPOS Engine-Zero v0.1.1

CPOS Engine-Zero v0.1.1 is a small stabilization release after the official v0.1.0 launch.

The focus is **CPOS for Agents**: making the External Agent Adapter safer, easier to validate, easier to integrate, and clearer to demo as a metadata-only safety/governance layer beside Codex-like, Hermes-like, or OpenClaw-like systems.

This release does not turn CPOS into an unrestricted auto-execution agent. It preserves the v0.1.0 posture: review-gated, sandbox-first, metadata-only, and explicit about human approval boundaries.

## Highlights

### External Agent Adapter validation

`/agent-adapter/intake` now validates payloads before Task Tape persistence.

Validation covers:

- supported event types
- `commands` and `changed_files` arrays
- `metadata.risk` values
- boolean and integer metadata fields
- required command request / proposed diff / execution result shapes
- rejection of raw-output keys such as `stdout`, `stderr`, `output`, `raw_output`, `logs`, and `traceback`

Invalid responses are metadata-only and do not echo raw commands, raw diffs, raw stdout/stderr, request bodies, or secret-like values.

### Integration examples and 5-minute guide

New secret-free payload examples live under `examples/payloads/`:

- command request
- proposed diff
- redacted/status-only execution result
- intentionally invalid raw-output example

The new `docs/EXTERNAL_AGENT_5_MIN_GUIDE.md` walks through a local, localhost-first flow without public port exposure or secrets.

### Dashboard clarity

Dashboard copy now more clearly explains:

- External Agent Adapter is a metadata-only review queue
- contract approval does not run commands
- result reports are redacted/status-only scoreboard inputs
- Human Escalation is a metadata-only assisted-autonomy gate
- Ready-to-Run plan approval and actual run remain separate

### Local runtime hygiene

`docs/LOCAL_RUNTIME_FILE_INVENTORY.md` documents local runtime artifacts such as `.venv/`, `cpos/*.jsonl`, `certs/`, `hackathon_report.html`, caches, logs, and local captures.

It is doc-only: no automatic cleanup and no destructive deletion without explicit confirmation.

### Communication copy

`docs/ANNOUNCEMENT_COPY_v0.1.0.md` provides reusable social/community/README/Notion copy and safe positioning guidance.

## Safety posture

v0.1.1 keeps these invariants:

```json
{
  "metadata_only": true,
  "raw_request_stored": false,
  "raw_diff_stored": false,
  "raw_outputs_stored": false,
  "secret_values_stored": false,
  "execute_automatically": false,
  "destructive_actions_performed": false
}
```

Not enabled by default:

- automatic live repo patching
- automatic commit/push/PR creation
- real MCP tool execution
- production deployment automation
- port opening automation
- destructive cleanup
- `authorized_keys` changes

## Validation

Latest local checks before this draft:

```text
PYTHONPATH=. .venv/bin/python -m pytest tests -q
333 passed

PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
ok=true
secret_scan ok=true count=0

git status --short --branch
## main...origin/main
```

Before publishing/tagging, confirm:

- remote is `https://github.com/kagioneko/cpos-engine-zero.git`
- working tree is clean
- full tests pass
- `prepublish_check --json` is OK
- `release_check --json` is OK
- secret scan reports `count=0`

Do not publish runtime ledgers, `.venv`, cache files, generated local reports, workspace demos, certificates, `.env` files, API keys, OAuth tokens, SSH keys, private keys, or secret material.
