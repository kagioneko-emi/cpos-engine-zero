# OSS Release Checklist

Use this before pushing CPOS Engine-Zero to a public GitHub repository.

## Must pass

- [ ] `PYTHONPATH=. .venv/bin/pytest -q tests`
- [ ] `python3 -m cpos.secret_scan . --exclude .git --exclude .venv --exclude __pycache__ --exclude .pytest_cache --exclude workspace --exclude certs --exclude hackathon_report.html --exclude audit_log.jsonl --exclude pointers.jsonl --exclude task_runs.jsonl --exclude task_checkpoints.jsonl --json --exclude workspace --exclude certs --exclude hackathon_report.html --exclude audit_log.jsonl --exclude pointers.jsonl --exclude task_runs.jsonl --exclude task_checkpoints.jsonl --json`
- [ ] `git status --short` reviewed line-by-line
- [ ] No `.venv/`, `__pycache__/`, `workspace/`, `certs/`, runtime `*.jsonl`, or generated local reports staged
- [ ] No real API keys, tokens, SSH keys, OAuth secrets, private certs, or `.env` files staged
- [ ] README clearly states current MCP limitation: dry-run/governance only, no real tool execution by default
- [ ] LICENSE present
- [ ] SECURITY.md present

## Recommended polish

- [ ] Add screenshots or a short demo GIF of the dashboard
- [ ] Add architecture diagram for Context Pointer OS / Task Tape / MCP Governance
- [ ] Add minimal quickstart with local-only dev settings
- [ ] Tag initial release as `v0.1.0`

## Suggested positioning

> CPOS Engine-Zero is a defensive, memory-governed agent runtime: Context Pointer OS,
> append-only Task Tape, hash-chained audits, approval-gated remediation, and
> governance-first MCP integration.
