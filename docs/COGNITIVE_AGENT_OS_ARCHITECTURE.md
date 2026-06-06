# Kagioneko Cognitive Agent OS — Architecture Draft

This is an architecture draft for organizing the VPS repo family into a safer Cognitive Agent OS / artificial cognitive runtime.

It is not a claim that the system is AGI. The safer claim is:

> A safety-first cognitive agent runtime for helping a human and multiple AI agents create, remember, reflect, and act without losing control of risky execution.

## Origin story

The repo family makes the most sense when viewed as tools for handling creative overfocus, context loss, late-night momentum, and AI-assisted execution safely.

The goal is not “an AI controls the human”. The goal is:

> 人間の創作衝動とAIの実行力を、壊れないように一緒に走らせるOS。

In this framing, CPOS is the safety kernel, not the whole organism. The other repos provide memory, cognitive pulses, branch thinking, state modeling, observability, immune/security checks, and multi-model orchestration.

## Current building blocks

| Layer | Candidate repos | Role |
|---|---|---|
| Safety kernel | `cpos_defensive_agent` | Review gates, Task Tape, Human Escalation, sandbox/release safety, External Agent Adapter. |
| Memory virtualization | `context-pointer-os` | Context pointers, managed memory registry, virtual memory style context control. |
| Fast resume / compressed memory | `tape-memory-mcp-oss`, `ai-instruction-tape` | Token-light memory pointers, TOA/AIT packets, resume cache. |
| Cognitive pulse / organism core | `ait-next-gen/vn_cpu` | VN-CPU, UNO, heartbeat, metabolism, resonance, fluidic context experiments. Observe-only at first. |
| Branch thinking | `metacognitive-agent-runtime`, `git-driven-cognition` | Candidate futures, risk forecasts, thought graph branches/merges/cherry-picks. |
| State model | `workspace/neurostate-engine`, `neurostate-*` | Synthetic state, EthicsGate, affect-like modulation, user/agent state signals. |
| Observatory | `neurostate-observatory` | Event timelines, traces, packet/state/memory selection observation. |
| Immune/security layer | `ait_firewall`, `ai-red-teaming-engine-v2`, `claude-code-security-kit`, `claude-code-immune`, `nekoguard` | Prompt-injection defense, authority separation, red-team probes, hardening. |
| Multi-model orchestration | `multi-llm-lab` | Claude/Gemini/Codex-style role delegation. |
| Public narrative | `zenn`, Notion docs | External explanation, release notes, origin story, design notes. |

## High-level architecture

```text
User / Goal / Session
        |
        v
+-----------------------+
| Sensor Layer          |  filesystem, git, GitHub, Docker, time, logs, user session
+-----------------------+
        |
        v
+-----------------------+        +-----------------------+
| World Model           | <----> | Goal Manager          |
| current state/risk    |        | active/paused/blocked |
+-----------------------+        +-----------------------+
        |
        v
+-----------------------+
| Metacognitive Layer   |  branch, forecast, critique, select
+-----------------------+
        |
        v
+-----------------------+
| CPOS Safety Kernel    |  Task Tape, Human Escalation, review gates, sandbox
+-----------------------+
        |
        v
+-----------------------+
| Action / Adapter Bus  |  propose, review, run only when allowed
+-----------------------+
        |
        v
+-----------------------+
| Observatory + Memory  |  traces, summaries, tape-memory, handoff docs
+-----------------------+
```

VN-CPU / UNO can sit beside this as a cognitive pulse source. Initially it should be observed, not controlled.

```text
VN-CPU / UNO heartbeat
        |
        v
Sensor event / status summary
        |
        v
CPOS External Agent Adapter or Observatory
        |
        v
metadata-only record, no direct command authority
```

## Missing component 1 — Sensor Layer

The first sensors should be software sensors, not physical sensors.

Candidate sensors:

- `filesystem_changed`: important files changed, new runtime artifacts appeared.
- `git_state_changed`: dirty tree, ahead/behind, new tag, untracked risky file.
- `github_release_state`: draft/prerelease/final release state.
- `docker_process_state`: container running/stopped, image, bind mounts, command.
- `time_session_state`: late-night, long session, post-overtime caution.
- `test_result_state`: latest test/prepublish/release_check summary.
- `docs_state`: handoff/backlog/release notes stale or current.
- `user_session_signal`: user says sleep/pause/ぷす/final/release.

Sensor events must be metadata-only.

Example schema:

```json
{
  "schema": "kagioneko.sensor_event.v1",
  "source": "git",
  "event_type": "git_state_changed",
  "observed_at": "ISO-8601",
  "target": "/home/mayutama/cpos_defensive_agent",
  "summary": "main clean, origin synced",
  "risk": "low",
  "raw_output_stored": false,
  "secret_values_stored": false
}
```

## Missing component 2 — Goal Manager

The Goal Manager tracks long-running goals without turning them into uncontrolled self-preservation drives.

Goal states:

- `active`
- `paused`
- `blocked`
- `observing`
- `ready_for_review`
- `done`

Goal fields:

