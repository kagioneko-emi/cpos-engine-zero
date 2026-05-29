from __future__ import annotations

import argparse
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

from .key_registry import HMACKeyRegistry
from .pointer_os import PointerManager, utc_now

HANDOFF_SCHEMA = "cpos.multi_agent_handoff.v1"
SIGNATURE_ALGO = "hmac-sha256"


def load_json_file(path: str | Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"handoff_unreadable: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("handoff_must_be_json_object")
    return data


def read_secret_file(path: str | Path) -> str:
    try:
        secret = Path(path).read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ValueError(f"secret_file_unreadable: {exc}") from exc
    if not secret:
        raise ValueError("secret_file_empty")
    return secret


def resolve_secret(*, secret_file: str | None = None, registry_file: str | None = None, key_id: str | None = None) -> tuple[str, str | None]:
    if registry_file:
        if not key_id:
            raise ValueError("key_id_required_with_registry")
        record = HMACKeyRegistry(registry_file).get(key_id)
        if record is None:
            raise ValueError("key_not_found")
        usable, reason = record.is_usable()
        if not usable:
            raise ValueError(reason)
        return read_secret_file(record.secret_file), record.key_id
    if not secret_file:
        raise ValueError("secret_file_required")
    return read_secret_file(secret_file), key_id


def strip_signature(bundle: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in bundle.items() if key != "signature"}


def canonical_bundle(bundle: dict[str, Any]) -> bytes:
    return json.dumps(strip_signature(bundle), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def bundle_digest(bundle: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bundle(bundle)).hexdigest()


def sign_bundle(bundle: dict[str, Any], *, secret: str, key_id: str | None = None, signer_agent: str = "CPOSHandoffSigner") -> dict[str, Any]:
    digest = bundle_digest(bundle)
    signature = hmac.new(secret.encode("utf-8"), canonical_bundle(bundle), hashlib.sha256).hexdigest()
    signed = strip_signature(bundle)
    signed["signature"] = {
        "algo": SIGNATURE_ALGO,
        "key_id": key_id,
        "signer_agent": signer_agent,
        "signed_at": utc_now(),
        "bundle_sha256": digest,
        "signature": signature,
    }
    return signed


def verify_signed_bundle(bundle: dict[str, Any], *, secret: str, expected_key_id: str | None = None) -> dict[str, Any]:
    signature_block = bundle.get("signature")
    if not isinstance(signature_block, dict):
        return {"ok": False, "error": "signature_missing"}
    if signature_block.get("algo") != SIGNATURE_ALGO:
        return {"ok": False, "error": "unsupported_signature_algo"}
    key_id = signature_block.get("key_id")
    if expected_key_id and key_id != expected_key_id:
        return {"ok": False, "error": "key_id_mismatch", "key_id": key_id, "expected_key_id": expected_key_id}
    digest = bundle_digest(bundle)
    if signature_block.get("bundle_sha256") != digest:
        return {"ok": False, "error": "bundle_digest_mismatch", "expected_digest": digest, "actual_digest": signature_block.get("bundle_sha256")}
    expected = hmac.new(secret.encode("utf-8"), canonical_bundle(bundle), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(str(signature_block.get("signature", "")), expected):
        return {"ok": False, "error": "signature_mismatch"}
    return {
        "ok": True,
        "key_id": key_id,
        "signer_agent": signature_block.get("signer_agent"),
        "signed_at": signature_block.get("signed_at"),
        "bundle_sha256": digest,
    }


def validate_handoff_bundle(bundle: dict[str, Any], *, require_signature: bool = False, verification: dict[str, Any] | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if bundle.get("schema") != HANDOFF_SCHEMA:
        errors.append("schema_mismatch")
    safety = bundle.get("safety") if isinstance(bundle.get("safety"), dict) else {}
    if safety.get("secrets_included") is not False:
        errors.append("safety_secrets_flag_not_false")
    if safety.get("checkpoint_contents_included") is not False:
        errors.append("safety_checkpoint_flag_not_false")
    if safety.get("request_bodies_included") is not False:
        errors.append("safety_request_body_flag_not_false")
    for required in ("generated_at", "integrity", "pointers", "tasks", "secret_inventory"):
        if required not in bundle:
            errors.append(f"missing_{required}")
    if require_signature and not (verification or {}).get("ok"):
        errors.append("signature_required_but_not_valid")
    integrity = bundle.get("integrity") if isinstance(bundle.get("integrity"), dict) else {}
    failed_ledgers = [name for name, result in integrity.items() if isinstance(result, dict) and not result.get("ok")]
    if failed_ledgers:
        warnings.append("integrity_failures:" + ",".join(sorted(failed_ledgers)))
    return {"ok": not errors, "errors": errors, "warnings": warnings}


def build_import_pointer(bundle: dict[str, Any], *, verification: dict[str, Any] | None = None, source_file: str | None = None) -> dict[str, Any]:
    verification = verification or {"ok": False}
    pointers = bundle.get("pointers") if isinstance(bundle.get("pointers"), dict) else {}
    tasks = bundle.get("tasks") if isinstance(bundle.get("tasks"), dict) else {}
    task_summary = tasks.get("summary") if isinstance(tasks.get("summary"), dict) else {}
    inventory = bundle.get("secret_inventory") if isinstance(bundle.get("secret_inventory"), dict) else {}
    digest = bundle_digest(bundle)
    signer = verification.get("signer_agent") or "unsigned"
    summary = (
        f"Imported CPOS handoff from {bundle.get('generated_at', 'unknown time')}: "
        f"pointers={pointers.get('count', 0)}, tasks={task_summary.get('task_count', 0)}, "
        f"secret_artifacts={inventory.get('count', 0)}, signature_ok={bool(verification.get('ok'))}"
    )
    pointer_id = f"ptr://handoff/{digest[:16]}"
    return {
        "pointer_id": pointer_id,
        "context_type": "handoff_summary",
        "summary": summary,
        "source": f"handoff:{signer}",
        "location": f"handoff://{digest}",
        "priority": 0.55,
        "trust_score": 0.75 if verification.get("ok") else 0.35,
        "sensitivity_level": "internal",
        "retrieval_rule": "handoff_review_required",
        "metadata": {
            "schema": bundle.get("schema"),
            "generated_at": bundle.get("generated_at"),
            "imported_at": utc_now(),
            "source_file": source_file,
            "bundle_sha256": digest,
            "signature": {key: verification.get(key) for key in ("ok", "key_id", "signer_agent", "signed_at", "bundle_sha256") if key in verification},
            "counts": {
                "pointers": pointers.get("count", 0),
                "tasks": task_summary.get("task_count", 0),
                "task_events": task_summary.get("event_count", 0),
                "checkpoints": task_summary.get("checkpoint_count", 0),
                "secret_artifacts": inventory.get("count", 0),
            },
            "integrity_ok": all(isinstance(result, dict) and result.get("ok") for result in (bundle.get("integrity") or {}).values()),
        },
    }


def import_handoff_bundle(
    bundle: dict[str, Any],
    *,
    pointer_path: str | Path,
    pointer_audit_path: str | Path | None = None,
    apply: bool = False,
    require_signature: bool = False,
    verification: dict[str, Any] | None = None,
    source_file: str | None = None,
) -> dict[str, Any]:
    validation = validate_handoff_bundle(bundle, require_signature=require_signature, verification=verification)
    planned_pointer = build_import_pointer(bundle, verification=verification, source_file=source_file)
    result = {"ok": validation["ok"], "applied": False, "validation": validation, "planned_pointer": planned_pointer}
    if not validation["ok"]:
        return result
    if not apply:
        return result
    manager = PointerManager(pointer_path, pointer_audit_path)
    pointer = manager.create_pointer(**planned_pointer)
    result.update({"applied": True, "pointer": pointer.to_dict()})
    return result


def _load_bundle_arg(path: str) -> dict[str, Any]:
    return load_json_file(path)


def _write_or_print(payload: dict[str, Any], output: str | None) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if output:
        p = Path(output)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(rendered + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "output": str(p)}, ensure_ascii=False))
        return
    print(rendered)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sign, verify, and safely import sanitized CPOS handoff bundles.")
    sub = parser.add_subparsers(dest="command", required=True)

    def secret_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--secret-file", help="Runtime HMAC secret file populated from Vault/secret volume.")
        p.add_argument("--registry-file", help="Non-secret HMAC registry JSON.")
        p.add_argument("--key-id")

    sign = sub.add_parser("sign", help="Attach an HMAC signature to a handoff JSON bundle.")
    sign.add_argument("bundle")
    secret_args(sign)
    sign.add_argument("--signer-agent", default="CPOSHandoffSigner")
    sign.add_argument("--output")

    verify = sub.add_parser("verify", help="Verify a signed handoff JSON bundle.")
    verify.add_argument("bundle")
    secret_args(verify)

    imp = sub.add_parser("import", help="Validate and optionally import a handoff summary pointer.")
    imp.add_argument("bundle")
    imp.add_argument("--pointer-path", default="cpos/pointers.jsonl")
    imp.add_argument("--pointer-audit-path", default="cpos/audit_log.jsonl")
    imp.add_argument("--apply", action="store_true", help="Actually create the handoff_summary pointer. Without this, performs dry-run only.")
    imp.add_argument("--require-signature", action="store_true")
    secret_args(imp)
    return parser


def _verify_from_args(bundle: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    if not args.secret_file and not args.registry_file:
        return {"ok": False, "error": "verification_secret_not_configured"}
    secret, key_id = resolve_secret(secret_file=args.secret_file, registry_file=args.registry_file, key_id=args.key_id)
    return verify_signed_bundle(bundle, secret=secret, expected_key_id=key_id if args.registry_file else args.key_id)


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    try:
        bundle = _load_bundle_arg(args.bundle)
        if args.command == "sign":
            secret, key_id = resolve_secret(secret_file=args.secret_file, registry_file=args.registry_file, key_id=args.key_id)
            _write_or_print(sign_bundle(bundle, secret=secret, key_id=key_id, signer_agent=args.signer_agent), args.output)
            return
        if args.command == "verify":
            result = _verify_from_args(bundle, args)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if not result.get("ok"):
                raise SystemExit(1)
            return
        if args.command == "import":
            verification = _verify_from_args(bundle, args) if (args.secret_file or args.registry_file or args.require_signature) else {"ok": False}
            result = import_handoff_bundle(
                bundle,
                pointer_path=args.pointer_path,
                pointer_audit_path=args.pointer_audit_path,
                apply=args.apply,
                require_signature=args.require_signature,
                verification=verification,
                source_file=args.bundle,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if not result.get("ok"):
                raise SystemExit(1)
            return
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
