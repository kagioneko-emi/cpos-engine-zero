# CPOS Engine-Zero (DevOps x AI Agent Hackathon 2026 Edition)

## Overview
CPOS Engine-Zero は、DevOps サイクルにおける「Run (まわす)」を自動化する、自律型安定性確保エージェントです。
Google Cloud (Gemini) と CPOS (Context Pointer OS) の設計思想を融合し、脆弱性やバグの検出から、AI による修正案の生成、そして Sandbox での検証までを完全自動で行います。

## Key Features
- **Autonomous Self-Healing**: Gemini CLI を活用し、検出された問題に対して最適な修正コードを自律的に生成・適用します。
- **Context Pointers (#ctx)**: ファイル間の依存関係や過去の失敗パターンをポインタとして管理し、LLM に最適な文脈を提供します。
- **Audit & Sandbox**: すべての修正は Docker Sandbox 内で検証され、安定性が確認されたコードのみが最終的なアウトプットとなります。
- **Visual DevOps Dashboard**: 解析と修正のプロセスを可視化する HTML レポートを自動生成します。

## Directory Structure
- `agents/`:
    - `main_agent.py`: オーケストレーター。
    - `architect_gemini.py`: Gemini を使った自律修正エンジン。
    - `subagent_python.py`: ルールベースの解析エンジン。
- `sandbox/`: Docker による安全な検証環境。
- `memory/`: 過去のミスパターン (`mistakes.jsonl`)。
- `cpos/`: 監査ログとコンテキストポインタ。

## Usage
1. 依存関係のインストール:
   ```bash
   # Gemini CLI がインストール・認証済みであること
   gemini auth login
   ```

2. 自律修正の実行:
   ```bash
   export PYTHONPATH=.
   python3 agents/main_agent.py workspace/test_app.py --fix
   ```

3. レポートの生成:
   ```bash
   python3 generate_report.py
   ```

## Evaluation Points (Hackathon Criteria)
- **AI Agent Centrality**: Gemini が単なるチャットではなく、コードの書き換えと検証という「判断と実行」の核となっています。
- **Practicality**: CI/CD パイプラインに組み込むことで、人間が介在せずにコードの品質を維持できます。
- **Implementation Power**: Docker による分離、ポインタによる文脈管理など、実運用に耐えうる設計を行っています。

## Context Pointer OS Layer

`cpos/pointer_os.py` implements the lightweight Context Pointer OS layer used by the agent.

Core objects:
- `ContextPointer`: lightweight reference to context, not the full memory body.
- `PointerManager`: JSONL-backed pointer lifecycle manager.
- `RetrievalPolicy`: retrieval governance for context type, sensitivity, trust, and status.

Minimal API:
```python
from cpos.pointer_os import PointerManager, RetrievalPolicy

manager = PointerManager("cpos/pointers.jsonl", "cpos/audit_log.jsonl")
pointer = manager.create_pointer(
    context_type="code",
    summary="test_app source",
    source="repo",
    location="workspace/test_app.py",
    priority=0.8,
    trust_score=0.9,
)
context = manager.retrieve_context(
    pointer.pointer_id,
    agent_id="CodingAgent",
    purpose="fix_generation",
    policy=RetrievalPolicy(allowed_context_types=["code"], minimum_trust_score=0.7),
)
```

`MainAgent.update_pointer()` now writes static-analysis findings as CPOS-compatible pointers with lifecycle fields, trust score, priority, sensitivity, retrieval rule, and metadata. The manager still reads the old `{file, line, rule_id}` pointer shape for backward compatibility.

### Pointer CLI

The pointer layer can be inspected and operated without importing Python internals:

```bash
python3 -m cpos.pointer_cli list --json
python3 -m cpos.pointer_cli retrieve 'ptr://...' --json
python3 -m cpos.pointer_cli trust-update 'ptr://...' --score 0.95 --reason user_confirmed --json
python3 -m cpos.pointer_cli exchange 'ptr://...' --from-agent CodingAgent --to-agent AuditAgent --purpose audit_required --json
python3 -m cpos.pointer_cli invalidate 'ptr://...' --reason outdated --json
```

The CLI uses `cpos/pointers.jsonl` and `cpos/audit_log.jsonl` by default. Use `--pointer-path` and `--audit-path` before the subcommand to point at another store.

### Pointer HTTPS API

The Flask server exposes read/inspection endpoints for the pointer layer:

```http
GET https://<host>/pointers
GET https://<host>/pointers?context_type=finding&query=eval&limit=5
GET https://<host>/pointers/<url-encoded-pointer-id>
POST https://<host>/pointers/<url-encoded-pointer-id>/invalidate
```

Invalidate body:
```json
{
  "reason": "outdated",
  "replacement_pointer": null
}
```

Pointer ids such as `ptr://finding/python/...` contain `/`, so clients should URL-encode the id before placing it in the path.

### Pointer Dashboard Section

`generate_report.py` now renders a Context Pointer OS section in `hackathon_report.html`:

- total pointer count
- active / invalidated lifecycle counts
- average trust score
- context type distribution
- top finding pointers with pointer id, status, trust, priority, and location
- recent invalidations

Regenerate it with:

```bash
python3 generate_report.py
```

Pointer governance actions are also exposed through HTTP:

```http
POST /pointers/<url-encoded-pointer-id>/trust-update
POST /pointers/<url-encoded-pointer-id>/exchange
```

Trust update body:
```json
{
  "score": 0.95,
  "reason": "user_confirmed"
}
```

Exchange body:
```json
{
  "from_agent": "CodingAgent",
  "to_agent": "AuditAgent",
  "purpose": "audit_required",
  "access_level": "internal"
}
```

The report also renders recent pointer governance audit events:

- `trust_score_updated`
- `pointer_exchanged`

These appear under **Pointer Governance Events** in `hackathon_report.html`.

### Context Reconstructor

`PointerManager.retrieve_context()` reconstructs pointer context before returning it.

For plain file locations, it returns the full file as `context` / `snippet` with `reconstruction.mode = "full_file"`.

For line locations such as `workspace/app.py:12`, it returns a compact line window:

```json
{
  "context": "...same as snippet...",
  "snippet": "line 10\nline 11\nline 12\nline 13\nline 14\n",
  "line_start": 10,
  "line_end": 14,
  "target_line": 12,
  "reconstruction": {
    "mode": "line_window",
    "window": 2
  }
}
```

This keeps retrieval closer to CPOS's goal: reconstruct only the context needed for the current task.

## Task Tape / Rollback

Autonomous fixes now write an append-only task tape and checkpoint before modifying files.

Files:
- `tapes/task_runs.jsonl`: append-only task events
- `tapes/task_checkpoints.jsonl`: pre-write checkpoints for rollback

CLI:
```bash
python3 -m cpos.task_cli summary --json
python3 -m cpos.task_cli events --json
python3 -m cpos.task_cli checkpoints --json
python3 -m cpos.task_cli rollback-latest --target workspace/app.py --json
```

`generate_report.py` renders a **Task Tape** section with task count, event count, checkpoint count, latest status, and recent task events.

### Task Tape HTTPS API

Task Tape can also be inspected and operated through Flask behind an HTTPS terminator:

```http
GET https://<host>/tasks
GET https://<host>/tasks/events?task_id=task_...
GET https://<host>/tasks/checkpoints?target=/path/to/file.py
POST https://<host>/tasks/rollback-latest
```

Rollback body requires explicit confirmation:
```json
{
  "target": "/path/to/file.py",
  "confirm": true
}
```

Checkpoint content is not returned by HTTP responses; only metadata and `content_size` are exposed.


## HTTPS and Review Gate Security

Production access must be served over HTTPS. The Flask app is protocol-agnostic and should sit behind Cloud Run, a load balancer, or a reverse proxy that terminates TLS.

Set this environment variable to reject non-HTTPS requests at the app layer when running behind a proxy that sends `X-Forwarded-Proto`:

```bash
export CPOS_ENFORCE_HTTPS=true
```

Autonomous fixes are approval-gated by default:

```bash
export CPOS_REQUIRE_FIX_APPROVAL=true
```

API endpoints can also be protected with a bearer token. Do **not** hardcode this token in code, `.env`, crontab, comments, or Git. Store the token in Vault and expose it at runtime as a restricted secret file/volume.

```bash
export CPOS_REQUIRE_API_AUTH=true
export CPOS_API_BEARER_TOKEN_FILE=/run/secrets/cpos_api_token
```

Example client request:

```bash
curl -H "Authorization: Bearer $(vault kv get -field=api_token secret/cpos/api)"   https://<host>/tasks
```

If `CPOS_REQUIRE_API_AUTH=true` is set but `CPOS_API_BEARER_TOKEN_FILE` is missing/unreadable, the API fails closed with `api_token_not_configured`.

For route-level authorization, provide a scopes file. The scopes file can be comma-separated or one scope per line:

```bash
export CPOS_API_BEARER_TOKEN_SCOPES_FILE=/run/secrets/cpos_api_scopes
```

Supported scopes:

| Scope | Allows |
| --- | --- |
| `read:pointers` | `GET /pointers...` |
| `write:pointers` | pointer invalidation, trust update, exchange |
| `read:tasks` | task summaries, events, checkpoints |
| `read:reviews` | pending review list |
| `write:reviews` | approve/reject generated fixes |
| `write:rollback` | rollback latest checkpoint |
| `webhook:github` | GitHub webhook endpoint |
| `read:integrity` | `GET /integrity` hash-chain verification |
| `read:*`, `write:*`, `*` | wildcard scopes |

If `CPOS_API_BEARER_TOKEN_SCOPES_FILE` is set but unreadable/empty, the API fails closed with `api_scopes_not_configured`.

Security-relevant API decisions are written to an append-only audit log without recording bearer tokens or request bodies:

```bash
export CPOS_SECURITY_AUDIT_PATH=/var/log/cpos/security_audit.jsonl
```

If unset, the default is `cpos/security_audit.jsonl` under the project root. Recorded events include auth decisions, scope denials, rollback execution, review approve/reject, and pointer mutations.

### HMAC-signed Requests / Replay Protection

Bearer token auth can be upgraded to per-request HMAC signatures. The shared secret must come from Vault/secret volume, not code or `.env`.

```bash
export CPOS_REQUIRE_API_AUTH=true
export CPOS_REQUIRE_HMAC_AUTH=true
export CPOS_API_HMAC_SECRET_FILE=/run/secrets/cpos_hmac_secret
export CPOS_API_SCOPES_FILE=/run/secrets/cpos_api_scopes
export CPOS_API_NONCE_STORE_PATH=/var/lib/cpos/nonce_seen.jsonl
export CPOS_HMAC_TIMESTAMP_WINDOW_SECONDS=300
```

Required request headers:

```http
X-CPOS-Timestamp: <unix seconds>
X-CPOS-Nonce: <unique nonce>
X-CPOS-Signature: <hex hmac-sha256>
X-Agent-Id: <client/agent id>
```

Signature message:

```txt
METHOD
PATH
QUERY_STRING
SHA256(body)
TIMESTAMP
NONCE
```

The server rejects missing signatures, invalid signatures, old timestamps, and reused nonces. Tokens/secrets/signatures are not written to audit logs.

For key rotation, configure a non-secret key registry. Each key points to a secret file populated from Vault/secret volume. The registry itself must not contain secret material.

```bash
export CPOS_API_HMAC_KEY_REGISTRY_FILE=/run/secrets/cpos_hmac_keys.json
```

Registry example:

```json
{
  "keys": {
    "2026-05-active": {
      "secret_file": "/run/secrets/cpos_hmac_2026_05",
      "status": "active",
      "scopes": ["read:tasks", "read:integrity"],
      "not_before": 1770000000,
      "not_after": 1800000000
    },
    "2026-04-old": {
      "secret_file": "/run/secrets/cpos_hmac_2026_04",
      "status": "deprecated",
      "scopes": ["read:tasks"]
    }
  }
}
```

Clients send the selected key id:

```http
X-CPOS-Key-Id: 2026-05-active
```

Supported key statuses: `active`, `deprecated` are allowed; `revoked` or any other status is rejected. Key-scoped permissions override the global scopes file when the registry is enabled.

Client helper CLI:

```bash
python3 -m cpos.auth_cli sign GET 'https://<host>/tasks?limit=1'   --registry-file /run/secrets/cpos_hmac_keys.json   --key-id 2026-05-active   --agent-id CodingAgent   --curl
```

For direct secret-file mode:

```bash
python3 -m cpos.auth_cli sign POST /tasks/rollback-latest   --secret-file /run/secrets/cpos_hmac_2026_05   --body-file /tmp/request.json   --json
```

The helper prints headers only; it does not print the secret.

### Tamper-evident Hash Chaining

Append-only ledgers now add a `_chain` envelope containing `prev_hash` and `row_hash` so rewrites, deletion, and reordering can be detected.

Chained ledgers:

- `tapes/task_runs.jsonl`
- `tapes/task_checkpoints.jsonl`
- `cpos/audit_log.jsonl`
- `cpos/security_audit.jsonl`

Integrity API:

```http
GET https://<host>/integrity
```

Requires `read:integrity` when API auth is enabled. Existing legacy rows are allowed as a prefix; all new rows are verified from the first chained row onward.

Generated fixes are recorded as `review_required` task tape events and are not written to disk until approved. Review APIs intentionally hide `proposed_code` from the review list and require explicit confirmation before writing.

```http
GET https://<host>/tasks/reviews
POST https://<host>/tasks/<task_id>/approve-fix
POST https://<host>/tasks/<task_id>/reject-fix
```

Approval body:
```json
{"confirm": true}
```
