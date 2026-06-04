## Start Here — 10-line Resume Card

1. `cd /home/mayutama/cpos_defensive_agent`
2. `git status --short --branch`
3. `PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json`
4. Expected state after this update is committed: `main...origin/main [ahead 4]`, clean tree, `prepublish_check ok=true`, secret scan `count=0`.
5. Correct remote: `origin https://github.com/kagioneko/cpos-engine-zero.git`
6. **Do not tag v0.1 yet** unlessねこさん explicitly says so.
7. Latest feature work: Ready-to-Run Execution Reviews helper for final human run gate after safe advance.
8. Fast resume cache: `TAPE_MEMORY_DIR=/home/mayutama/.tape-memory-mcp-cpos`, keys `cpos_resume_latest`, `cpos_safety_invariants`, `cpos_next_action`.
9. Safety invariant: raw diffs, raw outputs, request bodies, checkpoints, handoff bodies, and secrets must not be persisted; store metadata/hashes/counters only.
10. GitHub push/publish is Human Escalation; ask before pushing.

---

# Latest Handoff — Context Clean Checkpoint

Generated: `2026-06-04T00:00:00+09:00`
Repo: `https://github.com/kagioneko/cpos-engine-zero.git`
Working directory: `/home/mayutama/cpos_defensive_agent`
Branch: `main`
Remote status at handoff after committing this memo: `main...origin/main [ahead 1]`
Latest pushed commit: `fb0debc Add patch generation safe advance`
Latest local-only memo commit: see `git log -1` after this handoff commit.
Release/tag status: **v0.1 tag has NOT been created yet**.

## Absolute first steps next session

Run these before continuing:

```bash
cd /home/mayutama/cpos_defensive_agent
git status --short --branch
PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
```

Expected clean result at handoff after the memo commit:

- `git status --short --branch`: `## main...origin/main [ahead 1]`
- `prepublish_check`: `ok=true`
- Secret scan: `ok=true count=0`
- Working tree: clean

## Latest pushed commits in this session

Pushed to `origin main`:

1. `36005e0 Add demo capture guide`
2. `4cb6650 Add review-gated patch generation`
3. `a1932bb Add patch generation validation harness`
4. `fb0debc Add patch generation safe advance`

## What changed most recently

### Review-Gated Patch Generator

Added `cpos/patch_generation_review.py` and connected it to API/dashboard/report/flow graph.

Core behavior:

- Auto Fix Candidate -> Patch Generation Review -> human approval gate.
- Persisted metadata only: hashes, sizes, counters, task IDs, lineage, status flags.
- Raw generated diff text is transient input only.
- No live repo patch, no command execution, no commit, no push, no PR creation.

Key APIs:

- `GET /sandbox/patch-generations`
- `POST /sandbox/fix-candidates/<task_id>/create-patch-generation`
- `POST /sandbox/patch-generations/<task_id>/approve`
- `POST /sandbox/patch-generations/<task_id>/reject`
- `POST /sandbox/patch-generations/<task_id>/create-github-diff-review`

Dashboard:

- Added `Patch Generation Reviews` section.
- Auto Fix Candidate cards now expose `Create Patch Generation Review`.
- Patch Generation cards support approve/reject and routing transient generated diff into GitHub Diff Review.

Report / graph:

- Report renders `Patch Generation Reviews`.
- Sandbox Flow Graph now includes `patch_generation_review` and generated-diff -> GitHub Diff Review lineage.

### Patch Generation Validation Harness

Added a safe pre-review harness for generated patches:

- API: `POST /sandbox/patch-generations/<task_id>/validate-output`
- Runs `git apply --check` in an ephemeral copied workspace only.
- Validation commands are policy-checked but **not executed** by this harness.
- Does not apply the patch, mutate live repo, commit, push, create PRs, or store raw diff/output.
- Stores only diff hash/size, command hashes, apply-check exit/status/output hashes, counters, and lineage.

Dashboard:

- Added `Validate Generated Diff` button.

Report / graph:

- Report shows `Validation Harness Runs`.
- Sandbox Flow Graph includes `patch_generation_validation` nodes.

### Patch Generation Safe Advance

Added one-click safe route from approved Patch Generation Review to pending Sandbox Execution Review:

- API: `POST /sandbox/patch-generations/<task_id>/advance-to-execution-review`
- Requires `confirm=true`.
- Steps:
  1. validate generated diff with the validation harness
  2. create GitHub Diff Review from transient diff
  3. approve GitHub Diff Review metadata-only gate
  4. create Sandbox Patch Plan
  5. approve Sandbox Patch Plan metadata-only gate
  6. create pending Sandbox Execution Review
