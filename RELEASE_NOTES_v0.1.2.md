# CPOS Engine-Zero v0.1.2 Release Notes Draft

Draft date: 2026-06-07

Draft only. This is a release-notes draft only. It does not authorize a tag, GitHub Release,
publication, deployment, or real tape-memory write.

## Candidate theme

**Fast resume without raw logs.**

v0.1.2 is a candidate safety-layer release that turns the post-`v0.1.1-rc1`
resume work into a coherent metadata-only handoff and memory-preparation path.
It improves how CPOS summarizes current state, validates persisted goals,
packages safe resume pointers, and prepares future memory writes without storing
raw logs, raw diffs, full handoff bodies, phone/DB rows, private repo content,
or secrets.

## Highlights

### Goal Store and World Model integration

- Added a read-only Goal Store validator and metadata-only summary/export path.
- Connected Goal Store validation summaries into the World Model.
- Connected Goal Store validation to the Reflection Evaluator so invalid stored
  goals block reliance on persisted goals.
- Kept outputs compact: counts, IDs, states, and validation metadata only.

### Read-only resume pointer

- Added `cpos.resume_pointer build` for a stdout-only CPOS resume pointer.
- Added metadata-only reflection summary support.
- Added safe heading-only `NEXT_HANDOFF.md` digest support.
- Added `cpos.resume_pointer validate` for fail-closed pointer validation.
- Added `cpos.resume_pointer write-plan` for dry-run tape-memory write planning.

The write plan remains disabled:

```text
dry_run=true
would_write=false
write_enabled=false
```

### Integrated resume pipeline

- Added `cpos.resume_pipeline run` to connect:
  1. World Model snapshot
  2. Reflection Evaluator
  3. Resume Pointer
  4. Resume Pointer validation
  5. tape-memory write-plan dry run
- Added `--compact` for handoff/article/memory-friendly output.
- Added `--scan-compact` to attach a compact secret-pattern scan summary.
- Added `docs/V0_1_2_RESUME_PIPELINE_SUMMARY.md`.

Primary review command:

```bash
PYTHONPATH=. .venv/bin/python -m cpos.resume_pipeline run \
  --goal-store goals/goals.example.json \
  --scan-compact \
  --json
```

### tape-memory bridge and write-gate safety

- Documented a metadata-only tape-memory bridge design.
- Documented a design-only real write safety gate.
- Added a test-only local mock writer: `cpos.tape_memory_mock_writer`.
- The mock writer is not a tape-memory backend adapter.
- It writes only to an explicit existing local directory for tests.
- It requires the exact phrase `WRITE TAPE MEMORY RESUME POINTER`.
- It rejects shorthand such as `ぷす`, `ok`, or `go`.
- It validates the pointer and scans the payload before writing.
- It does not store the confirmation phrase in the output envelope.

No real tape-memory writes are enabled in this draft.

### Vault-backed Notion and Zenn bridge dry-runs

- Added `cpos.notion_vault_client` as a Vault-backed Notion helper.
- The Notion helper is dry-run by default and reads Vault only under `--execute`.
- Added local Notion credential hygiene notes and a replacement plan for older
  hardcoded helper scripts.
- Added Notion credential rotation runbook.
- Added `cpos.notion_zenn_bridge` as a safe dry-run replacement path for Zenn
  draft uploads to Notion.
- The Zenn-to-Notion bridge does not read Vault in dry-run mode and requires
  explicit `--execute` confirmation for any real Notion write.

### Public communication readiness

- Added a v0.1.2 readiness review.
- Added Zenn publish checklist.
- Continued public-safe positioning as a Cognitive Agent OS / safety kernel,
  not an unrestricted auto-execution agent and not an AGI-completion claim.

## Safety posture

v0.1.2 candidate work preserves these invariants:

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

Still not enabled by default:

- real tape-memory writes
- automatic memory sync
- automatic commit/push/tag/release/publish
- automatic live repo patching
- production deployment automation
- real MCP tool execution
- port opening automation
- destructive cleanup
- credential rotation automation
- `authorized_keys` changes

## Validation baseline

Latest local validation before this draft:

```text
PYTHONPATH=. .venv/bin/python -m pytest tests -q
426 passed

PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
ok=true
secret_scan ok=true count=0
destructive_actions_performed=false

git status --short
# clean
```

Before any actual `v0.1.2` tag or GitHub Release, re-run:

```text
git status --short --branch
PYTHONPATH=. .venv/bin/python -m pytest tests -q
PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
PYTHONPATH=. .venv/bin/python -m cpos.release_check --json
```

## Release blockers / cautions

Before publishing v0.1.2:

1. Obtain explicit human confirmation for tag/release creation.
2. Confirm remote is `https://github.com/kagioneko/cpos-engine-zero.git`.
3. Re-run full tests and release checks from a clean working tree.
4. Review public wording and avoid AGI-completion claims.
5. Review Notion credential hygiene and rotate older exposed Notion credentials
   if practical.
6. Confirm no runtime ledgers, caches, `.venv`, certs, `.env`, API keys,
   OAuth tokens, SSH keys, private keys, or secret material are tracked.
7. Do not release late-night without extra confirmation.

## Related docs

- `docs/V0_1_2_READINESS_REVIEW.md`
- `docs/V0_1_2_RESUME_PIPELINE_SUMMARY.md`
- `docs/TAPE_MEMORY_BRIDGE_DESIGN.md`
- `docs/TAPE_MEMORY_REAL_WRITE_GATE_DESIGN.md`
- `docs/VAULT_BACKED_NOTION_HELPER.md`
- `docs/ZENN_TO_NOTION_BRIDGE_DRY_RUN.md`
- `docs/NOTION_CREDENTIAL_ROTATE_RUNBOOK.md`
- `docs/ZENN_COGNITIVE_AGENT_OS_PUBLISH_CHECKLIST.md`
- `docs/backlog/V0_1_2_BACKLOG.md`
