# CPOS Engine-Zero — Hackathon Submission Summary

## One-liner

CPOS Engine-Zero is a zero-trust DevOps runtime for safely executing AI/autonomous code-fix cycles through AIT Firewall input separation, disposable workspaces, Docker sandbox validation, malware scanning, and atomic deploy.

## What to demo

```bash
python3 engine_zero_cli.py demo
```

The CLI creates a fresh buggy sample app, applies a deterministic demo fix for division-by-zero handling, validates it inside a locked-down Docker sandbox, and atomically deploys the verified result.

## Google Cloud collaboration

- `cloudbuild.yaml` runs reproducible tests and Docker validation on Google Cloud Build.
- The container can be deployed to Cloud Run as a signed webhook/control-plane surface.
- Cloud Run does not normally provide Docker-in-Docker, so Docker sandbox validation is demonstrated in Cloud Build/local Docker while Cloud Run remains fail-closed by default.

## Why it matters

The core contribution is not a magic universal bug fixer. It is the safety runtime around AI/autonomous fixes: isolate untrusted context, test changes in a constrained sandbox, discard failures, and only deploy verified outputs.

## Links

- GitHub: https://github.com/kagioneko-emi/cpos-engine-zero
- Demo video: https://www.youtube.com/watch?v=k8KWmq11De8
