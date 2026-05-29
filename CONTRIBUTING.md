# Contributing

Thanks for helping improve CPOS Engine-Zero.

## Development Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONPATH=. .venv/bin/pytest -q tests
```

## Safety Rules

- Do not commit secrets, `.env` files, private keys, tokens, or generated runtime ledgers.
- Keep MCP additions governance-first: static checks, review queues, dry-run metadata,
  and explicit approval gates before any real execution capability.
- Add tests for security-sensitive behavior.
- Prefer HTTPS-only examples.
- Do not weaken approval gates or secret redaction.

## Before a PR

```bash
PYTHONPATH=. .venv/bin/pytest -q tests
python3 -m cpos.secret_scan . --exclude .git --exclude .venv --exclude __pycache__ --exclude .pytest_cache --exclude workspace --exclude certs --exclude hackathon_report.html --exclude audit_log.jsonl --exclude pointers.jsonl --exclude task_runs.jsonl --exclude task_checkpoints.jsonl --json --exclude workspace --exclude certs --exclude hackathon_report.html --exclude audit_log.jsonl --exclude pointers.jsonl --exclude task_runs.jsonl --exclude task_checkpoints.jsonl --json
```
