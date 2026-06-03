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
- Safe autonomy loop: dry-run planning -> diff review -> sandbox execution -> retry/replan -> auto fix candidate -> diff review draft -> flow graph/demo snapshot

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
- Sandbox failure replan driver: failed execution metadata can advance to retry review, replan template, and diff-intake checklist without rerun or raw output storage
- Completed sandbox execution results dashboard: statuses, hashes, sizes, and exit codes only
- Sandbox execution retry reviews: failed runs become review-gated metadata-only retry plans
- Sandbox replan templates: approved retries produce suggested focus and next review chain
- Sandbox diff intakes: metadata-only checklist for the next human-supplied diff review
- Auto Fix Candidates: metadata-only repair strategies from replan templates with confidence, required inputs, and no raw diff/output storage
- Diff Review Drafts: metadata-only next-review payload shape from Auto Fix Candidates; diff_text remains an external required input
- Diff Review Draft -> GitHub Diff Review routing: transient diff input only; persisted lineage stores hashes, sizes, counters, and task IDs, not raw diff text
- Sandbox Autonomy Flow Graph: links failed execution -> retry review -> replan template -> diff intake -> auto fix candidate -> diff review draft -> GitHub diff review
- Human Escalation pipeline hints: queue rows include owning pipeline, stage, endpoint hints, and flow graph hints without duplicating approval authority
- Autonomy Loop Demo Panel: dashboard one-screen view of Diff Draft, GitHub Diff Review, Sandbox Execution Review, Execution Result, Retry/Replan, and Flow Graph with safety flags
- Autonomy Loop Demo Snapshot: generated report version of the same safe execution loop for demos and audits
- Execution Scoreboard: completed/success/failure counts, success rate, failure kinds, retry/replan/intake load, and recent failure metadata
- Failure classification: `patch_apply`, `validation_command`, `sandbox_unavailable`, and `policy_rejected`
- Dashboard safe return actions: diff review can be approved back into sandbox execution review; execution reviews can be approved and run only with supplied transient diff input
- Release readiness CLI: non-destructive checks for remote, clean tree, tracked bad artifacts, and required files
- README/PITCH architecture overview, safer-by-design positioning, and safe autonomy demo flow

## Security posture

MCP support is intentionally conservative in this release:

- Real MCP tool execution is not enabled by default.
- Connector definitions must pass static checks.
- Unsafe definitions are rejected and not stored.
- Execution requests are dry-run / metadata-only.
- Capability probes create approval-gated plans only.

Data minimization is a first-class release goal:

- Secrets, `.env` values, SSH keys, tokens, and private certs must stay in Vault/secret files.
- Raw stdout/stderr, raw diff text, request bodies, checkpoint contents, raw handoff bodies, and proposed code blobs are not persisted in Task Tape/dashboard/report surfaces.
- Sandbox run outputs are represented as hashes, sizes, exit codes, status flags, and failure kinds only.
- Runtime JSONL ledgers, caches, pycache, pytest cache, `.venv`, certs, and local reports are ignored and release-blocked.

## Validation

Latest local validation before this release candidate:

```text
PYTHONPATH=. .venv/bin/python -m pytest tests -q
290 passed

PYTHONPATH=. .venv/bin/python -m cpos.secret_scan ... --json
ok=true count=0

PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
ok=true, secret_scan ok=true count=0, destructive_actions_performed=false

PYTHONPATH=. .venv/bin/python -m cpos.release_check --json
ok=true
```

## Before publishing

Follow `OSS_RELEASE_CHECKLIST.md` and review `git status --short` line-by-line.
Confirm the remote is `https://github.com/kagioneko/cpos-engine-zero.git` before pushing.
Do not publish runtime ledgers, `.venv`, cache files, generated local reports,
workspace demos, certificates, or secret material. Keep all API keys, OAuth tokens,
SSH keys, and passwords in Vault or secret files only.
