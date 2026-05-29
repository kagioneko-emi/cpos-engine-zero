import json
import subprocess
import sys
from pathlib import Path

from cpos.handoff_export import build_handoff_bundle
from cpos.handoff_receiver import (
    import_handoff_bundle,
    sign_bundle,
    validate_handoff_bundle,
    verify_signed_bundle,
)
from cpos.pointer_os import PointerManager


def test_sign_verify_and_tamper_detection(tmp_path):
    bundle = build_handoff_bundle(project_root=tmp_path, environ={"CPOS_SECURITY_PROFILE": "dev"})
    signed = sign_bundle(bundle, secret="test-secret", key_id="handoff-v1", signer_agent="AgentA")

    verified = verify_signed_bundle(signed, secret="test-secret", expected_key_id="handoff-v1")
    assert verified["ok"] is True
    assert verified["signer_agent"] == "AgentA"
    assert validate_handoff_bundle(signed, require_signature=True, verification=verified)["ok"] is True

    tampered = json.loads(json.dumps(signed))
    tampered["pointers"]["count"] = 999
    assert verify_signed_bundle(tampered, secret="test-secret", expected_key_id="handoff-v1")["ok"] is False


def test_import_requires_apply_and_stores_summary_only(tmp_path):
    (tmp_path / "cpos").mkdir(exist_ok=True)
    bundle = build_handoff_bundle(project_root=tmp_path, environ={"CPOS_SECURITY_PROFILE": "dev"})
    signed = sign_bundle(bundle, secret="test-secret", key_id="handoff-v1", signer_agent="AgentA")
    verification = verify_signed_bundle(signed, secret="test-secret", expected_key_id="handoff-v1")

    dry = import_handoff_bundle(
        signed,
        pointer_path=tmp_path / "cpos" / "pointers.jsonl",
        pointer_audit_path=tmp_path / "cpos" / "audit_log.jsonl",
        require_signature=True,
        verification=verification,
        apply=False,
        source_file="handoff.json",
    )
    assert dry["ok"] is True
    assert dry["applied"] is False
    assert not (tmp_path / "cpos" / "pointers.jsonl").exists()

    applied = import_handoff_bundle(
        signed,
        pointer_path=tmp_path / "cpos" / "pointers.jsonl",
        pointer_audit_path=tmp_path / "cpos" / "audit_log.jsonl",
        require_signature=True,
        verification=verification,
        apply=True,
        source_file="handoff.json",
    )
    assert applied["ok"] is True
    assert applied["applied"] is True

    pointers = PointerManager(tmp_path / "cpos" / "pointers.jsonl", tmp_path / "cpos" / "audit_log.jsonl").load()
    assert len(pointers) == 1
    pointer = pointers[0]
    assert pointer.context_type == "handoff_summary"
    assert pointer.retrieval_rule == "handoff_review_required"
    raw = json.dumps(pointer.to_dict(), ensure_ascii=False)
    assert "NEXT_HANDOFF excerpt" not in raw
    assert "checkpoint" in raw  # counts only are okay
    assert "test-secret" not in raw


def test_cli_sign_verify_import_with_secret_file(tmp_path):
    project = tmp_path / "project"
    (project / "cpos").mkdir(parents=True)
    (project / "tapes").mkdir()
    bundle = build_handoff_bundle(project_root=project, environ={"CPOS_SECURITY_PROFILE": "dev"})
    bundle_path = tmp_path / "handoff.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("cli-secret", encoding="utf-8")
    signed_path = tmp_path / "signed.json"

    sign = subprocess.run(
        [
            sys.executable,
            "-m",
            "cpos.handoff_receiver",
            "sign",
            str(bundle_path),
            "--secret-file",
            str(secret_file),
            "--key-id",
            "cli-key",
            "--output",
            str(signed_path),
        ],
        cwd=str(Path(__file__).resolve().parents[1]),
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(sign.stdout)["ok"] is True

    verify = subprocess.run(
        [sys.executable, "-m", "cpos.handoff_receiver", "verify", str(signed_path), "--secret-file", str(secret_file), "--key-id", "cli-key"],
        cwd=str(Path(__file__).resolve().parents[1]),
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(verify.stdout)["ok"] is True

    imp = subprocess.run(
        [
            sys.executable,
            "-m",
            "cpos.handoff_receiver",
            "import",
            str(signed_path),
            "--secret-file",
            str(secret_file),
            "--key-id",
            "cli-key",
            "--require-signature",
            "--apply",
            "--pointer-path",
            str(project / "cpos" / "pointers.jsonl"),
            "--pointer-audit-path",
            str(project / "cpos" / "audit_log.jsonl"),
        ],
        cwd=str(Path(__file__).resolve().parents[1]),
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(imp.stdout)
    assert result["ok"] is True
    assert result["applied"] is True