- Still does **not** approve execution, run commands, patch live repo, commit, push, create PRs, or store raw diff/output.

Dashboard:

- Added `Advance to Execution Review` button.

Report / graph:

- Report shows `Safe Advances`.
- Sandbox Flow Graph includes `patch_generation_safe_advance` and `sandbox_execution_review` nodes.

### Docs

Updated:

- `README.md`
  - Documents Patch Generation Reviews, validation harness, and safe advance curl flow.
- `PITCH.md`
  - Demo path now includes Diff Draft / Patch Generation Review and generated patch validation harness.
- `docs/DEMO_CAPTURE_GUIDE.md`
  - Added earlier demo capture guide commit.

## Verification at handoff

Latest verified commands:

```bash
PYTHONPATH=. .venv/bin/python -m py_compile cpos/patch_generation_review.py cpos/sandbox_flow_graph.py server.py generate_report.py
PYTHONPATH=. .venv/bin/python -m pytest tests/test_patch_generation_review.py tests/test_sandbox_patch_api.py::test_sandbox_patch_generation_api_flow tests/test_sandbox_patch_api.py::test_sandbox_patch_generation_scope_mapping tests/test_dashboard.py::test_dashboard_contains_patch_generation_review_ui tests/test_sandbox_flow_graph.py::test_sandbox_flow_graph_links_failure_to_draft tests/test_sandbox_flow_graph.py::test_sandbox_flow_graph_filters_by_source_execution tests/test_report.py::test_generate_report_renders_patch_generation_reviews -q
PYTHONPATH=. .venv/bin/python -m pytest tests/test_patch_generation_review.py tests/test_sandbox_patch_api.py tests/test_dashboard.py tests/test_sandbox_flow_graph.py tests/test_report.py -q
PYTHONPATH=. .venv/bin/python -m pytest tests -q
PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
```

Results:

- Targeted safe-advance tests: `13 passed`
- Related tests: `84 passed`
- Full test suite: `301 passed`
- `prepublish_check`: `ok=true`
- Secret scan: `ok=true count=0`
- After feature push: `main...origin/main` was synced and clean. This handoff memo commit is intentionally local-only unless user asks to push it.

## Safety / publishing rules to preserve

- Secrets/API keys/tokens/SSH keys stay in Vault; never hardcode, log, or push.
- Do not stage/publish `.env`, secret files, cert/key files, `.venv`, pycache, pytest cache, runtime `*.jsonl`, generated local reports, or workspace artifacts.
- Raw diff text, raw stdout/stderr, request bodies, checkpoint contents, and raw handoff bodies must not be persisted in Task Tape/dashboard/report. Store hashes, sizes, exit codes, status flags, and metadata only.
- `authorized_keys` changes are forbidden.
- User creation/deletion requiresねこさん confirmation.
- `rm -rf`, destructive overwrite, and systemd stop/delete require confirmation.
- Port opening requires explicit approval, 15-minute auto-close, and Discord notification.
- GitHub publish/push is Human Escalation. The latest push was explicitly approved in this session and completed.
- Correct remote is `origin https://github.com/kagioneko/cpos-engine-zero.git`.

## Recommended next steps

1. **Do not tag v0.1 yet unless user explicitly says so.** User said “まだv0.1にはせずに”.
2. Next execution-power improvement: add a dashboard/report “ready-to-run execution review” helper after safe advance, but keep run approval separate and transient-diff-only.
3. Add docs/release note polish for Patch Generation + Safe Advance if preparing v0.1.
4. Consider demo script path:
   - failed sandbox result
   - retry/replan
   - auto fix candidate
   - patch generation review
   - validation harness
   - safe advance to execution review
   - explicit approve+run in ephemeral sandbox
   - result / flow graph / report
5. If new commits are made, run full tests + `prepublish_check --json`; ask before push unless user gives clear push instruction.

## Honest product assessment

CPOS now has a materially strong safe execution loop: failure metadata can become a review-gated generated-patch path, generated patches can be checked in an ephemeral harness, and validated generated patches can be promoted to a pending sandbox execution review without live repo mutation or raw diff persistence. This is much closer to Hermes/OpenClaw/Claude Code-style execution power, while retaining stronger audit/safety constraints. Still avoid claiming definitive superiority until there is a crisp demo and real-world run evidence.

