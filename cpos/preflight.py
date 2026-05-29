from __future__ import annotations

import argparse
import json
import os
import subprocess
import importlib.util
from typing import Any

from .security_profile import apply_security_profile_defaults, effective_security_profile
from .security_validation import validate_security_posture
from .key_registry import HMACKeyRegistry


def docker_available() -> bool:
    try:
        subprocess.run(["docker", "info"], capture_output=True, check=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def validate_key_registry(path: str | None) -> dict[str, Any]:
    if not path:
        return {"ok": True, "enabled": False, "keys": [], "failures": []}
    registry = HMACKeyRegistry(path)
    records = registry.load()
    failures = []
    for key_id, record in records.items():
        usable, reason = record.is_usable()
        secret = record.load_secret()
        if not usable:
            failures.append({"key_id": key_id, "error": reason})
        if not secret:
            failures.append({"key_id": key_id, "error": "secret_unreadable_or_empty"})
    if not records:
        failures.append({"key_id": None, "error": "no_keys_loaded"})
    return {
        "ok": not failures,
        "enabled": True,
        "keys": sorted(records.keys()),
        "failures": failures,
    }



def validate_rate_limit_backend(environ) -> dict[str, Any]:
    backend = str(environ.get("CPOS_RATE_LIMIT_BACKEND", "memory")).lower()
    enabled = str(environ.get("CPOS_RATE_LIMIT_ENABLED", "false")).lower() in {"1", "true", "yes"}
    failures = []
    if not enabled:
        return {"ok": True, "enabled": False, "backend": backend, "failures": []}
    if backend not in {"memory", "file", "redis"}:
        failures.append({"name": "rate_limit_backend", "error": f"unsupported_backend:{backend}"})
    if backend == "file":
        store_path = environ.get("CPOS_RATE_LIMIT_STORE_PATH")
        if not store_path:
            failures.append({"name": "rate_limit_file_store", "error": "store_path_not_configured"})
    if backend == "redis":
        url_file = environ.get("CPOS_RATE_LIMIT_REDIS_URL_FILE")
        if not url_file:
            failures.append({"name": "rate_limit_redis_url_file", "error": "redis_url_file_not_configured"})
        else:
            try:
                url = open(url_file, encoding="utf-8").read().strip()
            except OSError:
                url = ""
            if not url:
                failures.append({"name": "rate_limit_redis_url_file", "error": "redis_url_file_unreadable_or_empty"})
        if importlib.util.find_spec("redis") is None:
            failures.append({"name": "rate_limit_redis_dependency", "error": "redis_python_package_missing"})
    return {"ok": not failures, "enabled": enabled, "backend": backend, "failures": failures}

def run_preflight(*, profile: str | None = None, include_docker: bool = True, environ=None) -> dict[str, Any]:
    environ = os.environ.copy() if environ is None else dict(environ)
    if profile:
        environ["CPOS_SECURITY_PROFILE"] = profile
    apply_security_profile_defaults(environ)
    docker_ok = docker_available() if include_docker else None
    validation = validate_security_posture(environ, docker_available=docker_ok)
    key_registry = validate_key_registry(environ.get("CPOS_API_HMAC_KEY_REGISTRY_FILE"))
    rate_limit_backend = validate_rate_limit_backend(environ)
    ok = validation["ok"] and key_registry["ok"] and rate_limit_backend["ok"]
    return {
        "ok": ok,
        "security_profile": effective_security_profile(environ),
        "validation": validation,
        "key_registry": key_registry,
        "rate_limit_backend": rate_limit_backend,
        "docker_available": docker_ok,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CPOS deployment preflight checks.")
    parser.add_argument("--profile", choices=["dev", "audit", "hardened"], help="Apply profile defaults for this preflight run.")
    parser.add_argument("--skip-docker", action="store_true", help="Skip docker availability check.")
    parser.add_argument("--json", action="store_true")
    return parser


def print_text(result: dict[str, Any]) -> None:
    status = "OK" if result["ok"] else "CHECK"
    profile = result["security_profile"]["profile"]
    print(f"CPOS preflight: {status} profile={profile}")
    failures = result["validation"].get("failures", []) + result["key_registry"].get("failures", []) + result.get("rate_limit_backend", {}).get("failures", [])
    if not failures:
        print("No blocking validation failures detected.")
        return
    for failure in failures:
        name = failure.get("name") or failure.get("key_id") or "key_registry"
        message = failure.get("message") or failure.get("error") or "unknown"
        severity = failure.get("severity", "error")
        print(f"- [{severity}] {name}: {message}")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = run_preflight(profile=args.profile, include_docker=not args.skip_docker)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_text(result)
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
