# Notion Credential Rotate Runbook

Date: 2026-06-07

## Purpose

Provide a safe procedure for rotating Notion credentials after old local helper
scripts were found with hardcoded credential patterns.

This runbook does not rotate credentials by itself.

## Preconditions

- Neko-san explicitly approves rotation.
- Current Notion integration usage is understood.
- Vault is reachable with:
  - `VAULT_ADDR=https://127.0.0.1:8200`
  - `VAULT_CACERT=/etc/vault.d/tls/vault-cert.pem`

## Rotation steps

1. In Notion, create a new integration token or rotate the affected integration token.
2. Confirm the new integration has access to the target memo database.
3. Update Vault `secret/notion` fields:
   - `api_key`
   - `memo_db_id` if needed
   - `post_db_id` if needed
4. Do not paste the token into shell history, code, docs, `.env`, crontab, or logs.
5. Run a dry-run check:

```bash
PYTHONPATH=. .venv/bin/python -m cpos.notion_vault_client page \
  --source docs/NOTION_RESUME_PIPELINE_SUMMARY_2026_06_07.md \
  --title "Credential rotation smoke test" \
  --json
```

6. If an actual smoke test page is needed, run only after explicit confirmation:

```bash
PYTHONPATH=. .venv/bin/python -m cpos.notion_vault_client page \
  --source docs/NOTION_RESUME_PIPELINE_SUMMARY_2026_06_07.md \
  --title "Credential rotation smoke test" \
  --execute \
  --json
```

7. Revoke the old token.
8. Verify old helper scripts are not used as-is.
9. Run local secret scan after migration.

## Do not do

- Do not print the token.
- Do not commit the token.
- Do not store the token in `.env`.
- Do not update crontab with raw token values.
- Do not run old helper scripts with hardcoded credentials.

## Current status

- Rotation is recommended.
- Rotation has not been performed by this runbook.
- Old helper scripts remain untouched.