---

# Previous handoff history

# Latest Handoff — Context Clean Checkpoint

Generated: `2026-05-31T00:00:00+09:00`
Repo: `https://github.com/kagioneko/cpos-engine-zero.git`
Branch: `main`
Remote status at handoff: `main...origin/main [ahead 5]`
Latest local commit: `1830ba1 Add sandbox test dependencies`
Latest previously pushed commit before execution-driver work: `d8aa103 Document human escalation reporting`

## What changed in the latest execution-power session

- Added review-gated sandbox execution driver: `cpos.execution_driver.advance_sandbox_patch_pipeline()`.
  - API: `POST /sandbox/execution-driver/advance`.
  - Can coordinate approved diff -> sandbox patch plan -> plan approval -> execution review -> execution approval -> optional ephemeral run.
  - Explicit booleans are required for approvals/runs; no bypass of Task Tape review events.
- Added failed-execution replan driver: `advance_failed_sandbox_replan()`.
  - API: `POST /sandbox/execution-driver/replan-failure`.
  - Can coordinate failed execution -> retry review -> retry approval -> replan template -> diff intake checklist.
  - Never reruns automatically, never reuses failed workspace, never stores raw stdout/stderr or raw diff text.
- Added dashboard one-click safe replan action for failed sandbox results.
  - Button: `Create Retry → Replan → Diff Intake`.
  - Calls `/sandbox/execution-driver/replan-failure` with explicit review/replan flags.
- Added Execution Scoreboard.
  - Function: `build_execution_scoreboard(store)`.
  - API: `GET /sandbox/scoreboard`.
  - Dashboard/report show completed runs, success/failure counts, success rate, failure kinds, retry/replan/intake counts, and recent failure metadata.
- Added sandbox Docker image test dependencies: `flask`, `pyyaml`, and `cryptography`.
- Local experimental CPOS prototype/demo modules were intentionally **not** committed.
  - They are ignored locally in `.git/info/exclude` only.
  - Some contain `os.system("rm -rf ...")`, `shutil.rmtree(...)`, file writes, and network reads; keep them out of OSS publish until safety-reviewed and rewritten.

## Latest verification

- Full test suite after Execution Scoreboard: `265 passed`.
- Sandbox/execution focused tests after Dockerfile dependency update: `34 passed`.
- `python -m py_compile cpos/execution_driver.py server.py generate_report.py`: passed.
- `prepublish_check --json` after final commit: `ok=true`.
- Secret scan: `ok=true count=0`.
- Correct remote confirmed: `origin https://github.com/kagioneko/cpos-engine-zero.git`.

## Current safety posture

- Working tree is clean as of the final check.
- Branch is ahead of `origin/main` by 5 commits:
  - `1830ba1 Add sandbox test dependencies`
  - `6870e2f Add execution scoreboard`
  - `15476d2 Add dashboard safe replan action`
  - `c79fb24 Add sandbox failure replan driver`
  - `109b299 Add sandbox execution driver`
- Do not push unless the user explicitly approves GitHub publishing.
- Correct public repo is `kagioneko/cpos-engine-zero`; do not push to similarly named repos/accounts.
- Secrets must stay in Vault or secret files; never code, `.env`, comments, logs, crontab, or GitHub.
- Do not stage/publish `.venv`, `__pycache__`, `.pytest_cache`, runtime `*.jsonl`, cert/key files, generated local reports, or workspace artifacts.
- `authorized_keys` changes remain forbidden.
- Destructive operations, systemd stop/delete, user creation/deletion, and port opening require explicit user approval. Port opening also requires 15-minute auto-close and Discord notification.

## Recommended next steps

1. If continuing execution-power work: build a safe Auto Fix Candidate Builder from failure metadata only.
2. If preparing release: run full tests and `PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json`, then ask before pushing.
3. If deciding whether to include local experimental modules: review/sanitize them one feature at a time; do not commit the current raw demo/prototype files wholesale.
4. Consider updating release notes/checklist if these execution-driver commits become part of the release branch.

## Honest product assessment

CPOS is now materially stronger on safe execution: it has review-gated pipeline advancement, failure-to-replan routing, dashboard one-click recovery scaffolding, and metadata-only execution scoring. This is a strong differentiator versus ordinary tool agents. Still avoid claiming full superiority over Hermes/OpenClaw/Claude Code until there is a crisp demo and more real-world success evidence.

---

# NEXT HANDOFF


