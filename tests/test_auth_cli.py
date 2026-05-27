import json
import subprocess
import sys

from cpos.auth_cli import sign_request, signature_message


def test_sign_request_is_deterministic_for_fixed_inputs():
    headers = sign_request(
        method="GET",
        path="/tasks",
        query_string="limit=1",
        body=b"",
        timestamp=123,
        nonce="abc",
        secret="secret",
    )

    assert headers["X-CPOS-Timestamp"] == "123"
    assert headers["X-CPOS-Nonce"] == "abc"
    assert len(headers["X-CPOS-Signature"]) == 64
    assert signature_message("GET", "/tasks", "limit=1", b"", 123, "abc").startswith("GET\n/tasks\nlimit=1")


def test_auth_cli_signs_with_secret_file_without_printing_secret(tmp_path):
    secret_file = tmp_path / "secret"
    secret_file.write_text("cli-secret\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cpos.auth_cli",
            "sign",
            "GET",
            "/tasks?limit=1",
            "--secret-file",
            str(secret_file),
            "--nonce",
            "nonce-cli",
            "--timestamp",
            "123",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["headers"]["X-CPOS-Nonce"] == "nonce-cli"
    assert payload["headers"]["X-CPOS-Timestamp"] == "123"
    assert "cli-secret" not in result.stdout


def test_auth_cli_signs_with_registry_key_id(tmp_path):
    secret_file = tmp_path / "secret"
    registry_file = tmp_path / "registry.json"
    secret_file.write_text("registry-secret\n", encoding="utf-8")
    registry_file.write_text(
        json.dumps({"keys": {"active": {"secret_file": str(secret_file), "status": "active", "scopes": ["read:tasks"]}}}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cpos.auth_cli",
            "sign",
            "GET",
            "/tasks",
            "--registry-file",
            str(registry_file),
            "--key-id",
            "active",
            "--nonce",
            "nonce-registry",
            "--timestamp",
            "123",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["headers"]["X-CPOS-Key-Id"] == "active"
    assert "registry-secret" not in result.stdout
