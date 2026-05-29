from cpos.security_profile import apply_security_profile_defaults, effective_security_profile, selected_security_profile


def test_dev_profile_sets_freedom_defaults_without_overwriting_explicit_values():
    env = {"CPOS_SECURITY_PROFILE": "dev", "CPOS_SANDBOX_MODE": "strict"}

    applied = apply_security_profile_defaults(env)
    summary = effective_security_profile(env)

    assert selected_security_profile(env) == "dev"
    assert env["CPOS_SANDBOX_MODE"] == "strict"
    assert applied["CPOS_REQUIRE_API_AUTH"] == "false"
    assert summary["profile"] == "dev"
    assert summary["overrides"]["CPOS_SANDBOX_MODE"] == "strict"


def test_hardened_profile_fails_closed_defaults():
    env = {"CPOS_SECURITY_PROFILE": "hardened"}

    apply_security_profile_defaults(env)

    assert env["CPOS_SANDBOX_MODE"] == "strict"
    assert env["CPOS_ENFORCE_HTTPS"] == "true"
    assert env["CPOS_REQUIRE_API_AUTH"] == "true"
    assert env["CPOS_REQUIRE_HMAC_AUTH"] == "true"
    assert env["CPOS_REQUIRE_CLIENT_CERT"] == "true"
    assert env["CPOS_CLIENT_CERT_POLICY_MODE"] == "enforce"
    assert env["CPOS_RATE_LIMIT_ENABLED"] == "true"


def test_audit_profile_prefers_observation_without_blocking_defaults():
    env = {"CPOS_SECURITY_PROFILE": "audit"}

    apply_security_profile_defaults(env)

    assert env["CPOS_SANDBOX_MODE"] == "permissive"
    assert env["CPOS_CLIENT_CERT_POLICY_MODE"] == "audit"
    assert env["CPOS_REQUIRE_API_AUTH"] == "false"
    assert env["CPOS_RATE_LIMIT_ENABLED"] == "false"


def test_unknown_profile_is_custom_and_does_not_apply_defaults():
    env = {"CPOS_SECURITY_PROFILE": "weird"}

    applied = apply_security_profile_defaults(env)
    summary = effective_security_profile(env)

    assert applied == {}
    assert summary["profile"] == "custom"
