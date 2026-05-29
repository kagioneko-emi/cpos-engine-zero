#!/usr/bin/env bash
set -euo pipefail

# Example only. Review before use.
# Renders CPOS runtime secret files from Vault without printing secret values.
# Requirements:
#   VAULT_ADDR=https://127.0.0.1:8200
#   VAULT_CACERT=/etc/vault.d/tls/vault-cert.pem
#   vault CLI authenticated with a token from a secure channel

: "${VAULT_ADDR:?VAULT_ADDR is required}"
: "${VAULT_CACERT:?VAULT_CACERT is required}"

SECRET_DIR="${CPOS_SECRET_DIR:-/run/secrets}"
install -d -m 0700 "$SECRET_DIR"

write_secret_file() {
  local vault_path="$1"
  local field="$2"
  local output_path="$3"
  local tmp_path
  tmp_path="$(mktemp "${output_path}.tmp.XXXXXX")"
  chmod 0600 "$tmp_path"
  vault kv get -field="$field" "$vault_path" > "$tmp_path"
  mv "$tmp_path" "$output_path"
  chmod 0600 "$output_path"
  echo "rendered: $output_path"
}

# Adjust Vault paths/fields to your deployment. Do not echo secret values.
write_secret_file secret/cpos/hmac/2026-05 active "$SECRET_DIR/cpos_hmac_2026_05"
write_secret_file secret/cpos/client-certs fingerprints "$SECRET_DIR/cpos_client_fingerprints.txt"
write_secret_file secret/cpos/storage fernet_key "$SECRET_DIR/cpos_storage.key"

# The key registry is usually non-secret but references secret file paths.
# If you store it in Vault, render it too:
# write_secret_file secret/cpos/hmac-registry json "$SECRET_DIR/cpos_hmac_keys.json"

python3 -m cpos.preflight --profile hardened
