# CPOS Engine-Zero v0.1.2

> Draft only. Do not publish/tag without explicit human confirmation.

CPOS Engine-Zero v0.1.2 is a candidate safety-layer release focused on:

**Fast resume without raw logs.**

It adds a metadata-only resume pipeline that can summarize current state, validate
persisted goals, build a compact resume pointer, validate it, dry-run a
future tape-memory write plan, and attach a compact secret-pattern scan gate.

This release candidate does **not** enable real tape-memory writes, unrestricted
auto-execution, automatic publishing, or autonomous deployment.

## Highlights

### Metadata-only Resume Pipeline

New command:

```bash
PYTHONPATH=. .venv/bin/python -m cpos.resume_pipeline run \
  --goal-store goals/goals.example.json \
  --scan-compact \
  --json
```

The pipeline connects:

1. World Model snapshot
2. Reflection Evaluator
3. Resume Pointer
4. Resume Pointer validation
5. tape-memory write-plan dry run
6. compact secret-pattern scan

Compact output is intended for safe handoff, article, review, and future memory
preparation without raw logs or raw bodies.

### Goal Store validation path

- Goal Store validation summary in the World Model
- Reflection Evaluator gate for invalid stored goals
- metadata-only Goal Store summary/export
- no autonomous goal updates

### Resume Pointer and tape-memory preparation

- `cpos.resume_pointer build`
- `cpos.resume_pointer validate`
- `cpos.resume_pointer write-plan`
- safe heading-only handoff digest
- metadata-only reflection summary
- dry-run-only tape-memory write plan

The write plan remains:

```text
dry_run=true
would_write=false
write_enabled=false
```

### tape-memory write-gate design and mock writer

- Added design-only real write safety gate.
- Added test-only local mock writer for the gate.
- The mock writer is not a real tape-memory backend.
- It requires exact confirmation phrase:

```text
WRITE TAPE MEMORY RESUME POINTER
```

- Shorthand such as `ぷす`, `ok`, or `go` is rejected for memory writes.
- Pointer validation and secret scan must pass before mock write.
- Confirmation phrase is not stored in the mock output envelope.

### Vault-backed Notion and Zenn dry-run helpers

- Vault-backed Notion helper, dry-run by default
- Zenn-to-Notion bridge dry-run replacement path
- local Notion credential hygiene note
- Notion helper replacement plan
- Notion credential rotation runbook
- Zenn publish checklist

## Safety posture

v0.1.2 preserves CPOS safety boundaries:

- metadata-only outputs
- no raw request body persistence
- no raw diff persistence
- no raw stdout/stderr persistence
- no full handoff body persistence
- no DB row or Android/phone data persistence
- no secret value persistence
- no automatic commit/push/tag/release/publish
- no real tape-memory writes
- no real MCP tool execution by default
- no destructive cleanup

Not an AGI-completion claim. Public positioning should remain:

> Cognitive Agent OS / safety-first agent runtime / safety kernel for assisted autonomy.

## Validation

Latest local checks before this draft:

```text
PYTHONPATH=. .venv/bin/python -m pytest tests -q
426 passed

PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
ok=true
secret_scan ok=true count=0
```

Before publishing/tagging, confirm:

- remote is `https://github.com/kagioneko/cpos-engine-zero.git`
- working tree is clean
- full tests pass
- `prepublish_check --json` is OK
- `release_check --json` is OK
- secret scan reports `count=0`
- release wording avoids AGI-completion claims
- Notion credential hygiene / rotation note has been reviewed

Do not publish runtime ledgers, `.venv`, cache files, generated local reports,
workspace demos, certificates, `.env` files, API keys, OAuth tokens, SSH keys,
private keys, or secret material.
