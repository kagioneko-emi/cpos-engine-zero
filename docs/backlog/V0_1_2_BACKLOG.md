# CPOS Engine-Zero v0.1.2 Backlog Ideas

This is an ideas-only backlog created after `v0.1.1-rc1` was published as a prerelease.

Do not start implementation from this file automatically. Treat it as a parking lot for future planning after the `v0.1.1` RC observation period.

## Guiding rule

Keep the CPOS safety posture intact:

- no automatic live repo patching by default
- no automatic commit/push/PR creation
- no real MCP tool execution by default
- no production deployment automation
- no port opening automation
- no destructive cleanup
- no `authorized_keys` changes
- no secret values, raw diffs, raw stdout/stderr, raw request bodies, or cert/key material in persisted docs/runtime surfaces

## Candidate Priority 1 — Adapter contract schema export

Goal: make External Agent Adapter integration easier for external clients.

Ideas:

- Add machine-readable JSON Schema for `/agent-adapter/intake` payloads.
- Add schema for successful contract response.
- Add schema for validation error response.
- Keep examples aligned with `examples/payloads/`.

Acceptance notes:

- Secret-free schema files only.
- Tests validate example payloads against schemas if a lightweight dependency-free path is available.

## Candidate Priority 2 — Adapter mini SDK / client helpers

Goal: reduce boilerplate for external agents.

Ideas:

- Extend `examples/agent_adapter_client.py` with payload-file send mode.
- Add helper commands for `proposed-diff` and invalid validation demo.
- Consider a tiny `cpos.agent_adapter_client` module only if it does not pull runtime dependencies.

Acceptance notes:

- Stdlib-first.
- No token printing.
- Token file remains Vault-rendered / local protected file only.

## Candidate Priority 3 — OpenAPI-style endpoint reference

Goal: make CPOS for Agents easier to understand from API docs.

Ideas:

- Add `docs/API_EXTERNAL_AGENT_ADAPTER.md` or an OpenAPI-lite Markdown table.
- Include endpoint, method, auth posture, request body, response body, and safety invariants.
- Link from README and 5-minute guide.

Acceptance notes:

- Do not imply public deployment or open ports.
- Keep localhost/protected deployment examples.

## Candidate Priority 4 — Demo video / script guide

Goal: make the safe autonomy / CPOS for Agents demo repeatable.

Ideas:

- Add `docs/DEMO_SCRIPT_CP0S_FOR_AGENTS.md` or similar.
- 5-minute screen-flow: start local server, submit payload, show queue, show Human Escalation, show scoreboard, show no raw-output rejection.
- Include screenshot checklist.

Acceptance notes:

- No real secrets.
- No public ports required.
- No final release/publish actions.

## Candidate Priority 5 — GitHub Actions safety checks

Goal: move some local safety checks into CI.

Ideas:

- Run tests or a reduced safe subset on PRs.
- Run secret scan on tracked files.
- Run release_check-like artifact checks where possible.

Acceptance notes:

- Avoid adding credentials.
- Do not require external secret setup for basic checks.
- Do not publish releases from CI by default.

## Candidate Priority 6 — External agent integration profiles

Goal: document integration patterns by agent type.

Ideas:

- Codex-like local coding assistant profile.
- Hermes-like orchestrator profile.
- OpenClaw-like external tool runner profile.
- For each: what to send, what not to send, how to handle results.

Acceptance notes:

- Avoid claiming official integration unless it exists.
- Use “-like” language unless verified.
- Keep examples metadata-only.

## Candidate Priority 7 — Final v0.1.1 release follow-through

Goal: safely move from `v0.1.1-rc1` to final `v0.1.1` if no issues appear.

Steps:

1. Re-run full verification.
2. Review `v0.1.1-rc1` prerelease for issues.
3. Confirm release notes and draft body.
4. Only after explicit user confirmation, create final tag/release.

Commands to run before final release consideration:

```bash
git status --short --branch
PYTHONPATH=. .venv/bin/python -m pytest tests -q
PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
PYTHONPATH=. .venv/bin/python -m cpos.release_check --json
gh release view v0.1.1-rc1 --repo kagioneko/cpos-engine-zero --json tagName,isDraft,isPrerelease,url,name
```

## Parking lot

- Better dashboard labels for first-time demos.
- More generated report snippets for CPOS for Agents.
- Optional diagrams for adapter flow.
- More Zenn/Notion copy based on the RC feedback.


## Implemented during post-RC exploration — Resume Pipeline stabilization

These items were implemented after the original v0.1.2 parking lot was created.
They should be treated as completed seed work to review before cutting any future
v0.1.2 plan or release.

Completed pieces:

- Goal Store validation summary in World Model.
- Reflection Evaluator consumption of Goal Store validation.
- Goal Store metadata-only summary/export output.
- tape-memory bridge design, still no runtime writes.
- read-only Resume Pointer CLI.
- safe heading-only handoff digest.
- Resume Pointer validator.
- tape-memory write dry-run plan.
- integrated `cpos.resume_pipeline run` bundle.
- compact `cpos.resume_pipeline run --compact` output for handoff/article use.

Safety status:

- still read-only / metadata-only
- no tape-memory writes
- no automatic commit/push/release/publish
- no raw command output, raw diffs, request bodies, full handoff bodies, DB rows, Android/phone data, or secrets

Future candidates from here:

1. Secret-scan a compact pipeline payload before any future memory write path.
2. Add docs-only examples for external agents consuming compact pipeline JSON.
3. Add Zenn/README narrative around “fast resume without raw logs.”
4. Keep real tape-memory writes behind explicit human confirmation.
