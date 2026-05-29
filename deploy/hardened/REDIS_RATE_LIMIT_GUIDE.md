# CPOS Redis/Valkey Rate Limit Backend Guide

Use this only when CPOS is deployed across multiple hosts or containers where the
file-backed backend is not shared.

## Secret handling

Do **not** place Redis/Valkey credentials in code, `.env`, crontab, logs, or
GitHub. Store the URL in Vault and render it to a runtime secret file.

Example Vault target:

```text
secret/cpos/redis_rate_limit url
```

Runtime env:

```bash
export CPOS_RATE_LIMIT_ENABLED=true
export CPOS_RATE_LIMIT_BACKEND=redis
export CPOS_RATE_LIMIT_REDIS_URL_FILE=/run/secrets/cpos_redis_rate_limit_url
export CPOS_RATE_LIMIT_REDIS_KEY_PREFIX=cpos:rate_limit
```

## Preflight

```bash
python3 -m cpos.preflight --profile hardened --json
```

Preflight checks that the URL file is configured and non-empty. It never prints
the URL value.

## Behavior

The Redis/Valkey backend stores only sorted-set timestamps by bucket key. It does
not store Authorization headers, request bodies, tokens, API keys, or secret
values.

If the URL file is missing, runtime fails closed with:

```text
rate_limit_redis_url_not_configured
```