## Latest session handoff (2026-05-30)

Repository / safety status:

- Working repo: `/home/mayutama/cpos_defensive_agent`
- Correct remote: `origin https://github.com/kagioneko/cpos-engine-zero.git`
- Do **not** push to similarly named `emi`/hackathon repos. This is CPOS-only.
- Latest pushed commits at handoff:
  - `ad94395 Document safe autonomy demo flow`
  - `c372157 Show sandbox diff intakes on dashboard`
  - `9a5ef27 Ignore runtime JSONL artifacts`
  - `b971557 Add sandbox replan diff intakes`
  - `77fd2b0 Classify sandbox execution failures`
- Validation after latest pushed work: `219 passed`; secret scan `ok=true count=0`.
- `.gitignore` now blocks `*.jsonl`, `.venv/`, `__pycache__/`, `.pytest_cache/`, runtime ledgers, certs, secret/env/key/cert files.
- Before any future commit/push, always run:
  - `git status --short`
  - `git remote -v` and confirm `kagioneko/cpos-engine-zero`
  - tracked bad artifact check for `.venv`, pycache, pytest cache, JSONL runtime files, `.env`, keys/certs
  - full tests
  - secret scan

Security / credentials rules to preserve:

- API keys, tokens, SSH keys, OAuth tokens, passwords, and `.env` values must stay in Vault/secret files only.
- Never hardcode or print secrets. Never push secrets to GitHub.
- Raw diff text, raw stdout/stderr, request bodies, checkpoint contents, and raw handoff bodies should not be persisted in Task Tape/dashboard/report. Store hashes, sizes, exit codes, status flags, and metadata only.
- `authorized_keys` changes are forbidden. User creation/deletion requires confirmation. `rm -rf`, destructive overwrite, and systemd stop/delete require confirmation.

Recent feature state:

- Safe autonomy loop is now documented in README under `Safe Autonomy Demo Flow`.
- Dashboard now shows PR dry-runs, diff reviews, sandbox patch plans, execution reviews, completed execution results, retry reviews, replan templates, and diff intakes.
- Sandbox execution run applies patches only in ephemeral workspace copies and stores result metadata only.
- Validation commands are allowlisted (`pytest` style), shell metacharacters are rejected, and `local-dev` runner mode requires `CPOS_ALLOW_LOCAL_DEV_RUN=true`.
- Failure kinds are classified as `patch_apply`, `validation_command`, `sandbox_unavailable`, or `policy_rejected`.
- Failed sandbox execution flow now supports:
  1. completed result metadata
  2. retry review
  3. approved retry -> replan template
  4. replan template -> diff intake checklist
  5. human supplies new diff through normal GitHub diff review path
- Diff intake records `required_human_inputs` and `target_api` only; it never stores raw diff and never executes automatically.

Recommended next steps:

1. Update `SECURITY.md` with an explicit “Data We Never Persist” section:
   - secrets/tokens/keys
   - raw stdout/stderr
   - raw diff text
   - request bodies
   - checkpoint contents
   - `.venv`, pycache, pytest cache, runtime JSONL
2. Update `OSS_RELEASE_CHECKLIST.md` to include the tracked bad artifact check and secret scan command.
3. Add a small release-readiness CLI/check script if useful, but keep it non-destructive.
4. Consider dashboard action button from replan template to diff intake creation, still metadata-only.
5. Only after release docs/checklist are clean, consider tagging v0.1.0.

Current honest product assessment:

