## Start Here — 10-line Resume Card

1. `cd /home/mayutama/cpos_defensive_agent`
2. `git status --short --branch`
3. `PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json`
4. Expected state at handoff: `main...origin/main` after pushing this memo, clean tree, `prepublish_check ok=true`, secret scan `count=0`, full tests `325 passed`.
5. Correct remote: `origin https://github.com/kagioneko/cpos-engine-zero.git`; latest pushed commit before this memo: `bd250b8 Add adapter schema validation`.
6. Final **v0.1.0** tag and GitHub Release are published. Existing RC tag remains: `v0.1.0-rc1` -> `0f1e585` from 2026-05-29.
7. Latest pushed work: External Agent Adapter schema validation, External Agent Adapter MVP, adapter dashboard queue, Human Escalation integration, adapter demo readiness/fixture integration, plus prior Competitive Demo Readiness / Ready-to-Run / Patch Generation / tape-memory MCP review work.
8. Fast resume cache: `TAPE_MEMORY_DIR=/home/mayutama/.tape-memory-mcp-cpos`, keys `cpos_resume_latest`, `cpos_safety_invariants`, `cpos_next_action`, `cpos_mcp_tape_memory`, `cpos_competitive_demo_readiness`, `cpos_demo_fixture`, `cpos_pitch_demo_polish`, `cpos_release_docs_polish`, `cpos_push_checkpoint`, `cpos_release_tag_audit`; MCP review pending: `mcp_review_cca928799d599640`.
9. Safety invariant: raw diffs, raw outputs, request bodies, checkpoint/handoff bodies, and secrets must not be persisted; store metadata/hashes/counters only.
10. GitHub push/publish is Human Escalation; ask before pushing. Final release tag also requires explicit instruction.

---

# Latest Handoff — External Agent Adapter Checkpoint

Generated: `2026-06-05T00:00:00+09:00`
Repo: `https://github.com/kagioneko/cpos-engine-zero.git`
Working directory: `/home/mayutama/cpos_defensive_agent`
Branch: `main`
Remote status before this memo commit: `main...origin/main`
Latest pushed commit: `bd250b8 Add adapter schema validation`
Release/tag status: final **v0.1.0** tag has been created and pushed; GitHub Release is published. Existing remote/local release-candidate tag: `v0.1.0-rc1` -> `0f1e585 Prepare CPOS Engine-Zero for OSS release` from 2026-05-29.

## Absolute first steps next session

Run these before continuing:

```bash
cd /home/mayutama/cpos_defensive_agent
git status --short --branch
PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
```

Expected after this memo is committed and pushed:

- `git status --short --branch`: `## main...origin/main`
- `prepublish_check`: `ok=true`
- Secret scan: `ok=true count=0`
- Working tree: clean
- Full tests last verified: `325 passed`

## Latest pushed commits

Pushed to `origin main`:

1. `493c7ce Add external agent adapter MVP`
2. `4ee3d2e Add agent adapter to demo readiness`
3. `5d27190 Update handoff after agent adapter`
4. `840ee62 Update release docs test count`
5. `238bc3d Add external agent result scoreboard`
6. `9e31015 Highlight external agent result readiness`
7. `6371bc1 Update handoff with result scoreboard readiness`
8. `4121591 Add metadata-only demo capture assets`
9. `cce2855 Add demo evidence assets to README`
10. `c5129aa Update handoff with demo asset polish`
11. `c6c2298 Add external agent adapter integration example`
12. `bd250b8 Add adapter schema validation`

Previous pushed handoff/tag status commit:

- `e7d641b Clarify v0.1 release tag status`

Latest full test count after adapter schema validation: `325 passed`.

## Completion/readiness assessment

Current completion feel is **very strong for a v0.1 defensive agent runtime / safety layer**:

- Defensive agent runtime / governance layer: roughly **90%+ v0.1-ready**.
- Fully autonomous coding agent brain: still separate future work, but now CPOS can govern native and external agent actions.
- Strategic positioning is solid: CPOS is both **CPOS Agent** and **CPOS for Agents**.
- Main proof chain is connected: adapter intake → Human Escalation → dashboard/report → demo readiness → metadata-only fixture → demo assets → README → release docs.

