# Zenn Cognitive Agent OS Publish Checklist

Date: 2026-06-07

## Scope

Checklist for `articles/cognitive-agent-os-safety-kernel.md`.

This document does not publish the article.

## Current draft status

- Repo: `/home/mayutama/zenn`
- Article: `articles/cognitive-agent-os-safety-kernel.md`
- Current intended state: `published: false`

## Pre-publish checks

Before publishing:

1. Confirm `published: false` before review.
2. Run secret scan against the article.
3. Confirm no tokens, API keys, database IDs, private paths, raw logs, raw diffs, DB rows, or phone data are present.
4. Confirm AGI framing is public-safe:
   - OK: “AGIではない”
   - OK: “AGI完成宣言ではない”
   - Avoid: “AGI completed”, “完全なAGI”, “AGIできた”
5. Confirm `fast resume without raw logs` is framed as safety/handoff, not as autonomous memory write.
6. Confirm tape-memory real writes are described as disabled/dry-run only.
7. Confirm Notion credential issue is not described with secret values.
8. Confirm title and intro are understandable to external readers.
9. Get explicit publish confirmation from Neko-san.
10. Only then change `published: true` and push.

## Current review conclusion

The latest review found:

- article remained `published: false`
- secret scan was clean
- final section order was improved so the article ends with `まとめ`
- AGI wording was made safer

Publishing still requires explicit confirmation.
