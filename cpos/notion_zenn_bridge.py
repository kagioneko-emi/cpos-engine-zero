from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .notion_vault_client import DRY_RUN_SCHEMA, CREATE_RESULT_SCHEMA, create_page, dry_run_page

BRIDGE_SCHEMA = "kagioneko.notion_zenn_bridge.v1"
DEFAULT_ZENN_ARTICLE = "/home/mayutama/zenn/articles/cognitive-agent-os-safety-kernel.md"
SAFETY_FLAGS = {
    "metadata_only": True,
    "raw_request_stored": False,
    "raw_diff_stored": False,
    "raw_outputs_stored": False,
    "secret_values_stored": False,
    "execute_automatically": False,
}


def read_zenn_frontmatter(path: str | Path) -> dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    result: dict[str, Any] = {"published": None, "title": None, "frontmatter_present": False}
    if not text.startswith("---\n"):
        return result
    end = text.find("\n---", 4)
    if end < 0:
        return result
    result["frontmatter_present"] = True
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"')
        if key == "published":
            result["published"] = value.lower() == "true"
        elif key == "title":
            result["title"] = value
    return result


def build_zenn_to_notion_bridge(
    *,
    article: str | Path = DEFAULT_ZENN_ARTICLE,
    title_prefix: str = "【Zenn記事下書き】",
    execute: bool = False,
) -> dict[str, Any]:
    article_path = Path(article)
    frontmatter = read_zenn_frontmatter(article_path)
    title = f"{title_prefix}{frontmatter.get('title') or article_path.stem}"
    notion_result = create_page(title=title, source=article_path) if execute else dry_run_page(title=title, source=article_path)
    return {
        "schema": BRIDGE_SCHEMA,
        "mode": "execute" if execute else "dry_run",
        "article": str(article_path),
        "article_exists": article_path.exists(),
        "frontmatter_present": bool(frontmatter.get("frontmatter_present")),
        "published": frontmatter.get("published"),
        "title": frontmatter.get("title"),
        "notion_result_schema": notion_result.get("schema"),
        "notion_ok": bool(notion_result.get("ok")),
        "notion_url": notion_result.get("url") if execute else None,
        "block_count": notion_result.get("block_count"),
        "dry_run_schema": DRY_RUN_SCHEMA,
        "create_result_schema": CREATE_RESULT_SCHEMA,
        "vault_required_for_execute": True,
        "secrets_printed": False,
        "old_helper_modified": False,
        "old_helper_executed": False,
        **SAFETY_FLAGS,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vault-backed Zenn draft to Notion bridge; dry-run by default.")
    sub = parser.add_subparsers(dest="command", required=True)
    bridge = sub.add_parser("bridge", help="Dry-run or explicitly execute Zenn draft upload through Vault-backed Notion helper.")
    bridge.add_argument("--article", default=DEFAULT_ZENN_ARTICLE, help="Zenn markdown article path.")
    bridge.add_argument("--title-prefix", default="【Zenn記事下書き】")
    bridge.add_argument("--execute", action="store_true", help="Actually create a Notion page using Vault credentials.")
    bridge.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command != "bridge":
        raise SystemExit(2)
    result = build_zenn_to_notion_bridge(article=args.article, title_prefix=args.title_prefix, execute=args.execute)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"notion_zenn_bridge: mode={result['mode']} ok={result['notion_ok']} published={result['published']}")


if __name__ == "__main__":
    main()