```json
{
  "schema": "kagioneko.goal.v1",
  "goal_id": "cpos_v0_1_1_final",
  "title": "Decide final v0.1.1 release",
  "state": "paused",
  "priority": "medium",
  "revisit_after": "2026-06-??",
  "success_criteria": ["tests pass", "prepublish ok", "release_check ok", "user explicitly approves final release"],
  "safety_constraints": ["no final tag without confirmation", "no release publish without confirmation"],
  "source_of_truth": ["NEXT_HANDOFF.md", "GITHUB_RELEASE_DRAFT_v0.1.1.md"]
}
```

Wellbeing goals should be advisory and consent-based:

- suggest sleep after late shift + overtime
- add friction before late-night release/tag/publish decisions
- recommend breaks during long sessions
- avoid shame/self-judgment wording
- never frame the system as controlling the user

## Missing component 3 — Self-Evaluation Gate

Self-evaluation should not directly mutate identity, goals, or permissions.

Unsafe loop to avoid:

```text
external prompt -> self-evaluation -> state update -> behavior shift -> more self-evaluation
```

Safer loop:

```text
external prompt
  -> sensor event
  -> self-evaluation proposal
  -> state update proposal
  -> safety/ethics gate
  -> limited state update
  -> audit / observability event
```

Rules:

- Treat self-evaluation as a signal, not truth.
- Do not connect other people's prompts directly to reward or punishment.
- Rate-limit state changes.
- Keep strong state shifts review-gated.
- Detect dependence, self-negation, manipulation, and defensive rationalization patterns.
- Use sleep/consolidation before durable memory updates.

## Missing component 4 — Unified Event Bus / Schema

The repo family needs shared event shapes.

Core event types:

- `sensor_event`
- `goal_update`
- `memory_pointer`
- `state_delta`
- `action_proposal`
- `review_decision`
- `execution_result`
- `reflection_note`
- `sleep_consolidation`

CPOS Task Tape and External Agent Adapter can become the first implementation substrate.

Design constraints:

- Metadata-only by default.
- Raw secrets/diffs/outputs/request bodies are not persisted.
- Action proposals do not imply execution.
- Human Escalation remains the authority for risky operations.

## Missing component 5 — World Model

The world model is the current map of reality for the OS.

It should track:

- repo state
- release state
- Docker/process state
- active drafts/articles
- paused goals
- known risks
- stale memories
- pending decisions
- user session context

It should not store raw private logs or secrets.

Example world-model facts:

- `cpos_v0_1_1_rc1`: prerelease published, final paused.
- `zenn_cpos_for_agents`: draft pushed, `published=false`.
- `vn_cpu_v04_lean`: Docker container running, observe-only.
- `tape_memory_remote_token_incident`: local remote fixed; revoke/rotate recommended.

## Missing component 6 — Sleep / Consolidation

A cognitive OS needs deliberate shutdown and consolidation.

Session-end flow:

```text
user indicates sleep/pause
  -> summarize session
  -> update handoff docs
  -> update tape-memory pointer if approved
  -> mark goals paused/observing
  -> defer risky final decisions
  -> recommend rest
```

Sleep/consolidation jobs can later include:

- stale memory detection
- summary compression
- doc index refresh
- goal revisit scheduling
- dashboard/report snapshot

No background destructive cleanup should run automatically.

## Permission ladder

The OS should use explicit capability levels:

```text
Level 0: observe only
Level 1: summarize / index
Level 2: propose action
Level 3: draft change
Level 4: review required
Level 5: sandbox run with explicit approval
Level 6: limited autonomy for low-risk tasks
Level 7: final release / publish / destructive actions only with explicit user confirmation
```

VN-CPU / UNO should start at Level 0.

External agents should enter through CPOS External Agent Adapter at Levels 1–3 unless explicitly promoted.

## Safety invariants

Always preserve:

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

Additional local rules:

- Secrets/API keys/tokens/SSH keys stay in Vault.
- Never modify `authorized_keys`.
- Do not print cert/key material, `.env`, token values, private runtime logs, or raw JSONL histories.
- Port opening requires explicit confirmation, timed close, and notification.
- Final tags/releases/publishes require explicit user confirmation.

## Roadmap

### Phase 0 — Documentation only

- Keep CPOS `v0.1.1-rc1` paused before final.
- Maintain this architecture draft.
- Keep VN-CPU/UNO observe-only.
- Publish/park Zenn/Notion narrative safely.

### Phase 1 — Software sensors

- Add doc-only sensor schema.
- Prototype read-only sensors for git, Docker, time/session, and release status.
- Route sensor events into CPOS as metadata-only records.

### Phase 2 — Goal Manager

- Add paused/active/blocked goal registry.
- Track revisit dates and explicit confirmation requirements.
- Integrate with handoff and tape-memory pointers.

### Phase 3 — Observatory bridge

- Convert sensor/goal/state events into Observatory traces.
- Keep raw output and secrets out of traces.

### Phase 4 — External cognitive sources

- Let VN-CPU/UNO emit status summaries through an adapter or observe-only sensor.
- No direct execution authority.

### Phase 5 — Limited low-risk autonomy

- Only after stable review: allow narrowly scoped, low-risk autonomous maintenance.
- Keep CPOS gates for push/publish/tag/release/destructive operations.

## Next concrete design doc

If continuing, create:

```text
docs/SENSOR_AND_GOAL_MANAGER_SPEC.md
```

Scope:

- software sensor schemas
- goal registry schema
- permission ladder mapping
- CPOS Task Tape integration
- late-night/wellbeing advisory rules
- no implementation until reviewed
