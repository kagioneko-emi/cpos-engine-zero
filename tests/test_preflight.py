import json
import subprocess
import sys

from cpos.preflight import run_preflight, validate_key_registry


def test_preflight_hardened_reports_missing_required_files_without_docker_check():
    env = {}

    result = run_preflight(profile="hardened", include_docker=False, environ=env)

    assert result["ok"] is False
    names = {failure["name"] for failure in result["validation"]["failures"]}
    assert "hmac_secret_or_registry_configured" in names
    assert "client_cert_fingerprints_configured" in names
    assert result["docker_available"] is None


def test_preflight_hardened_passes_with_required_files_and_docker_true(tmp_path, monkeypatch):
    hmac_secret = tmp_path / "hmac"
    fingerprints = tmp_path / "fingerprints"
    hmac_secret.write_text("secret\n", encoding="utf-8")
    fingerprints.write_text("aabbccdd\n", encoding="utf-8")
    env = {
        "CPOS_API_HMAC_SECRET_FILE": str(hmac_secret),
        "CPOS_CLIENT_CERT_FINGERPRINTS_FILE": str(fingerprints),
    }
    monkeypatch.setattr("cpos.preflight.docker_available", lambda: True)

    result = run_preflight(profile="hardened", include_docker=True, environ=env)

    assert result["ok"] is True
    assert result["docker_available"] is True


def test_validate_key_registry_checks_secret_files(tmp_path):
    secret = tmp_path / "secret"
    registry = tmp_path / "registry.json"
    secret.write_text("registry-secret\n", encoding="utf-8")
    registry.write_text(
        json.dumps(
            {
                "keys": {
                    "active": {"secret_file": str(secret), "status": "active", "scopes": ["read:tasks"]},
                    "bad": {"secret_file": str(tmp_path / "missing"), "status": "active", "scopes": ["read:tasks"]},
                }
            }
        ),
        encoding="utf-8",
    )

    result = validate_key_registry(str(registry))

    assert result["ok"] is False
    assert result["enabled"] is True
    assert result["keys"] == ["active", "bad"]
    assert result["failures"][0]["key_id"] == "bad"


def test_preflight_cli_json_exits_nonzero_for_hardened_missing_files():
    result = subprocess.run(
        [sys.executable, "-m", "cpos.preflight", "--profile", "hardened", "--skip-docker", "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["security_profile"]["profile"] == "hardened"


def test_preflight_reports_redis_rate_limit_missing_url_file():
    env = {
        "CPOS_RATE_LIMIT_ENABLED": "true",
        "CPOS_RATE_LIMIT_BACKEND": "redis",
    }

    result = run_preflight(profile="dev", include_docker=False, environ=env)

    assert result["ok"] is False
    errors = {failure["error"] for failure in result["rate_limit_backend"]["failures"]}
    assert "redis_url_file_not_configured" in errors


def test_preflight_reports_redis_rate_limit_empty_url_file(tmp_path):
    url_file = tmp_path / "redis_url"
    url_file.write_text("\n", encoding="utf-8")
    env = {
        "CPOS_RATE_LIMIT_ENABLED": "true",
        "CPOS_RATE_LIMIT_BACKEND": "redis",
        "CPOS_RATE_LIMIT_REDIS_URL_FILE": str(url_file),
    }

    result = run_preflight(profile="dev", include_docker=False, environ=env)

    assert result["ok"] is False
    errors = {failure["error"] for failure in result["rate_limit_backend"]["failures"]}
    assert "redis_url_file_unreadable_or_empty" in errors