Latest pushed capabilities:

- External Agent Adapter accepts action contracts and `execution_result` reports.
- External agent result scoreboard is available at `/agent-adapter/execution-results`.
- Dashboard and generated report surface external agent contracts/results prominently.
- Competitive Demo Readiness now highlights External Agent Adapter + Result Scoreboard in the main demo path.
- Metadata-only demo capture assets are committed under `docs/assets/demo/` and linked from README.
- External agent integration docs and a stdlib-only example client are committed.
- Full test count is now `325 passed`; prepublish and secret scan are clean.

## What changed most recently

### Adapter Schema Validation

Added lightweight schema validation for `/agent-adapter/intake` and pushed it to `origin/main` in `bd250b8 Add adapter schema validation`.

Behavior:

- Invalid adapter payloads are rejected before any Task Tape event is written.
- Invalid responses use `error=schema_validation_failed` with `cpos.external_agent_action_validation.v1`.
- Validation errors are metadata-only: field names, stable error codes, and safety flags only.
- Raw command strings, raw diffs, raw stdout/stderr, raw request bodies, and secret-like values are not echoed in validation responses.
- `commands` and `changed_files` must be arrays of strings.
- `command_request` requires at least one command.
- `proposed_diff` requires a non-empty string.
- `metadata.risk` is limited to `low`, `medium`, `high`, or `critical`.
- bool/int metadata fields are type checked.
- `execution_result` must be a redacted/status-only object; raw output keys such as `stdout`, `stderr`, `output`, `raw_output`, `logs`, and `traceback` are rejected.

Touched files:

- `cpos/agent_adapter.py`
- `server.py`
- `tests/test_agent_adapter.py`
- `docs/AGENT_ADAPTER_SCHEMA.md`
- `docs/backlog/V0_1_1_BACKLOG.md`

Verification after commit/push:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/test_agent_adapter.py -q
# 9 passed

PYTHONPATH=. .venv/bin/python -m pytest tests -q
# 325 passed

PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
# ok=true; secret_scan ok=true count=0
```

### External Agent Adapter MVP

Added `cpos/agent_adapter.py` as a metadata-only ingress gate for Codex/Hermes/OpenClaw-style external agents.

Supported event types:

- `agent_intent`
- `proposed_action`
- `proposed_diff`
- `command_request`
- `execution_result`

Key behavior:

- Builds `cpos.external_agent_action_contract.v1` action contracts.
- Stores hashes, sizes, counters, metadata keys, file names, risk/decision flags, and Task Tape IDs only.
- Does **not** store raw request bodies, raw diffs, raw stdout/stderr, checkpoint bodies, handoff bodies, or secret values.
- Does **not** execute commands, apply patches, commit, push, create PRs, or approve downstream execution automatically.
- Risky actions route into existing Human Escalation with `review_type=external_agent_action`.

Key APIs:

- `POST /agent-adapter/intake`
- `GET /agent-adapter/actions`
- `POST /agent-adapter/actions/<task_id>/approve`
- `POST /agent-adapter/actions/<task_id>/reject`

Dashboard:

- Added **External Agent Adapter Queue**.
- Shows pending external action contracts, risk, command/file counts, contract hash, metadata-only flags.
- Approval button approves contract metadata only; it does not run external agent commands.

Human Escalation:

- `pending_human_escalations()` now recognizes `external_agent_action`.
- Endpoint hints:
  - review: `/agent-adapter/actions`
  - approve: `/agent-adapter/actions/<task_id>/approve`
  - reject: `/agent-adapter/actions/<task_id>/reject`
- Owning pipeline hint: `external_agent_adapter`.
- Pipeline stage hint: `external_agent_review_gate`.

Tests:

- Added `tests/test_agent_adapter.py`.
- Covers metadata-only storage, no raw diff persistence, Human Escalation integration, approve confirm gate, and API roundtrip.

### External Agent Result Scoreboard

Added metadata-only external-agent execution result reporting.

Key API:

- `GET /agent-adapter/execution-results`

Behavior:

- External agents can submit `event_type=execution_result` through `/agent-adapter/intake`.
- CPOS stores only result hash/size, success flag, exit code, failure kind, duration, task IDs, and safety flags.
- Raw stdout/stderr and raw execution bodies are not persisted.
- Scoreboard reports completed/success/failure counts, success rate, failure kinds, and recent metadata-only results.
- Execution-result reports are evidence/scoreboard inputs only; they do not trigger command execution.

Dashboard/report/readiness:

- Dashboard External Agent Adapter Queue shows result scoreboard.
- Generated report has `External Agent Adapter` result scoreboard.
- Competitive Demo Readiness now foregrounds `external_agent_actions` and `external_agent_results`.
- Demo path now includes `External Agent Adapter → External Agent Result Scoreboard`.

### Demo Readiness / Fixture Integration

`build_competitive_demo_readiness()` now includes:

- stage: `External Agent Adapter`
- count: `external_agent_actions` and `external_agent_results`
- posture flags: `external_agent_adapter_available=true`, `external_agent_result_scoreboard_available=true`
- next demo path includes `External Agent Adapter` and `External Agent Result Scoreboard`

`create_competitive_demo_fixture()` now seeds one metadata-only `command_request` adapter review plus one metadata-only `execution_result` report:

- agent: `demo-external-agent`
- command metadata: hashed only
- changed file: `README.md`
- `requires_human_approval=true`
- no command execution, no raw output storage
- execution result metadata uses redacted/status-only payloads; raw stdout/stderr are not persisted

Updated tests in `tests/test_demo_readiness.py` assert the adapter appears in readiness and fixture output.

### Docs / Demo Assets / Integration Example

`README.md` now has **External Agent Adapter MVP** with minimal curl examples:

- `POST /agent-adapter/intake`
- `GET /agent-adapter/actions`
- `GET /agent-adapter/execution-results`
- `GET /human-escalations`

README also links metadata-only demo assets:

- `docs/assets/demo/competitive-demo-readiness.png`
- `docs/assets/demo/external-agent-adapter-queue.png`
- `docs/assets/demo/human-escalation-queue.png`
- `docs/assets/demo/ready-to-run-gate.png`
- `docs/assets/demo/sandbox-flow-graph.png`
- `docs/assets/demo/report-demo-readiness.png`

These panels show hashes, counts, endpoint hints, statuses, and safety flags only. Asset secret scan was `ok=true count=0`.

Added external adapter integration materials:

- `docs/AGENT_ADAPTER_INTEGRATION.md`
  - endpoint list
  - supported event types
  - command_request example
  - execution_result example
  - safety invariants
  - local usage examples
- `examples/agent_adapter_client.py`
  - Python stdlib-only client
  - supports `command-request` and `execution-result`
  - dry-run by default; `--send` posts to `/agent-adapter/intake`
  - `--token-file` reads a Vault-rendered bearer token file without printing the token

Verification for the example/client docs:

```bash
PYTHONPATH=. .venv/bin/python -m py_compile examples/agent_adapter_client.py
PYTHONPATH=. .venv/bin/python examples/agent_adapter_client.py --command 'pytest tests -q' --changed-file README.md command-request
PYTHONPATH=. .venv/bin/python -m pytest tests/test_readme.py -q
PYTHONPATH=. .venv/bin/python -m cpos.secret_scan README.md docs/AGENT_ADAPTER_INTEGRATION.md examples/agent_adapter_client.py --json
# test_readme: 16 passed; secret scan ok=true count=0
```

## Verification at handoff

Latest verified commands:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/test_agent_adapter.py tests/test_dashboard.py tests/test_readme.py tests/test_human_escalation.py -q
# 46 passed

PYTHONPATH=. .venv/bin/python -m pytest tests -q
# 325 passed

PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
# ok=true; secret_scan ok=true count=0
```

`prepublish_check` after pushing adapter commits:

- `ok=true`
- remote URL correct: `https://github.com/kagioneko/cpos-engine-zero.git`
- tracked bad artifacts: none
- untracked risky files: none
- missing required files: none
- secret scan count: `0`


## Demo capture verification — 2026-06-05

Metadata-only demo path was exercised through the local Flask test client after pushing `840ee62`; after later adapter-result work, fixture/readiness includes `external_agent_results` as well:

