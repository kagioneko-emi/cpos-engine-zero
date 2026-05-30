# GitHub Publish Safety Spec

Reusable guardrail for AI CLI / agent workflows before publishing code to GitHub.

## Goal

Enforce two rules before staging, committing, or pushing:

1. Do not include things that are unnecessary for the repository.
2. Do not include things that must never be published.

This spec is intentionally tool-agnostic so it can be used by Codex skills, MCP
servers, CI jobs, local CLIs, or other AI CLI runtimes.

## Source policy

This policy is generalized from the VPS-wide AI CLI rules and existing local skill
patterns:

- `/home/mayutama/AGENTS.md` and `/home/mayutama/AI_RULES.md`: secrets in Vault,
  no credentials in code/`.env`/crontab/GitHub, no `authorized_keys` changes, and
  destructive operations require confirmation.
- `neko-agent` Guardian check: confirm output is safe to publish and does not
  contain core private logic or secrets.
- `claude-code-security` skill: check `.env`, local settings, git history, MCP
  configuration, and package/publication contents before exposing a project.

Generalized rules:

- Secrets must live in Vault or secret files, never in source code, `.env`, crontab,
  comments, logs, dashboards, or GitHub.
- API keys, passwords, OAuth tokens, SSH keys, and private certificates are never
  staged or printed.
- Runtime artifacts, caches, local virtualenvs, and generated local state are not
  repository source.
- Destructive remediation is out of scope for this guard. It reports problems; it
  does not delete files, rewrite history, reset branches, or edit `authorized_keys`.

## Publish boundary

### Never publish

- API keys, bearer tokens, OAuth tokens, HMAC secrets, passwords, SSH private keys,
  private certificates, and secret-derived values.
- `.env` files or rendered secret files.
- crontab-inlined secrets or comments containing secret values.
- `authorized_keys` changes.
- Raw stdout/stderr from tools or sandboxes.
- Raw diff text in persistent ledgers.
- Request bodies, webhook payloads, checkpoint contents, raw handoff bodies, or
  proposed code blobs generated during review.

### Usually do not publish

- `.venv/`, `venv/`, `env/`
- `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`
- `*.pyc`, `*.pyo`, coverage output, build artifacts
- Runtime `*.jsonl` ledgers and local state files
- Local certs, demo workspaces, generated local reports/screenshots unless reviewed

### Allowed when reviewed

- `*.example`, `.sample`, or template files that contain placeholder values only.
- Documentation that references Vault paths or secret-file paths without secret values.
- Generated release docs if they contain no local secrets, raw outputs, or runtime data.

## Required pre-publish checks

Run these before staging or pushing:

1. Confirm correct repository/remote.
2. Review `git status --short` line by line.
3. Verify tracked bad artifacts are absent.
4. Run secret scan.
5. Run tests or project-specific validation.
6. Confirm no raw high-risk data is persisted in docs, tests, JSONL ledgers, reports,
   or dashboards.

## Generic CLI contract

A guard implementation should be non-destructive and return:

```json
{
  "ok": true,
  "repo": ".",
  "remote_url": "https://github.com/example/project.git",
  "git_status_lines": [],
  "tracked_bad_artifacts": [],
  "untracked_risky_files": [],
  "failures": []
}
```

Failure examples:

- `unexpected_remote`
- `working_tree_not_clean`
- `tracked_bad_artifacts`
- `untracked_risky_files`
- `required_file_missing`

## Agent behavior

When this guard fails, an AI agent should:

- Stop before staging/committing/pushing.
- Report the exact paths/reasons.
- Do not auto-delete or rewrite files without user approval.
- Suggest `.gitignore`, Vault migration, or manual review as appropriate.
- If the user asks to install this as an actual Codex skill under `~/.codex/skills/`,
  ask for explicit confirmation first. Repository-local docs/CLIs are safe to add
  through the normal review flow.

## Skill / MCP adapter contract

A future skill or MCP wrapper should only call the non-destructive guard and return
metadata. It must not stage, commit, push, delete, rewrite history, open ports, or
read secret values. Recommended wrapper behavior:

1. Run the guard.
2. Run the project secret scanner if available.
3. Return `ok`, failures, and exact paths.
4. Require a separate human approval step before any Git mutation.
