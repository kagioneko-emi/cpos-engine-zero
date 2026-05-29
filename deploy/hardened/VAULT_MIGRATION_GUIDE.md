# Vault Migration Guide for Local Secret Artifacts

This guide is documentation only. It does not move, delete, overwrite, or upload
any files. Destructive cleanup must be explicitly approved before execution.

## Goal

Move runtime secrets out of the repository/worktree and into Vault-managed
runtime secret files.

Never commit:

- API keys / OAuth tokens / bearer tokens
- SSH keys / private keys
- TLS private keys
- HMAC shared secrets
- client certificate fingerprint allowlists when considered sensitive
- `.env` files containing secrets

## Required Vault environment

```bash
export VAULT_ADDR=https://127.0.0.1:8200
export VAULT_CACERT=/etc/vault.d/tls/vault-cert.pem
```

## Recommended Vault paths

| Artifact | Vault path | Field | Runtime file |
| --- | --- | --- | --- |
| CPOS active HMAC secret | `secret/cpos/hmac/2026-05` | `active` | `/run/secrets/cpos_hmac_2026_05` |
| CPOS HMAC registry JSON | `secret/cpos/hmac-registry` | `json` | `/run/secrets/cpos_hmac_keys.json` |
| CPOS client cert fingerprints | `secret/cpos/client-certs` | `fingerprints` | `/run/secrets/cpos_client_fingerprints.txt` |
| CPOS storage Fernet key | `secret/cpos/storage` | `fernet_key` | `/run/secrets/cpos_storage.key` |
| TLS private key | `secret/cpos/tls` | `private_key` | proxy-specific secret mount |
| TLS certificate | `secret/cpos/tls` | `certificate` | proxy-specific secret mount |

Existing global paths still apply:

- Discord: `secret/discord` field `bot_token`
- Notion: `secret/notion`
- WordPress: `secret/wordpress`
- SSH Xserver: `secret/ssh/vps-to-xserver`
- SSH Windows: `secret/ssh/vps-to-windows`

## Inventory without printing values

Use the non-revealing scanner:

```bash
python3 -m cpos.secret_scan . --json
```

It reports only path/line/pattern, not matched secret values.

## Store values in Vault

Examples. Replace `<file>` locally and do not paste values into shell history.
Prefer file-based input where possible.

```bash
vault kv put secret/cpos/hmac/2026-05 active=@/secure/source/cpos_hmac_2026_05
vault kv put secret/cpos/client-certs fingerprints=@/secure/source/cpos_client_fingerprints.txt
vault kv put secret/cpos/storage fernet_key=@/secure/source/cpos_storage.key
vault kv put secret/cpos/hmac-registry json=@deploy/hardened/cpos-hmac-keys.json.example
```

For multiline PEM material, use file input:

```bash
vault kv put secret/cpos/tls private_key=@/secure/source/tls.key certificate=@/secure/source/tls.crt
```

## Render runtime files

Dry-run first:

```bash
python3 -m cpos.vault_render deploy/hardened/vault-render-manifest.example.json --dry-run
```

Then render on the deployment host:

```bash
python3 -m cpos.vault_render deploy/hardened/vault-render-manifest.example.json --json
```

Run preflight:

```bash
python3 -m cpos.preflight --profile hardened
```

## Cleanup policy

Before deleting or overwriting any local secret artifact:

1. Confirm the value is stored in Vault.
2. Confirm runtime render works.
3. Confirm preflight passes.
4. Confirm no service depends on the old file path.
5. Ask for explicit approval before deletion.

Do **not** use `rm -rf` without explicit approval.
Do **not** modify `authorized_keys`.
Do **not** push cleanup commits until `cpos.secret_scan` passes or findings are documented as intentional fixtures.

## Commit safety checklist

Before GitHub push:

```bash
python3 -m cpos.secret_scan . --exclude cpos --exclude tapes --exclude certs
python3 -m cpos.preflight --profile hardened --skip-docker --json
python3 -m pytest tests -q
```

If findings appear in generated audit/report fixtures, review whether they are
safe synthetic examples. Avoid publishing real operational secrets.
