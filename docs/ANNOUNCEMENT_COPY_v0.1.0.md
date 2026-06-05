# CPOS Engine-Zero v0.1.0 — Announcement Copy Pack

Reusable post-release copy for CPOS Engine-Zero v0.1.0.

Use this as a source of truth for social posts, Discord updates, README blurbs, Notion summaries, and follow-up articles. Keep the tone grounded: CPOS is a defensive, review-gated, metadata-only runtime/safety layer for safer AI-agent autonomy. It is not an unrestricted auto-execution agent.

## Canonical links

- GitHub Release: https://github.com/kagioneko/cpos-engine-zero/releases/tag/v0.1.0
- Repository: https://github.com/kagioneko/cpos-engine-zero
- Zenn article: https://zenn.dev/kagioneko/articles/cpos-engine-zero-v010
- Notion summary: https://app.notion.com/p/CPOS-Engine-Zero-v0-1-0-Notion-37676d12b6d2812ea817daf2ed8017c7
- 5-minute external-agent guide: `docs/EXTERNAL_AGENT_5_MIN_GUIDE.md`
- Adapter integration guide: `docs/AGENT_ADAPTER_INTEGRATION.md`
- Adapter schema: `docs/AGENT_ADAPTER_SCHEMA.md`

## Positioning baseline

### CPOS is

- a defensive AI-agent runtime for safer autonomy
- a memory-governed execution and review layer
- review-gated and sandbox-first
- metadata-only by design for sensitive execution evidence
- compatible with external agents through the External Agent Adapter
- useful as “CPOS for Agents”: a safety/governance layer beside Codex-like, Hermes-like, or OpenClaw-like systems

### CPOS is not

- an unrestricted fully autonomous coding agent
- a remote command executor for external agents
- a tool that silently patches live repositories
- a system that stores raw diffs, raw stdout/stderr, request bodies, or secrets
- a bypass for human approval on risky actions
- a deployment automation system that opens ports, pushes, publishes, or creates PRs by default

## Short X / social posts

### Option A — release announcement

CPOS Engine-Zero v0.1.0 is released.

A defensive, memory-governed AI-agent runtime for safer autonomy:
review-gated, sandbox-first, metadata-only, and ready to sit beside external agents as a safety layer.

Release:
https://github.com/kagioneko/cpos-engine-zero/releases/tag/v0.1.0

### Option B — CPOS for Agents

CPOS Engine-Zero can now act as “CPOS for Agents”.

External agents can submit command plans, proposed diffs, and redacted execution results. CPOS stores metadata-only contracts, routes risky actions to Human Escalation, and never auto-executes external commands.

https://github.com/kagioneko/cpos-engine-zero

### Option C — safety posture

The core CPOS idea:

AI agents should have memory and execution power, but risky actions need review gates, sandbox-first flow, and metadata-only evidence.

CPOS Engine-Zero v0.1.0 is the first official release of that defensive runtime.

https://github.com/kagioneko/cpos-engine-zero/releases/tag/v0.1.0

### Option D — article link

I published a CPOS Engine-Zero v0.1.0 write-up.

It covers the release, the safety posture, and how CPOS can govern external agents without storing raw outputs or auto-executing commands.

https://zenn.dev/kagioneko/articles/cpos-engine-zero-v010

## Discord / community update

CPOS Engine-Zero v0.1.0 is officially released.

It is a defensive AI-agent runtime focused on safer autonomy rather than unrestricted auto-execution.

Key points:

- review-gated execution flow
- sandbox-first posture
- Task Tape / checkpoint evidence
- metadata-only persistence for sensitive execution evidence
- Human Escalation for risky operations
- External Agent Adapter for Codex-like, Hermes-like, or OpenClaw-like agents
- payload examples and a 5-minute local guide for “CPOS for Agents” use cases

What it does not do:

- does not silently patch live repositories
- does not store raw diffs or raw stdout/stderr
- does not store secrets
- does not execute external-agent commands automatically
- does not push, publish, create PRs, or open ports by default

