# CPOS Engine-Zero v0.1.0 Release Notes

Initial OSS-oriented release candidate.

## What it is

CPOS Engine-Zero is a defensive, memory-governed AI agent runtime focused on
safe automation rather than unconstrained tool use.

Core idea:

- Relationship/task/state separation by design intent
- Context Pointer OS for lightweight memory references
- Task Tape for append-only work history and rollback checkpoints
- Human approval gates before sensitive actions
- Hash-chained audit logs for tamper-evident operation
- Governance-first MCP integration
- Safe autonomy loop: dry-run planning -> diff review -> sandbox validation -> retry/replan metadata

## Highlights

- Context Pointer OS lifecycle, retrieval policy, trust scoring, invalidation, exchange
- Task Tape append-only execution ledger and checkpoint/rollback model
- Dashboard and generated HTML report
- HTTPS/auth/HMAC/mTLS/rate-limit/security-profile hardening hooks
- Vault-oriented secret handling and secret-scan tooling
- Handoff inbox, promotion plans, resume planning, and multi-agent handoff graph
- MCP connector static security checks
- MCP connector import/review queue
- MCP dry-run execution adapter: no tool execution, no raw argument storage
- MCP capability probe plans: no server start, no network request, no secret file read
- GitHub PR dry-run workflow: approval-gated issue-to-PR metadata plans with no branch/commit/push/PR creation
- GitHub diff review adapter: metadata-only diff hashes/sizes/line counts with no patch apply or commit
- Sandbox patch plan gate: metadata-only ephemeral workspace plan with no patch apply or command execution
- Sandbox patch execution review: metadata-only isolated runner readiness plan with no workspace copy or command execution
- Sandbox patch execution run: ephemeral workspace copy, patch apply, and validation with hash/metadata-only result storage
- Sandbox execution driver: one-call review-gated advance from approved diff to optional ephemeral run, with explicit confirmation flags and metadata-only storage
- Completed sandbox execution results dashboard: statuses, hashes, sizes, and exit codes only
- Sandbox execution retry reviews: failed runs become review-gated metadata-only retry plans
- Sandbox replan templates: approved retries produce suggested focus and next review chain
- Sandbox diff intakes: metadata-only checklist for the next human-supplied diff review
- Failure classification: `patch_apply`, `validation_command`, `sandbox_unavailable`, and `policy_rejected`
- Release readiness CLI: non-destructive checks for remote, clean tree, tracked bad artifacts, and required files
- README architecture overview and safe autonomy demo flow

## Security posture

MCP support is intentionally conservative in this release:

- Real MCP tool execution is not enabled by default.
- Connector definitions must pass static checks.
- Unsafe definitions are rejected and not stored.
- Execution requests are dry-run / metadata-only.
- Capability probes create approval-gated plans only.

Data minimization is a first-class release goal:

- Secrets, `.env` values, SSH keys, tokens, and private certs must stay in Vault/secret files.
- Raw stdout/stderr, raw diff text, request bodies, checkpoint contents, and raw handoff bodies are not persisted.
- Runtime JSONL ledgers, caches, pycache, pytest cache, `.venv`, certs, and local reports are ignored and release-blocked.

## Validation

Latest local validation before this release candidate:

```text
PYTHONPATH=. .venv/bin/pytest -q tests
228 passed

PYTHONPATH=. .venv/bin/python -m cpos.secret_scan ... --json
ok=true count=0

PYTHONPATH=. .venv/bin/python -m cpos.release_check --json
ok=true
```

## Before publishing

Follow `OSS_RELEASE_CHECKLIST.md` and review `git status --short` line-by-line.
Do not publish runtime ledgers, `.venv`, cache files, generated local reports,
workspace demos, certificates, or secret material.