- Strong unique direction: memory/task separation, Context Pointer OS, Task Tape, review-gated safe autonomy, metadata-only retry/replan loop, text-first MCP governance.
- Not ready for “Hermes/OpenClaw surpassed” claim yet; likely needs final docs/release polish and a crisp demo. If/when it crosses that line, explicitly report it.


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
- GitHub Diff Review Adapter added in `cpos/github_diff_review.py` with API routes `GET /github/diff-reviews`, `POST /github/pr-dry-runs/<source_task_id>/create-diff-review`, `POST /github/diff-reviews/<task_id>/approve|reject`. It requires an approved PR dry-run first and stores diff metadata only: hash/size/file list/line counts; no raw diff persistence, no patch apply, no commit, no push, no PR.
- Sandbox Patch Plan gate added in `cpos/sandbox_patch_plan.py` with API routes `GET /sandbox/patch-plans`, `POST /github/diff-reviews/<diff_task_id>/create-sandbox-plan`, `POST /sandbox/patch-plans/<task_id>/approve|reject`. It requires an approved diff review and records ephemeral-workspace validation metadata only: no live repo writes, no patch apply, no command execution, no commit/push/PR.
- Sandbox Patch Execution review added in `cpos/sandbox_patch_runner.py` with API routes `GET /sandbox/executions`, `POST /sandbox/patch-plans/<patch_task_id>/create-execution-review`, `POST /sandbox/executions/<task_id>/approve|reject`. It requires an approved sandbox patch plan and remains metadata-only: no workspace copy, no patch apply, no command execution, no commit/push/PR, and no raw command output storage.
- Sandbox Patch Execution run added in `cpos/sandbox_patch_runner.py` with API routes `POST /sandbox/executions/<task_id>/run` and `GET /sandbox/executions/completed`. It requires an approved sandbox patch execution plan, applies the patch only in an ephemeral workspace copy, validates command hashes before running, and stores hashes/exit codes/status only; raw patch text and raw command output stay out of Task Tape. Dashboard now shows completed result metadata. Validation commands now enforce pytest-style allowlisted prefixes, reject shell metacharacters, and block `local-dev` runner mode unless `CPOS_ALLOW_LOCAL_DEV_RUN=true` is explicitly set.
- Sandbox Patch Execution Retry Review added in `cpos/sandbox_patch_runner.py` with API routes `GET /sandbox/execution-retries`, `POST /sandbox/executions/<task_id>/create-retry-review`, and `POST /sandbox/execution-retries/<task_id>/approve|reject`. It requires a completed failed sandbox execution and builds a retry plan from hashes/status/exit codes only: no raw outputs, no raw patch text, no workspace reuse, and no automatic rerun.
- Sandbox Patch Replan Template added with API routes `GET /sandbox/replan-templates` and `POST /sandbox/execution-retries/<task_id>/create-replan-template`. It requires an approved retry review and emits metadata-only next-plan scaffolding: suggested focus, next review chain, failure hashes/status/exit codes, no diff text, no raw outputs, no workspace reuse, no automatic execution.
- Sandbox failure classification expanded to `patch_apply`, `validation_command`, `sandbox_unavailable`, and `policy_rejected`. Policy rejections are returned before workspace copy; completed failed executions persist `failure_kind` metadata for retry/replan routing.
- Sandbox Replan Diff Intake added with API routes `GET /sandbox/diff-intakes` and `POST /sandbox/replan-templates/<task_id>/create-diff-intake`. It turns a replan template into a metadata-only checklist for the next GitHub diff review: required human inputs, target API path, no raw diff storage, no automatic execution.
- OSS release prep added: `.gitignore`, `LICENSE` (MIT), `SECURITY.md`, `CONTRIBUTING.md`, `OSS_RELEASE_CHECKLIST.md`, and README OSS positioning. Test/source dummy secret fixtures were changed to avoid source-tree secret-scan false positives while preserving runtime scan tests.

- OSS publish cleanup started: `.venv`, pycache, workspace demos, runtime JSONL ledgers, certs, and generated `hackathon_report.html` were removed from Git index with `git rm --cached` only; files remain on disk. `.gitignore` now excludes them. `git ls-files` check for tracked bad artifacts returns none.
- Added `RELEASE_NOTES_v0.1.0.md`. Validation after cleanup: `207 passed`; secret scan `ok=true count=0`. Current status after Sandbox Patch Execution work: source/docs/tests modified locally; run `git status --short`, secret scan, commit, and push when ready.

## Verification

```bash
.venv/bin/python -m py_compile generate_report.py server.py cpos/pointer_os.py cpos/pointer_cli.py agents/main_agent.py
.venv/bin/python -m pytest tests -q
# 207 passed
.venv/bin/python generate_report.py
```

## Suggested next step

Next: do a staged GitHub OSS publish pass: review git status, stage only source/docs/tests (no runtime artifacts), run secret scan, then create initial public repo/release notes. HTTPS enforcement, mTLS fingerprint gate, approval gating, bearer-token/HMAC auth, route-level scopes, Security Audit Trail, tamper-evident hash chaining, replay protection, key rotation, HMAC helpers, Python API client, IP allowlist, rate limiting, sandbox policy modes, security profile presets, hardened validation, dashboard/report visibility, preflight CLI, hardened deployment templates, Vault render helper, secret scan, CI/preflight template, Vault migration docs, secret inventory CLI, and secret inventory dashboard/report view are implemented.
