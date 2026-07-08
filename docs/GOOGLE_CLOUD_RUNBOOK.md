# Google Cloud Runbook for CPOS Engine-Zero

This hackathon submission uses Google Cloud in two practical ways:

1. **Cloud Build validation**: reproducible tests, Docker image build, and CLI demo smoke.
2. **Cloud Run control plane**: public HTTPS surface for `/`, `/health`, and signed `/webhook`.

## Important Cloud Run constraint

Engine-Zero's strongest isolation path runs tests through a Docker sandbox:

- `docker run --network none --cap-drop=ALL ... engine-zero-sandbox:latest`

Cloud Run does not normally provide a Docker daemon inside the service container. Therefore:

- Cloud Run runs the webhook/control-plane container.
- Docker sandbox validation is demonstrated in local Docker or Cloud Build.
- On Cloud Run, sandbox execution remains **fail closed** unless `ENGINE_ZERO_ALLOW_LOCAL_FALLBACK=1` is explicitly set for a reduced-isolation demo.

Do not describe reduced-isolation mode as equivalent to the Docker sandbox.

## Build and validate on Google Cloud

```bash
gcloud builds submit --config cloudbuild.yaml .
```

The build runs:

- Python syntax checks
- AIT Firewall red-team tests
- target app tests
- security tests
- Docker image build
- repeatable CLI demo smoke with explicit reduced-isolation fallback
- Cloud Run container image build and push to Artifact Registry

## Artifact Registry setup

Create the repository once:

```bash
gcloud artifacts repositories create engine-zero \
  --repository-format=docker \
  --location=asia-northeast1 \
  --description="CPOS Engine-Zero hackathon images"
```

## Cloud Run deploy

Recommended public mode requires signed GitHub webhooks:

```bash
gcloud run deploy cpos-engine-zero \
  --image=asia-northeast1-docker.pkg.dev/PROJECT_ID/engine-zero/cpos-engine-zero:COMMIT_SHA \
  --region=asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars=ENGINE_ZERO_REQUIRE_SIGNATURE=1 \
  --set-secrets=GITHUB_WEBHOOK_SECRET=github-webhook-secret:latest
```

Store the webhook secret in Secret Manager; do not commit it:

```bash
echo -n 'REPLACE_WITH_RANDOM_SECRET' | \
  gcloud secrets create github-webhook-secret --data-file=-
```

## Demo-only Cloud Run mode

Only for a live presentation where Docker sandbox is not available inside Cloud Run:

```bash
gcloud run services update cpos-engine-zero \
  --region=asia-northeast1 \
  --set-env-vars=ENGINE_ZERO_ALLOW_LOCAL_FALLBACK=1
```

When using this mode, say clearly: **reduced-isolation demo mode**.

## Smoke checks

```bash
curl https://SERVICE_URL/
curl https://SERVICE_URL/health
```

Expected `/` response includes service metadata and endpoints.
