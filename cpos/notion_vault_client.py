from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

PAYLOAD_SCHEMA = "kagioneko.notion_page_payload.v1"
DRY_RUN_SCHEMA = "kagioneko.notion_dry_run.v1"
CREATE_RESULT_SCHEMA = "kagioneko.notion_create_result.v1"
VAULT_ADDR = "https://127.0.0.1:8200"
VAULT_CACERT = "/etc/vault.d/tls/vault-cert.pem"
NOTION_VERSION = "2022-06-28"
SAFETY_FLAGS = {
    "metadata_only": True,
    "raw_request_stored": False,
    "raw_diff_stored": False,
    "raw_outputs_stored": False,
    "secret_values_stored": False,
    "execute_automatically": False,
}


def vault_env() -> dict[str, str]:
    return {**os.environ, "VAULT_ADDR": VAULT_ADDR, "VAULT_CACERT": VAULT_CACERT}


def vault_field(field: str, *, path: str = "secret/notion") -> str:
    result = subprocess.run(
        ["vault", "kv", "get", f"-field={field}", path],
        env=vault_env(),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def rich_text(text: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": {"content": text[:1900]}}]


def markdown_to_blocks(markdown: str, *, max_blocks: int = 95) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    code_lines: list[str] = []
    in_code = False
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if line.startswith("```"):
            if in_code:
                blocks.append({"object": "block", "type": "code", "code": {"rich_text": rich_text("\n".join(code_lines) or " "), "language": "plain text"}})
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not line.strip():
            continue
        if line.startswith("#"):
            level = min(max(len(line) - len(line.lstrip("#")), 1), 3)
            block_type = f"heading_{level}"
            blocks.append({"object": "block", "type": block_type, block_type: {"rich_text": rich_text(line.lstrip("#").strip())}})
        elif line.startswith("- "):
            blocks.append({"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": rich_text(line[2:].strip())}})
        else:
            blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": rich_text(line)}})
    if code_lines:
        blocks.append({"object": "block", "type": "code", "code": {"rich_text": rich_text("\n".join(code_lines)), "language": "plain text"}})
    return blocks[:max_blocks]


def build_page_payload(*, title: str, markdown: str, database_id: str = "vault:secret/notion#memo_db_id") -> dict[str, Any]:
    return {
        "schema": PAYLOAD_SCHEMA,
        "notion_payload": {
            "parent": {"database_id": database_id},
            "properties": {
                "タイトル": {"title": [{"text": {"content": title[:200]}}]},
            },
            "children": markdown_to_blocks(markdown),
        },
        "vault_required": True,
        "vault_path": "secret/notion",
        "token_field": "api_key",
        "database_field": "memo_db_id",
        **SAFETY_FLAGS,
    }


def dry_run_page(*, title: str, source: str | Path) -> dict[str, Any]:
    markdown = Path(source).read_text(encoding="utf-8")
    payload = build_page_payload(title=title, markdown=markdown)
    notion_payload = payload["notion_payload"]
    return {
        "schema": DRY_RUN_SCHEMA,
        "ok": True,
        "would_create_page": True,
        "execute_required": True,
        "vault_required": True,
        "title": title,
        "source": str(source),
        "block_count": len(notion_payload.get("children", [])),
        "database_id_source": "vault:secret/notion#memo_db_id",
        "token_source": "vault:secret/notion#api_key",
        "secrets_printed": False,
        "payload_schema": PAYLOAD_SCHEMA,
        **SAFETY_FLAGS,
    }


def create_page(*, title: str, source: str | Path) -> dict[str, Any]:
    markdown = Path(source).read_text(encoding="utf-8")
    token = vault_field("api_key")
    database_id = vault_field("memo_db_id")
    payload = build_page_payload(title=title, markdown=markdown, database_id=database_id)["notion_payload"]
    request = urllib.request.Request(
        "https://api.notion.com/v1/pages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    return {
        "schema": CREATE_RESULT_SCHEMA,
        "ok": True,
        "url": data.get("url"),
        "title": title,
        "source": str(source),
        "block_count": len(payload.get("children", [])),
        "secrets_printed": False,
        **SAFETY_FLAGS,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vault-backed Notion helper; dry-run by default, secrets never printed.")
    sub = parser.add_subparsers(dest="command", required=True)
    page = sub.add_parser("page", help="Create or dry-run a Notion page from Markdown.")
    page.add_argument("--source", required=True, help="Markdown source file.")
    page.add_argument("--title", required=True, help="Notion page title.")
    page.add_argument("--execute", action="store_true", help="Actually create a Notion page using Vault credentials.")
    page.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command != "page":
        raise SystemExit(2)
    result = create_page(title=args.title, source=args.source) if args.execute else dry_run_page(title=args.title, source=args.source)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if args.execute:
            print(f"notion_page_created: ok={result['ok']} url={result.get('url')}")
        else:
            print(f"notion_page_dry_run: ok={result['ok']} blocks={result['block_count']} execute_required=true")


if __name__ == "__main__":
    main()
