from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Any


class VaultRenderError(RuntimeError):
    pass


def ensure_secure_dir(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    directory.chmod(0o700)
    return directory


def safe_output_path(secret_dir: Path, filename: str) -> Path:
    candidate = secret_dir / filename
    resolved_dir = secret_dir.resolve()
    resolved_candidate = candidate.resolve(strict=False)
    if resolved_dir not in resolved_candidate.parents and resolved_candidate != resolved_dir:
        raise VaultRenderError("output_path_escapes_secret_dir")
    return candidate


def write_secret(path: Path, value: str) -> None:
    tmp = path.with_name(f".{path.name}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(tmp, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(value)
            if not value.endswith("\n"):
                handle.write("\n")
        os.replace(tmp, path)
        path.chmod(0o600)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def vault_get_field(vault_path: str, field: str) -> str:
    env = os.environ.copy()
    result = subprocess.run(
        ["vault", "kv", "get", f"-field={field}", vault_path],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise VaultRenderError(f"vault_get_failed:{vault_path}:{field}")
    return result.stdout


def load_manifest(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def render_manifest(manifest: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    secret_dir = ensure_secure_dir(manifest.get("secret_dir", "/run/secrets"))
    rendered = []
    for item in manifest.get("secrets", []):
        filename = item["filename"]
        vault_path = item["vault_path"]
        field = item["field"]
        output_path = safe_output_path(secret_dir, filename)
        if not dry_run:
            value = vault_get_field(vault_path, field)
            write_secret(output_path, value)
        rendered.append({"filename": filename, "path": str(output_path), "vault_path": vault_path, "field": field, "dry_run": dry_run})
    return {"ok": True, "secret_dir": str(secret_dir), "rendered": rendered}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render CPOS runtime secret files from Vault without printing secret values.")
    parser.add_argument("manifest", help="JSON manifest describing Vault path/field to output filename mapping.")
    parser.add_argument("--dry-run", action="store_true", help="Validate manifest and paths without fetching/writing secret values.")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = render_manifest(load_manifest(args.manifest), dry_run=args.dry_run)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"rendered {len(result['rendered'])} secret file(s) into {result['secret_dir']}")
        for item in result["rendered"]:
            print(f"- {item['path']} from {item['vault_path']} field={item['field']}")


if __name__ == "__main__":
    main()
