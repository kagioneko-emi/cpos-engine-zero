# Local Notion Credential Hygiene Note

Date: 2026-06-07

## Summary

During the Resume Pipeline Notion-summary work, several old local Notion helper
scripts outside this repository were found with hardcoded credential patterns.
No credential values are recorded in this document.

The new Resume Pipeline Notion page was created using Vault-only credential
access and did not use the old helper scripts.

## Affected local files observed

These files should be treated as needing review and migration before reuse:

- `/home/mayutama/sync_notion_manual.py`
- `/home/mayutama/upload_zenn_to_notion.py`
- `/home/mayutama/shii_chan_diary_notion.py`
- `/home/mayutama/push_art_notion.py`
- `/home/mayutama/notion_sync.py`
- `/home/mayutama/chronicle_to_notion.py`

Observed pattern:

- hardcoded Notion credential/database-like values were detected by filename-scoped inspection
- the scripts did not appear to use Vault

Additional Notion-related files observed without the same hardcoded-secret pattern
in the scoped check:

- `/home/mayutama/workspace/neurostate-engine/experiments/summarize_to_notion.py`
- `/home/mayutama/workspace/blog_pipeline/notion_client_module.py`

These should still be reviewed before reuse.

## Required future policy

All future Notion tooling must:

- read Notion API tokens from Vault only
- use `VAULT_ADDR=https://127.0.0.1:8200`
- use `VAULT_CACERT=/etc/vault.d/tls/vault-cert.pem`
- retrieve from `secret/notion`
- avoid printing tokens, database IDs, or request headers
- avoid storing secrets in code, `.env`, docs, logs, shell history, or crontab

## Recommended remediation

Do not edit or delete the old helper scripts without explicit user confirmation.

Recommended next steps:

1. Revoke/rotate the exposed Notion credential in Notion.
2. Update Vault `secret/notion` with the new token/database fields.
3. Replace old helper scripts with Vault-backed versions or archive them after approval.
4. Add a small reusable Vault-backed Notion client helper that never prints secrets.
5. Re-run a local secret scan after migration.

## Current status

- No destructive action was taken.
- No credentials were printed into this document.
- No old helper script was used for the new Resume Pipeline Notion page.
- Revoke/rotate remains recommended but not yet performed.
