# Cognitive Agent OS / CPOS Resume Pipeline まとめ

作成日: 2026-06-07

## 一言まとめ

CPOS Engine-Zero は、AIエージェントをいきなり完全自律させるのではなく、観測・内省・提案・人間確認・安全な引き継ぎを回すための安全カーネルです。

今回の中心は **fast resume without raw logs** です。

長いログや危険な生データを次回へ持ち越すのではなく、現在地と次の安全な一歩だけを metadata-only なポインタに圧縮します。

## 何がつながったか

今回の Resume Pipeline では、以下の安全チェーンがつながりました。

```text
World Model
→ Reflection Evaluator
→ Resume Pointer
→ Resume Pointer Validation
→ tape-memory write-plan dry-run
→ compact payload secret scan
```

## それぞれの役割

### 1. World Model

現在のrepo状態、リスク、Goal Store validation、既知の注意点を metadata-only snapshot にします。

### 2. Reflection Evaluator

提案された行動を `proceed / ask / defer / block` で評価します。

公開・push・release・tag・秘密情報・raw DB・Android/phone data・authorized_keys などは安全境界として扱います。

### 3. Resume Pointer

次回復帰に必要な情報だけを短く持つポインタです。

含めるもの:

- repo / commit
- world model risk
- known risk names
- goal validation summary
- reflection recommendation
- safe handoff digest

含めないもの:

- raw logs
- raw diffs
- request bodies
- full handoff bodies
- DB rows
- Android/phone data
- private repo content
- secrets

### 4. Resume Pointer Validation

Resume Pointer が metadata-only / no-execute / stdout-only / no-write の安全条件を満たすか検査します。

### 5. tape-memory write-plan dry-run

将来 tape-memory に書くならどうするかを plan として作ります。

ただし現在は必ず以下の状態です。

```text
dry_run = true
would_write = false
write_enabled = false
```

### 6. compact payload secret scan

compact output に秘密情報らしきパターンが混ざっていないか検査します。

出すのは pattern 名と件数だけで、値そのものは出しません。

## 代表コマンド

```bash
PYTHONPATH=. .venv/bin/python -m cpos.resume_pipeline run \
  --goal-store goals/goals.example.json \
  --scan-compact \
  --json
```

## 現在の安全状態

- read-only
- metadata-only
- tape-memory real write disabled
- no automatic commit / push / tag / release / publish
- human confirmation required for future memory write path
- secret scan required before any future write

## Zenn記事

Zenn draft `cognitive-agent-os-safety-kernel.md` に “Fast resume without raw logs” の節を追加済みです。

状態は `published: false` のままです。

## 次にやるなら

1. Zenn公開前レビュー
   - 公開は明示確認までしない。
2. v0.1.2 readiness確認
   - `docs/V0_1_2_RESUME_PIPELINE_SUMMARY.md` を基準に確認。
3. tape-memory real write設計
   - 実writeは、明示確認・secret scan・dry-run検証の後。
4. 外部エージェント向けdocs
   - compact pipeline JSONをどう読むかを説明する。

## 注意メモ

古いNotion系スクリプトに認証情報の直書き形跡があったため、使用禁止。Notion連携は必ずVaultから `secret/notion` を取得する方式にすること。

該当する認証情報は revoke / rotate 推奨。
