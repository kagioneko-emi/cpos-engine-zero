# tape-memory Backend Interface Design

Date: 2026-06-08

## Status

Design only. No real tape-memory backend adapter is implemented or enabled by
this document.

Current implementation remains:

```text
resume pipeline: dry-run only
write plan: dry_run=true, would_write=false, write_enabled=false
mock writer: local_mock_file_for_tests_only, real_tape_memory_write=false
real backend: not implemented
```

## Purpose

Define the minimum interface shape for a future tape-memory backend adapter
without granting write authority.

This is the step between the test-only mock writer and any possible real backend
integration.

## Non-goals

- No real tape-memory write implementation.
- No background sync.
- No automatic memory write after sessions.
- No ingestion of full chat logs, raw diffs, raw outputs, DB rows, phone data,
  private repo content, or secrets.
- No shortcut confirmation such as `ぷす`, `ok`, or `go`.
- No credential loading in design-only or dry-run paths.

## Proposed protocol

A future backend adapter should satisfy a narrow protocol:

```python
class TapeMemoryBackendProtocol:
    def write_resume_pointer(
        self,
        *,
        pointer: dict,
        validation: dict,
        secret_scan: dict,
        target: dict,
        confirmation: dict,
        audit: dict,
    ) -> dict:
        ...
```

The protocol returns metadata only:

```json
{
  "ok": true,
  "backend": "tape-memory",
  "record_type": "cpos_resume_pointer",
  "record_id": "metadata-only-id-or-key",
  "payload_sha256": "...",
  "validation_ok": true,
  "secret_scan_ok": true,
  "real_tape_memory_write": true,
  "raw_payload_echoed": false
}
```

## Required inputs

A real backend adapter must receive all inputs explicitly:

- resume pointer payload
- pointer validation result
- compact secret scan result
- explicit target backend and record type
- exact human confirmation result
- metadata-only audit envelope

The adapter must not infer target, confirmation, or credential source from raw
chat/session context.

## Required preconditions

Fail closed unless all are true:

- `validate_resume_pointer(pointer).ok == true`
- compact secret scan exists
- compact secret scan count is `0`
- target backend is explicit
- target record type is `cpos_resume_pointer`
- exact confirmation phrase was accepted:
  `WRITE TAPE MEMORY RESUME POINTER`
- confirmation phrase itself is not stored in output
- payload is metadata-only
- no raw logs, raw diffs, raw outputs, request bodies, DB rows, Android/phone
  data, private repo content, or secrets are present

## Confirmation boundary

The backend interface must not accept routine workflow shorthand.

Allowed for future real memory write:

```text
WRITE TAPE MEMORY RESUME POINTER
```

Rejected for memory write:

```text
ぷす
ok
go
yes
```

## Credential boundary

Any future credentials must come from Vault or a backend-specific approved secret
source. They must not be passed through:

- CLI flags
- `.env` files
- docs
- logs
- test fixtures
- committed config
- chat transcript snippets

Design-only and mock paths must not read credentials.

## Audit envelope

A future write should record metadata only:

- timestamp
- repo name
- commit hash
- pointer schema
- pointer type
- target backend name
- target record type
- payload hash
- validation result
- secret scan count and pattern names only
- confirmation accepted boolean or hash, not the raw phrase

It must not store raw command output, raw diffs, raw request bodies, secrets, or
full handoff bodies.

## Failure behavior

Return a structured failure without writing when:

- validation is missing or false
- secret scan is missing or non-zero
- confirmation phrase is absent or mismatched
- target is ambiguous
- backend credentials are unavailable
- payload is not metadata-only
- write result attempts to echo raw payload or secrets

## Suggested implementation phases

1. Keep current mock writer as the only writer.
2. Add a pure interface module with `Protocol` and validators only.
3. Add tests that prove invalid inputs fail before any backend call.
4. Add an in-memory fake backend for tests only.
5. Add a Vault-backed real backend adapter only after explicit approval.
6. Re-run full tests, `prepublish_check`, `release_check`, and manual review.
7. Require explicit confirmation before enabling any real write path.

## Relationship to existing docs

- `docs/TAPE_MEMORY_BRIDGE_DESIGN.md` defines the metadata-only bridge.
- `docs/TAPE_MEMORY_REAL_WRITE_GATE_DESIGN.md` defines the real-write safety gate.
- `cpos/tape_memory_mock_writer.py` tests the gate locally only.
- This document defines the future backend interface boundary before any real
  adapter exists.


## Current foundation module

`cpos/tape_memory_backend.py` now provides the test-only in-memory fake backend foundation and the `TapeMemoryBackendProtocol`. It remains metadata-only and does not implement a real tape-memory backend.