- `POST /demo/fixture` with `confirm=true`: `200 OK`, `ok=true`
- Fixture `step_count`: `16` after adapter result scoreboard work
- `GET /demo/readiness`: `ready=true`, `ready_count=9`, `stage_count=9`
- Safety flags confirmed:
  - `metadata_only=true`
  - `raw_diff_stored=false`
  - `raw_outputs_stored=false`
  - `raw_request_stored=false`
  - `secret_values_stored=false`
  - `execute_automatically=false`

Readiness counts after fixture:

- `external_agent_actions`: `1`
- `external_agent_results`: `1`
- `human_escalations`: `5`
- `ready_to_run_reviews`: `2`
- `patch_generation_reviews`: `2`
- `flow_nodes`: `12`
- `fast_resume_keys`: `13`
- `completed_runs`: `2`
- `diff_drafts`: `2`
- `auto_fix_candidates`: `2`
- `pending_tape_memory_reviews`: `1`

Report check:

- `generate_report.py` generated `hackathon_report.html` locally.
- Report contains all capture targets:
  - `Competitive Demo Readiness`
  - `External Agent Adapter` / result scoreboard
  - `Human Escalation`
  - `Ready-to-Run`
  - `Sandbox Autonomy Flow Graph`

Important: demo fixture writes metadata-only Task Tape events; they are ignored runtime data and were not committed. Git status remained `main...origin/main` after demo/report checks.

## Feature recommendation / remaining work

No urgent core feature is missing for v0.1. The project is in a good "ship/demo" state.

Optional additions ifねこさん wants more polish:

1. **Adapter JSON schema docs**: next recommended item. Add `docs/AGENT_ADAPTER_SCHEMA.md` for `command_request`, `proposed_diff`, `execution_result`, response contract, and safety flags. Link from README/integration docs and update tests.
2. **README badges/diagram polish**: add a small architecture diagram or link directly to demo assets. Mostly presentation.
3. **Final v0.1.0 release packaging**: only if explicitly instructed; create final tag/release after final checks.
4. **Real browser screenshots/GIF**: only if local browser tooling is available; current metadata-only panels are already safe and committed.

Recommendation: do not add large new runtime features before v0.1 unless there is a concrete target integration. Prefer schema docs/release polish/final handoff.


## Final pre-release audit — 2026-06-05

Final pre-release audit was run after `88eaa7e Add external agent adapter schema docs` was pushed. No final tag was created.

Verified commands/results:

```bash
git status --short --branch
# ## main...origin/main

git remote -v
# origin https://github.com/kagioneko/cpos-engine-zero.git (fetch/push)

PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
# ok=true; secret_scan ok=true count=0

PYTHONPATH=. .venv/bin/python -m cpos.release_check --json
# ok=true

PYTHONPATH=. .venv/bin/python -m pytest tests -q
# 325 passed

git tag --list 'v0.1*'
# v0.1.0-rc1

git ls-remote --tags origin 'v0.1*'
# remote has v0.1.0-rc1 only; final v0.1.0 not present
```

Release docs/checklist status:

- `RELEASE_NOTES_v0.1.0.md` records `320 passed`.
- `OSS_RELEASE_CHECKLIST.md` records `320 passed`.
- `GITHUB_RELEASE_DRAFT_v0.1.0.md` exists.
- Existing RC tag: `v0.1.0-rc1` -> annotated tag object `38488de...`, peeled commit `0f1e585 Prepare CPOS Engine-Zero for OSS release`.
- Final tag **`v0.1.0` has not been created**.

Recommendation:

- Safe path: stop here, keep handoff pushed, create final tag later after explicit instruction.
- Ifねこさん explicitly says to release: rerun `git status`, `prepublish_check`, `release_check`, full tests, confirm remote, then create/push final `v0.1.0` tag.
- Do not create or push final tag without explicit confirmation.


## Final v0.1.0 release — 2026-06-05

ねこさん explicitly approved proceeding with the official final release. Final checks were rerun immediately before tagging.

Final pre-tag checks:

