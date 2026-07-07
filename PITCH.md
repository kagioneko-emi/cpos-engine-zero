# 🛡️ CPOS Engine-Zero: Defensive Agent Runtime
> **"Autonomous execution power, without hidden side effects."**

---

## 1. The Core Problem: Agent Power Without Operator Trust
AI coding agents are getting fast enough to plan, edit, run, and recover. But the common failure mode is still the same:

1. **Unsafe write power**: an agent that can silently patch, commit, push, or open PRs can create outages faster than humans can audit them.
2. **Context decay**: long repositories and long sessions create prompt bloat, stale handoffs, and expensive re-discovery.
3. **Weak failure lineage**: when a sandbox run fails, many systems show logs but do not turn failure metadata into a governed next-step pipeline.
4. **Demo opacity**: it is hard to prove what the agent did *not* do: no raw secrets, no raw stdout, no live repo mutation, no hidden publish.

---

## 2. Our Solution: CPOS Engine-Zero
**CPOS Engine-Zero** is a defensive runtime for safe autonomous development. It gives agents a deep repair loop—plan, review, sandbox, observe, replan, generate, validate, and prepare the next run—while keeping execution power separated from approval.

### The current engine loop

1. **Fast Resume**
   - `NEXT_HANDOFF.md` starts with a 10-line resume card.
   - `tape-memory-mcp` keeps a token-light compressed resume cache for quick context reload.
2. **Human Escalation Queue**
   - Risky stages expose owning review/approve/reject endpoints through one queue.
   - It does not become a second approval authority; it routes back to the real pipeline.
3. **Patch Generation Review**
   - Failure metadata can become an Auto Fix Candidate and a review-gated Patch Generation Review.
   - Generated diff text is transient input only.
4. **Validation Harness**
   - Generated patches can be checked with `git apply --check` in an ephemeral workspace.
   - Stores only hashes, sizes, counters, statuses, and lineage.
5. **Safe Advance → Ready-to-Run Gate**
   - Approved/generated patch metadata can advance to a pending Sandbox Execution Review.
   - The final run still requires explicit human approval and transient supplied diff text.
6. **Sandbox Flow Graph + Report**
   - Failed execution → retry review → replan template → auto fix candidate → patch generation / diff draft → ready-to-run gate is visible in dashboard and generated report.

---

## 3. Technical Moats

- **Metadata-only persistence**: raw diffs, raw stdout/stderr, request bodies, checkpoint contents, raw handoff bodies, and secrets are excluded from persistent Task Tape/dashboard/report surfaces.
- **Approval separated from execution**: CPOS can prepare a ready-to-run review, but it does not approve execution, run commands, patch the live repo, commit, push, or create PRs automatically.
- **Human Escalation as first-class control plane**: GitHub, MCP, sandbox plan, patch generation, sandbox execution, retry, and ready-to-run gates are visible through one assisted-autonomy queue.
- **Fast resume without prompt bloat**: compressed `tape-memory-mcp` keys summarize the current state; detailed `NEXT_HANDOFF.md` remains the source of context depth.
- **Competitive Demo Readiness**: `GET /demo/readiness` shows whether Fast Resume, Human Escalation, Patch Generation, Validation Harness, Ready-to-Run Gate, Flow Graph, and Report are demo-ready.
- **Metadata-only demo fixture**: `POST /demo/fixture` creates safe demo data for screenshots without executing tools or storing raw values.
- **Tamper-evident governance**: hash-chain integrity, security profile validation, prepublish checks, and secret scanning are part of the release path.

### Positioning vs. Hermes / OpenClaw / Claude Code-style agents

CPOS is not trying to win by granting unrestricted write power. The bet is **safer-by-design execution depth**: comparable autonomous workflow breadth, but with stronger auditability, explicit approval boundaries, sandbox-first execution, metadata-only persistence, and failure-to-replan lineage.

That makes CPOS especially strong for defensive, regulated, or team-operated environments where the question is not only “can the agent fix it?” but also “can we prove what it did and did not do?”

---

## 4. The Demo: Competitive Safe Autonomy Loop

### One-command readiness view

```bash
curl https://<host>/demo/readiness
```

This returns a metadata-only readiness snapshot for:

- Fast Resume / tape-memory cache
- MCP-reviewed Tape Memory connector
- Human Escalation Queue
- Patch Generation Review
- Generated patch validation harness
- Ready-to-Run Execution Gate
- Sandbox Flow Graph
- Report Snapshot

### Metadata-only fixture for screenshots

```bash
curl -X POST https://<host>/demo/fixture \
  -d '{"confirm":true,"reason":"demo_capture"}'
```

The fixture creates a full safe-loop demo chain in Task Tape: failed execution metadata, retry/replan, auto fix candidate, patch generation review, diff draft, ready-to-run execution review, and flow graph nodes. It does **not** run tools, apply patches, mutate the live repo, commit, push, create PRs, or store raw diffs/outputs.

### Dashboard/report story

1. **Competitive Demo Readiness**: prove all safe-loop stages are present.
2. **Human Escalation Queue**: show approval routing and metadata-only safety posture.
3. **Patch Generation Reviews**: show generated-patch path without raw diff persistence.
4. **Ready-to-Run Execution Reviews**: show final explicit human run gate.
5. **Sandbox Flow Graph**: show lineage from failure to next attempt.
6. **Generated Report**: export static evidence with safety flags.

---

## 5. Future Vision: The Defensive Agent OS
Engine-Zero is a step toward a **defensive execution OS** for AI agents: more autonomy without less accountability. Agents should improve through failure metadata, governed memory, and operator-approved execution—not hidden side effects.

---

### 🚀 Technical Stack
- **AI Runtime**: CPOS + Context Pointers + Task Tape
- **Fast Resume**: `NEXT_HANDOFF.md` resume card + `tape-memory-mcp` compressed keys
- **Safety Gates**: Human Escalation Queue, review approvals, ready-to-run gate, prepublish guard, secret scan
- **Execution**: Docker/ephemeral sandbox, validation harness, allowlisted commands
- **Observability**: Competitive Demo Readiness, Execution Scoreboard, Sandbox Flow Graph, report snapshot
- **Security**: Hash-chain integrity, HMAC auth support, Vault-first secret handling policy

---
**Kagioneko (2026) | DevOps x AI Agent Hackathon**
