# External Agent Adapter Integration

CPOS can be used as a defensive runtime/safety layer for external agents such as Codex-like, Hermes-like, or OpenClaw-like systems.

The adapter is intentionally metadata-only. It accepts action contracts and result reports, then records hashes, counters, statuses, endpoint hints, and Human Escalation decisions in Task Tape. It does not execute commands for the caller.

## Schema reference

See `docs/AGENT_ADAPTER_SCHEMA.md` for field-level request/response examples and safety flags.

## Endpoints

- `POST /agent-adapter/intake` — submit an action contract or result report.
- `GET /agent-adapter/actions` — list pending external agent action reviews.
- `GET /agent-adapter/execution-results` — summarize metadata-only external execution results.
- `POST /agent-adapter/actions/<task_id>/approve` — approve contract metadata only; requires `confirm=true`.
- `POST /agent-adapter/actions/<task_id>/reject` — reject the contract.

## Supported event types

- `agent_intent`
- `proposed_action`
- `proposed_diff`
- `command_request`
- `execution_result`

## Payload examples and curl

Secret-free payload files are available under `examples/payloads/`:

- `examples/payloads/command_request.json`
- `examples/payloads/proposed_diff.json`
- `examples/payloads/execution_result.json`
- `examples/payloads/invalid_raw_execution_result.json`

Send a command request contract:

```bash
curl -sS -X POST http://127.0.0.1:8080/agent-adapter/intake \
  -H 'Content-Type: application/json' \
  --data @examples/payloads/command_request.json
```

Send a proposed diff contract:

```bash
curl -sS -X POST http://127.0.0.1:8080/agent-adapter/intake \
  -H 'Content-Type: application/json' \
  --data @examples/payloads/proposed_diff.json
```

Send a redacted/status-only execution result:

```bash
curl -sS -X POST http://127.0.0.1:8080/agent-adapter/intake \
  -H 'Content-Type: application/json' \
  --data @examples/payloads/execution_result.json
```

Check review queues and result scoreboard:

```bash
curl -sS http://127.0.0.1:8080/agent-adapter/actions
curl -sS http://127.0.0.1:8080/agent-adapter/execution-results
curl -sS http://127.0.0.1:8080/human-escalations
```

Validate the raw-output rejection path:

```bash
curl -sS -X POST http://127.0.0.1:8080/agent-adapter/intake \
  -H 'Content-Type: application/json' \
  --data @examples/payloads/invalid_raw_execution_result.json
```

Expected invalid result: HTTP `400`, `error=schema_validation_failed`, and `validation.metadata_only=true`. The response should not echo raw stdout/stderr values.

## Command request example

```json
{
  "agent_name": "codex-or-hermes",
  "event_type": "command_request",
  "commands": ["pytest tests -q"],
  "changed_files": ["README.md"],
  "metadata": {
    "risk": "medium",
    "requires_human_approval": true
  }
}
```

CPOS response contains `contract.schema=cpos.external_agent_action_contract.v1`, a `contract_sha256`, safety flags, and a Human Escalation decision when approval is required.

## Execution result example

```json
{
  "agent_name": "codex-or-hermes",
  "event_type": "execution_result",
  "execution_result": {
    "status": "failed",
    "output_redacted": true
  },
  "metadata": {
    "success": false,
    "exit_code": 1,
    "failure_kind": "validation_command",
    "duration_ms": 1200
  }
}
```

`execution_result` payloads are hashed for correlation. Store status/redaction metadata only; do not send raw stdout/stderr, raw diffs, secrets, tokens, or request bodies that should not be persisted.

## Safety invariants

Adapter records must keep these flags true/false:

- `metadata_only=true`
- `raw_request_stored=false`
- `raw_diff_stored=false`
- `raw_outputs_stored=false`
- `secret_values_stored=false`
- `execute_automatically=false`

Approval of an adapter action approves the metadata contract only. It does not run commands, apply patches, commit, push, create PRs, or open network ports.

## Local example client

Dry-run a command request:

```bash
python3 examples/agent_adapter_client.py \
  --base-url http://127.0.0.1:8080 \
  --agent-name demo-agent \
  --command 'pytest tests -q' \
  --changed-file README.md \
  command-request
```

Send to a local CPOS instance:

```bash
python3 examples/agent_adapter_client.py \
  --base-url http://127.0.0.1:8080 \
  --agent-name demo-agent \
  --command 'pytest tests -q' \
  --changed-file README.md \
  --send \
  command-request
```

For protected deployments, use a Vault-rendered token file:

```bash
python3 examples/agent_adapter_client.py --token-file /path/to/vault-rendered-token --send command-request
```

Do not hardcode bearer tokens, API keys, SSH keys, or passwords in code, docs, shell history, crontab, `.env`, or examples.
