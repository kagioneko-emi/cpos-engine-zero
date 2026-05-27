from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import time
import uuid
from urllib.parse import urlsplit

from .key_registry import HMACKeyRegistry


def _read_secret(path: str) -> str:
    try:
        secret = open(path, encoding="utf-8").read().strip()
    except OSError as exc:
        raise SystemExit(f"secret_file_unreadable: {exc}") from exc
    if not secret:
        raise SystemExit("secret_file_empty")
    return secret


def _resolve_secret(args: argparse.Namespace) -> tuple[str, str | None]:
    if args.registry_file:
        if not args.key_id:
            raise SystemExit("key_id_required_with_registry")
        record = HMACKeyRegistry(args.registry_file).get(args.key_id)
        if record is None:
            raise SystemExit("key_not_found")
        usable, reason = record.is_usable()
        if not usable:
            raise SystemExit(reason)
        return _read_secret(record.secret_file), record.key_id
    if not args.secret_file:
        raise SystemExit("secret_file_required")
    return _read_secret(args.secret_file), args.key_id


def _split_target(target: str, query_string: str | None) -> tuple[str, str]:
    parsed = urlsplit(target)
    path = parsed.path or target
    query = query_string if query_string is not None else parsed.query
    return path, query


def signature_message(method: str, path: str, query_string: str, body: bytes, timestamp: int, nonce: str) -> str:
    return "\n".join(
        [
            method.upper(),
            path,
            query_string,
            hashlib.sha256(body).hexdigest(),
            str(timestamp),
            nonce,
        ]
    )


def sign_request(*, method: str, path: str, query_string: str = "", body: bytes = b"", timestamp: int | None = None, nonce: str | None = None, secret: str) -> dict[str, str]:
    timestamp = int(time.time()) if timestamp is None else int(timestamp)
    nonce = nonce or uuid.uuid4().hex
    message = signature_message(method, path, query_string, body, timestamp, nonce)
    signature = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "X-CPOS-Timestamp": str(timestamp),
        "X-CPOS-Nonce": nonce,
        "X-CPOS-Signature": signature,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate CPOS HMAC request headers without exposing secrets.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sign = subparsers.add_parser("sign", help="Sign a request and print headers.")
    sign.add_argument("method")
    sign.add_argument("target", help="Path or URL, e.g. /tasks or https://host/tasks?x=1")
    sign.add_argument("--query-string")
    sign.add_argument("--body", default="", help="Literal request body. Prefer --body-file for non-trivial payloads.")
    sign.add_argument("--body-file", help="Read request body bytes from file.")
    sign.add_argument("--secret-file", help="Runtime secret file populated from Vault/secret volume.")
    sign.add_argument("--registry-file", help="Non-secret HMAC key registry JSON.")
    sign.add_argument("--key-id")
    sign.add_argument("--agent-id")
    sign.add_argument("--nonce")
    sign.add_argument("--timestamp", type=int)
    sign.add_argument("--json", action="store_true")
    sign.add_argument("--curl", action="store_true", help="Print curl -H fragments instead of raw headers.")
    return parser


def _body_bytes(args: argparse.Namespace) -> bytes:
    if args.body_file:
        return open(args.body_file, "rb").read()
    return args.body.encode("utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "sign":
        secret, key_id = _resolve_secret(args)
        path, query = _split_target(args.target, args.query_string)
        headers = sign_request(
            method=args.method,
            path=path,
            query_string=query,
            body=_body_bytes(args),
            timestamp=args.timestamp,
            nonce=args.nonce,
            secret=secret,
        )
        if key_id:
            headers["X-CPOS-Key-Id"] = key_id
        if args.agent_id:
            headers["X-Agent-Id"] = args.agent_id

        if args.json:
            print(json.dumps({"ok": True, "headers": headers}, ensure_ascii=False, indent=2))
            return
        if args.curl:
            print(" ".join(f"-H {json.dumps(f'{key}: {value}')}" for key, value in headers.items()))
            return
        for key, value in headers.items():
            print(f"{key}: {value}")
        return


if __name__ == "__main__":
    main()