```bash
git status --short --branch
# ## main...origin/main

PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
# ok=true; secret_scan ok=true count=0

PYTHONPATH=. .venv/bin/python -m cpos.release_check --json
# ok=true

PYTHONPATH=. .venv/bin/python -m pytest tests -q
# 325 passed

git tag --list 'v0.1.0'
# no output before final tag creation
```

Release actions completed:

```bash
git tag -a v0.1.0 -m "CPOS Engine-Zero v0.1.0"
git push origin v0.1.0
gh release create v0.1.0 --repo kagioneko/cpos-engine-zero --title "CPOS Engine-Zero v0.1.0" --notes-file GITHUB_RELEASE_DRAFT_v0.1.0.md --verify-tag
```

Published release:

- URL: https://github.com/kagioneko/cpos-engine-zero/releases/tag/v0.1.0
- GitHub Release: `isDraft=false`, `isPrerelease=false`
- Tag: annotated `v0.1.0`
- Tag object: `97f5ae94223eabe4f743de74991ee87f3ad24ab0`
- Peeled commit: `d0c908c6e716888726a896e23ba658628c482cde` (`Record final pre-release audit`)
- Post-release state: `main...origin/main`, `prepublish_check ok=true`, secret scan `count=0`

Important: after this memo is committed, `main` will advance beyond the released tag by the handoff commit only. That is normal; the release tag remains pinned to `d0c908c`.


## Next reconnect note

When this thread is reconnected, prepare a Notion-ready summary of the v0.1.0 release and keep it in two forms:

- short paste-ready version
- longer structured version

Use the v0.1.0 release draft and current README/adapter docs as the source of truth. The summary should cover:

- what CPOS v0.1.0 is
- what it can and cannot do
- External Agent Adapter overview
- demo/readiness story
- safety / metadata-only invariants
- the next step after v0.1.0

Treat this as the next post-release documentation task when the user says "つないだらやる".


## Notion post-release summary — 2026-06-05

Created a Japanese-first Notion page for the v0.1.0 post-release summary.

- Notion URL: https://app.notion.com/p/CPOS-Engine-Zero-v0-1-0-Notion-37676d12b6d2812ea817daf2ed8017c7
- Source Markdown: `docs/POST_RELEASE_NOTION_SUMMARY_v0.1.0.md`
- GitHub Markdown URL: https://github.com/kagioneko/cpos-engine-zero/blob/main/docs/POST_RELEASE_NOTION_SUMMARY_v0.1.0.md
- Content style: Japanese main summary + English reference version preserved in Markdown.
- Notion DB used: Vault `secret/notion` field `memo_db_id`; title property was `タイトル`.
- Secret handling: Notion API token was read from Vault `secret/notion(api_key)` and was not printed or stored in repo.
- Created page block count: `197`.

If updating the Notion page later, continue using Vault for Notion credentials. Do not hardcode Notion tokens or database IDs in code, docs, shell history, `.env`, or crontab.

## Current recommended next action

Recommended next session path:

1. Verify `git status --short --branch` and `prepublish_check`.
2. If this handoff memo is not pushed yet, push the memo commit after explicit approval.
3. Then choose one:
   - **Post-release path**: update any announcement/social copy if needed.
   - **Patch path**: future fixes should target post-v0.1.0 commits and, if needed, v0.1.1.
   - **Integration path**: use `docs/AGENT_ADAPTER_INTEGRATION.md`, `docs/AGENT_ADAPTER_SCHEMA.md`, and `examples/agent_adapter_client.py` for external agent demos.

Recommended strategic framing:

- “CPOS Agent” = defensive agent runtime.
- “CPOS for Agents” = safety/memory/governance adapter layer for Codex/Hermes/OpenClaw/Claude Code-style agents.
- Current implementation proves both: it has native review pipelines and now accepts external agent contracts.

## Safety / policy reminders

- Secrets/API keys/tokens/SSH keys must stay in Vault.
- Never hardcode credentials in code, docs, comments, crontab, or `.env`.
- Never edit `authorized_keys`.
- `rm -rf`, destructive overwrites, systemd stop/delete require prior confirmation.
- Port opening requires explicit approval, Discord notice, and 15-minute auto-close.
- GitHub push/publish requires explicit human approval.
- Final `v0.1.0` was explicitly approved, tagged, pushed, and published on 2026-06-05.
