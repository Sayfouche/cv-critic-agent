# Deployment Plan

CV Critic Agent is split into two deployable surfaces:

- Python FastAPI server: runs the agent and exposes run/report/source endpoints.
- Next.js UI: launches demo runs and visualises agent progress.

## API

Recommended hosts: Render, Fly.io, or Railway.

Install command:

```bash
pip install -e ".[server]"
```

Start command:

```bash
python -m cv_critic_agent --serve --host 0.0.0.0 --port $PORT
```

Environment:

```bash
CV_CRITIC_PROVIDER=mistral
CV_CRITIC_MODEL=mistral-medium-latest
MISTRAL_API_KEY=...
CV_CRITIC_API_TOKEN=...
CV_CRITIC_ALLOWED_ORIGINS=https://your-ui.vercel.app
```

Optional fallback:

```bash
CV_CRITIC_PROVIDER=anthropic
CV_CRITIC_MODEL=claude-haiku-4-5-20251001
ANTHROPIC_API_KEY=...
```

Smoke checks:

```bash
curl https://your-api.example.com/api/health
curl https://your-api.example.com/api/graph
```

Real runs are disabled unless `CV_CRITIC_API_TOKEN` is set. Mock runs stay public for demos.

## UI

Recommended host: Vercel, with root directory set to `ui`.

Build command:

```bash
npm run build
```

Environment:

```bash
NEXT_PUBLIC_API_URL=https://your-api.example.com
```

## Rollout Order

1. Deploy the API and verify `/api/health`.
2. Deploy the UI and verify that a mock run appears in the dashboard.
3. Set `CV_CRITIC_API_TOKEN` and verify that real runs are rejected without the token.
4. Trigger one protected Mistral run through the API.
5. Verify generated files under `reports/latest/` on the API host.

