# CPOS Engine-Zero v0.1.2 Final Release Runbook

Date: 2026-06-08

## Status

Runbook only. This document does not authorize a tag, GitHub Release, Zenn
publication, Notion publication, deployment, credential rotation, or real
tape-memory write.

## Purpose

Provide the exact release-safe order for a possible future `v0.1.2` final
release.

The goal is to avoid momentum-based release mistakes after the `fast resume
without raw logs` work.

## Release theme

Candidate theme:

> fast resume without raw logs

Public framing should remain:

> Cognitive Agent OS / safety-first agent runtime / safety kernel for assisted autonomy.

Do not claim AGI completion.

## Hard stop conditions

Stop before tag/release if any condition is true:

- working tree is dirty
- local branch is not the intended release branch
- remote is not `https://github.com/kagioneko/cpos-engine-zero.git`
- tests fail
- `prepublish_check` fails
- `release_check` fails
- secret scan count is non-zero
- release notes or GitHub draft still contain placeholder text
- public wording implies AGI completion
- any credential, token, SSH key, `.env`, cert, runtime ledger, cache, or local
  artifact is tracked
- it is late-night and Neko-san has not reconfirmed
- explicit human confirmation for tag/release is missing

## Pre-release verification order

Run from `/home/mayutama/cpos_defensive_agent`:

```bash
git status --short --branch

git remote -v

PYTHONPATH=. .venv/bin/python -m pytest tests -q

PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json

PYTHONPATH=. .venv/bin/python -m cpos.release_check --json
```

Expected baseline at the time this runbook was created:

```text
pytest tests -q -> 429 passed
prepublish_check -> ok=true, secret_scan count=0
```

Do not reuse this baseline for release. Re-run the commands immediately before
any actual tag/release.

## Manual review checklist

Review these files before final release:

- `RELEASE_NOTES_v0.1.2.md`
- `GITHUB_RELEASE_DRAFT_v0.1.2.md`
- `docs/V0_1_2_READINESS_REVIEW.md`
- `docs/V0_1_2_RESUME_PIPELINE_SUMMARY.md`
- `docs/TAPE_MEMORY_REAL_WRITE_GATE_DESIGN.md`
- `docs/ZENN_COGNITIVE_AGENT_OS_PUBLISH_CHECKLIST.md`
- `docs/NOTION_CREDENTIAL_ROTATE_RUNBOOK.md`

Confirm:

- all release notes are draft-safe or final-safe
- no AGI-completion claim exists
- no real tape-memory writes are described as enabled
- mock writer is clearly test-only
- Notion/Zenn helper execute paths require explicit confirmation
- credential rotation note is visible

## Human confirmation gate

Before creating a tag or GitHub Release, require an explicit release phrase such
as:

```text
RELEASE CPOS v0.1.2 FINAL
```

Shorthand such as `ぷす`, `ok`, or `go` must not authorize tag/release creation.
Those shorthand approvals may be acceptable for routine Git push in the current
workflow, but not for final release operations.

## Tag and release steps

Only after all checks pass and the explicit release phrase is provided:

```bash
git status --short --branch

git tag -a v0.1.2 -m "CPOS Engine-Zero v0.1.2"

git push origin v0.1.2
```

Then create the GitHub Release from `GITHUB_RELEASE_DRAFT_v0.1.2.md`.

Recommended GitHub CLI shape, if used:

```bash
gh release create v0.1.2 \
  --title "CPOS Engine-Zero v0.1.2" \
  --notes-file GITHUB_RELEASE_DRAFT_v0.1.2.md
```

Do not run these commands from this runbook without explicit confirmation.

## Post-release tasks

After release, record:

- tag object / commit hash
- GitHub Release URL
- final validation command outputs, summarized without secrets
- whether Zenn stayed draft or was published separately
- whether Notion summary was created separately
- whether credentials were rotated separately

Suggested follow-up docs:

- `docs/POST_RELEASE_NOTION_SUMMARY_v0.1.2.md`
- handoff entry in `NEXT_HANDOFF.md`

## Out of scope

This runbook does not authorize:

- Zenn publication
- Notion publication
- real tape-memory write
- credential rotation
- deployment
- destructive cleanup
- port opening
- systemd changes
- `authorized_keys` changes
