# AI White-Hatter Operation Templates

このファイルは `AI_WHITE_HATTER_SYSTEM_SPEC.md` の運用テンプレ集。
バグバウンティや許可済み検証環境で、そのままコピペして使う前提。

---

## 1. タスクメモ

```md
# Task Memo

- Date:
- Owner:
- Target program:
- Scope:
- Allowed repos:
- Forbidden actions:
- Goal:

## AI roles

- Codex:
- Gemini:
- Claude Code:

## Inputs

- Target repo:
- Reference repo(s):
- Logs:
- Screenshots:
- Notes:

## Output

- Findings:
- Reproduction:
- Evidence:
- Report draft:

## Safety

- Scope checked: yes / no
- Secrets involved: yes / no
- Destructive actions needed: yes / no
- Human approval required: yes / no
```

---

## 2. リポ比較表

```md
# Repo Comparison

| Item | Target | Reference | Difference | Impact | Repro? |
|------|--------|-----------|------------|--------|--------|
| Auth |        |           |            |        |        |
| Input validation | | | | | |
| Authorization | | | | | |
| File handling | | | | | |
| Error handling | | | | | |
| Session/state | | | | | |
| API behavior | | | | | |
| Logging | | | | | |

## Notes

- Shared patterns:
- Unique patterns:
- Candidate findings:
- Reuse opportunities:
```

---

## 3. 証跡テンプレ

```md
# Finding

- Title:
- Severity:
- Scope:
- Repo(s):
- AI roles:
- Date observed:

## Hypothesis

Describe the suspected issue in one or two sentences.

## Reproduction

1. Step one
2. Step two
3. Step three

## Expected

What should have happened.

## Actual

What happened instead.

## Evidence

- Logs:
- Screenshots:
- File paths:
- Commit/diff refs:

## Impact

Explain the practical effect in one short paragraph.

## Notes

- False-positive checks:
- Remaining uncertainty:
- Follow-up:
```

---

## 4. Scope Gate チェックリスト

```md
# Scope Gate

- [ ] Program scope confirmed
- [ ] Target asset is allowed
- [ ] Reference repo is allowed
- [ ] No production data will be stored
- [ ] No secrets will be logged
- [ ] No destructive action planned
- [ ] No rate-limit abuse planned
- [ ] Reproduction will be minimal
- [ ] Human approval required items identified
- [ ] Reporting path confirmed
```

---

## 5. AI 役割割り当てテンプレ

```md
# AI Assignment

- Coordinator: Codex
- Broad survey: Gemini
- Deep code review: Claude Code
- Local validation: Codex
- Report polishing: Codex

## Task split

### Gemini

- Collect broad hypotheses
- Summarize related docs
- List similar patterns

### Claude Code

- Trace code paths
- Inspect diffs
- Identify exact control flow

### Codex

- Run local checks
- Collect evidence
- Keep notes and templates
- Produce final draft
```

---

## 6. 最小再現プロンプト

```md
# Minimal Repro Prompt

You are working only within the approved scope.
Use the allowed repos and reference repos listed below.
Do not access secrets, production data, or forbidden assets.
Do not perform destructive actions.
Aim for the smallest reproducible test that proves or disproves the hypothesis.

Target:
- 

Allowed repos:
- 

Reference repos:
- 

Hypothesis:
- 

Needed output:
- concise reproduction steps
- evidence checklist
- report-ready summary
```

---

## 7. 報告ドラフト雛形

```md
# Report Draft

## Summary

## Scope

## Finding

## Impact

## Reproduction

## Evidence

## Suggested Fix

## Notes
```

---

## 8. 推奨運用順

1. Scope Gate
2. 既存リポ確認
3. リポ比較
4. 仮説化
5. 最小再現
6. 証跡整理
7. 報告ドラフト
8. 人間レビュー

---

## 9. 使い方メモ

- まず `Scope Gate` を埋める
- 次に `Repo Comparison` で比較する
- `Finding` は1件ずつ分ける
- 証跡は最小限にする
- 最後は人間が確認する

