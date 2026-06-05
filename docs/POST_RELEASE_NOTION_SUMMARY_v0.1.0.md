# CPOS Engine-Zero v0.1.0 — Notionまとめ

## 日本語版：短く貼れる版

CPOS Engine-Zero v0.1.0 は、**安全な自律実行**を目的にした、防御型・メモリ統治型のAIエージェントランタイムの正式リリースです。

これは「何でも自動で書き換える無制限コーディングエージェント」ではなく、**レビューゲート・サンドボックス優先・メタデータのみ保存**を重視した、安全寄りのエージェント基盤です。

主なポイント：

- 正式リリース：`v0.1.0`
- Release URL：https://github.com/kagioneko/cpos-engine-zero/releases/tag/v0.1.0
- テスト：`320 passed`
- `prepublish_check` / `release_check`：`ok=true`
- secret scan：`count=0`
- raw diff / raw stdout / raw stderr / request body / checkpoint本文 / handoff本文 / secret値は永続保存しない
- デモ素材：`docs/assets/demo/`
- External Agent Adapter により、外部エージェントの action contract / execution result を統治できる
- 位置づけ：**CPOS Agent** かつ **CPOS for Agents**

できること：

- 危険な処理を Human Escalation に回す
- Task Tape にメタデータ中心で履歴を残す
- GitHub diff / sandbox plan / execution review をレビューゲート化する
- 実行結果と failure-to-replan の流れを追跡する
- dashboard / report / demo readiness で証跡を見せる
- 外部エージェントから `command_request`、`proposed_diff`、`execution_result` を受ける

まだ言いすぎになる表現：

- 完全自律の無制限コーディングエージェント
- 自動で本番リポジトリを書き換えるエージェント
- 自動で commit / push / PR を作成するシステム
- Vault の代替となる秘密情報管理システム

次のおすすめ：

- post-release stabilization
- v0.1.1 の小さめ backlog 作り
- Adapter integration / schema / examples の微調整
- v0.1.0 release draft を基準に、告知文・Notion・README文面を整える

---

## 日本語版：詳しめ構造化版

## 1. CPOS v0.1.0 とは

CPOS Engine-Zero v0.1.0 は、安全な自律実行のための防御型AIエージェントランタイムです。

中心にある考え方は、以下を分離することです。

- 長期記憶 / 文脈記憶
- タスク実行履歴
- 短期的なランタイム状態
- レビューが必要な危険操作

CPOS は、エージェントに無制限の実行権限を与えるのではなく、**実行力にガバナンスをかける**ことを目的にしています。

一言でいうと：

> CPOS Engine-Zero は、安全な自律実行のための、防御型・メモリ統治型AIエージェントランタイム兼、外部エージェント向け安全レイヤーです。

見せ方は2つあります。

1. **CPOS Agent**  
   CPOS自身がレビューゲート付きの防御型エージェントランタイムとして動く。

2. **CPOS for Agents**  
   Codex系、Hermes系、OpenClaw系のような外部エージェントの横に置き、安全・記憶・レビュー・証跡を担当する。

## 2. v0.1.0 の意味

多くのAIコーディングエージェントは、速度やツール実行範囲を強みにします。

CPOS はそこではなく、**実行の安全性・説明可能性・レビュー可能性**を強みにしています。

v0.1.0 で示せたこと：

- 危険操作をレビューゲートに通せる
- 承認と実行を分離できる
- planning/review段階では live repo を直接書き換えない
- 失敗を retry/replan 用のメタデータに変換できる
- dashboard / report で流れを説明できる
- raw diff や raw output や秘密情報を永続保存しない
- 外部エージェントの行動も adapter 経由で統治できる

そのため、防御用途、監査が必要な用途、レビュー前提の開発支援、外部エージェントの安全レイヤーとして向いています。

## 3. 中核機能

### Review-gated execution loop

CPOS の安全な自律ループ：

```text
Diff Draft
→ GitHub Diff Review
→ Sandbox Plan
→ Sandbox Execution Review
→ Supplied-diff Sandbox Run
→ Execution Result Metadata
→ Retry/Replan
→ Auto Fix Candidate
→ Diff Review Draft
→ Flow Graph / Report Snapshot
```

重要なのは、planning / review の段階では危険操作を直接実行しないことです。

### Metadata-only persistence

CPOS が保存するもの：

- hash
- size
- count
- task ID
- status
- endpoint hint
- failure kind
- lineage metadata

CPOS が保存しないもの：

- raw diff
- raw stdout / stderr
- request body
- checkpoint / handoff の本文
- token
- API key
- SSH key
- secret値

