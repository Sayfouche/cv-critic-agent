# CV Critic Agent UI

Next.js dashboard for launching and visualising CV Critic Agent runs.

## Development

Start the Python API first:

```bash
cd ..
source .venv/bin/activate
python -m cv_critic_agent --serve --port 8000
```

Then run the UI:

```bash
cp .env.local.example .env.local
npm run dev
```

Open http://localhost:3000.

## Environment

`NEXT_PUBLIC_API_URL` points the browser client to the FastAPI server.

Mock runs are public. Real runs require the API token configured on the Python server.

## Phase 3 Scope

Commit 1 adds the UI shell, landing page, API client, mock run launcher, and run route placeholder.

Next commits add the live SSE agent graph, source/report panels, and deployment configuration.
