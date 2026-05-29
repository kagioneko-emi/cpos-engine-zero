# NEXT HANDOFF

## Current state

- Project: `cpos_defensive_agent`
- Added `cpos/pointer_os.py`, a lightweight Context Pointer OS implementation.
- Added `cpos/pointer_cli.py`, a command-line interface for listing, retrieving, invalidating, updating trust, and exchanging pointers.
- Added Flask pointer endpoints in `server.py`: `GET /pointers`, `GET /pointers/<pointer_id>`, `POST /pointers/<pointer_id>/invalidate`, `POST /pointers/<pointer_id>/trust-update`, `POST /pointers/<pointer_id>/exchange`.
- Added CPOS pointer dashboard rendering and pointer governance event rendering in `generate_report.py`; regenerated `hackathon_report.html`.
- Added `cpos/__init__.py` exports.
- `MainAgent.update_pointer()` now writes static-analysis findings as CPOS-compatible `ContextPointer` records instead of the old minimal `{file, line, rule_id}` shape.
- Old pointer rows are still readable through `ContextPointer.from_dict()` for backward compatibility.

## Implemented CPOS pieces

- Pointer lifecycle fields: `active`, `stale`, `archived`, `invalidated`, `deleted`
- Context invalidation with reason validation
- Retrieval governance via `RetrievalPolicy`
- Trust score update history
- Multi-agent pointer exchange audit event
- JSONL pointer store and audit logging
- Context retrieval with access count / last accessed updates
- Pointer CLI: `list`, `retrieve`, `invalidate`, `trust-update`, `exchange`
- Pointer HTTP API for demo/dashboard integration, including trust updates and pointer exchange
- Pointer dashboard section in generated hackathon report
- Pointer governance event section for `trust_score_updated` and `pointer_exchanged` audit events
- Context Reconstructor line-window retrieval for `file.py:line` pointer locations
- Task Tape / rollback core in `cpos/task_tape.py`
- Task Tape CLI in `cpos/task_cli.py`: `summary`, `events`, `checkpoints`, `rollback-latest`
- Task Tape HTTPS-facing API in `server.py`: `GET /tasks`, `GET /tasks/events`, `GET /tasks/checkpoints`, guarded `POST /tasks/rollback-latest`
- Autonomous fix flow records task events and creates pre-write checkpoints
- Autonomous fixes are approval-gated by default: `review_required` before file write, then approve/reject APIs
- Optional HTTPS enforcement via `CPOS_ENFORCE_HTTPS=true` and `X-Forwarded-Proto=https`
- Optional bearer-token API authentication via `CPOS_REQUIRE_API_AUTH=true` and `CPOS_API_BEARER_TOKEN_FILE`; token must come from Vault/secret volume, not code or `.env`
- Optional route-level scopes via `CPOS_API_BEARER_TOKEN_SCOPES_FILE`: `read:pointers`, `write:pointers`, `read:tasks`, `read:reviews`, `write:reviews`, `write:rollback`, `webhook:github`, `read:integrity`, plus wildcards
- Security Audit Trail in `cpos/security_audit.py` / default `cpos/security_audit.jsonl`, recording auth decisions and successful security-sensitive mutations without tokens/request bodies
- Generated report includes Security Audit Trail summary and recent events
- Tamper-evident hash chaining in `cpos/hash_chain.py` for task events/checkpoints, pointer audit, and security audit; `GET /integrity` verifies ledgers
- Optional HMAC-signed request auth with nonce/timestamp replay protection via `CPOS_REQUIRE_HMAC_AUTH=true`, `CPOS_API_HMAC_SECRET_FILE`, `CPOS_API_NONCE_STORE_PATH`, `CPOS_HMAC_TIMESTAMP_WINDOW_SECONDS`
- Optional HMAC key registry / rotation in `cpos/key_registry.py` via `CPOS_API_HMAC_KEY_REGISTRY_FILE` and `X-CPOS-Key-Id`; supports `active`, `deprecated`, revoked rejection, validity windows, and key-scoped permissions
- HMAC client helper CLI in `cpos/auth_cli.py`: `python3 -m cpos.auth_cli sign ...` prints signed headers without printing secrets
- Python signed API wrapper in `cpos/api_client.py`: `CPOSClient("https://host", registry_file=..., key_id=...).get_json/post_json(...)`
- Network policy middleware: IP allowlist via `CPOS_IP_ALLOWLIST`/`CPOS_TRUST_PROXY_HEADERS`; in-memory rate limiting via `cpos/rate_limit.py`, `CPOS_RATE_LIMIT_ENABLED`, `CPOS_RATE_LIMIT_REQUESTS`, `CPOS_MUTATION_RATE_LIMIT_REQUESTS`
- mTLS/reverse-proxy client certificate fingerprint gate via `CPOS_REQUIRE_CLIENT_CERT`, `CPOS_CLIENT_CERT_FINGERPRINTS_FILE`, `CPOS_CLIENT_CERT_FINGERPRINT_HEADER`, `CPOS_CLIENT_CERT_POLICY_MODE=enforce|audit`
- Sandbox Policy Modes in `sandbox/runner.py`: `CPOS_SANDBOX_MODE=strict|permissive|local-dev`; hardened Docker flags and fail-closed strict mode
- Security Profile Presets in `cpos/security_profile.py`: `CPOS_SECURITY_PROFILE=dev|audit|hardened`; defaults only, explicit env overrides preserved; `GET /security-profile` introspection
- Hardened profile validation in `cpos/security_validation.py`; `/security-profile` reports missing HMAC/client-cert files, Docker availability, HTTPS/auth/rate-limit/sandbox posture
- Security profile validation is displayed in `templates/dashboard.html` and `hackathon_report.html` via `generate_report.py`
- Preflight check CLI in `cpos/preflight.py`: `python3 -m cpos.preflight --profile hardened [--json]`, validates profile posture, Docker, HMAC registry, secret files, client-cert file
- Hardened deployment template bundle in `deploy/hardened/`: env example, HMAC key registry shape, client fingerprint example, systemd unit example, nginx mTLS reverse proxy example; no real secrets or service installation
- Vault render helper in `cpos/vault_render.py` plus `deploy/hardened/vault-render-secrets.example.sh` and manifest example; writes 0600 files, no secret values in output, supports dry-run
- Secret scan CLI in `cpos/secret_scan.py`, reports pattern/path/line without matched values
- Non-active CI/preflight workflow template at `deploy/hardened/github-actions/cpos-hardened-preflight.example.yml`; runs secret scan, Vault dry-run, hardened preflight, tests, report generation
- Vault migration docs/checklists: `deploy/hardened/VAULT_MIGRATION_GUIDE.md` and `SECRET_ARTIFACT_INVENTORY.md`; non-destructive, no secret values, emphasizes approval before cleanup
- Secret inventory metadata CLI in `cpos/secret_inventory.py`; hash-chained JSONL metadata only, supports add/mark/list/verify without storing secret values
- Secret inventory migration status is visible in `/security-profile`, dashboard, and generated report; path override via `CPOS_SECRET_INVENTORY_PATH`
- Multi-agent handoff export in `cpos/handoff_export.py`: `python3 -m cpos.handoff_export --format json|markdown`; sanitized bundle excludes secrets, checkpoint contents, request bodies, and proposed code while including security profile, integrity, Pointer OS, Task Tape, Secret Inventory, and NEXT_HANDOFF summaries.
- Signed/importable handoff receiver in `cpos/handoff_receiver.py`: sign/verify/import sanitized JSON bundles using HMAC secrets from secret files or key registry; import is dry-run unless `--apply`, requires valid safety flags, can require signature, and writes one `handoff_summary` pointer with `retrieval_rule=handoff_review_required` instead of storing raw handoff contents.
- Handoff Inbox / Review Queue in `cpos/handoff_inbox.py` and HTTP routes: `GET /handoff-inbox`, `POST /handoff-inbox/<pointer_id>/approve`, `POST /handoff-inbox/<pointer_id>/reject`; uses `read:reviews`/`write:reviews`, approval changes retrieval rule to `handoff_approved`, rejection invalidates with `handoff_rejected`.
- Handoff Promotion Rules in `cpos/handoff_promotion.py` and HTTP routes: `GET /handoff-inbox/<pointer_id>/promotion-plan`, `POST /handoff-inbox/<pointer_id>/promote`; approved handoffs only, emits safe retrieval/task continuation plan, blocks raw handoff body/checkpoint contents/request bodies/secrets/unreviewed code, creates `handoff_promotion_plan` with `retrieval_rule=handoff_promotion_review_required`.
- Promotion Plan Executor in `cpos/promotion_executor.py` and HTTP routes: `POST /handoff-inbox/<promotion_pointer_id>/execute-plan`, `GET /handoff-executions`, `POST /handoff-executions/<task_id>/approve|reject`; creates fresh Task Tape `review_required` events with `review_type=handoff_promotion_execution`, keeps fix-review queue separate, approval only marks `handoff_promotion_execution_ready` and does not execute code/import raw context.
- Execution Resume Planner in `cpos/resume_planner.py` and HTTP routes: `GET /handoff-executions/<task_id>/resume-plan`, `POST /handoff-executions/<task_id>/create-resume-review`, `GET /resume-reviews`, `POST /resume-reviews/<task_id>/approve|reject`; creates metadata-only scoped next-action proposals, review-gated, approval appends `resume_action_ready`, `execute_automatically=false`.
- Lightweight Footprint Metrics in `cpos/footprint.py` and `GET /footprint`; dashboard/report show pointer/task JSONL size, counts, and safety flags (`secrets_included=false`, raw handoff/checkpoint contents excluded) to demonstrate low LLM context footprint.
- Handoff Flow Graph in `cpos/handoff_graph.py` and `GET /handoff-graph[?source_pointer_id=...]`; metadata-only link view from `handoff_summary` → promotion plan → execution review → resume review → ready events, rendered in dashboard without exposing raw handoff/checkpoint/secret contents.
- Persistent rate-limit backend in `cpos/rate_limit.py`: `FileBackedRateLimiter` plus `CPOS_RATE_LIMIT_BACKEND=file` and `CPOS_RATE_LIMIT_STORE_PATH`; single-host multi-process workers share sliding-window buckets via locked JSON file, storing timestamps only and no tokens/request bodies/secrets.
- Rate-limit backend visibility: `/security-profile` now includes active backend; dashboard shows off/memory/file/redis state and file path/config status.
- Optional Redis/Valkey rate-limit hook in `cpos/rate_limit.py`: `RedisRateLimiter` uses optional redis-py when available, configured via Vault-rendered `CPOS_RATE_LIMIT_REDIS_URL_FILE`; missing URL file fails closed with `rate_limit_redis_url_not_configured`.
- Redis/Valkey rate-limit deployment docs in `deploy/hardened/REDIS_RATE_LIMIT_GUIDE.md`; preflight validates `CPOS_RATE_LIMIT_REDIS_URL_FILE` exists/non-empty and checks optional `redis` Python dependency without printing URL secret values.
- Handoff Graph filters: `GET /handoff-graph?review_status=approved&source_pointer_id=...&limit=...`; dashboard includes status/source filters.
- Generated report includes Tamper-evident Integrity summary
- Generated report includes Task Tape summary and recent task events

