# Human Escalation Protocol

CPOS uses assisted autonomy: the agent should move quickly when the task is safe,
but ask a human when the next action is risky, ambiguous, or policy-gated.

## Why this is agentic

Human escalation is not a weakness. It is a control surface that lets the agent keep
working without pretending to know things it cannot safely decide alone.

The goal is:

- autonomous for low-risk routine work,
- cautious for medium-risk work,
- human-assisted for destructive, secret-touching, production, network, or GitHub
  publishing actions.

## Escalation triggers

Ask a human before continuing when a task involves:

- secrets, `.env`, tokens, credentials, private keys, or Vault values,
- destructive operations such as deletion, overwrite, hard reset, or force push,
- `authorized_keys` or SSH access changes,
- opening ports or changing exposure,
- production deploys or service stops,
- GitHub publishing,
- low confidence or conflicting context.

## Decision output

Use:

```bash
PYTHONPATH=. .venv/bin/python -m cpos.human_escalation \
  --summary "push release to GitHub" --risk high --json
```

The command returns:

- `requires_human`: whether to stop and ask,
- `severity`: `low`, `medium`, `high`, or `critical`,
- `reasons`: why escalation is needed,
- `recommended_mode`: `safe_autonomy`, `cautious_autonomy`, or `assisted_autonomy`,
- `question` and `options`: human-friendly next step.

It is non-destructive and does not stage, commit, push, delete, open ports, or read
secret values.

## Human request style

When asking for help, the agent should provide:

1. what it wants to do,
2. why it needs approval or clarification,
3. the exact safety concern,
4. the smallest useful choices,
5. a safe default such as replan or stop.

Example:

```text
I need approval before opening a port because network exposure requires a timed
close and notification. Options: approve with constraints, request more context,
or reject/replan.
```


## Review Queue / Dashboard Integration

Review pipelines can embed a metadata-only `human_escalation` decision in their
Task Tape `review_required` payload. The aggregate queue is exposed at:

```bash
curl https://<host>/human-escalations
```

Current queue sources include:

- GitHub PR dry-run reviews,
- GitHub diff reviews,
- MCP execution and capability-probe reviews,
- sandbox patch plans,
- sandbox execution reviews,
- sandbox retry reviews.

The queue stores only review metadata: task ID, review type, severity, reasons,
recommended mode, safe-autonomy flag, and owning approve/reject endpoint hints. It
must not store secret values, raw request bodies, raw diff text, raw stdout/stderr,
checkpoint contents, raw handoff bodies, or proposed code blobs.

Dashboard approve/reject buttons call the owning pipeline endpoint instead of
creating a parallel approval authority. A GitHub PR dry-run approval still only
unlocks the next review stage; it does not create branches, commits, pushes, or PRs.
Sandbox approvals likewise remain metadata-only until the explicitly approved
isolated execution endpoint is called.
