# Vault-backed Notion Helper

`cpos.notion_vault_client` is the safe replacement path for old local Notion
helper scripts that contained hardcoded credential patterns.

## Dry-run first

By default, the helper does not contact Notion and does not read Vault:

```bash
PYTHONPATH=. .venv/bin/python -m cpos.notion_vault_client page \
  --source docs/NOTION_RESUME_PIPELINE_SUMMARY_2026_06_07.md \
  --title "Cognitive Agent OS / CPOS Resume Pipeline まとめ" \
  --json
```

Dry-run output reports counts and Vault source placeholders only. It does not
print tokens or database IDs.

## Real page creation

Real Notion creation requires explicit `--execute`:

```bash
PYTHONPATH=. .venv/bin/python -m cpos.notion_vault_client page \
  --source docs/NOTION_RESUME_PIPELINE_SUMMARY_2026_06_07.md \
  --title "Cognitive Agent OS / CPOS Resume Pipeline まとめ" \
  --execute \
  --json
```

When `--execute` is used, credentials are read from Vault:

- `secret/notion(api_key)`
- `secret/notion(memo_db_id)`

Required Vault environment:

- `VAULT_ADDR=https://127.0.0.1:8200`
- `VAULT_CACERT=/etc/vault.d/tls/vault-cert.pem`

## Safety rules

- Do not hardcode Notion tokens or database IDs.
- Do not print Authorization headers.
- Do not store tokens, DB IDs, request headers, or raw API responses in repo.
- Prefer dry-run output for review.
- Use `--execute` only after explicit human confirmation.
