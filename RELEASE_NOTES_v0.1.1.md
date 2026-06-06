# CPOS Engine-Zero v0.1.1 Release Notes

Post-`v0.1.0` stabilization release focused on External Agent Adapter hardening, integration guidance, dashboard clarity, and local/runtime hygiene.

## What it is

CPOS Engine-Zero v0.1.1 is a small, safety-preserving stabilization release for the defensive, memory-governed AI agent runtime introduced in v0.1.0.

The main theme is **CPOS for Agents**: making CPOS easier to use as a metadata-only safety/governance layer beside external agent systems such as Codex-like, Hermes-like, or OpenClaw-like agents.

## Highlights

### External Agent Adapter schema validation

- Added validation for `/agent-adapter/intake` before Task Tape persistence.
- Invalid payloads return `schema_validation_failed` with metadata-only validation errors.
- Validates event types, command/file arrays, risk values, bool/int metadata fields, proposed diffs, and execution result shapes.
- Rejects raw-output keys such as `stdout`, `stderr`, `output`, `raw_output`, `logs`, and `traceback`.
- Validation responses do not echo raw commands, raw diffs, raw stdout/stderr, request bodies, or secret-like values.

### Adapter payload examples

- Added secret-free fixtures under `examples/payloads/`:
  - `command_request.json`
  - `proposed_diff.json`
  - `execution_result.json`
  - `invalid_raw_execution_result.json`
- Updated adapter integration docs with curl examples for command request, proposed diff, execution result, queue checks, scoreboard checks, and raw-output rejection.

### 5-minute external-agent guide

- Added `docs/EXTERNAL_AGENT_5_MIN_GUIDE.md`.
- Covers local dry-run, localhost curl examples, review queue checks, Human Escalation, execution result scoreboard, raw-output rejection, and safety invariants.
- Does not require public port exposure or secrets.

### Announcement copy pack

- Added `docs/ANNOUNCEMENT_COPY_v0.1.0.md` for reusable post-release/social/community copy.
- Includes CPOS is / is not positioning and do-not-claim guidance.
- Keeps claims grounded: defensive runtime, review-gated, sandbox-first, metadata-only, and external-agent-ready.

### Local runtime file inventory

- Added `docs/LOCAL_RUNTIME_FILE_INVENTORY.md`.
- Documents ignored local/runtime artifacts such as `.venv/`, `cpos/*.jsonl`, `certs/`, `hackathon_report.html`, caches, logs, and local captures.
- Reinforces that cleanup is not automatic and destructive deletion requires explicit user confirmation.

### Dashboard wording polish

- Clarified External Agent Adapter dashboard copy as a metadata-only review queue.
- Clarified that contract approval records metadata only and does not run commands.
- Renamed result display wording toward External Agent Result Scoreboard / redacted-status-only reports.
- Clarified Human Escalation and Ready-to-Run copy around metadata-only decisions and separated approval/run gates.

## Safety posture

v0.1.1 does not add unrestricted auto-execution.

Still not enabled by default:

- automatic live repo patching
- automatic commit/push/PR creation
- real MCP tool execution
- production deployment automation
- port opening automation
- destructive cleanup
- `authorized_keys` changes

Data minimization remains central:

- no raw request body persistence
- no raw diff persistence
- no raw stdout/stderr persistence
- no secret value persistence
- external-agent command approval is contract-only and does not run commands

## Validation

Latest local validation before this release notes draft:

```text
PYTHONPATH=. .venv/bin/python -m pytest tests -q
337 passed

PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
ok=true, secret_scan ok=true count=0, destructive_actions_performed=false
```

Before any `v0.1.1` tag or GitHub Release, run:

```text
git status --short --branch
PYTHONPATH=. .venv/bin/python -m pytest tests -q
PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
PYTHONPATH=. .venv/bin/python -m cpos.release_check --json
```

## Related docs

- `docs/V0_1_1_SUMMARY.md`
- `docs/backlog/V0_1_1_BACKLOG.md`
- `docs/EXTERNAL_AGENT_5_MIN_GUIDE.md`
- `docs/AGENT_ADAPTER_INTEGRATION.md`
- `docs/AGENT_ADAPTER_SCHEMA.md`
- `docs/LOCAL_RUNTIME_FILE_INVENTORY.md`
- `docs/ANNOUNCEMENT_COPY_v0.1.0.md`
