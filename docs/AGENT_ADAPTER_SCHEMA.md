# External Agent Adapter Schema

This document defines the public metadata contract for `/agent-adapter/intake`.

The adapter is a safety/governance boundary, not an execution service. Inputs should be metadata-rich and secret-free. CPOS persists hashes, sizes, counters, statuses, endpoint hints, and safety flags only.

## Common request envelope

```json
{
  "agent_name": "codex-or-hermes",
  "event_type": "command_request",
  "intent": null,
  "proposed_action": null,
  "proposed_diff": null,
  "commands": [],
  "execution_result": null,
  "changed_files": [],
  "metadata": {}
}
```

### Common fields

| Field | Type | Required | Notes |
|---|---:|---:|---|
| `agent_name` | string | no | Defaults to `external-agent`. |
| `event_type` | string | yes | One of `agent_intent`, `proposed_action`, `proposed_diff`, `command_request`, `execution_result`. |
| `intent` | any | no | Intent metadata. Persisted as digest only. |
| `proposed_action` | any | no | Proposed action metadata. Persisted as digest only. |
| `proposed_diff` | string | no | Raw diff is accepted transiently and persisted as digest/size only. |
| `commands` | string[] | no | Command metadata. Do not include secrets. Persisted as digests only. |
| `execution_result` | object | no | Result metadata/redacted payload. Persisted as digest/size only. |
| `changed_files` | string[] | no | File path metadata. |
| `metadata` | object | no | Risk flags, result counters, client name, duration, etc. |

## Event types

### `command_request`

Use when an external agent wants CPOS to review a command plan before execution.

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

Expected behavior:

- `adapter_decision=requires_review`
- Human Escalation is created.
- No command is executed.
- Command strings are stored as hashes/sizes in the contract.

### `proposed_diff`

Use when an external agent wants CPOS to review a diff before it enters the normal diff/sandbox pipeline.

```json
{
  "agent_name": "diff-agent",
  "event_type": "proposed_diff",
  "proposed_diff": "diff --git ...",
  "changed_files": ["server.py"],
  "metadata": {
    "risk": "medium",
    "requires_human_approval": true
  }
}
```

Expected behavior:

- Raw diff is not persisted.
- `input_digests.proposed_diff` stores `sha256` and `size_bytes` only.
- Human approval is required.

### `execution_result`

Use when an external agent reports a result from work it performed elsewhere.

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

Expected behavior:

- Result contributes to `/agent-adapter/execution-results` scoreboard.
- Raw stdout/stderr must not be sent and are not persisted.
- The result payload is stored as digest/size only.

## Schema validation

`POST /agent-adapter/intake` validates the request shape before any Task Tape event is written. Invalid requests return `400` with `error=schema_validation_failed` and a metadata-only validation report. The response lists field names and error codes only; it does not echo raw commands, raw diffs, raw stdout/stderr, or secret-looking values.

Validation rules:

- `event_type` must be one of `agent_intent`, `proposed_action`, `proposed_diff`, `command_request`, `execution_result`.
- `commands` and `changed_files`, when present, must be arrays of strings.
- `command_request` requires at least one command string. Commands are never executed by the adapter.
- `proposed_diff` requires a non-empty string. The raw diff is accepted transiently only and persisted as digest/size on valid intake.
- `metadata.risk`, when present, must be `low`, `medium`, `high`, or `critical`.
- Boolean metadata flags such as `requires_human_approval`, `touches_secrets`, `touches_production`, `destructive`, and `success` must be booleans when present.
- `metadata.exit_code` and `metadata.duration_ms` must be integers when present.
- `execution_result` must be a redacted/status-only object. Keys such as `stdout`, `stderr`, `output`, `raw_output`, `logs`, and `traceback` are rejected.

Example invalid response:

```json
{
  "ok": false,
  "error": "schema_validation_failed",
  "validation": {
    "schema": "cpos.external_agent_action_validation.v1",
    "ok": false,
    "errors": [
      {
        "code": "commands_must_be_string_array",
        "field": "commands",
        "message": "commands must be an array of strings when provided."
      }
    ],
    "metadata_only": true,
    "raw_request_stored": false,
    "raw_diff_stored": false,
    "raw_outputs_stored": false,
    "secret_values_stored": false,
    "execute_automatically": false
  },
  "execute_automatically": false
}
```

## Response contract

Successful intake returns:

```json
{
  "ok": true,
  "task_id": "task_...",
  "status": "pending_review",
  "contract": {
    "schema": "cpos.external_agent_action_contract.v1",
    "agent_name": "codex-or-hermes",
    "event_type": "command_request",
    "risk": "medium",
    "changed_files": ["README.md"],
    "changed_file_count": 1,
    "command_count": 1,
    "input_digests": {
      "intent": null,
      "proposed_action": null,
      "proposed_diff": null,
      "commands": [{"sha256": "...", "size_bytes": 15}],
      "execution_result": null
    },
    "result_summary": null,
    "adapter_decision": "requires_review",
    "requires_human_approval": true,
    "execute_automatically": false,
    "raw_request_stored": false,
    "raw_diff_stored": false,
    "raw_outputs_stored": false,
    "secret_values_stored": false,
    "destructive_actions_performed": false,
    "contract_sha256": "..."
  },
  "human_escalation": {
    "schema": "cpos.human_escalation_decision.v1",
    "review_type": "external_agent_action",
    "requires_human": true
  },
  "execute_automatically": false
}
```

## Execution result scoreboard

`GET /agent-adapter/execution-results` returns:

```json
{
  "ok": true,
  "schema": "cpos.external_agent_result_scoreboard.v1",
  "completed_results": 1,
  "success_results": 0,
  "failure_results": 1,
  "success_rate": 0.0,
  "failure_kind_counts": {"validation_command": 1},
  "recent_results": [],
  "metadata_only": true,
  "raw_outputs_stored": false,
  "secret_values_stored": false,
  "execute_automatically": false
}
```

## Safety flags

Every adapter record should preserve:

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

## Prohibited input content

Do not send or persist:

- API keys, bearer tokens, OAuth tokens, passwords, private certs, SSH keys, or Vault values
- raw stdout/stderr
- raw request bodies that contain secrets
- `.env` values
- unredacted production credentials
- `authorized_keys` changes

If the agent needs to reference sensitive material, use Vault-backed identifiers or non-secret metadata only.
