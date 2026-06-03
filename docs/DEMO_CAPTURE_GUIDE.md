# CPOS Engine-Zero Demo Capture Guide

Use this guide to capture screenshots or a short GIF for the v0.1.0 release without exposing secrets, runtime ledgers, or local-only artifacts.

## Capture targets

Recommended order for release screenshots/GIFs:

1. **Autonomy Loop Demo Panel**
   - Shows the safe execution loop in one screen.
   - Best first image for README/release notes.
2. **Sandbox Autonomy Flow Graph**
   - Shows failure -> retry/replan -> candidate -> diff draft -> GitHub diff review lineage.
3. **Execution Scoreboard**
   - Shows completed/success/failure counts, success rate, failure kinds, and replay load.
4. **Human Escalation Queue**
   - Shows owning pipeline, stage, endpoint hints, and flow hints without raw request data.
5. **Generated Report: Autonomy Loop Demo Snapshot**
   - Good for audit/release proof because it is static HTML.

## Safety rules before capture

Before saving or publishing an image/GIF:

- Do not include API keys, OAuth tokens, bearer tokens, SSH keys, private certs, passwords, or `.env` values.
- Do not include raw diff text, raw stdout/stderr, request bodies, checkpoint contents, or raw handoff bodies.
- Do not capture runtime JSONL ledgers, local filesystem secret paths, or Vault values.
- Prefer metadata-only demo data: task IDs, statuses, hashes, sizes, counts, failure kinds, and safety flags.
- Crop browser chrome if it shows local usernames, paths, private URLs, or ports.
- Review the final asset before committing. Generated local reports/screenshots must be explicitly reviewed before staging.

## Recommended local flow

1. Confirm repo safety state:

   ```bash
   git status --short --branch
   PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
   ```

2. Start CPOS locally using the project’s normal local-dev path.

   - Do not open public ports for screenshots.
   - If a port must be exposed beyond localhost, follow the project rule: explicit approval, auto-close after 15 minutes, and Discord notification.

3. Open the dashboard and capture:

   - `Autonomy Loop Demo Panel`
   - `Sandbox Autonomy Flow Graph`
   - `Execution Scoreboard`
   - `Human Escalation Queue`

4. Generate a report and capture:

   - `Autonomy Loop Demo Snapshot`
   - `Sandbox Autonomy Flow Graph`
   - `Human Escalation Queue`

5. Store reviewed assets under a reviewed docs path, for example:

   ```text
   docs/assets/demo/autonomy-loop-panel.png
   docs/assets/demo/sandbox-flow-graph.png
   docs/assets/demo/execution-scoreboard.png
   docs/assets/demo/report-demo-snapshot.png
   ```

6. Re-run release checks before committing images:

   ```bash
   PYTHONPATH=. .venv/bin/python -m pytest tests -q
   PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
   ```

## Suggested GIF storyboard

A 20-30 second GIF should show:

1. Autonomy Loop Demo Panel overview.
2. Click/focus into a failed sandbox execution’s Flow Graph.
3. Show `Create Retry -> Replan -> Diff Intake + Focus Flow` as the recovery path.
4. Show Execution Scoreboard updated counts.
5. End on Report Demo Snapshot safety flags.

## Caption template

Use this caption for README or GitHub Release assets:

> CPOS Engine-Zero safe autonomy loop: review-gated, sandbox-first, metadata-only, and failure-to-replan aware. Raw diffs, raw stdout/stderr, secrets, commits, pushes, and PR creation are excluded from the automated loop.
