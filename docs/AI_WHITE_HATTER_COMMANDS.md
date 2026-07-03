# AI White-Hatter Command Set

このコマンド集は、`AI_WHITE_HATTER_SYSTEM_SPEC.md` と
`AI_WHITE_HATTER_TASK_SCHEMA.md` を実際に回すためのもの。

前提:

- `/home/mayutama/cpos_defensive_agent` を基幹として使う
- 秘密情報はコマンドに直書きしない
- 破壊的操作は事前確認
- スコープ外は触らない
- 最終判断は人間

---

## 0. 共通の起動方針

```bash
cd /home/mayutama/cpos_defensive_agent
PYTHONPATH=. .venv/bin/python ...
```

---

## 1. まず確認するコマンド

### 1-1. 現在の状態を読む

```bash
PYTHONPATH=. .venv/bin/python -m cpos.world_model snapshot --json
```

補足:

- `--include-resume-pointer` で復帰用ポインタを付ける
- `--goal-store goals/goals.example.json` で目標ストアを含める

### 1-2. 目標一覧を読む

```bash
PYTHONPATH=. .venv/bin/python -m cpos.goals list --json
```

### 1-3. 目標ストアを検証する

```bash
PYTHONPATH=. .venv/bin/python -m cpos.goal_store validate --path goals/goals.example.json --json
```

### 1-4. 目標ストア要約を読む

```bash
PYTHONPATH=. .venv/bin/python -m cpos.goal_store summary --path goals/goals.example.json --json
```

---

## 2. 既存資産を読むコマンド

### 2-1. リポ構成を確認する

```bash
find . -maxdepth 2 -type f | sort
```

### 2-2. 対象ファイルをざっと読む

```bash
sed -n '1,220p' README.md
sed -n '1,220p' docs/AI_WHITE_HATTER_SYSTEM_SPEC.md
sed -n '1,220p' docs/AI_WHITE_HATTER_OPERATION_TEMPLATES.md
sed -n '1,260p' docs/AI_WHITE_HATTER_TASK_SCHEMA.md
```

### 2-3. 既存の安全ガイドを確認する

```bash
sed -n '1,220p' docs/HUMAN_ESCALATION_PROTOCOL.md
sed -n '1,220p' docs/AGENT_ADAPTER_INTEGRATION.md
sed -n '1,220p' SECURITY.md
```

---

## 3. 比較・調査コマンド

### 3-1. リポ比較の候補を探す

```bash
rg -n "red team|review|security|tape|scope|human escalation|adapter" .
```

### 3-2. テンプレ差分を見る

```bash
diff -u docs/AI_WHITE_HATTER_OPERATION_TEMPLATES.md docs/AI_WHITE_HATTER_TASK_SCHEMA.md
```

### 3-3. 既存の安全系コードを読む

```bash
rg -n "Human Escalation|metadata_only|raw_diff_stored|raw_outputs_stored|blocked|reference_only" cpos docs
```

---

## 4. 検証コマンド

### 4-1. ルール評価を回す

```bash
PYTHONPATH=. .venv/bin/python -m cpos.reflection_evaluator evaluate --json
```

### 4-2. リジュームパイプラインを読む

```bash
PYTHONPATH=. .venv/bin/python -m cpos.resume_pipeline run --goal-store goals/goals.example.json --json
```

補足:

- `--compact` で小さくする
- `--scan-compact` で secret-pattern gate を付ける

### 4-3. ポインタを作る

```bash
PYTHONPATH=. .venv/bin/python -m cpos.resume_pointer build --goal-store goals/goals.example.json --json
```

### 4-4. ポインタ検証

```bash
PYTHONPATH=. .venv/bin/python -m cpos.resume_pointer validate --pointer-json pointer.json --json
```

### 4-5. 書き込み計画を読む

```bash
PYTHONPATH=. .venv/bin/python -m cpos.resume_pointer write-plan --pointer-json pointer.json --json
```

---

## 5. タスク/アダプタ系コマンド

### 5-1. 受け口のレビューを読む

```bash
curl -sS http://127.0.0.1:8080/agent-adapter/actions
curl -sS http://127.0.0.1:8080/agent-adapter/execution-results
curl -sS http://127.0.0.1:8080/human-escalations
```

### 5-2. メタデータだけの契約を送る

```bash
curl -sS -X POST http://127.0.0.1:8080/agent-adapter/intake \
  -H 'Content-Type: application/json' \
  --data @examples/payloads/command_request.json
```

### 5-3. メタデータだけの結果を送る

```bash
curl -sS -X POST http://127.0.0.1:8080/agent-adapter/intake \
  -H 'Content-Type: application/json' \
  --data @examples/payloads/execution_result.json
```

---

## 6. デモ・確認コマンド

### 6-1. デモ fixture を作る

```bash
curl -X POST https://<host>/demo/fixture -d '{"confirm":true,"reason":"demo_capture"}'
```

### 6-2. デモ readiness を読む

```bash
curl https://<host>/demo/readiness
```

---

## 7. レポート・出力系コマンド

### 7-1. Notion dry-run

```bash
PYTHONPATH=. .venv/bin/python -m cpos.notion_vault_client page \
  --source docs/NOTION_RESUME_PIPELINE_SUMMARY_2026_06_07.md \
  --title "Cognitive Agent OS / CPOS Resume Pipeline まとめ" \
  --json
```

### 7-2. Zenn-to-Notion dry-run

```bash
PYTHONPATH=. .venv/bin/python -m cpos.notion_zenn_bridge bridge \
  --article /home/mayutama/zenn/articles/cognitive-agent-os-safety-kernel.md \
  --json
```

---

## 8. AIホワイトハッター用の最小コマンド列

### フローA: まず比較する

```bash
cd /home/mayutama/cpos_defensive_agent
PYTHONPATH=. .venv/bin/python -m cpos.world_model snapshot --json
rg -n "red team|review|security|tape|scope" .
sed -n '1,220p' docs/AI_WHITE_HATTER_SYSTEM_SPEC.md
sed -n '1,260p' docs/AI_WHITE_HATTER_TASK_SCHEMA.md
```

### フローB: 目標ストア付きで進める

```bash
cd /home/mayutama/cpos_defensive_agent
PYTHONPATH=. .venv/bin/python -m cpos.goal_store validate --path goals/goals.example.json --json
PYTHONPATH=. .venv/bin/python -m cpos.resume_pipeline run --goal-store goals/goals.example.json --json
PYTHONPATH=. .venv/bin/python -m cpos.resume_pointer build --goal-store goals/goals.example.json --json
```

### フローC: レビュー結果を確認する

```bash
curl -sS http://127.0.0.1:8080/agent-adapter/actions
curl -sS http://127.0.0.1:8080/human-escalations
curl -sS http://127.0.0.1:8080/agent-adapter/execution-results
```

---

## 9. 使わないもの

- secrets の直書き
- `.env` のべた書き
- `rm -rf` の無確認実行
- `git push --force`
- `authorized_keys` の変更
- スコープ外のアクセス

---

## 10. 迷ったときの優先順位

1. Scope確認
2. 既存資産確認
3. 比較
4. 最小再現
5. 証跡整理
6. 人間確認

