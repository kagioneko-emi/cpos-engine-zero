# OSS Release Checklist

Use this before pushing CPOS Engine-Zero to a public GitHub repository.

## Must pass

- [ ] Confirm this is the correct repo: `git remote -v` shows `https://github.com/kagioneko/cpos-engine-zero.git`.
- [ ] Review `git status --short` line-by-line before staging; final push state should be `## main...origin/main`.
- [ ] Run all tests: `PYTHONPATH=. .venv/bin/python -m pytest tests -q` and record the current pass count (latest verified: `316 passed`).
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
- [ ] README documents Quick Competitive Demo, `/demo/readiness`, `/demo/fixture`, Autonomy Loop Demo Panel, and Diff Review Draft -> GitHub Diff Review routing with transient diff input only.
- [ ] PITCH.md positions CPOS as `safer-by-design execution power` versus unrestricted write-power agents; avoid unsupported claims that CPOS has fully surpassed Hermes/OpenClaw/Claude Code.
- [ ] Dashboard includes Competitive Demo Readiness and the Autonomy Loop Demo Panel with stage counts and safety flags: `metadata_only=true`, `raw_diff_stored=false`, `raw_outputs_stored=false`, `live_repo_patch=false`, `commit_created=false`, `pushed=false`, `pr_created=false`.
- [ ] Generated report includes Competitive Demo Readiness and the Autonomy Loop Demo Snapshot with the same metadata-only safety flags.
- [ ] Sandbox Flow Graph shows failed execution -> retry/replan -> candidate -> diff draft -> GitHub diff review lineage without raw diffs or raw outputs.
- [ ] Execution Scoreboard shows completed/success/failure counts and recent failure metadata only.
- [ ] README and `docs/HUMAN_ESCALATION_PROTOCOL.md` document `/human-escalations`, dashboard queue routing, and metadata-only persistence.
- [ ] Dashboard/report Human Escalation summaries show review type, severity, reasons, owning pipeline, endpoint hints, and flow hints only; no raw request bodies, raw diffs, stdout/stderr, checkpoint contents, or secret values.
- [ ] SECURITY.md includes `Data We Never Persist`.
- [ ] LICENSE present.

## Never stage / never publish

- Secrets or secret-derived values. Store them in Vault/secret files only.
- `.env`, local cert/key files, SSH material, OAuth tokens, or API tokens.
- Runtime state: root or `cpos/`/`tapes/` JSONL ledgers, nonce/rate-limit state, local pointer/task data.
- Python/local build artifacts: `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, coverage output.
- Generated local reports or screenshots that may contain local paths or runtime metadata unless reviewed.

## Recommended polish

- [ ] Add screenshots or a short demo GIF of Competitive Demo Readiness, Human Escalation Queue, Ready-to-Run Gate, and Sandbox Flow Graph.
- [ ] Add architecture diagram for Context Pointer OS / Task Tape / Human Escalation / Sandbox Flow Graph.
- [ ] Add minimal quickstart with local-only dev settings.
- [ ] Add release notes for the safe execution loop: execution driver, retry/replan, auto fix candidates, patch generation review, validation harness, ready-to-run gate, demo fixture, competitive demo readiness, flow graph, and report snapshot.
- [ ] Tag initial release as `v0.1.0` only after final push-state, test, prepublish, and secret scan checks are clean.

## Suggested positioning

> CPOS Engine-Zero is a defensive, memory-governed agent runtime: Context Pointer OS,
> append-only Task Tape, hash-chained audits, Human Escalation, sandbox-first
> execution, metadata-only failure-to-replan lineage, and safer-by-design
> autonomy loop demos in dashboard/report form.
