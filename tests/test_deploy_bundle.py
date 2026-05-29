from pathlib import Path


def test_hardened_deploy_bundle_contains_templates_without_real_secret_material():
    root = Path("deploy/hardened")
    required = [
        "README.md",
        "hardened.env.example",
        "cpos-hmac-keys.json.example",
        "cpos-client-fingerprints.txt.example",
        "cpos-engine-zero.service.example",
        "nginx-mtls.conf.example",
    ]
    for name in required:
        assert (root / name).exists(), name

    combined = "\n".join((root / name).read_text(encoding="utf-8") for name in required)
    assert "CPOS_SECURITY_PROFILE=hardened" in combined
    assert "cpos.preflight --profile hardened" in combined
    assert "ssl_verify_client on" in combined
    assert "proxy_set_header X-SSL-Client-SHA256 $ssl_client_fingerprint" in combined
    assert "Do not commit real values" in combined


def test_systemd_template_does_not_embed_secret_values():
    text = Path("deploy/hardened/cpos-engine-zero.service.example").read_text(encoding="utf-8")
    assert "EnvironmentFile=" in text
    assert "ExecStartPre=" in text
    assert "VAULT_TOKEN" not in text
    assert "bot_token" not in text
    assert "private_key" not in text
