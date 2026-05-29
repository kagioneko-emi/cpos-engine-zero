from __future__ import annotations

import os

PROFILE_DEFAULTS = {
    "dev": {
        "CPOS_SANDBOX_MODE": "local-dev",
        "CPOS_ENFORCE_HTTPS": "false",
        "CPOS_REQUIRE_API_AUTH": "false",
        "CPOS_REQUIRE_HMAC_AUTH": "false",
        "CPOS_REQUIRE_CLIENT_CERT": "false",
        "CPOS_CLIENT_CERT_POLICY_MODE": "audit",
        "CPOS_RATE_LIMIT_ENABLED": "false",
        "CPOS_REQUIRE_FIX_APPROVAL": "true",
    },
    "audit": {
        "CPOS_SANDBOX_MODE": "permissive",
        "CPOS_ENFORCE_HTTPS": "false",
        "CPOS_REQUIRE_API_AUTH": "false",
        "CPOS_REQUIRE_HMAC_AUTH": "false",
        "CPOS_REQUIRE_CLIENT_CERT": "false",
        "CPOS_CLIENT_CERT_POLICY_MODE": "audit",
        "CPOS_RATE_LIMIT_ENABLED": "false",
        "CPOS_REQUIRE_FIX_APPROVAL": "true",
    },
    "hardened": {
        "CPOS_SANDBOX_MODE": "strict",
        "CPOS_ENFORCE_HTTPS": "true",
        "CPOS_REQUIRE_API_AUTH": "true",
        "CPOS_REQUIRE_HMAC_AUTH": "true",
        "CPOS_REQUIRE_CLIENT_CERT": "true",
        "CPOS_CLIENT_CERT_POLICY_MODE": "enforce",
        "CPOS_RATE_LIMIT_ENABLED": "true",
        "CPOS_RATE_LIMIT_REQUESTS": "60",
        "CPOS_MUTATION_RATE_LIMIT_REQUESTS": "10",
        "CPOS_RATE_LIMIT_WINDOW_SECONDS": "60",
        "CPOS_REQUIRE_FIX_APPROVAL": "true",
    },
}

SAFE_PROFILE_KEYS = tuple(sorted({key for values in PROFILE_DEFAULTS.values() for key in values}))


def selected_security_profile(environ=None) -> str | None:
    environ = os.environ if environ is None else environ
    profile = environ.get("CPOS_SECURITY_PROFILE", "").strip().lower()
    return profile if profile in PROFILE_DEFAULTS else None


def apply_security_profile_defaults(environ=None) -> dict[str, str]:
    """Apply profile defaults without overwriting explicit environment values."""
    environ = os.environ if environ is None else environ
    profile = selected_security_profile(environ)
    if profile is None:
        return {}
    applied = {}
    for key, value in PROFILE_DEFAULTS[profile].items():
        if key not in environ:
            environ[key] = value
            applied[key] = value
    return applied


def effective_security_profile(environ=None) -> dict[str, object]:
    environ = os.environ if environ is None else environ
    profile = selected_security_profile(environ) or "custom"
    values = {key: environ.get(key) for key in SAFE_PROFILE_KEYS if environ.get(key) is not None}
    defaults = PROFILE_DEFAULTS.get(profile, {})
    overrides = {
        key: values[key]
        for key in values
        if key in defaults and values[key] != defaults[key]
    }
    return {
        "profile": profile,
        "known_profiles": sorted(PROFILE_DEFAULTS.keys()),
        "values": values,
        "overrides": overrides,
    }