### Human Escalation

危険または方針上レビューが必要な処理は Human Escalation に回します。

例：

- destructive 操作
- secret / `.env` 関連
- production / deploy 関連
- network exposure
- GitHub publish
- low-confidence task
- 外部エージェントからの承認必須 action contract

### External Agent Adapter

External Agent Adapter は、外部エージェントが CPOS に action contract や result metadata を送るための入口です。

対応 event type：

- `agent_intent`
- `proposed_action`
- `proposed_diff`
- `command_request`
- `execution_result`

主な endpoint：

- `POST /agent-adapter/intake`
- `GET /agent-adapter/actions`
- `GET /agent-adapter/execution-results`
- `POST /agent-adapter/actions/<task_id>/approve`
- `POST /agent-adapter/actions/<task_id>/reject`

Adapter の安全デフォルト：

- `raw_request_stored=false`
- `raw_diff_stored=false`
- `raw_outputs_stored=false`
- `secret_values_stored=false`
- `execute_automatically=false`

Adapter action の approve は、あくまで metadata contract の承認です。コマンド実行はしません。

### External Agent Result Scoreboard

外部エージェントは、別の場所で行った実行結果を redacted metadata として CPOS に報告できます。

CPOS はそれを scoreboard として集計します。

- completed result count
- success / failure count
- success rate
- failure kind count
- recent result metadata

これにより、外部エージェントが実行した結果も、CPOS 側で監査・可視化できます。

## 4. デモと証跡

デモ素材は以下にあります。

```text
docs/assets/demo/
```

主なデモ画面：

- Competitive Demo Readiness
- External Agent Adapter Queue / Result Scoreboard
- Human Escalation Queue
- Ready-to-Run Gate
- Sandbox Flow Graph
- Generated Report Snapshot

デモの流れ：

```text
Fast Resume
→ External Agent Adapter
→ Result Scoreboard
→ Human Escalation
→ Patch Generation Review
→ Validation Harness
→ Ready-to-Run Gate
→ Flow Graph
→ Report Snapshot
```

デモ素材は metadata-only です。表示するのは status、count、hash、endpoint hint、安全フラグなどで、raw diff / raw output / secret は含みません。

## 5. リリース検証

v0.1.0 は最終チェック後に正式リリース済みです。

記録された状態：

- `git status`: `main...origin/main`
- tests: `320 passed`
- `prepublish_check`: `ok=true`
- `release_check`: `ok=true`
- secret scan: `count=0`
- final tag: `v0.1.0`
- GitHub Release: published / not draft / not prerelease

Release URL：

https://github.com/kagioneko/cpos-engine-zero/releases/tag/v0.1.0

## 6. 言っていいこと / 言いすぎなこと

言っていいこと：

- defensive AI agent runtime
- safe autonomy loop
- external-agent-ready governance layer
- metadata-only review and execution pipeline
- Human Escalation / sandbox-first architecture
- failure-to-replan lineage
- release-time safety checks

まだ言いすぎなこと：

- 完全自律の無制限コーディングエージェント
- 自動で live repo を書き換えるエージェント
- 自動で commit / push / PR を作るシステム
- Vault の代替
- operator approval なしの本番デプロイシステム

## 7. 次の方針

v0.1.0 後のおすすめ：

1. post-release stabilization
2. フィードバック収集
3. 大きな runtime 変更は具体的な統合先が出るまで控える
4. v0.1.1 向けの小さめ backlog を作る
5. 外部エージェント連携を重視するなら adapter docs / examples / schema を磨く
6. v0.1.0 release draft を基準に、告知文・Notion・README文面を整える

v0.1.1 の候補：

- adapter request の JSON schema validation 強化
- example client の追加
- dashboard 文言の polish
- release / announcement template
- 安全に撮れる環境があれば browser GIF

## 8. 告知文たたき台

短い版：

> CPOS Engine-Zero v0.1.0 を正式リリースしました。レビューゲート・サンドボックス優先・メタデータのみ保存・外部エージェント対応を特徴とする、防御型AIエージェントランタイムです。

少し長い版：

> CPOS Engine-Zero v0.1.0 は、安全寄りの実行力を重視したAIエージェントランタイムです。live repo を静かに書き換えたり、raw output を永続保存したりするのではなく、危険操作をレビューゲートに通し、メタデータのみを保存し、failure-to-replan の流れを可視化します。External Agent Adapter により、外部エージェントの行動も CPOS 側で統治できます。

## 9. 今後の文章作成で参照するもの

