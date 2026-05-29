import json
import subprocess
import sys

from cpos.secret_inventory import add_artifact, latest_records, mark_status
from cpos.hash_chain import verify_hash_chain


def test_secret_inventory_add_mark_and_verify_without_values(tmp_path):
    path = tmp_path / "inventory.jsonl"
    add_artifact(
        path,
        artifact_path="certs/key.pem",
        artifact_type="tls_private_key",
        vault_path="secret/cpos/tls",
        field="private_key",
        runtime_destination="proxy secret mount",
    )
    mark_status(path, artifact_path="certs/key.pem", status="stored_in_vault")

    records = latest_records(path)
    assert records["certs/key.pem"]["status"] == "stored_in_vault"
    assert verify_hash_chain(path)["ok"] is True
    raw = path.read_text(encoding="utf-8")
    assert "-----BEGIN " + "PRIVATE KEY-----" not in raw
    assert "secret/cpos/tls" in raw


def test_secret_inventory_cli_list_json(tmp_path):
    path = tmp_path / "inventory.jsonl"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "cpos.secret_inventory",
            "--inventory-path",
            str(path),
            "add",
            "certs/key.pem",
            "--type",
            "tls_private_key",
            "--vault-path",
            "secret/cpos/tls",
            "--field",
            "private_key",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        [sys.executable, "-m", "cpos.secret_inventory", "--inventory-path", str(path), "list", "--json"],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload[0]["artifact_path"] == "certs/key.pem"
    assert payload[0]["field"] == "private_key"
    assert "PRIVATE KEY-----" not in result.stdout


def test_secret_inventory_mark_unknown_fails(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cpos.secret_inventory",
            "--inventory-path",
            str(tmp_path / "inventory.jsonl"),
            "mark",
            "missing",
            "--status",
            "stored_in_vault",
            "--json",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "artifact_not_found" in result.stdout