- MCP Connector Registry / Governance added in `cpos/mcp_registry.py` and `cpos/mcp_cli.py`. It is text-first: connector JSON definitions are statically security-checked before registration; no MCP tool execution is performed yet. Remote connector URLs must be HTTPS, raw secret/env fields are rejected, `env_secret_files` is used for Vault-rendered secret files, allowed tools must be explicit, dangerous/private/restricted connectors require human approval, stdio shell wrappers/metacharacters are blocked, and MCP audit is hash-chained.
- MCP HTTP APIs added in `server.py`: `POST /mcp/connectors/check`, `GET/POST /mcp/connectors`, `POST /mcp/connectors/<connector_id>/disable`, `POST /mcp/connectors/<connector_id>/check-tool`. Scopes: `read:mcp` for GET, `write:mcp` for mutations/checks. `/integrity` now includes `mcp_audit`.

- MCP Review UI/report added. Dashboard now has an `MCP Connectors` card and `MCP Connector Review` section showing registered connectors, active/approval-gated counts, allowed/blocked tools, secret-file reference posture, plus metadata-only `check-tool` and `disable` actions. Generated reports now include `MCP Connector Registry` with audit-chain status. This remains governance-only: no MCP server launch or MCP tool execution.

- MCP Connector Import/Review Queue added. Safe definitions can be submitted via CLI/API into `mcp_reviews.jsonl`; failed static security checks are rejected and not stored. Pending reviews are visible in Dashboard and reports. Approval requires `confirm=true` and registers the connector; rejection records reason. Review queue is hash-chained and `/integrity` includes `mcp_reviews`.

