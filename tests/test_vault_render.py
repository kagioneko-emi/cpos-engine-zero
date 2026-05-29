import json
import os
import stat

import pytest

from cpos.vault_render import render_manifest, safe_output_path, VaultRenderError


def test_vault_render_dry_run_does_not_create_secret_files(tmp_path):
    manifest = {
        "secret_dir": str(tmp_path / "secrets"),
        "secrets": [
            {"filename": "cpos_hmac", "vault_path": "secret/cpos/hmac", "field": "active"}
        ],
    }

    result = render_manifest(manifest, dry_run=True)

    assert result["ok"] is True
    assert result["rendered"][0]["dry_run"] is True
    assert not (tmp_path / "secrets" / "cpos_hmac").exists()
    assert stat.S_IMODE((tmp_path / "secrets").stat().st_mode) == 0o700


def test_vault_render_writes_secret_with_0600_without_printing_value(tmp_path, monkeypatch):
    manifest = {
        "secret_dir": str(tmp_path / "secrets"),
        "secrets": [
            {"filename": "cpos_hmac", "vault_path": "secret/cpos/hmac", "field": "active"}
        ],
    }
    monkeypatch.setattr("cpos.vault_render.vault_get_field", lambda path, field: "super-secret")

    result = render_manifest(manifest, dry_run=False)

    output = tmp_path / "secrets" / "cpos_hmac"
    assert output.read_text(encoding="utf-8") == "super-secret\n"
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert "super-secret" not in json.dumps(result)


def test_vault_render_rejects_path_escape(tmp_path):
    secret_dir = tmp_path / "secrets"
    secret_dir.mkdir()

    with pytest.raises(VaultRenderError):
        safe_output_path(secret_dir, "../escape")
