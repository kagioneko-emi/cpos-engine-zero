from __future__ import annotations

from pathlib import Path
from typing import Any
import os

from .security_profile import effective_security_profile, selected_security_profile


def _exists(path: str | None) -> bool:
    return bool(path) and Path(path).exists()


def validate_security_posture(environ=None, *, docker_available: bool | None = None) -> dict[str, Any]:
    environ = os.environ if environ is None else environ
    profile = selected_security_profile(environ) or "custom"
    checks = []

    def add(name: str, ok: bool, severity: str, message: str):
        checks.append({"name": name, "ok": bool(ok), "severity": severity, "message": message})

    if profile == "hardened":
        add("https_enforced", environ.get("CPOS_ENFORCE_HTTPS", "").lower() in {"1", "true", "yes"}, "critical", "CPOS_ENFORCE_HTTPS should be true in hardened profile.")
        add("api_auth_required", environ.get("CPOS_REQUIRE_API_AUTH", "").lower() in {"1", "true", "yes"}, "critical", "CPOS_REQUIRE_API_AUTH should be true in hardened profile.")
        add("hmac_auth_required", environ.get("CPOS_REQUIRE_HMAC_AUTH", "").lower() in {"1", "true", "yes"}, "critical", "CPOS_REQUIRE_HMAC_AUTH should be true in hardened profile.")
        add("hmac_secret_or_registry_configured", _exists(environ.get("CPOS_API_HMAC_KEY_REGISTRY_FILE")) or _exists(environ.get("CPOS_API_HMAC_SECRET_FILE")), "critical", "HMAC registry or secret file must exist.")
        add("client_cert_required", environ.get("CPOS_REQUIRE_CLIENT_CERT", "").lower() in {"1", "true", "yes"}, "high", "Client certificate fingerprint gate should be enabled.")
        add("client_cert_fingerprints_configured", _exists(environ.get("CPOS_CLIENT_CERT_FINGERPRINTS_FILE")), "high", "Client certificate fingerprint file must exist when client-cert gate is enabled.")
        add("sandbox_strict", environ.get("CPOS_SANDBOX_MODE") == "strict", "critical", "Sandbox mode should be strict in hardened profile.")
        if docker_available is not None:
            add("docker_available", docker_available, "critical", "Docker must be available for strict sandbox execution.")
        rate_limit_enabled = environ.get("CPOS_RATE_LIMIT_ENABLED", "").lower() in {"1", "true", "yes"}
        add("rate_limit_enabled", rate_limit_enabled, "medium", "Rate limiting should be enabled.")
        backend = environ.get("CPOS_RATE_LIMIT_BACKEND", "memory").lower()
        add("rate_limit_backend_supported", backend in {"memory", "file", "redis"}, "medium", "CPOS_RATE_LIMIT_BACKEND should be memory, file, or redis.")
        if rate_limit_enabled and backend == "redis":
            add("rate_limit_redis_url_file_configured", _exists(environ.get("CPOS_RATE_LIMIT_REDIS_URL_FILE")), "high", "Redis/Valkey rate-limit URL file must exist and be Vault-rendered.")
    elif profile == "audit":
        add("approval_gate_enabled", environ.get("CPOS_REQUIRE_FIX_APPROVAL", "true").lower() not in {"0", "false", "no"}, "high", "Approval gate should remain enabled in audit profile.")
        add("sandbox_not_strict", environ.get("CPOS_SANDBOX_MODE") in {"permissive", "local-dev", None, ""}, "medium", "Audit profile should avoid accidental fail-closed sandbox unless explicitly overridden.")
    elif profile == "dev":
        add("approval_gate_enabled", environ.get("CPOS_REQUIRE_FIX_APPROVAL", "true").lower() not in {"0", "false", "no"}, "medium", "Approval gate should remain enabled even in dev by default.")

    failed = [check for check in checks if not check["ok"]]
    return {
        "ok": not failed,
        "profile": profile,
        "checks": checks,
        "failures": failed,
        "summary": effective_security_profile(environ),
    }
