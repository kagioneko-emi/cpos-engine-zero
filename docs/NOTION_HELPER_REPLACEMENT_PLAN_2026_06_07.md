# Notion Helper Replacement Plan

Date: 2026-06-07

## Purpose

Replace old local Notion helper scripts with the Vault-backed helper path in
`cpos.notion_vault_client`.

This is a plan only. No old helper script was edited, deleted, renamed, or
executed as part of this plan.

## Current safe replacement

Use the CPOS helper:

```bash
PYTHONPATH=. .venv/bin/python -m cpos.notion_vault_client page \
  --source docs/NOTION_RESUME_PIPELINE_SUMMARY_2026_06_07.md \
  --title "Cognitive Agent OS / CPOS Resume Pipeline まとめ" \
  --json
```

Default mode is dry-run. Real Notion creation requires explicit `--execute` and
reads credentials from Vault `secret/notion`.

## Files to replace or retire

The following old local helper scripts should not be reused as-is. They should be
migrated, archived, or removed only after explicit user confirmation.

| Local file | Observed purpose | Replacement approach |
|---|---|---|
| `/home/mayutama/sync_notion_manual.py` | Manual CPOS/operation page creation | Convert source content to Markdown, use `cpos.notion_vault_client page --source ... --execute` only after confirmation |
| `/home/mayutama/upload_zenn_to_notion.py` | Upload a Zenn draft to Notion | Replace with Markdown source path + Vault-backed helper |
| `/home/mayutama/shii_chan_diary_notion.py` | Generate/push diary-like content | Keep private; migrate only after privacy review; avoid raw diary/private content by default |
| `/home/mayutama/push_art_notion.py` | Push art/diary-like Notion content | Keep private; migrate only after privacy review; avoid embedded credentials |
| `/home/mayutama/notion_sync.py` | Generic page creation | Replace with `cpos.notion_vault_client` or a tiny wrapper around it |
| `/home/mayutama/chronicle_to_notion.py` | Push chronicle-style content | Keep private; migrate only after privacy review; no raw private logs by default |
| `/home/mayutama/workspace/neurostate-engine/experiments/summarize_to_notion.py` | Experiment summary to Notion | Review before reuse; if kept, switch to shared Vault-backed helper |
| `/home/mayutama/workspace/blog_pipeline/notion_client_module.py` | Blog pipeline Notion client | Review before reuse; centralize Vault access and never print secrets |

## Migration phases

### Phase 0 — Freeze unsafe helpers

- Do not run old scripts as-is.
- Do not copy credential values from old scripts.
- Do not commit old helper contents into public repos.

### Phase 1 — Rotate credential

- Revoke/rotate the exposed Notion credential in Notion.
- Update Vault `secret/notion` with the new fields.
- Confirm no old process depends on the revoked token.

This requires explicit user action/confirmation and is not performed by this doc.

### Phase 2 — Wrapper migration

For each old helper that is still useful:

1. Extract non-secret content generation into Markdown.
2. Call `cpos.notion_vault_client page` for dry-run.
3. Require explicit confirmation before `--execute`.
4. Do not print Authorization headers, token values, database IDs, raw API request bodies, or private raw content.

### Phase 3 — Archive or remove old helpers

Only after confirmation:

- archive old helpers with secrets removed, or
- remove them if no longer needed.

Do not delete or overwrite them without explicit user confirmation.

## Safety invariants

- Vault-only credential access.
- No hardcoded Notion tokens or database IDs.
- No secret values in code, docs, logs, `.env`, crontab, or shell output.
- Dry-run by default.
- `--execute` requires explicit human confirmation.
- Private diary/chronicle/neurostate content requires privacy review before uploading.

## Current status

- Replacement helper exists: `cpos.notion_vault_client`.
- Replacement helper docs exist: `docs/VAULT_BACKED_NOTION_HELPER.md`.
- Old helper scripts are untouched.
- Credential revoke/rotate remains recommended but not performed.
