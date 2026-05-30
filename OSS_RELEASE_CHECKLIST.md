# OSS Release Checklist

Use this before pushing CPOS Engine-Zero to a public GitHub repository.

## Must pass

- [ ] Confirm this is the correct repo: `git remote -v` shows `https://github.com/kagioneko/cpos-engine-zero.git`.
- [ ] Review `git status --short` line-by-line before staging.
- [ ] Run all tests: `PYTHONPATH=. .venv/bin/pytest -q tests`.
- [ ] Run secret scan:

  ```bash
  PYTHONPATH=. .venv/bin/python -m cpos.secret_scan . \
    --exclude .git --exclude .venv --exclude __pycache__ --exclude .pytest_cache \
    --exclude workspace --exclude certs --exclude hackathon_report.html \
    --exclude audit_log.jsonl --exclude pointers.jsonl \
    --exclude task_runs.jsonl --exclude task_checkpoints.jsonl --json
  ```

- [ ] Run the combined pre-publish safety gate and confirm it reports OK:

  ```bash
  PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
  ```

- [ ] Run the release-readiness CLI and confirm it reports OK:

  ```bash
  PYTHONPATH=. .venv/bin/python -m cpos.release_check
  ```

- [ ] Run tracked bad-artifact check and confirm it prints nothing:

  ```bash
  git ls-files | grep -E '(^|/)__pycache__/|(^|/)\.pytest_cache/|^\.venv/|\.pyc$|\.pyo$|(^|/)pointers\.jsonl$|(^|/)audit_log\.jsonl$|(^|/)task_runs\.jsonl$|(^|/)task_checkpoints\.jsonl$|\.env$|\.pem$|\.key$|\.crt$|\.p12$|\.pfx$'
  ```

- [ ] No `.venv/`, `__pycache__/`, `.pytest_cache/`, `workspace/`, `certs/`, runtime `*.jsonl`, generated local reports, or local demo artifacts staged.
- [ ] No real API keys, bearer tokens, HMAC secrets, OAuth secrets, SSH keys, private certs, passwords, `.env` files, or crontab-inlined secrets staged.
- [ ] No raw stdout/stderr, raw diff text, request bodies, checkpoint contents, raw handoff bodies, or proposed code blobs persisted in docs, ledgers, reports, or tests.
- [ ] If using an AI skill/MCP wrapper for publishing, confirm it follows `docs/GITHUB_PUBLISH_SAFETY_SPEC.md` and performs no staging/commit/push/delete operations by itself.
- [ ] README includes `Safe Autonomy Demo Flow` and clearly states current MCP limitation: dry-run/governance only, no real tool execution by default.
- [ ] README and `docs/HUMAN_ESCALATION_PROTOCOL.md` document `/human-escalations`, dashboard queue routing, and metadata-only persistence.
- [ ] Dashboard/report Human Escalation summaries show review type, severity, reasons, and endpoint hints only; no raw request bodies, raw diffs, stdout/stderr, checkpoint contents, or secret values.
- [ ] SECURITY.md includes `Data We Never Persist`.
- [ ] LICENSE present.

## Never stage / never publish

- Secrets or secret-derived values. Store them in Vault/secret files only.
- `.env`, local cert/key files, SSH material, OAuth tokens, or API tokens.
- Runtime state: root or `cpos/`/`tapes/` JSONL ledgers, nonce/rate-limit state, local pointer/task data.
- Python/local build artifacts: `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, coverage output.
- Generated local reports or screenshots that may contain local paths or runtime metadata unless reviewed.

## Recommended polish

- [ ] Add screenshots or a short demo GIF of the dashboard
- [ ] Add architecture diagram for Context Pointer OS / Task Tape / MCP Governance
- [ ] Add minimal quickstart with local-only dev settings
- [ ] Tag initial release as `v0.1.0`

## Suggested positioning

> CPOS Engine-Zero is a defensive, memory-governed agent runtime: Context Pointer OS,
> append-only Task Tape, hash-chained audits, approval-gated remediation, and
> governance-first MCP integration.
