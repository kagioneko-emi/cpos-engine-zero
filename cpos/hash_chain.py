from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json

GENESIS_HASH = "0" * 64
CHAIN_FIELD = "_chain"


def canonical_row(row: dict[str, Any]) -> str:
    body = {key: value for key, value in row.items() if key != CHAIN_FIELD}
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def row_hash(row: dict[str, Any], prev_hash: str) -> str:
    payload = f"{prev_hash}\n{canonical_row(row)}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def last_chain_hash(path: str | Path) -> str:
    rows = read_jsonl(path)
    for row in reversed(rows):
        chain = row.get(CHAIN_FIELD)
        if isinstance(chain, dict) and chain.get("row_hash"):
            return str(chain["row_hash"])
    return GENESIS_HASH


def attach_chain(row: dict[str, Any], prev_hash: str) -> dict[str, Any]:
    chained = dict(row)
    digest = row_hash(chained, prev_hash)
    chained[CHAIN_FIELD] = {
        "algo": "sha256",
        "prev_hash": prev_hash,
        "row_hash": digest,
    }
    return chained


def append_chained_jsonl(path: str | Path, row: dict[str, Any]) -> dict[str, Any]:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    chained = attach_chain(row, last_chain_hash(path))
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(chained, ensure_ascii=False) + "\n")
    return chained


def verify_hash_chain(path: str | Path, *, allow_legacy_prefix: bool = True) -> dict[str, Any]:
    rows = read_jsonl(path)
    prev_hash = GENESIS_HASH
    legacy_prefix_count = 0
    verified_count = 0
    chain_started = False

    for index, row in enumerate(rows, start=1):
        chain = row.get(CHAIN_FIELD)
        if not isinstance(chain, dict):
            if allow_legacy_prefix and not chain_started:
                legacy_prefix_count += 1
                continue
            return {
                "ok": False,
                "error": "missing_chain",
                "line": index,
                "verified_count": verified_count,
                "legacy_prefix_count": legacy_prefix_count,
            }

        chain_started = True
        expected_prev = prev_hash
        actual_prev = str(chain.get("prev_hash", ""))
        if actual_prev != expected_prev:
            return {
                "ok": False,
                "error": "prev_hash_mismatch",
                "line": index,
                "expected_prev_hash": expected_prev,
                "actual_prev_hash": actual_prev,
                "verified_count": verified_count,
                "legacy_prefix_count": legacy_prefix_count,
            }

        expected_hash = row_hash(row, actual_prev)
        actual_hash = str(chain.get("row_hash", ""))
        if actual_hash != expected_hash:
            return {
                "ok": False,
                "error": "row_hash_mismatch",
                "line": index,
                "expected_row_hash": expected_hash,
                "actual_row_hash": actual_hash,
                "verified_count": verified_count,
                "legacy_prefix_count": legacy_prefix_count,
            }
        verified_count += 1
        prev_hash = actual_hash

    return {
        "ok": True,
        "row_count": len(rows),
        "verified_count": verified_count,
        "legacy_prefix_count": legacy_prefix_count,
        "head_hash": prev_hash,
    }
