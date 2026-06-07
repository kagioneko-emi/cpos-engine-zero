# Zenn to Notion Bridge Dry-run

`cpos.notion_zenn_bridge` is a safe dry-run replacement path for the old local
`upload_zenn_to_notion.py` style helper.

The old helper is not edited, deleted, or executed by this bridge.

## Dry-run

```bash
PYTHONPATH=. .venv/bin/python -m cpos.notion_zenn_bridge bridge \
  --article /home/mayutama/zenn/articles/cognitive-agent-os-safety-kernel.md \
  --json
```

Dry-run behavior:

- reads Zenn frontmatter
- confirms draft/published state
- builds a Vault-backed Notion dry-run via `cpos.notion_vault_client`
- does not read Vault
- does not contact Notion
- does not print secrets or database IDs
- does not modify old helper scripts

## Execute mode

Actual Notion creation requires explicit `--execute`:

```bash
PYTHONPATH=. .venv/bin/python -m cpos.notion_zenn_bridge bridge \
  --article /home/mayutama/zenn/articles/cognitive-agent-os-safety-kernel.md \
  --execute \
  --json
```

Use `--execute` only after explicit human confirmation. Credentials are read
through the Vault-backed Notion helper.
