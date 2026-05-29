from cpos.security_validation import validate_security_posture


def test_hardened_validation_reports_missing_secret_files_and_docker():
    env = {
        "CPOS_SECURITY_PROFILE": "hardened",
        "CPOS_ENFORCE_HTTPS": "true",
        "CPOS_REQUIRE_API_AUTH": "true",
        "CPOS_REQUIRE_HMAC_AUTH": "true",
        "CPOS_REQUIRE_CLIENT_CERT": "true",
        "CPOS_SANDBOX_MODE": "strict",
        "CPOS_RATE_LIMIT_ENABLED": "true",
    }

    result = validate_security_posture(env, docker_available=False)

    assert result["ok"] is False
    failure_names = {failure["name"] for failure in result["failures"]}
    assert "hmac_secret_or_registry_configured" in failure_names
    assert "client_cert_fingerprints_configured" in failure_names
    assert "docker_available" in failure_names


def test_hardened_validation_passes_with_required_files(tmp_path):
    hmac_secret = tmp_path / "hmac"
    fingerprints = tmp_path / "fingerprints"
    hmac_secret.write_text("secret\n", encoding="utf-8")
    fingerprints.write_text("aabbccdd\n", encoding="utf-8")
    env = {
        "CPOS_SECURITY_PROFILE": "hardened",
        "CPOS_ENFORCE_HTTPS": "true",
        "CPOS_REQUIRE_API_AUTH": "true",
        "CPOS_REQUIRE_HMAC_AUTH": "true",
        "CPOS_API_HMAC_SECRET_FILE": str(hmac_secret),
        "CPOS_REQUIRE_CLIENT_CERT": "true",
        "CPOS_CLIENT_CERT_FINGERPRINTS_FILE": str(fingerprints),
        "CPOS_SANDBOX_MODE": "strict",
        "CPOS_RATE_LIMIT_ENABLED": "true",
    }

    result = validate_security_posture(env, docker_available=True)

    assert result["ok"] is True
    assert result["failures"] == []


def test_dev_validation_keeps_approval_gate_warning_only_when_disabled():
    env = {"CPOS_SECURITY_PROFILE": "dev", "CPOS_REQUIRE_FIX_APPROVAL": "false"}

    result = validate_security_posture(env)

    assert result["ok"] is False
    assert result["failures"][0]["name"] == "approval_gate_enabled"


def test_hardened_validation_reports_missing_redis_rate_limit_url_file(tmp_path):
    hmac_secret = tmp_path / "hmac"
    fingerprints = tmp_path / "fingerprints"
    hmac_secret.write_text("secret\n", encoding="utf-8")
    fingerprints.write_text("aabbccdd\n", encoding="utf-8")
    env = {
        "CPOS_SECURITY_PROFILE": "hardened",
        "CPOS_ENFORCE_HTTPS": "true",
        "CPOS_REQUIRE_API_AUTH": "true",
        "CPOS_REQUIRE_HMAC_AUTH": "true",
        "CPOS_API_HMAC_SECRET_FILE": str(hmac_secret),
        "CPOS_REQUIRE_CLIENT_CERT": "true",
        "CPOS_CLIENT_CERT_FINGERPRINTS_FILE": str(fingerprints),
        "CPOS_SANDBOX_MODE": "strict",
        "CPOS_RATE_LIMIT_ENABLED": "true",
        "CPOS_RATE_LIMIT_BACKEND": "redis",
    }

    result = validate_security_posture(env, docker_available=True)

    assert result["ok"] is False
    names = {failure["name"] for failure in result["failures"]}
    assert "rate_limit_redis_url_file_configured" in names
