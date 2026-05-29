# Security Policy

CPOS Engine-Zero is designed as a defensive, approval-gated agent runtime. Treat it
as security-sensitive infrastructure.

## Supported Use

- Defensive code review, remediation planning, audit trails, and governed agent workflows.
- MCP support is currently governance-first: connector checks, review queues,
  dry-run execution reviews, and capability probe plans. Real MCP tool execution is
  intentionally not enabled by default.

## Secrets

Never commit API keys, tokens, SSH keys, OAuth credentials, `.env` files, or private
certificates. Use Vault or a secret-volume file and reference paths only.

Recommended local scan before publishing:

```bash
python3 -m cpos.secret_scan . \
  --exclude .git --exclude .venv --exclude __pycache__ --exclude .pytest_cache \
  --exclude workspace --exclude certs --exclude hackathon_report.html \
  --exclude audit_log.jsonl --exclude pointers.jsonl \
  --exclude task_runs.jsonl --exclude task_checkpoints.jsonl --json
```

## Data We Never Persist

CPOS stores operational metadata so agents can be audited and resumed, but it must
not persist sensitive or high-risk raw data. Keep these out of code, Task Tape,
dashboards, generated reports, handoff bundles, and commits:

- API keys, bearer tokens, HMAC secrets, OAuth tokens, passwords, SSH keys, and private certificates.
- `.env` contents, crontab-inlined secrets, and any secret values rendered from Vault.
- Raw stdout/stderr from sandbox or tool execution; store hashes, sizes, exit codes, and status flags only.
- Raw diff text in persistent ledgers; store diff hashes, byte sizes, changed file paths, and line counts only.
- Request bodies, webhook payloads, checkpoint contents, raw handoff bodies, and proposed code blobs.
- Runtime/local artifacts such as `.venv/`, `__pycache__/`, `.pytest_cache/`, root/runtime `*.jsonl`, local certs, and generated demo reports.

If a feature needs one of these values as input, pass it only through the immediate
review/execution request and avoid logging or writing it to JSONL ledgers.

## Reporting Vulnerabilities

Please open a private security advisory or contact the maintainer privately before
public disclosure. Include impact, reproduction steps, and affected commit/version.

## Deployment Baseline

For production-like deployments, enable HTTPS, API auth, HMAC signing, scoped keys,
rate limits, mTLS fingerprint checks, sandbox strict mode, preflight checks, and
human approval gates.
