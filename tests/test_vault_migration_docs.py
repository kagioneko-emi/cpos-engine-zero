from pathlib import Path


def test_vault_migration_guide_exists_and_is_non_destructive():
    text = Path("deploy/hardened/VAULT_MIGRATION_GUIDE.md").read_text(encoding="utf-8")
    assert "documentation only" in text
    assert "does not move, delete, overwrite, or upload" in text
    assert "VAULT_ADDR=https://127.0.0.1:8200" in text
    assert "python3 -m cpos.secret_scan" in text
    assert "python3 -m cpos.vault_render" in text
    assert "Do **not** use `rm -rf` without explicit approval." in text
    assert "Do **not** modify `authorized_keys`." in text


def test_secret_artifact_inventory_template_has_no_secret_values():
    text = Path("deploy/hardened/SECRET_ARTIFACT_INVENTORY.md").read_text(encoding="utf-8")
    assert "Secret Artifact Inventory Template" in text
    assert "Do not paste secret values" in text
    assert "certs/key.pem" in text
    assert "review" in text
    assert "-----BEGIN " + "PRIVATE KEY-----" not in text
    assert "sk" + "-" not in text
