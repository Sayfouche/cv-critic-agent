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

Delivered:

- Landing page with mock run launcher.
- Run dashboard with SSE replay.
- Live Agent Graph showing Global Critic, Printable CV Critic, and Strategy Agent lifecycle.
- Side panel with event log, report previews, and source snapshots.
- API client wired to `/api/runs`, `/api/runs/{id}/events`, `/api/runs/{id}/reports/{slug}`, and `/api/sources`.

Deployment target:

- UI on Vercel.
- API on Render, Fly.io, or Railway.
- `NEXT_PUBLIC_API_URL` points to the deployed FastAPI base URL.