- MCP Execution Adapter dry-run/metadata-only mode added in `cpos/mcp_execution.py`. API routes: `GET /mcp/executions`, `POST /mcp/executions/dry-run`, `POST /mcp/executions/<task_id>/approve|reject`. It checks connector status, allowlist/blocklist, secret-like argument keys, and approval requirements. It never launches MCP servers, never executes tools, never stores raw argument values; Task Tape stores only args hash/size/top-level keys. Dashboard/report now show pending MCP execution reviews. Approval is dry-run-only and still `tool_executed=false`.

- MCP Capability Probe Harness dry-run/metadata-only added in `cpos/mcp_probe.py` with API routes `GET /mcp/probes`, `POST /mcp/probes/dry-run`, `POST /mcp/probes/<task_id>/approve|reject`. It creates approval-gated probe plans only: no server start, no network request, no tool call, no secret file read.
- GitHub PR Dry-run Workflow added in `cpos/github_pr_flow.py` with API routes `GET /github/pr-dry-runs`, `POST /github/pr-dry-runs`, `POST /github/pr-dry-runs/<task_id>/approve|reject`. It creates approval-gated issue-to-PR metadata plans only: no branch creation, no commits, no push, no GitHub PR creation, no raw summary storage; dashboard/report show pending plans.
- OSS release prep added: `.gitignore`, `LICENSE` (MIT), `SECURITY.md`, `CONTRIBUTING.md`, `OSS_RELEASE_CHECKLIST.md`, and README OSS positioning. Test/source dummy secret fixtures were changed to avoid source-tree secret-scan false positives while preserving runtime scan tests.

