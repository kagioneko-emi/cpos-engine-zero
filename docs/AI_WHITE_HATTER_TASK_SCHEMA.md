# AI White-Hatter Task Schema

このスキーマは、`AI_WHITE_HATTER_SYSTEM_SPEC.md` と
`AI_WHITE_HATTER_OPERATION_TEMPLATES.md` を機械可読にするためのもの。

用途:

- タスク管理
- 既存リポ比較
- 最小再現の指示
- 証跡の記録
- 報告ドラフト生成

---

## 1. 基本原則

- スコープ外は `blocked`
- 参照専用リポは `reference_only`
- 検証専用は `test_only`
- 最終判断は `human`
- 秘密情報は保存しない
- 生ログは必要最小限
- 破壊的操作は禁止または事前承認

---

## 2. 推奨 JSON 形式

```json
{
  "task_id": "wh-2026-001",
  "title": "Example finding review",
  "date": "2026-06-10",
  "owner": "codex",
  "target_program": "example-program",
  "scope": {
    "status": "confirmed",
    "notes": "Only approved assets"
  },
  "repos": [
    {
      "name": "target-repo",
      "role": "allowed"
    },
    {
      "name": "reference-repo",
      "role": "reference_only"
    }
  ],
  "ai_roles": {
    "coordinator": "codex",
    "broad_survey": "gemini",
    "deep_review": "claude",
    "local_validation": "codex"
  },
  "hypothesis": [
    "Possible authz mismatch in a handler",
    "Possible error handling gap in upload flow"
  ],
  "constraints": {
    "no_secrets": true,
    "no_production_data": true,
    "no_destructive_actions": true,
    "minimal_reproduction": true
  },
  "evidence": {
    "logs": [],
    "screenshots": [],
    "paths": [],
    "commits": []
  },
  "status": "planned",
  "next_action": "scope_gate",
  "human_review_required": true
}
```

---

## 3. 推奨 YAML 形式

```yaml
task_id: wh-2026-001
title: Example finding review
date: "2026-06-10"
owner: codex
target_program: example-program

scope:
  status: confirmed
  notes: Only approved assets

repos:
  - name: target-repo
    role: allowed
  - name: reference-repo
    role: reference_only

ai_roles:
  coordinator: codex
  broad_survey: gemini
  deep_review: claude
  local_validation: codex
  report_polish: codex

hypothesis:
  - Possible authz mismatch in a handler
  - Possible error handling gap in upload flow

constraints:
  no_secrets: true
  no_production_data: true
  no_destructive_actions: true
  minimal_reproduction: true

evidence:
  logs: []
  screenshots: []
  paths: []
  commits: []

status: planned
next_action: scope_gate
human_review_required: true
```

---

## 4. フィールド定義

### `task_id`
ユニークなタスク ID。

### `title`
人間が読める短い題名。

### `date`
作成日。

### `owner`
主担当。通常は `codex`。

### `target_program`
対象のプログラム名や案件名。

### `scope`

- `status`: `confirmed` / `uncertain` / `blocked`
- `notes`: スコープ上の注意点

### `repos`

各リポの扱い。

- `allowed`
- `reference_only`
- `test_only`
- `blocked`
- `scope_unknown`

### `ai_roles`
どの AI がどの役割を担うか。

### `hypothesis`
検証したい仮説の一覧。

### `constraints`
安全制約。

### `evidence`
証跡の置き場。

### `status`

- `planned`
- `in_progress`
- `waiting_review`
- `completed`
- `blocked`

### `next_action`
次にやるべき最小アクション。

### `human_review_required`
人間確認が必要か。

---

## 5. 状態遷移

```text
planned
  -> scope_gate
  -> in_progress
  -> waiting_review
  -> completed

planned
  -> blocked
  -> waiting_review
```

ルール:

- `scope` が `blocked` なら `status` は進めない
- `human_review_required=true` のときは、報告前に必ず確認する
- 証跡不足なら `waiting_review`

---

## 6. サンプル: 既存リポ確認タスク

```yaml
task_id: wh-2026-002
title: Compare existing red-team assets
date: "2026-06-10"
owner: codex
target_program: local-lab

scope:
  status: confirmed
  notes: Use only local repos already present under /home/mayutama

repos:
  - name: cpos_defensive_agent
    role: allowed
  - name: ai-red-teaming-engine
    role: reference_only
  - name: ai-instruction-tape
    role: reference_only
  - name: claude-code-security-kit
    role: reference_only

ai_roles:
  coordinator: codex
  broad_survey: gemini
  deep_review: claude
  local_validation: codex
  report_polish: codex

hypothesis:
  - Some templates can be shared across repos
  - Some review gates can be normalized
  - Some evidence formats can be unified

constraints:
  no_secrets: true
  no_production_data: true
  no_destructive_actions: true
  minimal_reproduction: true

evidence:
  logs: []
  screenshots: []
  paths: []
  commits: []

status: planned
next_action: repo_comparison
human_review_required: false
```

---

## 7. サンプル: 最小再現タスク

```yaml
task_id: wh-2026-003
title: Minimal repro for suspected authz gap
date: "2026-06-10"
owner: codex
target_program: approved-bounty

scope:
  status: confirmed
  notes: Repro only within approved endpoints

repos:
  - name: target-repo
    role: allowed
  - name: internal-reference-repo
    role: reference_only

ai_roles:
  coordinator: codex
  broad_survey: gemini
  deep_review: claude
  local_validation: codex
  report_polish: codex

hypothesis:
  - A handler may miss a permission check on one branch

constraints:
  no_secrets: true
  no_production_data: true
  no_destructive_actions: true
  minimal_reproduction: true

evidence:
  logs: []
  screenshots: []
  paths: []
  commits: []

status: planned
next_action: minimal_reproduction
human_review_required: true
```

---

## 8. 運用メモ

- まず JSON か YAML のどちらかに統一する
- 1 finding = 1 task に分ける
- `evidence` は後から埋める
- `allowed` と `reference_only` を混ぜない
- 人間レビューが必要なものは `human_review_required: true`

