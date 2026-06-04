## Start Here — 10-line Resume Card

1. `cd /home/mayutama/cpos_defensive_agent`
2. `git status --short --branch`
3. `PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json`
4. Expected state at handoff: `main...origin/main` after pushing this memo, clean tree, `prepublish_check ok=true`, secret scan `count=0`, full tests `318 passed`.
5. Correct remote: `origin https://github.com/kagioneko/cpos-engine-zero.git`; latest pushed commit before this memo: `840ee62 Update release docs test count`.
6. **Do not create final v0.1.0 tag yet** unlessねこさん explicitly says so. Existing remote/local RC tag: `v0.1.0-rc1` -> `0f1e585` from 2026-05-29.
7. Latest pushed work: External Agent Adapter MVP, adapter dashboard queue, Human Escalation integration, adapter demo readiness/fixture integration, plus prior Competitive Demo Readiness / Ready-to-Run / Patch Generation / tape-memory MCP review work.
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
Latest pushed commit: `840ee62 Update release docs test count`
Release/tag status: final **v0.1.0** tag has NOT been created yet. Existing remote/local release-candidate tag: `v0.1.0-rc1` -> `0f1e585 Prepare CPOS Engine-Zero for OSS release` from 2026-05-29.

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
- Full tests last verified: `318 passed`

## Latest pushed commits

Pushed to `origin main`:

1. `493c7ce Add external agent adapter MVP`
2. `4ee3d2e Add agent adapter to demo readiness`
3. `5d27190 Update handoff after agent adapter`
4. `840ee62 Update release docs test count`

Previous pushed handoff/tag status commit:

- `e7d641b Clarify v0.1 release tag status`

Release docs now record latest full test count: `318 passed`.

## What changed most recently

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

### Demo Readiness / Fixture Integration

`build_competitive_demo_readiness()` now includes:

- stage: `External Agent Adapter`
- count: `external_agent_actions`
- posture flag: `external_agent_adapter_available=true`
- next demo path includes `External Agent Adapter`

`create_competitive_demo_fixture()` now seeds one metadata-only `command_request` adapter review:

- agent: `demo-external-agent`
- command metadata: hashed only
- changed file: `README.md`
- `requires_human_approval=true`
- no command execution, no raw output storage

Updated tests in `tests/test_demo_readiness.py` assert the adapter appears in readiness and fixture output.

### Docs

`README.md` now has **External Agent Adapter MVP** with a minimal curl example:

- `POST /agent-adapter/intake`
- `GET /agent-adapter/actions`
- `GET /human-escalations`

## Verification at handoff

Latest verified commands:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/test_agent_adapter.py tests/test_dashboard.py tests/test_readme.py tests/test_human_escalation.py -q
# 46 passed

PYTHONPATH=. .venv/bin/python -m pytest tests -q
# 318 passed

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

Metadata-only demo path was exercised through the local Flask test client after pushing `840ee62`:

- `POST /demo/fixture` with `confirm=true`: `200 OK`, `ok=true`
- Fixture `step_count`: `15`
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
  - `External Agent Adapter`
  - `Human Escalation`
  - `Ready-to-Run`
  - `Sandbox Autonomy Flow Graph`

Important: demo fixture writes metadata-only Task Tape events; they are ignored runtime data and were not committed. Git status remained `main...origin/main` after demo/report checks.

## Current recommended next action

Recommended next session path:

1. Verify `git status --short --branch` and `prepublish_check`.
2. If this handoff memo is not pushed yet, push the memo commit after explicit approval.
3. Then choose one:
   - **Dashboard capture path**: open dashboard and capture Competitive Demo Readiness + External Agent Adapter Queue + Human Escalation + Ready-to-Run + Flow Graph; backend fixture/readiness/report are already verified.
   - **Release path**: prepare final `v0.1.0` only ifねこさん explicitly says so.
   - **Adapter expansion path**: add external-agent “execution_result” reporting to sandbox scoreboard/report.

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
- GitHub push/publish and final release tagging require explicit human approval.
- Do not create final `v0.1.0` tag unless explicitly instructed.
