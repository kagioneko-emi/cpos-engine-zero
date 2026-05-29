import json
import subprocess
import sys

from cpos.secret_scan import scan_paths


def test_secret_scan_detects_private_key_without_printing_value(tmp_path):
    secret_file = tmp_path / "key.pem"
    secret_file.write_text("-----BEGIN " + "PRIVATE KEY-----\nsecret-body\n-----END PRIVATE KEY-----\n", encoding="utf-8")

    findings = scan_paths([tmp_path])

    assert len(findings) == 1
    assert findings[0]["pattern"] == "private_key_pem"
    assert "secret-body" not in json.dumps(findings)


def test_secret_scan_respects_excludes(tmp_path):
    excluded = tmp_path / "certs"
    excluded.mkdir()
    (excluded / "key.pem").write_text("-----BEGIN " + "PRIVATE KEY-----\n", encoding="utf-8")

    findings = scan_paths([tmp_path], excludes={"certs"})

    assert findings == []


def test_secret_scan_cli_json_returns_nonzero_on_findings(tmp_path):
    fake_key = "sk-" + "1234567890abcdef1234567890abcdef"
    (tmp_path / "app.py").write_text(f'token = "{fake_key}"\n', encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "cpos.secret_scan", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["findings"][0]["pattern"] == "openai_like_key"
    assert fake_key not in result.stdout
