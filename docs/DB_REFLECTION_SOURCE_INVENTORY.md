# DB Reflection Source Inventory — Draft

This is a documentation-only note for treating local DB files as possible reflection, goal-design, and prompt-evaluation sources.

It does not inspect DB contents.

## Why this matters

Some local repositories/tools may contain SQLite databases with useful signals for:

- goal-design experiments
- introspection prompt evaluation
- conversation/runtime state transitions
- NeuroState or spirit state histories
- multi-agent coordination traces

However, DBs can also contain credentials, personal logs, private prompts, OAuth tokens, chat histories, or publish/upload state.

## Safe initial posture

Initial CPOS integration should be inventory-only:

- path
- file size
- modified time
- database type if detectable
- table names only after explicit review
- row counts only after explicit review
- no row contents
- no prompt text
- no diary text
- no token/config values
- no credentials DB inspection

## Sensitive DB classes

Never inspect contents by default:

- cloud credentials DBs
- access token DBs
- browser/session/cookie DBs
- OAuth/client auth stores
- app DBs known to contain raw private chat or diary logs

## Candidate event types

- `db_source_inventory_available`
- `db_source_sensitive_skipped`
- `db_source_schema_summary_available`
- `db_reflection_review_required`
- `db_prompt_eval_source_candidate`

## Recommended path

1. Keep DB work documentation-only until reviewed.
2. Create a path-only DB inventory sensor.
3. Add denylist rules for credentials/tokens/cloud/browser/session paths.
4. Add optional schema-only inspection for explicitly approved DBs.
5. Only after review, derive redacted summaries for goal/introspection prompt research.

Potential first implementation, if approved later:

```text
cpos/sensors/db_inventory_sensor.py
```

The first implementation should not open DB files. It should only list candidate paths and mark sensitive classes as skipped.
