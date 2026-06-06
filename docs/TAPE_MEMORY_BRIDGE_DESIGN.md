# tape-memory Bridge Design — metadata-only resume pointers

This document describes a future CPOS bridge to tape-memory for fast resume and
low-token handoff. It is design-only; no runtime integration is enabled here.

## Purpose

Use tape-memory as a compact resume-pointer cache for CPOS state, not as a raw
log store. The bridge should help future agents quickly reconstruct:

- latest World Model snapshot status
- Goal Store validation/summary status
- Reflection Evaluator decision metadata
- current handoff pointer and next safe action

## Non-goals / hard boundaries

The bridge must not store or emit:

- API keys, tokens, SSH keys, passwords, OAuth material, or `.env` values
- raw command output, raw diffs, raw request bodies, raw DB rows, diary text, or phone data
- full handoff bodies or private repo content
- autonomous execution permissions or self-preservation goals

## Proposed pointer schema

```json
{
  "schema": "kagioneko.tape_memory_bridge_pointer.v1",
  "pointer_type": "cpos_resume",
  "repo": "kagioneko/cpos-engine-zero",
  "commit": "<git-commit-sha>",
  "world_model": {
    "overall_risk": "low|medium|high|critical",
    "known_risk_names": ["late_night_high_stakes_caution"]
  },
  "goal_store": {
    "validation_ok": true,
    "merged_goal_count": 0,
    "validation_error_codes": []
  },
  "reflection": {
    "last_recommendation": "proceed|ask|defer|block",
    "last_risk": "low|medium|high|critical"
  },
  "handoff": {
    "file": "NEXT_HANDOFF.md",
    "section": "Latest Handoff"
  },
  "metadata_only": true,
  "raw_request_stored": false,
  "raw_diff_stored": false,
  "raw_outputs_stored": false,
  "secret_values_stored": false,
  "execute_automatically": false
}
```

## Write policy

Initial implementation should be explicit and manual:

1. Build World Model / Goal Store / Reflection summaries locally.
2. Redact to the pointer schema above.
3. Run secret scan on the pointer payload before any tape-memory write.
4. Require human confirmation before enabling a write path.

Until then, CPOS may document pointer shapes and read-safe resume behavior only.

## Read policy

A future reader may consume pointer metadata to decide where to resume, but must
not treat tape-memory as authority for execution. High-stakes actions still route
through Human Escalation and current repository checks.


## Validator and dry-run write plan

The public CPOS implementation includes a validator and dry-run write plan only:

```bash
PYTHONPATH=. .venv/bin/python -m cpos.resume_pointer validate --pointer-json pointer.json --json
PYTHONPATH=. .venv/bin/python -m cpos.resume_pointer write-plan --pointer-json pointer.json --json
```

The validator checks that pointer safety flags remain metadata-only/no-execute,
that tape-memory writes are disabled, and that handoff bodies are not embedded.
The write plan is deliberately non-executing: `dry_run=true`, `would_write=false`,
and `write_enabled=false`. A real write path would require explicit human
confirmation and a secret scan immediately before writing.
