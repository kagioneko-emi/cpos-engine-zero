# tape-memory Real Write Gate Design

Date: 2026-06-07

## Status

Design only. No real tape-memory write implementation is enabled by this document.

Current CPOS behavior remains:

```text
dry_run = true
would_write = false
write_enabled = false
```

## Purpose

Define the minimum safety gate required before CPOS may write a compact resume
pointer to tape-memory.

The goal is **fast resume without raw logs**, not unrestricted memory writes.

## Hard preconditions for any future write

A future real write path must require all of the following:

1. Pointer is generated from compact/metadata-only Resume Pipeline output.
2. Pointer validation passes.
3. Compact payload secret scan passes immediately before writing.
4. Human explicitly confirms a confirmation phrase.
5. The write target is explicit and not inferred from private/raw context.
6. An audit record is created without storing raw payload bodies or secrets.
7. The operation remains non-destructive and does not grant future autonomous write authority.

## Confirmation phrase

Recommended phrase:

```text
WRITE TAPE MEMORY RESUME POINTER
```

A future CLI should require an exact flag such as:

```bash
--confirm-write "WRITE TAPE MEMORY RESUME POINTER"
```

Shorthand such as `ぷす`, `ok`, or `go` must not be accepted for real memory
writes. Shorthand may be acceptable for Git push in this workflow, but not for
credential rotation, publishing, release, or real memory writes.

## Required pre-write checks

A future write command must fail closed unless all checks pass:

- `resume_pointer_validation.ok == true`
- `compact_secret_scan.ok == true`
- `tape_memory_write_plan.validation_ok == true`
- `tape_memory_write_plan.would_write == false` before confirmation
- `tape_memory_write_plan.write_enabled == false` before confirmation
- current repo safety check is clean when the pointer references repo state
- payload contains no raw logs, raw diffs, request bodies, full handoff bodies,
  DB rows, Android/phone data, private repo content, or secrets

## Proposed command shape

Dry-run remains the default:

```bash
PYTHONPATH=. .venv/bin/python -m cpos.resume_pipeline run \
  --goal-store goals/goals.example.json \
  --scan-compact \
  --json
```

A future write command should be separate and explicit, for example:

```bash
PYTHONPATH=. .venv/bin/python -m cpos.tape_memory_writer write \
  --pipeline-json compact-pipeline.json \
  --confirm-write "WRITE TAPE MEMORY RESUME POINTER" \
  --json
```

This writer does not exist yet.

## Audit requirements

A future write must record metadata only:

- timestamp
- repo name
- commit hash
- pointer schema
- pointer type
- validation result
- secret scan count/pattern names only
- target record ID or pointer key
- confirmation phrase hash or boolean, not the raw phrase if avoidable

It must not store:

- raw pointer payload body if the tape-memory backend already stores it
- raw command output
- raw diff
- request body
- Notion/Discord/GitHub/Vault credentials
- DB rows or phone data

## Rollback and deletion caveat

Memory writes may be practically append-only or difficult to fully erase from
backups/logs. Therefore the UX must warn:

> Memory writes may be difficult to fully roll back. Confirm only after secret
> scan and payload validation pass.

If deletion is supported by the backend, deletion should be a separate explicit
human-confirmed operation. Do not rely on deletion as the primary safety control.

## Failure behavior

Fail closed when:

- validation is missing or false
- secret scan is missing or false
- confirmation phrase is absent or mismatched
- target backend is ambiguous
- payload is not compact/metadata-only
- any secret-like pattern is detected
- current session is late-night and the user has not reconfirmed

## Non-goals

- No automatic write after every session.
- No background memory sync.
- No ingestion of full chat logs.
- No raw database reflection content.
- No self-preservation memory goals.
- No bypass of Human Escalation.

## Recommended implementation phases

1. Keep current dry-run design as-is.
2. Add tests for confirmation phrase and fail-closed behavior before writing any backend adapter.
3. Add a mock writer that writes to a temp file in tests only.
4. Add backend adapter only after explicit approval.
5. Run full tests, prepublish, and manual review before enabling any real write path.

## Test-only mock writer

The test-only mock writer exists to exercise the safety gate without connecting
to tape-memory:

```bash
PYTHONPATH=. .venv/bin/python -m cpos.tape_memory_mock_writer write \
  --pointer-json pointer.json \
  --output-dir /tmp/cpos-tape-memory-mock \
  --confirm-write "WRITE TAPE MEMORY RESUME POINTER" \
  --json
```

Safety properties:

- backend is `local_mock_file_for_tests_only`
- `real_tape_memory_write = false`
- output directory must already exist and be explicit
- exact confirmation phrase is required
- `ぷす`, `ok`, or `go` are rejected
- pointer validation must pass
- payload secret scan must pass
- confirmation phrase is not stored in the output envelope

This mock writer is not a tape-memory adapter and does not grant permission to
enable a real writer.
