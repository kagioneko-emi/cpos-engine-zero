# CPOS Engine-Zero Demo Capture Guide

Use this guide to capture screenshots or a short GIF without exposing secrets, runtime ledgers, raw diffs, raw outputs, or local-only artifacts.

## Recommended capture story

Capture in this order so the viewer immediately understands why CPOS is different from unrestricted coding agents:

1. **Competitive Demo Readiness**
   - Show `ready=true`, ready stages, safety flags, and demo path.
   - This is the strongest opening shot.
2. **External Agent Adapter Queue**
   - Show external agent contract metadata, result scoreboard, risk, command/file counts, contract hash, and `execute_automatically=false`.
   - This proves CPOS can act as a defensive runtime/safety layer for Codex/Hermes/OpenClaw-style agents.
3. **Human Escalation Queue**
   - Show owning pipeline, stage, approve/reject endpoint hints, and flow hints.
4. **Patch Generation Reviews**
   - Show generated-patch review state and metadata-only guardrails.
5. **Ready-to-Run Execution Reviews**
   - Show that CPOS can prepare execution but still separates final run approval.
6. **Sandbox Autonomy Flow Graph**
   - Show failure → retry/replan → auto fix candidate → patch generation/diff draft → ready-to-run lineage.
7. **Execution Scoreboard**
   - Show completed/success/failure counts, failure kinds, and replay load.
8. **Generated Report: Competitive Demo Readiness + Autonomy Loop Snapshot**
   - Use as static audit/release proof.

## Safety rules before capture

Before saving or publishing an image/GIF:

- Do not include API keys, OAuth tokens, bearer tokens, SSH keys, private certs, passwords, or `.env` values.
- Do not include raw diff text, raw stdout/stderr, request bodies, checkpoint contents, or raw handoff bodies.
- Do not capture runtime JSONL ledgers, local filesystem secret paths, Vault values, or terminal output containing secrets.
- Prefer metadata-only demo data: task IDs, statuses, hashes, sizes, counts, failure kinds, endpoint hints, and safety flags.
- Crop browser chrome if it shows local usernames, private URLs, ports, or unrelated tabs.
- Review the final asset before committing. Generated local reports/screenshots must be explicitly reviewed before staging.

## Recommended local flow

1. Confirm repo safety state:

   ```bash
   git status --short --branch
   PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
   ```

2. Seed safe metadata-only demo data if needed:

   ```bash
   curl -X POST http://127.0.0.1:<port>/demo/fixture \
     -H 'Content-Type: application/json' \
     -d '{"confirm":true,"reason":"demo_capture"}'
   ```

   This writes demo Task Tape events only. It does not execute tools, apply patches, mutate the live repo, commit, push, create PRs, or store raw diffs/outputs.

3. Confirm readiness:

   ```bash
   curl http://127.0.0.1:<port>/demo/readiness
   ```

   Look for:

   - `ready=true`
   - `metadata_only=true`
   - `raw_diff_stored=false`
   - `raw_outputs_stored=false`
   - `approval_separated_from_execution=true`
   - nonzero `external_agent_actions`, `human_escalations`, `ready_to_run_reviews`, `patch_generation_reviews`, and `flow_nodes` after fixture creation

4. Open the dashboard and capture:

   - `Competitive Demo Readiness`
   - `External Agent Adapter Queue`
   - `Human Escalation Queue`
   - `Patch Generation Reviews`
   - `Ready-to-Run Execution Reviews`
   - `Sandbox Autonomy Flow Graph`
   - `Execution Scoreboard`

5. Generate a report and capture:

   - `Competitive Demo Readiness`
   - `Autonomy Loop Demo Snapshot`
   - `Sandbox Autonomy Flow Graph`
   - `External Agent Adapter Queue`
   - `Human Escalation Queue`

6. Store reviewed assets under a reviewed docs path, for example:

   ```text
   docs/assets/demo/competitive-demo-readiness.png
   docs/assets/demo/external-agent-adapter-queue.png
   docs/assets/demo/human-escalation-queue.png
   docs/assets/demo/patch-generation-review.png
   docs/assets/demo/ready-to-run-gate.png
   docs/assets/demo/sandbox-flow-graph.png
   docs/assets/demo/report-demo-readiness.png
   ```

7. Re-run release checks before committing images:

   ```bash
   PYTHONPATH=. .venv/bin/python -m pytest tests -q
   PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
   ```

## Suggested 30-second GIF storyboard

1. Start on **Competitive Demo Readiness**: all readiness stages and safety pills visible.
2. Click **Create Metadata-only Demo Fixture** if showing from a blank state.
3. Show **External Agent Adapter Queue**: external agent actions become metadata-only contracts.
4. Show **Human Escalation Queue**: approval routing is first-class.
5. Show **Patch Generation Reviews** and **Ready-to-Run Execution Reviews**: generated patch path and final run gate are separate.
6. Focus **Sandbox Flow Graph**: failure-to-replan lineage is visible.
7. End on **Generated Report** with safety flags.

## Latest verified backend demo counts

Last verified on 2026-06-05 after `POST /demo/fixture`:

- readiness: `ready=true`, `ready_count=9`, `stage_count=9`
- `external_agent_actions=1`
- `external_agent_results=1` after the latest fixture path
- `human_escalations=5`
- `ready_to_run_reviews=2`
- `patch_generation_reviews=2`
- `flow_nodes=12`
- `fast_resume_keys=13`
- safety flags: `metadata_only=true`, `raw_diff_stored=false`, `raw_outputs_stored=false`, `raw_request_stored=false`, `secret_values_stored=false`, `execute_automatically=false`
- generated report contains: Competitive Demo Readiness, External Agent Adapter result scoreboard, Human Escalation, Ready-to-Run, Sandbox Autonomy Flow Graph

## Caption template

> CPOS Engine-Zero safe autonomy loop: fast-resume, external-agent-ready, review-gated, sandbox-first, metadata-only, and failure-to-replan aware. Raw diffs, raw stdout/stderr, secrets, live repo patches, commits, pushes, and PR creation are excluded from the automated loop.
