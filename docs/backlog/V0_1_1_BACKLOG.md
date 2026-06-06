# CPOS Engine-Zero v0.1.1 Backlog

This backlog starts after the official `v0.1.0` release. Keep v0.1.1 small, stabilization-focused, and compatible with the v0.1.0 safety posture.

## Guiding rule

Do not add large runtime features unless there is a concrete target integration. Prefer documentation, examples, schema validation, dashboard wording, and safety-preserving polish.

## Priority 1 — Adapter schema validation

Status: implemented on `main` after v0.1.0; keep extending tests/docs as integrations appear.

Goal: make External Agent Adapter requests easier to validate and safer to integrate.

Suggested scope:

- Add lightweight validation helper for `/agent-adapter/intake` payloads.
- Validate `event_type` required values.
- Validate `commands` and `changed_files` are arrays of strings.
- Validate `metadata.risk` when present: `low`, `medium`, `high`, `critical`.
- Validate `execution_result` uses redacted/status-only shape in examples/tests.
- Return metadata-only validation errors without echoing raw request bodies.

Acceptance criteria:

- New tests cover valid/invalid `command_request`, `proposed_diff`, and `execution_result`.
- Invalid responses do not persist raw request bodies or secrets.
- `prepublish_check` remains `ok=true`.

## Priority 2 — More adapter client examples

Status: implemented on `main`; payload fixtures live under `examples/payloads/`.

Goal: make CPOS easy to connect to external agents.

Suggested scope:

- Add curl examples for:
  - command request
  - proposed diff
  - execution result
- Add example payload files under `examples/payloads/` if useful.
- Keep examples secret-free and metadata-only.

Acceptance criteria:

- README or integration docs link to examples.
- Secret scan returns `count=0`.

## Priority 3 — 5-minute external-agent safety-layer guide

Status: implemented on `main`; see `docs/EXTERNAL_AGENT_5_MIN_GUIDE.md`.

Goal: explain how to use CPOS as “CPOS for Agents”.

Suggested scope:

- New doc: `docs/EXTERNAL_AGENT_5_MIN_GUIDE.md`
- Sections:
  - what CPOS does
  - what CPOS does not do
  - local dry-run with `examples/agent_adapter_client.py`
  - review queue check
  - result scoreboard check
  - safety invariants

Acceptance criteria:

- Can be followed without secrets.
- Does not require opening public ports.
- Uses localhost/protected endpoint examples only.

## Priority 4 — Announcement copy pack

Status: implemented on `main`; see `docs/ANNOUNCEMENT_COPY_v0.1.0.md`.

Goal: prepare reusable post-release communications.

Suggested scope:

- New doc: `docs/ANNOUNCEMENT_COPY_v0.1.0.md`
- Include:
  - short X/social post
  - Discord-style update
  - GitHub/README blurb
  - Notion summary link
  - “what it is / is not” positioning

Acceptance criteria:

- No unsupported claims like “fully autonomous unrestricted coding agent”.
- Uses v0.1.0 release draft as tone baseline.

## Priority 5 — Local runtime file inventory

Status: implemented on `main`; see `docs/LOCAL_RUNTIME_FILE_INVENTORY.md`.

Goal: help keep the working directory understandable after release.

Suggested scope:

- Add doc-only inventory of ignored runtime/local artifacts.
- Include examples:
  - `hackathon_report.html`
  - `cpos/*.jsonl`
  - `certs/`
  - `.venv/`
- Do not delete anything automatically.

Acceptance criteria:

- No destructive action.
- Clear instructions that deletion/cleanup requires explicit confirmation.

## Priority 6 — Dashboard wording polish

Status: implemented on `main`; dashboard copy now emphasizes metadata-only review contracts, no auto execution, and separated approval/run gates.

Goal: make demo/dashboard copy clearer for first-time viewers.

Suggested scope:

- Improve labels around External Agent Adapter result scoreboard.
- Ensure “metadata-only” and “no auto execute” are visible.
- Avoid clutter and unsupported claims.

Acceptance criteria:

- Dashboard tests remain green.
- No functional behavior change unless separately reviewed.

## Out of scope for v0.1.1 unless explicitly requested

- automatic live repo patching
- automatic commit/push/PR creation
- real MCP tool execution by default
- production deployment automation
- port opening automation
- destructive cleanup
- `authorized_keys` changes

## Release discipline

Before any v0.1.1 release candidate:

```bash
git status --short --branch
PYTHONPATH=. .venv/bin/python -m pytest tests -q
PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
PYTHONPATH=. .venv/bin/python -m cpos.release_check --json
```

Current stabilization baseline after Priority 1–6:

- full tests: `335 passed`
- prepublish: `ok=true`
- secret scan: `count=0`
