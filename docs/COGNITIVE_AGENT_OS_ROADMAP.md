# Kagioneko Cognitive Agent OS — Roadmap Draft

This roadmap turns the documentation chain into a safe implementation path.

Current doc chain:

1. `docs/COGNITIVE_AGENT_OS_ARCHITECTURE.md`
2. `docs/SENSOR_AND_GOAL_MANAGER_SPEC.md`
3. `docs/EVENT_BUS_AND_WORLD_MODEL_SPEC.md`

This roadmap is still documentation-only. It does not start implementation.

## Release posture

CPOS Engine-Zero currently has `v0.1.1-rc1` published as a prerelease.

Final `v0.1.1` remains paused until explicit user confirmation and a fresh readiness pass.

Before any final release:

```bash
git status --short --branch
PYTHONPATH=. .venv/bin/python -m pytest tests -q
PYTHONPATH=. .venv/bin/python -m cpos.prepublish_check --json
PYTHONPATH=. .venv/bin/python -m cpos.release_check --json
gh release view v0.1.1-rc1 --repo kagioneko/cpos-engine-zero --json tagName,isDraft,isPrerelease,url,name
```

## Phase 0 — Documentation and pause

Status: current phase.

Goals:

- Keep CPOS final `v0.1.1` paused after RC.
- Keep VN-CPU/UNO observe-only.
- Keep all Cognitive Agent OS work doc-only until reviewed.
- Preserve the origin story and safety framing.

Completed docs:

- Cognitive Agent OS architecture draft
- Sensor and Goal Manager spec
- Event Bus and World Model spec
- v0.1.2 parked ideas backlog
- next-work sequence log

Exit criteria:

- Docs are committed and pushed.
- `prepublish_check ok=true`.
- User agrees whether to prototype read-only sensors or continue narrative/docs.

## Phase 1 — Read-only software sensors

Goal: observe the world without acting.

Candidate sensors:

- Git sensor
- Time/session sensor
- Docker/process sensor
- Release sensor
- Filesystem/doc sensor
- Test/prepublish sensor
- Zenn/Notion state sensor
- User intent sensor
- Android Emilia bridge sensor (observe-only candidate)
- DB inventory sensor for reflection/prompt-eval sources (path-only first)

Implementation posture:

- read-only
- metadata-only
- no background daemon initially
- no automatic action
- no raw stdout/stderr persistence
- no secrets or credential-bearing values

Suggested minimal first prototype:

```text
cpos/sensors/git_sensor.py
cpos/sensors/time_session_sensor.py
```

Potential commands:

```bash
PYTHONPATH=. .venv/bin/python -m cpos.sensors.git_sensor --json
PYTHONPATH=. .venv/bin/python -m cpos.sensors.time_session_sensor --json
```

Exit criteria:

- sensor outputs match `kagioneko.sensor_event.v1`
- tests cover no raw secret/diff/output persistence
- no automatic execution or notification

## Phase 2 — Goal Manager MVP

Goal: track goals as user-aligned work items, not self-preservation drives.

Candidate features:

- goal schema
- states: active, paused, blocked, observing, ready_for_review, done, archived
- revisit date
- success criteria
- safety constraints
- explicit confirmation flag

Initial goals to represent:

- `cpos_v0_1_1_final`: paused
- `zenn_cpos_for_agents`: ready_for_review or paused
- `cognitive_agent_os_specs`: active/done
- `neko_late_night_pause`: observing

Implementation posture:

- local JSON or Task Tape metadata event, to be decided
- no scheduler yet
- no autonomous goal pursuit

Exit criteria:

- goals can be listed and updated with explicit user action
- risky goal transitions are review-gated
- wellbeing goals stay advisory

## Phase 3 — World Model snapshot

Goal: provide a compact current-state map.

Facts to track:

- repo state
- release state
- Docker/process state
- Zenn/article draft state
- goal state
- known risks
- memory pointer freshness

Implementation posture:

- build snapshot from sensors and source-of-truth docs
- no raw log storage
- no secret values
- conflict handling marks facts stale rather than overwriting silently

Suggested command:

```bash
PYTHONPATH=. .venv/bin/python -m cpos.world_model snapshot --json
```

Exit criteria:

- answers “what is current?” without reading every handoff/doc
- stale facts are visible
- release/publish decisions still require confirmation

## Phase 4 — Observatory and tape-memory bridge

Goal: make the Cognitive Agent OS resumable and observable.

Observatory bridge:

- ingest selected cognitive events
- timeline view of sensor/goal/review/reflection events
- no raw diff/output/secret bodies

Tape-memory bridge:

- store short pointers only
- update `cpos_resume_latest` or similar after reviewed handoff updates
- keep CPOS Task Tape/docs as source of truth

Exit criteria:

- next session can resume from handoff + tape pointer
- timeline is metadata-only
- stale tape pointers are detected or marked

## Phase 5 — VN-CPU / UNO observe-only bridge

Goal: bring the Docker-running cognitive organism into the architecture safely.

Initial mode:

- observe container status
- read high-level heartbeat/journal status only if safe
- do not exec commands automatically
- do not stop/start container automatically
- do not grant CPOS execution authority to VN-CPU

Potential event types:

- `cognitive_pulse_source_running`
- `organism_heartbeat_observed`
- `organism_journal_summary_available`
- `organism_memory_pressure_warning`

Exit criteria:

- VN-CPU/UNO appears as observed state, not a controller
- no raw private logs or memory dumps are persisted
- user can decide later whether to route summaries through External Agent Adapter or Observatory

## Phase 6 — Limited low-risk autonomy

Goal: only after the read-only layers are stable, allow narrow low-risk automation.

Candidate low-risk tasks:

- create/update summaries
- mark stale docs
- propose next actions
- run non-mutating checks
- draft payloads/articles with `published=false`

Still gated:

- push
- tag
- release/publish
- PR creation
- port opening
- destructive cleanup
- systemd changes
- user management
- `authorized_keys`
- secret handling

Exit criteria:

- clear permission ladder
- Human Escalation integration
- tests for no auto-execute boundary

## Phase 7 — Final release / public narrative follow-through

Goal: turn useful milestones into safe public artifacts.

Possible actions:

- final `v0.1.1` after RC observation
- Zenn “CPOS for Agents” article polish/publish
- Notion “Cognitive Agent OS origin story” page
- architecture article once docs stabilize

Rules:

- final release requires explicit user confirmation
- Zenn publish requires explicit user confirmation
- public claims avoid “completed AGI”
- use “Cognitive Agent OS”, “artificial cognitive runtime”, or “safety-first agent OS” framing

## Recommended immediate next choices

After this roadmap is committed/pushed:

1. Pause and review the docs.
2. Polish the Zenn draft.
3. Create a Notion page for the origin story.
4. Start Phase 1 with a read-only Git sensor prototype.

Recommended: pause/review or Zenn polish before implementation.
