# CPOS Engine-Zero Hardened Deployment Template

This bundle is documentation/template only. It does **not** install or modify
systemd, nginx, firewall, users, or secret files.

Security intent:

- keep CPOS flexible through `CPOS_SECURITY_PROFILE`, but fail closed in production
- terminate HTTPS/mTLS at a trusted reverse proxy
- pass only sanitized client certificate fingerprint headers to CPOS
- use Vault/secret volumes for every secret
- run `cpos.preflight` before starting the service

## Required secret material

Do not commit real values. Store and render these from Vault or your platform
secret manager at runtime:

| Runtime path | Purpose |
| --- | --- |
| `/run/secrets/cpos_hmac_keys.json` | Non-secret key registry pointing to secret files |
| `/run/secrets/cpos_hmac_2026_05` | HMAC shared secret for active key |
| `/run/secrets/cpos_client_fingerprints.txt` | Allowed client certificate SHA-256 fingerprints |
| `/run/secrets/cpos_storage.key` | Optional Fernet key for encrypted pointer store |

Vault reminder:

```bash
export VAULT_ADDR=https://127.0.0.1:8200
export VAULT_CACERT=/etc/vault.d/tls/vault-cert.pem
```

## Suggested startup flow

1. Render runtime secret files from Vault into `/run/secrets/...` with restricted permissions.
2. Run preflight:

   ```bash
   cd /home/mayutama/cpos_defensive_agent
   .venv/bin/python -m cpos.preflight --profile hardened
   ```

3. Start CPOS behind a trusted reverse proxy.
4. Verify:

   ```bash
   curl https://<host>/security-profile
   ```

## Files in this bundle

- `cpos-engine-zero.service.example`: systemd unit template, not installed
- `nginx-mtls.conf.example`: reverse proxy/mTLS example
- `hardened.env.example`: non-secret env template
- `cpos-hmac-keys.json.example`: key registry shape with placeholder secret paths
- `cpos-client-fingerprints.txt.example`: fingerprint allowlist shape

## Operational notes

- Keep `CPOS_SECURITY_PROFILE=hardened` for production.
- Prefer HMAC key registry rotation over single secret mode.
- Use `CPOS_CLIENT_CERT_POLICY_MODE=audit` briefly during rollout, then switch to `enforce`.
- Use proxy/LB or Redis/Valkey for distributed rate limiting in multi-instance deployments.
- Never put tokens, keys, or real certificate fingerprints in this repo.
