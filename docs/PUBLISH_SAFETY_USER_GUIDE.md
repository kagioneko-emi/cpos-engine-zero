# GitHub Publish Safety User Guide

A friendly guide for checking whether CPOS Engine-Zero is safe to publish to GitHub.

## What this protects

Before pushing, the safety gate checks for common mistakes:

- Wrong GitHub repository or account.
- Uncommitted changes that have not been reviewed.
- Local-only files such as `.venv/`, caches, runtime JSONL logs, and generated reports.
- High-risk secret patterns such as private keys, API-like keys, Vault tokens, and GitHub tokens.
- Missing release files such as `README.md` or `SECURITY.md`.

It is intentionally non-destructive. It does not stage, commit, push, delete, rewrite
history, open ports, or read secret values from Vault.

## The one command

Run this from the repository root:

```bash
PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
```

## How to read the result

If everything is safe enough to proceed, you should see:

```json
{
  "ok": true,
  "failures": []
}
```

If `ok` is `false`, stop before pushing and look at `failures`.

Common failure names:

| Failure | Meaning | What to do |
| --- | --- | --- |
| `github_publish_guard` | Repository, git status, or publish-boundary issue | Check remote, review dirty files, remove/ignore local artifacts |
| `release_check` | CPOS release checklist issue | Add missing required docs or fix tracked bad artifacts |
| `secret_scan` | High-risk secret-like pattern found | Move real secrets to Vault, replace examples with placeholders |

## Safe response rules

When the gate fails:

1. Do not push.
2. Do not paste secret values into chat, logs, commits, or issues.
3. Do not auto-delete files without human confirmation.
4. Fix the cause, then run the command again.

## What is okay to publish

Usually okay after review:

- Placeholder examples such as `TOKEN_PLACEHOLDER` or `example.invalid`.
- Docs that mention Vault paths without exposing secret values.
- Tests that use fake values and do not resemble real credentials.

Never publish:

- API keys, OAuth tokens, passwords, HMAC secrets, SSH private keys, private certs.
- `.env` files or rendered secret files.
- Runtime task/pointer/audit JSONL ledgers.
- Raw tool stdout/stderr, raw diffs, request bodies, or checkpoint contents.

## Why this exists

The goal is not to make GitHub publishing complicated. The goal is to let an AI
agent move fast while still stopping before it leaks secrets, pushes local junk, or
uses the wrong repository.
