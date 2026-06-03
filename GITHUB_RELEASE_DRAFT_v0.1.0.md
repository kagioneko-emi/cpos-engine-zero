# CPOS Engine-Zero v0.1.0

CPOS Engine-Zero is a defensive, memory-governed AI agent runtime focused on **safer-by-design execution power**: review-gated, sandbox-first, metadata-only, and failure-to-replan aware.

This release is not positioned as an unrestricted coding agent. Instead, it demonstrates an auditable execution loop for AI agents that can plan, route, sandbox, observe failure metadata, replan, and prepare the next diff attempt without silently patching the live repository or persisting sensitive raw data.

## Why it matters

Most autonomous coding agents optimize for speed and tool reach. CPOS Engine-Zero optimizes for controlled execution:

- Human approval before risky stages
- Sandbox-first patch validation
- No live repository patching from planning/review stages
- No automatic commit, push, or PR creation
- Raw diffs and raw stdout/stderr excluded from persistent Task Tape/dashboard/report surfaces
- Failure metadata converted into retry/replan artifacts instead of blind automatic reruns
- Dashboard and report views that explain the loop end-to-end

## Safe autonomy loop

The v0.1.0 flow is:

```text
Diff Draft
→ GitHub Diff Review
→ Sandbox Execution Review
→ Supplied-diff Sandbox Run
→ Execution Result
→ Retry/Replan
→ Auto Fix Candidate
→ Diff Review Draft
→ Sandbox Flow Graph / Demo Snapshot
```

The loop stores hashes, sizes, counters, statuses, task IDs, failure kinds, and lineage metadata. It does not persist raw diff text, raw command output, secrets, request bodies, or checkpoint contents.

## Highlights

### Execution and replan loop

- Sandbox execution driver for review-gated advancement from approved diff to sandbox plan, execution review, optional approval, and optional ephemeral run
- Failed sandbox execution replan driver for retry review, replan template, and diff-intake checklist
- Auto Fix Candidates from failure/replan metadata only
- Diff Review Drafts that describe the next review payload shape while keeping `diff_text` external
- Diff Review Draft → GitHub Diff Review routing with transient diff input and metadata-only persisted lineage

### Dashboard and report visibility

- Autonomy Loop Demo Panel in the dashboard
- Autonomy Loop Demo Snapshot in generated reports
- Sandbox Autonomy Flow Graph linking failed execution → retry/replan → candidate → diff draft → GitHub diff review
- Execution Scoreboard with completed/success/failure counts, success rate, failure kinds, and recent failure metadata
- Human Escalation Queue with owning pipeline, stage, endpoint hints, and flow hints

### Security and release safety

- Metadata-only persistence policy for raw diffs, raw outputs, request bodies, checkpoint contents, and secrets
- Secret scan and prepublish safety gate
- Release readiness check for correct remote, clean tree, tracked bad artifacts, and required files
- Vault-first secret handling policy
- Runtime ledgers, caches, `.venv`, certs, and local reports excluded from release artifacts

## Positioning

CPOS Engine-Zero is best compared with autonomous coding agents on a specific axis: **safe and auditable execution loops**.

It does not claim to be the fastest unrestricted coding agent. The differentiation is that CPOS adds governance around execution power:

- review-gated actions
- sandbox-first validation
- metadata-only storage
- failure-to-replan lineage
- operator-visible flow graphs
- release-time secret and artifact checks

That makes CPOS suitable for defensive, regulated, or audit-sensitive workflows where agent actions must be explainable and reversible.

## Validation

Latest verified local checks before this release draft:

```text
PYTHONPATH=. .venv/bin/python -m pytest tests -q
290 passed

PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
ok=true
secret_scan ok=true count=0

git status --short --branch
## main...origin/main
```

## Before publishing

Before creating a GitHub Release or tag, follow `OSS_RELEASE_CHECKLIST.md` and confirm:

- remote is `https://github.com/kagioneko/cpos-engine-zero.git`
- working tree is clean
- full tests pass
- `prepublish_check --json` is OK
- secret scan reports `count=0`
- tracked bad-artifact check prints nothing

Do not publish runtime ledgers, `.venv`, cache files, generated local reports, workspace demos, certificates, `.env` files, API keys, OAuth tokens, SSH keys, or secret material.
