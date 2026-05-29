# Secret Artifact Inventory Template

Use this template to track migration. Do not paste secret values.

| Path | Type | Owner | Vault path | Field | Runtime destination | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `certs/key.pem` | TLS/private key candidate | TBD | `secret/cpos/tls` | `private_key` | proxy secret mount | review | Do not delete without approval |
| `/run/secrets/cpos_hmac_2026_05` | HMAC runtime secret | CPOS | `secret/cpos/hmac/2026-05` | `active` | `/run/secrets/cpos_hmac_2026_05` | planned | Runtime only |
| `/run/secrets/cpos_client_fingerprints.txt` | client cert fingerprints | CPOS | `secret/cpos/client-certs` | `fingerprints` | `/run/secrets/cpos_client_fingerprints.txt` | planned | Runtime only |

Statuses:

- `review`
- `stored_in_vault`
- `render_verified`
- `preflight_passed`
- `cleanup_approved`
- `removed`
