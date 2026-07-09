# CPOS Engine-Zero — Hackathon Submission Summary

## One-liner

CPOS Engine-Zero is a zero-trust DevOps runtime for safely executing Gemini/AI-generated code-fix cycles through AIT Firewall input separation, disposable workspaces, Docker sandbox validation, malware scanning, and atomic deploy.


## Google Cloud AI / Gemini usage

- `agents/architect_gemini.py` connects Gemini CLI as an AI architect adapter for test generation and code-fix proposal generation.
- Engine-Zero intentionally does not trust AI output directly. It treats Gemini/AI output as an untrusted candidate change, then validates it through isolation, scanning, sandbox tests, and atomic deploy.
- The repeatable judge demo uses a deterministic division-by-zero fixture so reviewers can reproduce the full safety pipeline without depending on model variability.

## What to demo

```bash
python3 engine_zero_cli.py demo
```

The CLI creates a fresh buggy sample app, applies a deterministic demo fix for division-by-zero handling, validates it inside a locked-down Docker sandbox, and atomically deploys the verified result.

## Google Cloud collaboration

- Gemini is used as the intended AI code-fix generator layer through `agents/architect_gemini.py`.
- `cloudbuild.yaml` runs reproducible tests and Docker validation on Google Cloud Build.
- The container can be deployed to Cloud Run as a signed webhook/control-plane surface.
- Cloud Run does not normally provide Docker-in-Docker, so Docker sandbox validation is demonstrated in Cloud Build/local Docker while Cloud Run remains fail-closed by default.

## Why it matters

The core contribution is not a magic universal bug fixer. It is the safety runtime around AI/autonomous fixes: isolate untrusted context, test changes in a constrained sandbox, discard failures, and only deploy verified outputs.

## Links

- GitHub: https://github.com/kagioneko-emi/cpos-engine-zero
- Demo video: https://www.youtube.com/watch?v=4SAGBobBjiY
- ProtoPedia draft: `docs/PROTOPEDIA_SUBMISSION.md`

## Verified deployment

- Cloud Build ID: `04fe2b94-f43f-4336-81ff-8d6ad32af4d7` — SUCCESS
- Cloud Run URL: https://cpos-engine-zero-951178130166.asia-northeast1.run.app
- Container image: `asia-northeast1-docker.pkg.dev/engine-zero-hackathon-2026/engine-zero/cpos-engine-zero:04fe2b94-f43f-4336-81ff-8d6ad32af4d7`