今後の告知文・README・Notionまとめ・次回リリースノートは、以下を基準に作るとよいです。

- `GITHUB_RELEASE_DRAFT_v0.1.0.md`
- `README.md`
- `RELEASE_NOTES_v0.1.0.md`
- `OSS_RELEASE_CHECKLIST.md`
- `docs/AGENT_ADAPTER_INTEGRATION.md`
- `docs/AGENT_ADAPTER_SCHEMA.md`
- `docs/DEMO_CAPTURE_GUIDE.md`
- `NEXT_HANDOFF.md`
- `docs/backlog/V0_1_1_BACKLOG.md`

---

## English reference version

# CPOS Engine-Zero v0.1.0 — Notion Summary

## Short paste-ready version

CPOS Engine-Zero v0.1.0 is an official release of a defensive, memory-governed AI agent runtime for safer autonomy.

It is not positioned as an unrestricted coding agent. Its value is a review-gated, sandbox-first, metadata-only execution loop that can govern both native CPOS workflows and external agents.

Key points:

- Official release: `v0.1.0`
- Release URL: https://github.com/kagioneko/cpos-engine-zero/releases/tag/v0.1.0
- Tests: `320 passed`
- Prepublish / release checks: `ok=true`
- Secret scan: `count=0`
- Safety stance: no persisted raw diffs, raw stdout/stderr, request bodies, checkpoint/handoff bodies, or secrets
- Demo assets: `docs/assets/demo/`
- External Agent Adapter: external agents can submit action contracts and execution result metadata
- Main positioning: **CPOS Agent** and **CPOS for Agents**

What it can do:

- Route risky work through Human Escalation
- Keep Task Tape append-only and metadata-oriented
- Review GitHub diff / sandbox plan / execution stages
- Track execution results and failure-to-replan lineage
- Provide dashboard/report/demo readiness evidence
- Accept external agent `command_request`, `proposed_diff`, and `execution_result` metadata

What it does not claim:

- It is not a fully unrestricted autonomous coding agent
- It does not automatically patch the live repo from planning/review stages
- It does not automatically commit, push, or create PRs
- It does not persist raw secrets, raw diffs, or raw command output

Next recommended direction:

- Post-release stabilization
- Small v0.1.1 backlog items only
- Adapter integration examples / schema polish
- Announcement or README/Notion/social copy based on the v0.1.0 release draft

---

## Longer structured version

## 1. What CPOS v0.1.0 is

CPOS Engine-Zero v0.1.0 is a defensive AI agent runtime focused on safe autonomy.

The core idea is to separate:

- long-term/context memory
- task execution history
- short-lived runtime state
- risky actions that require review

Instead of optimizing for unrestricted agent power, CPOS optimizes for controlled, auditable execution.

The best positioning is:

> CPOS Engine-Zero is a defensive, memory-governed AI agent runtime and safety layer for external agents.

It can be described in two ways:

1. **CPOS Agent** — a defensive agent runtime with its own review-gated execution loop.
2. **CPOS for Agents** — a safety, memory, and governance layer that can sit beside systems like Codex-like, Hermes-like, or OpenClaw-like agents.

## 2. Why the release matters

Many AI coding agents focus on tool reach and speed. CPOS focuses on execution governance.

v0.1.0 proves that an agent runtime can:

- keep risky operations review-gated
- separate approval from execution
- avoid silent live-repo mutation
- convert failures into retry/replan metadata
- provide operator-visible dashboard/report evidence
- avoid persisting sensitive raw data
- accept external agent actions through a governed adapter

This makes CPOS suitable for defensive, regulated, audit-sensitive, or operator-supervised workflows.

## 3. Core capabilities

### Review-gated execution loop

CPOS supports a safe autonomy loop:

```text
Diff Draft
→ GitHub Diff Review
→ Sandbox Plan
→ Sandbox Execution Review
→ Supplied-diff Sandbox Run
→ Execution Result Metadata
→ Retry/Replan
→ Auto Fix Candidate
→ Diff Review Draft
→ Flow Graph / Report Snapshot
```

The important point is that planning/review stages do not directly perform dangerous actions.

### Metadata-only persistence

CPOS stores:

- hashes
- sizes
- counters
- task IDs
- statuses
- endpoint hints
- failure kinds
- lineage metadata

CPOS avoids persisting:

- raw diffs
- raw stdout/stderr
- request bodies
- checkpoint/handoff bodies
- tokens
- API keys
- SSH keys
- secret values

### Human Escalation

Risky or policy-sensitive stages route through Human Escalation.

Examples include:

- destructive changes
- secrets or `.env` related work
- production/deploy changes
- network exposure
- GitHub publishing
- low-confidence work
- external agent action contracts that require approval

### External Agent Adapter

The External Agent Adapter lets outside agents submit metadata-rich events to CPOS.

Supported event types:

- `agent_intent`
- `proposed_action`
- `proposed_diff`
- `command_request`
- `execution_result`

Key endpoints:

- `POST /agent-adapter/intake`
- `GET /agent-adapter/actions`
- `GET /agent-adapter/execution-results`
- `POST /agent-adapter/actions/<task_id>/approve`
- `POST /agent-adapter/actions/<task_id>/reject`

Adapter safety defaults:

- `raw_request_stored=false`
- `raw_diff_stored=false`
- `raw_outputs_stored=false`
- `secret_values_stored=false`
- `execute_automatically=false`

Approval of an adapter action approves metadata only. It does not run commands.

### External Agent Result Scoreboard

External agents can report execution results as redacted metadata.

CPOS then provides a scoreboard with:

- completed result count
- success/failure count
- success rate
- failure kind counts
- recent result metadata

This is useful when another agent performs work elsewhere but CPOS remains the audit/governance layer.

## 4. Demo and proof assets

The repo includes metadata-only demo panels under:

```text
docs/assets/demo/
```

Key demo views:

- Competitive Demo Readiness
- External Agent Adapter Queue / Result Scoreboard
- Human Escalation Queue
- Ready-to-Run Gate
- Sandbox Flow Graph
- Generated Report Snapshot

The demo path is:

```text
Fast Resume
→ External Agent Adapter
→ Result Scoreboard
→ Human Escalation
→ Patch Generation Review
→ Validation Harness
→ Ready-to-Run Gate
→ Flow Graph
→ Report Snapshot
```

The demo assets are designed to show statuses, counts, hashes, endpoint hints, and safety flags only.

## 5. Release verification

v0.1.0 was released after final checks.

Recorded status:

- `git status`: `main...origin/main`
- tests: `320 passed`
- `prepublish_check`: `ok=true`
- `release_check`: `ok=true`
- secret scan: `count=0`
- final tag: `v0.1.0`
- GitHub Release: published, not draft, not prerelease

Release URL:

https://github.com/kagioneko/cpos-engine-zero/releases/tag/v0.1.0

## 6. What CPOS v0.1.0 should and should not claim

Good claims:

- Defensive AI agent runtime
- Safe autonomy loop
- External-agent-ready governance layer
- Metadata-only review and execution pipeline
- Human escalation and sandbox-first architecture
- Failure-to-replan lineage
- Release-time safety checks

Avoid claiming:

- fully autonomous unrestricted coding agent
- automatic live-repo patching agent
- automatic commit/push/PR creation system
- secret-handling replacement for Vault
- production deployment system without operator approval

## 7. Post-release next steps

Recommended next steps after v0.1.0:

1. Post-release stabilization
2. Gather feedback
3. Keep large runtime changes out until a concrete integration target exists
4. Build small v0.1.1 backlog items
5. Improve adapter docs/examples if external-agent integration becomes the focus
6. Prepare announcement/social/Notion copy using the v0.1.0 release draft as the standard tone

Potential v0.1.1 seeds:

- stricter JSON schema validation for adapter requests
- more example clients
- dashboard copy polish
- release/announcement templates
- optional browser-captured GIFs if environment supports safe capture

## 8. Suggested announcement wording

Short version:

> CPOS Engine-Zero v0.1.0 is now released. It is a defensive, memory-governed AI agent runtime for safe autonomy: review-gated, sandbox-first, metadata-only, and external-agent-ready.

Longer version:

> CPOS Engine-Zero v0.1.0 focuses on safer-by-design execution power. Instead of silently patching live repositories or persisting sensitive raw outputs, CPOS routes risky actions through review gates, stores metadata only, tracks failure-to-replan lineage, and can govern external agents through its External Agent Adapter.

## 9. Source documents

Use these as the source of truth for future writing:

- `GITHUB_RELEASE_DRAFT_v0.1.0.md`
- `README.md`
- `RELEASE_NOTES_v0.1.0.md`
- `OSS_RELEASE_CHECKLIST.md`
- `docs/AGENT_ADAPTER_INTEGRATION.md`
- `docs/AGENT_ADAPTER_SCHEMA.md`
- `docs/DEMO_CAPTURE_GUIDE.md`
- `NEXT_HANDOFF.md`
- `docs/backlog/V0_1_1_BACKLOG.md`
