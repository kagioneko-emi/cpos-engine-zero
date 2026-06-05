# Next Work Sequence Log

Created after publishing `v0.1.1-rc1` prerelease and deciding to let CPOS Engine-Zero rest before final `v0.1.1`.

## Planned order

User selected order: **1 → 3 → 2** from the suggested next-work list.

1. **Zenn追加記事**
   - Draft a follow-up article about “CPOS for Agents”.
   - Focus: External Agent Adapter, metadata-only safety layer, `v0.1.1-rc1` stabilization.
   - Keep it draft until user explicitly approves publish/push.

2. **CPOS v0.1.2 backlog only**
   - Create an ideas/backlog doc.
   - Do not start implementation yet.
   - Candidate themes: adapter SDK, OpenAPI/schema export, demo video/script, GitHub Actions checks, external-agent examples.

3. **別プロジェクトに移動**
   - After CPOS log/backlog/articles are staged or parked, move attention to another repo/project.
   - Decide target project with the user at that time.

## Current CPOS release posture

- `v0.1.1-rc1` tag pushed.
- GitHub prerelease published: https://github.com/kagioneko/cpos-engine-zero/releases/tag/v0.1.1-rc1
- Final `v0.1.1` should wait unless the user explicitly asks to proceed.
- Before final release, re-run full tests, `prepublish_check`, and `release_check`.

## Safety notes

- Do not publish final `v0.1.1` without explicit user confirmation.
- Do not commit/push Zenn articles as published unless user explicitly approves.
- Do not add secrets, raw outputs, raw diffs, cert/key material, token values, `.env` values, or runtime ledgers to docs/articles.