Release:
https://github.com/kagioneko/cpos-engine-zero/releases/tag/v0.1.0

Zenn:
https://zenn.dev/kagioneko/articles/cpos-engine-zero-v010

## GitHub / README short blurb

CPOS Engine-Zero is a defensive, memory-governed AI-agent runtime for safer autonomy. It combines review-gated execution, sandbox-first flow, Task Tape evidence, Human Escalation, and metadata-only persistence. Through the External Agent Adapter, CPOS can also sit beside other agents as a safety/governance layer for command plans, proposed diffs, and redacted execution result summaries.

## Notion summary intro

CPOS Engine-Zero v0.1.0 is the first official release of a defensive AI-agent runtime designed for safer autonomy.

The release focuses on a safety-first execution posture: risky operations are routed through review gates, execution evidence is stored as metadata/hashes/counters rather than raw diffs or raw stdout/stderr, and external agents can be governed through a metadata-only adapter rather than being allowed to execute through CPOS directly.

## Longer announcement

CPOS Engine-Zero v0.1.0 has been released.

The project is a defensive, memory-governed AI-agent runtime built around the idea that autonomy should be observable, reviewable, and safe by default. Instead of giving an agent unrestricted write and execution power, CPOS separates proposal, review, execution evidence, and follow-up planning.

The v0.1.0 posture includes:

- review-gated execution and Human Escalation
- sandbox-first execution flow
- Task Tape and checkpoint-based lineage
- metadata-only storage for sensitive execution evidence
- no raw diff or raw stdout/stderr persistence
- release/publish safety checks
- External Agent Adapter for “CPOS for Agents” integrations

The External Agent Adapter lets another agent submit metadata-rich action contracts or redacted execution result summaries. CPOS records hashes, sizes, counters, review status, and safety flags, then routes risky actions into Human Escalation. It does not run commands for the external agent.

This makes CPOS useful both as its own defensive runtime and as a governance layer beside other agent systems.

## External Agent Safety Layer copy

CPOS can sit beside existing agent systems as an external safety layer.

An external agent can submit:

- intent metadata
- command request contracts
- proposed diff contracts
- redacted execution result summaries

CPOS then provides:

- schema validation
- metadata-only Task Tape evidence
- Human Escalation routing
- review and rejection endpoints
- execution result scoreboard
- safety invariants such as `execute_automatically=false`

The adapter is intentionally not a command runner. It is a governance boundary.

## Do-not-claim list

Avoid these claims unless future work explicitly implements and verifies them:

- “fully autonomous unrestricted coding agent”
- “automatically patches production safely”
- “executes external agent commands”
- “guarantees security”
- “prevents all secret leaks”
- “production deployment automation”
- “opens ports automatically”
- “pushes/publishes/creates PRs automatically”

Prefer these safer phrases:

- “defensive runtime”
- “review-gated”
- “sandbox-first”
- “metadata-only evidence”
- “Human Escalation for risky operations”
- “external-agent safety/governance layer”
- “does not auto-execute external commands”

## Japanese short copy

CPOS Engine-Zero v0.1.0 を正式リリースしました。

安全な自律実行を目指した、防御型・メモリ統治型のAIエージェントランタイムです。レビューゲート、サンドボックス優先、メタデータのみ保存、Human Escalation、External Agent Adapter を備えています。

https://github.com/kagioneko/cpos-engine-zero/releases/tag/v0.1.0

## Japanese “CPOS for Agents” copy

CPOS は “CPOS for Agents” として、外部エージェントの横に置く安全レイヤーにもできます。

外部エージェントは command request / proposed diff / redacted execution result を CPOS に送信し、CPOS は raw output や秘密情報を保存せず、メタデータのみの契約として記録し、危険操作を Human Escalation に回します。

## Hashtag / keyword pool

Use sparingly:

- AI agents
- safe autonomy
- defensive runtime
- Human Escalation
- sandbox-first
- metadata-only
- agent governance
- CPOS for Agents
