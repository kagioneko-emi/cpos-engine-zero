# CPOS for Agents — 5-minute External Agent Safety Layer Guide

Use CPOS Engine-Zero as a defensive runtime/safety layer beside another agent such as a Codex-like, Hermes-like, or OpenClaw-like system.

The shortest mental model:

> External agent proposes or reports work. CPOS records metadata-only evidence, routes risky work to Human Escalation, and never executes the external agent's commands by itself.

This guide is intentionally localhost-first and secret-free. It does not require opening public ports.

## 0. What CPOS does

CPOS accepts external-agent adapter payloads through `/agent-adapter/intake` and records a safety contract in Task Tape.

It stores:

- event type, agent name, risk, status, and review IDs
- changed file names and counts
- command/diff/result hashes and sizes
- redacted execution result summaries
- Human Escalation decisions and endpoint hints
- safety flags such as `execute_automatically=false`

It can show:

- pending external agent review contracts: `GET /agent-adapter/actions`
- external execution result scoreboard: `GET /agent-adapter/execution-results`
- unified Human Escalation queue: `GET /human-escalations`

## 1. What CPOS does not do

The External Agent Adapter is not a remote command executor.

It does not:

- execute external-agent commands
- apply patches or raw diffs
- commit, push, publish, or create PRs
- open network ports
- store raw request bodies, raw diffs, raw stdout/stderr, or checkpoint/handoff bodies
- store API keys, bearer tokens, OAuth tokens, passwords, Vault values, SSH keys, or `.env` values
- approve downstream execution automatically

Approval of an adapter action means “this metadata contract was reviewed”, not “run the command now”.

## 2. Start local CPOS

Use your normal local CPOS startup path. Keep it bound to localhost unless you have a separate approved deployment plan.

Example endpoint used below:

```bash
export CPOS_URL=http://127.0.0.1:8080
```

If your deployment requires a bearer token, render it from Vault into a local protected token file and pass it to the client with `--token-file`. Do not hardcode tokens in code, docs, shell history, crontab, `.env`, or examples.

## 3. Dry-run an adapter command request

Dry-run prints the JSON payload locally and does not contact CPOS:

```bash
python3 examples/agent_adapter_client.py \
  --base-url "$CPOS_URL" \
  --agent-name demo-agent \
  --command 'PYTHONPATH=. .venv/bin/python -m pytest tests/test_agent_adapter.py -q' \
  --changed-file cpos/agent_adapter.py \
  --changed-file tests/test_agent_adapter.py \
  command-request
```

Expected posture:

- command is represented as metadata
- adapter default is no automatic execution
- no secret material should appear in the payload

## 4. Send a command request contract

Use the checked-in secret-free payload example:

```bash
curl -sS -X POST "$CPOS_URL/agent-adapter/intake" \
  -H 'Content-Type: application/json' \
  --data @examples/payloads/command_request.json
```

Expected result:

- `ok=true`
- `contract.schema=cpos.external_agent_action_contract.v1`
- `contract.execute_automatically=false`
- `contract.raw_request_stored=false`
- `contract.raw_outputs_stored=false`
- `contract.secret_values_stored=false`
- `human_escalation.requires_human=true` for command requests

## 5. Check the external agent review queue

```bash
curl -sS "$CPOS_URL/agent-adapter/actions"
```

Look for:

- `metadata_only=true`
- `execute_automatically=false`
- contract hash and file/command counts
- approval/rejection endpoint hints

You can also check the unified Human Escalation queue:

```bash
curl -sS "$CPOS_URL/human-escalations"
```

The queue should identify external-agent reviews with `review_type=external_agent_action` and the `external_agent_adapter` owning pipeline.

## 6. Send a proposed diff contract

Use this when another agent wants CPOS to review a patch-shaped proposal.

```bash
curl -sS -X POST "$CPOS_URL/agent-adapter/intake" \
  -H 'Content-Type: application/json' \
  --data @examples/payloads/proposed_diff.json
```

Expected result:

- raw diff is accepted transiently only
- CPOS stores `input_digests.proposed_diff.sha256` and `size_bytes`
- CPOS does not apply the diff
- Human Escalation is required

## 7. Send an execution result summary

Use this when the external agent already performed work elsewhere and wants to report a redacted/status-only result.

```bash
curl -sS -X POST "$CPOS_URL/agent-adapter/intake" \
  -H 'Content-Type: application/json' \
  --data @examples/payloads/execution_result.json
```

Then inspect the scoreboard:

```bash
curl -sS "$CPOS_URL/agent-adapter/execution-results"
```

Expected scoreboard fields:

- completed/success/failure counts
- success rate
- failure kind counts
- result hash and size metadata
- `raw_outputs_stored=false`
- `secret_values_stored=false`

## 8. Validate raw-output rejection

The adapter rejects raw stdout/stderr style payloads before Task Tape persistence.

```bash
curl -sS -X POST "$CPOS_URL/agent-adapter/intake" \
  -H 'Content-Type: application/json' \
  --data @examples/payloads/invalid_raw_execution_result.json
```

Expected invalid result:

- HTTP `400`
- `error=schema_validation_failed`
- `validation.schema=cpos.external_agent_action_validation.v1`
- `validation.metadata_only=true`
- no raw stdout/stderr value echoed in the response

## 9. Safety invariant checklist

For every adapter integration, preserve these invariants:

```json
{
  "metadata_only": true,
  "raw_request_stored": false,
  "raw_diff_stored": false,
  "raw_outputs_stored": false,
  "secret_values_stored": false,
  "execute_automatically": false,
  "destructive_actions_performed": false
}
```

If an external agent needs sensitive material, pass a non-secret reference or Vault-backed identifier. Do not pass the secret value itself.

## 10. Next integration steps

After the 5-minute check works locally:

1. Decide which event types your external agent will send.
2. Keep the adapter payload schema in `docs/AGENT_ADAPTER_SCHEMA.md` as the contract source of truth.
3. Use `examples/payloads/` as fixtures for client tests.
4. Keep execution in a separately reviewed/gated pipeline.
5. Before push or publish, run the repo safety gate:

```bash
PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
```