- OSS publish cleanup started: `.venv`, pycache, workspace demos, runtime JSONL ledgers, certs, and generated `hackathon_report.html` were removed from Git index with `git rm --cached` only; files remain on disk. `.gitignore` now excludes them. `git ls-files` check for tracked bad artifacts returns none.
- Added `RELEASE_NOTES_v0.1.0.md`. Validation after cleanup: `181 passed`; secret scan `ok=true count=0`. Current status after GitHub PR dry-run work: source/docs/tests modified locally; run `git status --short`, secret scan, commit, and push when ready.

## Verification

```bash
.venv/bin/python -m py_compile generate_report.py server.py cpos/pointer_os.py cpos/pointer_cli.py agents/main_agent.py
.venv/bin/python -m pytest tests -q
# 181 passed
.venv/bin/python generate_report.py
```

## Suggested next step

Next: do a staged GitHub OSS publish pass: review git status, stage only source/docs/tests (no runtime artifacts), run secret scan, then create initial public repo/release notes. HTTPS enforcement, mTLS fingerprint gate, approval gating, bearer-token/HMAC auth, route-level scopes, Security Audit Trail, tamper-evident hash chaining, replay protection, key rotation, HMAC helpers, Python API client, IP allowlist, rate limiting, sandbox policy modes, security profile presets, hardened validation, dashboard/report visibility, preflight CLI, hardened deployment templates, Vault render helper, secret scan, CI/preflight template, Vault migration docs, secret inventory CLI, and secret inventory dashboard/report view are implemented.
